/**
 * v8.4.3: Offline Activepieces callFlow reference validator.
 * Accepts a manually exported REDACTED metadata snapshot. Never contacts providers,
 * calls an AI model, reads secrets, publishes or mutates an Activepieces flow.
 */
import { readFileSync } from 'node:fs';

const idPattern = /^[a-zA-Z0-9_-]{10,64}$/;
export function validateRoute(snapshot) {
  const flowList=Array.isArray(snapshot?.flows)?snapshot.flows:[];
  const caller=snapshot?.caller;
  const refs = flowList.filter(f=>f && typeof f.id==='string');
  const ids = new Set(refs.map(f=>f.id));
  const diagnostics=[];
  if(!caller || !idPattern.test(caller.flowId??'')) {
    diagnostics.push({code:'CALLER_ID_MISSING',severity:'ERROR'});
  }
  if(!idPattern.test(caller?.targetFlowId??'')) {
    diagnostics.push({code:'TARGET_ID_MISSING_OR_INVALID',severity:'ERROR'});
  }else if(!ids.has(caller.targetFlowId)) {
    diagnostics.push({code:'TARGET_FLOW_NOT_FOUND',severity:'ERROR',source_flow_id:caller.flowId,target_flow_id:caller.targetFlowId});
  } else {
    const target=refs.find(f=>f.id===caller.targetFlowId);
    if(target.status!=='ENABLED'||target.published!==true) {
      diagnostics.push({code:'TARGET_NOT_PUBLISHED_OR_ENABLED',severity:'ERROR',target_flow_id:caller.targetFlowId});
    }
  }
  if(caller?.expectedEngineId&&caller.expectedEngineId!==caller.targetFlowId) {
    diagnostics.push({code:'TARGET_DIFFERS_FROM_DESIGNATED_ENGINE',severity:'ERROR',expected_engine_id:caller.expectedEngineId,actual_target_id:caller.targetFlowId});
  }
  if((snapshot?.historicalWebhookAuthFailures??0)>0) {
    diagnostics.push({code:'WEBHOOK_AUTH_FAILURES_OBSERVED',severity:'WARNING',count:snapshot.historicalWebhookAuthFailures});
  }
  return {
    type:'OFFLINE_AP_FLOW_REFERENCE_AUDIT',
    verdict:diagnostics.some(x=>x.severity==='ERROR')?'FAIL':'PASS',
    diagnostics,
    provider_snapshot_live:false,
    global_chat_hook_proven:false,
    actual_chatgpt_message_trigger_proven:false,
    ai_model_calls:0,
    provider_write_calls:0,
  };
}
if(process.argv[1] && import.meta.url===new URL('file://'+process.argv[1]).href){
  if(process.argv.length!==3){console.error('USAGE: node ap_callflow_guard_v843.mjs snapshot.json');process.exitCode=2;}
  else {
    try{
      const obj=JSON.parse(readFileSync(process.argv[2],'utf8'));
      const result=validateRoute(obj);
      console.log('AP_V843_RESULT='+JSON.stringify(result));
      if(result.verdict!=='PASS')process.exitCode=1;
    }catch{console.error('SNAPSHOT_NOT_PARSEABLE');process.exitCode=2;}
  }
}
