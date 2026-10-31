import test from 'node:test';
import assert from 'node:assert/strict';
import {validateRoute,classifyWebhookHistory} from './ap_callflow_guard_v843.mjs';

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


const entryFlowId='H2P6JrVt2l0nb3J4boOOZ';
const productionRun=r=>({environment:'PRODUCTION',flowId:entryFlowId,...r});
const historicalRuns=[
 {id:'8D2vsJDFijVKiLU562CmT',status:'FAILED',created:'2026-10-28T17:38:52.396Z',error_code:'CALLFLOW_RUNTIME_TARGET_NOT_FOUND'},
 {id:'EMr6A2wktzuYL8PAim8Rv',status:'FAILED',created:'2026-10-28T16:41:03.025Z',error_code:'WEBHOOK_HEADER_AUTH_REJECTED'},
 {id:'WqtHmewLopkKouj7vAoZ2',status:'FAILED',created:'2026-10-28T14:57:48.253Z',error_code:'WEBHOOK_HEADER_AUTH_REJECTED'}
].map(productionRun);
test('observed October 28 failures are historical by November 1, not a current outage',()=>{
 const o=classifyWebhookHistory({expectedFlowId:entryFlowId,runs:historicalRuns,asOfIso:'2026-10-31T18:24:00Z',headerAuthConfigured:true});
 assert.equal(o.state,'HISTORICAL_RUNS_ONLY');
 assert.equal(o.verdict,'UNVERIFIED');
 assert.equal(o.historical_auth_rejections,2);
 assert.equal(o.historical_subflow_failures,1);
 assert.equal(o.auth_rejection_is_definitive_misconfiguration,false);
 assert.equal(o.native_chat_trigger_verified,false);
 assert.equal(o.runtime_recovery_verified,false);
 assert.equal(o.header_auth_configured,true);
 assert.equal(o.provider_calls,0);
});
test('new failed Activepieces entry run is failure only for Activepieces and not native',()=>{
 const o=classifyWebhookHistory({expectedFlowId:entryFlowId,runs:[productionRun({status:'FAILED',created:'2026-10-31T17:50:00Z',error_code:'WEBHOOK_HEADER_AUTH_REJECTED'}),...historicalRuns],
 asOfIso:'2026-10-31T18:24:00Z',headerAuthConfigured:true});
 assert.equal(o.state,'RECENT_ACTIVEPIECES_ENTRY_FAILED');
 assert.equal(o.verdict,'FAIL_AP_ENTRY');
 assert.equal(o.native_chat_trigger_verified,false);
});
test('a fresh successful entry run is bounded evidence, not global ChatGPT composer interception',()=>{
 const o=classifyWebhookHistory({expectedFlowId:entryFlowId,runs:[productionRun({status:'SUCCEEDED',created:'2026-10-31T18:00:00Z'}),...historicalRuns],
 asOfIso:'2026-10-31T18:24:00Z'});
 assert.equal(o.state,'RECENT_ACTIVEPIECES_ENTRY_SUCCEEDED');
 assert.equal(o.verdict,'PASS_AP_ENTRY_ONLY');
 assert.equal(o.native_chat_trigger_verified,false);
 assert.equal(o.runtime_recovery_verified,false);
});
test('missing or malformed run metadata fails closed and leaks no error message',()=>{
 for(const runs of [null,[],[{status:'BAD',created:'2026-10-31T18:00:00Z'}],[{status:'FAILED',created:'2026-11-02T00:00:00Z',error_code:'password_secret'}]]){
  const o=classifyWebhookHistory({expectedFlowId:entryFlowId,runs,asOfIso:'2026-10-31T18:24:00Z'});
  assert.equal(o.verdict,'UNVERIFIED');
  assert.equal(o.native_chat_trigger_verified,false);
  assert.ok(!JSON.stringify(o).includes('password_secret'));
 }
});

test('fresh TESTING success cannot be presented as production webhook success',()=>{
 const testRun={...productionRun({status:'SUCCEEDED',created:'2026-10-31T18:00:00Z'}),environment:'TESTING'};
 const o=classifyWebhookHistory({expectedFlowId:entryFlowId,runs:[testRun],asOfIso:'2026-10-31T18:24:00Z'});
 assert.equal(o.state,'INVALID_RUN_PROVENANCE');
 assert.equal(o.verdict,'UNVERIFIED');
 assert.equal(o.native_chat_trigger_verified,false);
});
test('other callable engine success cannot prove the webhook entry',()=>{
 const alien=productionRun({status:'SUCCEEDED',created:'2026-10-31T18:00:00Z'});
 alien.flowId='8qJV66lPObcBTqamLowTB';
 const o=classifyWebhookHistory({expectedFlowId:entryFlowId,runs:[alien],asOfIso:'2026-10-31T18:24:00Z'});
 assert.equal(o.state,'INVALID_RUN_PROVENANCE');
 assert.equal(o.verdict,'UNVERIFIED');
});
test('missing run provenance or expected entry identity fails closed',()=>{
 const run=productionRun({status:'SUCCEEDED',created:'2026-10-31T18:00:00Z'});
 for(const bad of [{...run,environment:undefined},{...run,flowId:undefined}]){
  const o=classifyWebhookHistory({expectedFlowId:entryFlowId,runs:[bad],asOfIso:'2026-10-31T18:24:00Z'});
  assert.equal(o.verdict,'UNVERIFIED');
 }
 const noTarget=classifyWebhookHistory({runs:[run],asOfIso:'2026-10-31T18:24:00Z'});
 assert.equal(noTarget.state,'EXPECTED_ENTRY_FLOW_MISSING');
 assert.equal(noTarget.verdict,'UNVERIFIED');
});
test('real PRODUCTION entry success remains bounded evidence',()=>{
 const run=productionRun({status:'SUCCEEDED',created:'2026-10-31T18:00:00Z'});
 const o=classifyWebhookHistory({expectedFlowId:entryFlowId,runs:[run],asOfIso:'2026-10-31T18:24:00Z'});
 assert.equal(o.verdict,'PASS_AP_ENTRY_ONLY');
 assert.equal(o.production_entry_provenance_verified,true);
 assert.equal(o.native_chat_trigger_verified,false);
});
