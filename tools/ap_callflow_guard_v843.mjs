/**
 * v8.4.3: Offline Activepieces callable-dropdown reference guard.
 *
 * IMPORTANT: Activepieces internal flow IDs from ap_list_flows may differ from
 * the EXTERNAL option values returned by ap_resolve_property_options("flowId").
 * Only the dynamic Call Flow dropdown is authoritative for callFlow input.
 *
 * Accepts manually exported redacted metadata; never sends a webhook,
 * publishes/edits a provider flow, uses credentials or invokes models.
 */
import {readFileSync} from 'node:fs';

const idPattern=/^[A-Za-z0-9_-]{10,64}$/;
const validId=x=>typeof x==='string'&&idPattern.test(x);
export function validateRoute(snapshot){
 const caller=snapshot?.caller??{};
 const options=Array.isArray(snapshot?.callableOptions)?snapshot.callableOptions:null;
 const diagnostics=[];
 if(!validId(caller.flowId)){
   diagnostics.push({code:'CALLER_ID_INVALID',severity:'ERROR'});
 }
 if(!validId(caller.targetFlowId)){
   diagnostics.push({code:'TARGET_VALUE_INVALID',severity:'ERROR'});
 }
 if(!options){
   diagnostics.push({code:'DYNAMIC_DROPDOWN_UNAVAILABLE',severity:'UNVERIFIED'});
 }else if(validId(caller.targetFlowId)){
   const selected=options.find(o=>o && validId(o.value) && o.value===caller.targetFlowId);
   if(!selected){
     diagnostics.push({code:'TARGET_NOT_IN_CALLFLOW_DROPDOWN',severity:'ERROR'});
   }else{
     const label=typeof selected.label==='string'?selected.label:'';
     if(/\(inactive\)\s*$/i.test(label)||selected.disabled===true){
       diagnostics.push({code:'TARGET_OPTION_INACTIVE',severity:'ERROR'});
     }
     if(typeof caller.expectedEngineLabel==='string' && caller.expectedEngineLabel.trim() &&
        label!==caller.expectedEngineLabel){
       diagnostics.push({code:'TARGET_LABEL_MISMATCH',severity:'ERROR'});
     }
   }
 }
 const authFailures=Number.isSafeInteger(snapshot?.historicalWebhookAuthFailures)
     && snapshot.historicalWebhookAuthFailures>0
       ?Math.min(snapshot.historicalWebhookAuthFailures,100000):0;
 if(authFailures){
   diagnostics.push({code:'HISTORICAL_WEBHOOK_AUTH_FAILURES',severity:'WARNING',count:authFailures});
 }
 const verdict=diagnostics.some(x=>x.severity==='ERROR')?'FAIL'
   :diagnostics.some(x=>x.severity==='UNVERIFIED')?'UNVERIFIED':'PASS';
 return {
   type:'OFFLINE_AP_CALLFLOW_DROPDOWN_GUARD',
   verdict,diagnostics,
   source_metadata_authority:'EXPORTED_DYNAMIC_DROPDOWN_VALUES',
   internal_flow_id_equivalence_assumed:false,
   provider_snapshot_live:false,
   published_runtime_execution_proven:false,
   global_chat_hook_proven:false,
   actual_chatgpt_message_trigger_proven:false,
   ai_model_calls:0,
   provider_write_calls:0
 };
}

/**
 * Classify run observations without interpreting past auth rejections as a
 * current outage or inferring ChatGPT-native composer/webhook integration.
 * Caller supplies redacted run summaries and a fixed observation timestamp.
 */
export function classifyWebhookHistory({runs,asOfIso,windowHours=24,headerAuthConfigured}={}){
  const asOf=Date.parse(asOfIso??'');
  if(!Number.isFinite(asOf)||!Number.isFinite(windowHours)||windowHours<=0||windowHours>168){
    return {state:'INVALID_WINDOW_OR_OBSERVATION',verdict:'UNVERIFIED',native_chat_trigger_verified:false};
  }
  if(!Array.isArray(runs)){
    return {state:'NO_RUN_EVIDENCE',verdict:'UNVERIFIED',native_chat_trigger_verified:false};
  }
  const safe=runs.map(r=>{
    const time=Date.parse(r?.created??'');
    if(!Number.isFinite(time)||time>asOf+60000||time<0||!['FAILED','SUCCEEDED'].includes(r?.status)){
      return null;
    }
    return {time,status:r.status,
      error_code:['WEBHOOK_HEADER_AUTH_REJECTED','CALLFLOW_RUNTIME_TARGET_NOT_FOUND'].includes(r?.error_code)?r.error_code:null};
  });
  if(safe.some(x=>x===null)){
    return {state:'INVALID_RUN_METADATA',verdict:'UNVERIFIED',native_chat_trigger_verified:false};
  }
  if(safe.length===0){
    return {state:'NO_RUN_EVIDENCE',verdict:'UNVERIFIED',native_chat_trigger_verified:false};
  }
  const sorted=[...safe].sort((a,b)=>b.time-a.time);
  const latest=sorted[0];
  const ageMs=asOf-latest.time;
  const fresh=ageMs>=0 && ageMs<=windowHours*3600000;
  const historicalAuthRejections=safe.filter(x=>x.error_code==='WEBHOOK_HEADER_AUTH_REJECTED').length;
  const historicalSubflowFailures=safe.filter(x=>x.error_code==='CALLFLOW_RUNTIME_TARGET_NOT_FOUND').length;
  return {
    state:!fresh?'HISTORICAL_RUNS_ONLY'
       :latest.status==='SUCCEEDED'?'RECENT_ACTIVEPIECES_ENTRY_SUCCEEDED':'RECENT_ACTIVEPIECES_ENTRY_FAILED',
    verdict:!fresh?'UNVERIFIED':latest.status==='SUCCEEDED'?'PASS_AP_ENTRY_ONLY':'FAIL_AP_ENTRY',
    newest_run_iso:new Date(latest.time).toISOString(),
    age_hours:Math.floor(Math.max(0,ageMs)/3600000),
    historical_auth_rejections:historicalAuthRejections,
    historical_subflow_failures:historicalSubflowFailures,
    header_auth_configured:headerAuthConfigured===true,
    auth_rejection_is_definitive_misconfiguration:false,
    runtime_recovery_verified:false,
    native_chat_trigger_verified:false,
    credential_values_inspected:false,
    provider_calls:0
  };
}

if(process.argv[1] && import.meta.url===new URL('file://'+process.argv[1]).href){
 if(process.argv.length!==3){console.error('USAGE: node ap_callflow_guard_v843.mjs redacted-snapshot.json');process.exitCode=2;}
 else {
   try{
     const input=JSON.parse(readFileSync(process.argv[2],'utf8'));
     const result=validateRoute(input);
     console.log('AP_V843_RESULT='+JSON.stringify(result));
     if(result.verdict!=='PASS')process.exitCode=1;
   }catch{console.error('SNAPSHOT_NOT_PARSEABLE');process.exitCode=2;}
 }
}
