import test from 'node:test';
import assert from 'node:assert/strict';
import {validateRoute} from './ap_callflow_guard_v843.mjs';

const base = () => ({
 flows:[
  {id:'H2P6JrVt2l0nb3J4boOOZ',displayName:'ChatGPT API 진입점',status:'ENABLED',published:true},
  {id:'8qJV66lPObcBTqamLowTB',displayName:'ChatGPT 답변 엔진',status:'ENABLED',published:true},
 ],
 caller:{flowId:'H2P6JrVt2l0nb3J4boOOZ',targetFlowId:'NPOQmODuykYZdDjoEP0gr',expectedEngineId:'8qJV66lPObcBTqamLowTB'},
 historicalWebhookAuthFailures:2
});

test('actual redacted metadata snapshot finds missing production reference',()=>{
 const o=validateRoute(base());
 assert.equal(o.verdict,'FAIL');
 assert.ok(o.diagnostics.some(x=>x.code==='TARGET_FLOW_NOT_FOUND'));
 assert.ok(o.diagnostics.some(x=>x.code==='TARGET_DIFFERS_FROM_DESIGNATED_ENGINE'));
 assert.ok(o.diagnostics.some(x=>x.code==='WEBHOOK_AUTH_FAILURES_OBSERVED'));
 assert.equal(o.global_chat_hook_proven,false);
 assert.equal(o.provider_write_calls,0);
});
test('valid target passes but historical webhook auth failure remains warning',()=>{
 const i=base();i.caller.targetFlowId='8qJV66lPObcBTqamLowTB';
 const o=validateRoute(i);
 assert.equal(o.verdict,'PASS');
 assert.deepEqual(o.diagnostics.map(x=>x.code),['WEBHOOK_AUTH_FAILURES_OBSERVED']);
});
test('disabled or unpublished target must not count as active',()=>{
 for(const field of ['status','published']){
  const i=base();i.caller.targetFlowId='8qJV66lPObcBTqamLowTB';
  const f=i.flows[1];if(field==='status')f.status='DISABLED';else f.published=false;
  assert.equal(validateRoute(i).verdict,'FAIL');
  assert.ok(validateRoute(i).diagnostics.some(x=>x.code==='TARGET_NOT_PUBLISHED_OR_ENABLED'));
 }
});
test('missing or malformed flow ids fail closed without exposing secrets',()=>{
 for(const id of ['','../foo','Bearer password-secret','http://secret.example','a']){
  const i=base();i.caller.targetFlowId=id;
  const o=validateRoute(i);
  assert.equal(o.verdict,'FAIL');
  assert.ok(o.diagnostics.some(x=>x.code==='TARGET_ID_MISSING_OR_INVALID'));
  assert.ok(!JSON.stringify(o).includes('password-secret'));
 }
});
test('unknown metadata cannot be mistaken for proven live ChatGPT interception',()=>{
 const i=base();delete i.caller.expectedEngineId;i.caller.targetFlowId='8qJV66lPObcBTqamLowTB';
 const o=validateRoute(i);
 assert.equal(o.verdict,'PASS');
 assert.equal(o.provider_snapshot_live,false);
 assert.equal(o.actual_chatgpt_message_trigger_proven,false);
 assert.equal(o.ai_model_calls,0);
});
