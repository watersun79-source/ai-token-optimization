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
 // The dropdown proves only the selected *target*. Verify the caller
 // is present and published in the independently supplied project inventory.
 const flows=Array.isArray(snapshot?.flows)?snapshot.flows:null;
 if(validId(caller.flowId)){
   if(!flows){
     diagnostics.push({code:'CALLER_FLOW_LIST_UNAVAILABLE',severity:'UNVERIFIED'});
   }else{
     const entry=flows.find(f=>f&&f.id===caller.flowId);
     if(!entry){
       diagnostics.push({code:'CALLER_NOT_IN_PROJECT',severity:'ERROR'});
     }else{
       if(entry.status==='DISABLED')diagnostics.push({code:'CALLER_FLOW_DISABLED',severity:'ERROR'});
       else if(entry.status!=='ENABLED')diagnostics.push({code:'CALLER_STATUS_UNVERIFIED',severity:'UNVERIFIED'});
       if(entry.published===false)diagnostics.push({code:'CALLER_FLOW_UNPUBLISHED',severity:'ERROR'});
       else if(entry.published!==true)diagnostics.push({code:'CALLER_PUBLISH_UNVERIFIED',severity:'UNVERIFIED'});
       // A callable or scheduled flow cannot stand in for the protected webhook entry.
       // Missing trigger metadata is inconclusive, not proof of webhook readiness.
       if(entry.triggerType==null)diagnostics.push({code:'CALLER_TRIGGER_UNVERIFIED',severity:'UNVERIFIED'});
       else if(entry.triggerType!=='@activepieces/piece-webhook')diagnostics.push({code:'CALLER_NOT_WEBHOOK_TRIGGER',severity:'ERROR'});
     }
   }
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
export function classifyWebhookHistory({runs,asOfIso,windowHours=24,headerAuthConfigured,expectedFlowId}={}){
  const asOf=Date.parse(asOfIso??'');
  if(!Number.isFinite(asOf)||!Number.isFinite(windowHours)||windowHours<=0||windowHours>168){
    return {state:'INVALID_WINDOW_OR_OBSERVATION',verdict:'UNVERIFIED',native_chat_trigger_verified:false};
  }
  if(!Array.isArray(runs)){
    return {state:'NO_RUN_EVIDENCE',verdict:'UNVERIFIED',native_chat_trigger_verified:false};
  }
  if(!validId(expectedFlowId)){
    return {state:'EXPECTED_ENTRY_FLOW_MISSING',verdict:'UNVERIFIED',native_chat_trigger_verified:false};
  }
  // Only official production runs from the intended webhook entry are admissible.
  // A successful TESTING run or another engine must never prove this entry live.
  const safe=runs.map(r=>{
    const time=Date.parse(r?.created??'');
    if(r?.environment!=='PRODUCTION'||r?.flowId!==expectedFlowId||
       !Number.isFinite(time)||time>asOf+60000||time<0||!['FAILED','SUCCEEDED'].includes(r?.status)){
      return null;
    }
    return {time,status:r.status,
      error_code:['WEBHOOK_HEADER_AUTH_REJECTED','CALLFLOW_RUNTIME_TARGET_NOT_FOUND'].includes(r?.error_code)?r.error_code:null};
  });
  if(safe.some(x=>x===null)){
    return {state:'INVALID_RUN_PROVENANCE',verdict:'UNVERIFIED',native_chat_trigger_verified:false};
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
    production_entry_provenance_verified:true,
    native_chat_trigger_verified:false,
    credential_values_inspected:false,
    provider_calls:0
  };
}


/**
 * Interpret the :30 gap-recovery flow without treating SUCCEEDED/SKIP as dispatch.
 * Only trustworthy metadata (run identity, environment, step names/statuses) is used.
 * Even a successful dispatch step does not independently prove a GitHub run or Slack post.
 */
export function classifyGapRecoveryRun({run,expectedFlowId}={}){
 const neutral=(state)=>({
  state,verdict:'UNVERIFIED',github_dispatch_step_succeeded:false,
  slack_post_step_succeeded:false,github_run_verified:false,
  slack_message_verified:false,native_chatgpt_run_verified:false,model_calls:0
 });
 if(!validId(expectedFlowId)||!run||run.flowId!==expectedFlowId||
    run.environment!=='PRODUCTION'||!validId(run.id)){
   return neutral('UNTRUSTED_RUN_PROVENANCE');
 }
 if(!['SUCCEEDED','FAILED'].includes(run.status)||!Array.isArray(run.steps)||
    !run.steps.length||run.steps.some(s=>!s||typeof s.name!=='string'||
    !/^trigger$|^step_[1-9]\d*$/.test(s.name)||!['SUCCEEDED','FAILED','SKIPPED'].includes(s.status))){
   return neutral('INVALID_RUN_OR_STEPS');
 }
 const stepNames=run.steps.map(s=>s.name);
 if(new Set(stepNames).size!==stepNames.length)return neutral('AMBIGUOUS_DUPLICATE_STEPS');
 if(run.status==='FAILED')return neutral('ACTIVEPIECES_FLOW_FAILED');
 const paths=new Map(run.steps.map(s=>[s.name,s.status]));
 const core=['trigger','step_1','step_2','step_3'].every(n=>paths.get(n)==='SUCCEEDED');
 if(!core)return neutral('CORE_STEPS_NOT_VERIFIED');
 const skip=paths.get('step_8')==='SUCCEEDED';
 const dispatched=['step_4','step_5','step_6','step_7'].every(n=>paths.get(n)==='SUCCEEDED');
 if(skip&& !['step_4','step_5','step_6','step_7'].some(n=>paths.has(n)) &&
    run.steps.length===5){
   return {...neutral('SKIPPED_DUPLICATE_DISPATCH'),verdict:'SKIP_AP_NO_DISPATCH'};
 }
 if(dispatched&&!paths.has('step_8')&&run.steps.length===8){
   return {
    ...neutral('RECOVERY_AND_SLACK_STEPS_SUCCEEDED'),
    verdict:'PASS_AP_STEPS_ONLY',github_dispatch_step_succeeded:true,
    slack_post_step_succeeded:true
   };
 }
 return neutral('MIXED_OR_INCOMPLETE_ROUTE');
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
