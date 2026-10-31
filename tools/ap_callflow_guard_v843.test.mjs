import test from 'node:test';
import assert from 'node:assert/strict';
import {validateRoute} from './ap_callflow_guard_v843.mjs';

// Redacted connected-source snapshot: list_flows internal IDs differ from
// ap_resolve_property_options("flowId") external option IDs.
const actual=()=>({
 flows:[
  {id:'H2P6JrVt2l0nb3J4boOOZ',displayName:'ChatGPT API 진입점',status:'ENABLED',published:true},
  {id:'8qJV66lPObcBTqamLowTB',displayName:'ChatGPT 답변 엔진',status:'ENABLED',published:true}
 ],
 callableOptions:[
  {label:'ChatGPT 답변 엔진',value:'NPOQmODuykYZdDjoEP0gr'},
  {label:'TEST ONLY · Join Child Worker (inactive)',value:'6OwqZHF62pCUOGPWRwonM'},
  {label:'MOCK ONLY · Promise.all 병렬 합류 검증기 (inactive)',value:'2360DkCqUZuY4XrzlhZ4j'}
 ],
 caller:{
  flowId:'H2P6JrVt2l0nb3J4boOOZ',
  targetFlowId:'NPOQmODuykYZdDjoEP0gr',
  expectedEngineLabel:'ChatGPT 답변 엔진'
 },
 historicalWebhookAuthFailures:2
});

test('real connected dropdown value is VALID despite different internal engine ID',()=>{
 const snapshot=actual();
 assert.notEqual(snapshot.flows[1].id,snapshot.caller.targetFlowId);
 const o=validateRoute(snapshot);
 assert.equal(o.verdict,'PASS');
 assert.deepEqual(o.diagnostics.map(x=>x.code),['HISTORICAL_WEBHOOK_AUTH_FAILURES']);
 assert.equal(o.internal_flow_id_equivalence_assumed,false);
 assert.equal(o.provider_write_calls,0);
 assert.equal(o.published_runtime_execution_proven,false);
});

test('internal flow ID incorrectly used as callable value must FAIL',()=>{
 const s=actual();s.caller.targetFlowId='8qJV66lPObcBTqamLowTB';
 const o=validateRoute(s);
 assert.equal(o.verdict,'FAIL');
 assert.ok(o.diagnostics.some(x=>x.code==='TARGET_NOT_IN_CALLFLOW_DROPDOWN'));
});

test('dropdown absent returns UNVERIFIED, never invent valid mapping',()=>{
 const s=actual();delete s.callableOptions;s.historicalWebhookAuthFailures=0;
 const o=validateRoute(s);
 assert.equal(o.verdict,'UNVERIFIED');
 assert.deepEqual(o.diagnostics.map(x=>x.code),['DYNAMIC_DROPDOWN_UNAVAILABLE']);
});

test('inactive callable option and mismatched expected label fail closed',()=>{
 const s=actual();s.caller.targetFlowId='6OwqZHF62pCUOGPWRwonM';
 const o=validateRoute(s);
 assert.equal(o.verdict,'FAIL');
 assert.ok(o.diagnostics.some(x=>x.code==='TARGET_OPTION_INACTIVE'));
 assert.ok(o.diagnostics.some(x=>x.code==='TARGET_LABEL_MISMATCH'));
 const t=actual();t.caller.expectedEngineLabel='Fake Engine';
 assert.ok(validateRoute(t).diagnostics.some(x=>x.code==='TARGET_LABEL_MISMATCH'));
});

test('invalid credential-shaped input value is rejected without echoing it',()=>{
 for(const id of ['','../foo','Bearer password-secret','http://secret.example','a']){
  const s=actual();s.caller.targetFlowId=id;
  const o=validateRoute(s);
  assert.equal(o.verdict,'FAIL');
  assert.ok(o.diagnostics.some(x=>x.code==='TARGET_VALUE_INVALID'));
  assert.ok(!JSON.stringify(o).includes('password-secret'));
 }
});

test('past webhook failures are warnings, not proof of current runtime failure',()=>{
 const s=actual();s.historicalWebhookAuthFailures=2;
 const o=validateRoute(s);
 assert.equal(o.verdict,'PASS');
 assert.ok(o.diagnostics.some(x=>x.code==='HISTORICAL_WEBHOOK_AUTH_FAILURES'));
 assert.equal(o.global_chat_hook_proven,false);
 assert.equal(o.actual_chatgpt_message_trigger_proven,false);
 assert.equal(o.ai_model_calls,0);
});

test('valid absence of previous auth failures yields PASS and no errors',()=>{
 const s=actual();s.historicalWebhookAuthFailures=0;
 const o=validateRoute(s);
 assert.equal(o.verdict,'PASS');
 assert.equal(o.diagnostics.length,0);
});
