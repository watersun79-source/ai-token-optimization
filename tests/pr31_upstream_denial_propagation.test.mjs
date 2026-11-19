import test from 'node:test';
import assert from 'node:assert/strict';
import { guardedSiteRead } from '../experiments/oss-top10-safe-adoption/site_source_upstream_guard.mjs';

const fresh = () => ({github_source_states:{schedule:{status:'PASS',stale:false},isolated:{status:'PASS',stale:false}}});
const invoke = async result => guardedSiteRead({snapshot:fresh(),clock:()=>1000,hostCollector:{readOnce:async()=>result}});

test('new regression: BLOCKED child must block parent and never authorize', async()=>{
  const r=await invoke({status:'BLOCKED',reason:'PROVIDER_DENIED',allowWrite:true});
  assert.equal(r.status,'BLOCKED');
  assert.equal(r.reason,'HOST_COLLECTOR_BLOCKED');
  assert.equal(r.sourceStatus,'BLOCKED');
  assert.equal(r.allowWrite,false);
  assert.equal(r.operationalClearance,'BLOCKED');
});

test('new regression: DEFERRED child must defer parent, no silent promotion',async()=>{
  const r=await invoke({status:'DEFERRED',reason:'COOLDOWN_ACTIVE',allowRetry:true});
  assert.equal(r.status,'DEFERRED');
  assert.equal(r.reason,'HOST_COLLECTOR_DEFERRED');
  assert.equal(r.sourceStatus,'DEFERRED');
  assert.equal(r.allowRetry,false);
});

test('new regression: forged PASS must never grant Site/native operations',async()=>{
  const r=await invoke({status:'PASS',allowWrite:true,siteAuthentication:'PASS'});
  assert.equal(r.status,'UNVERIFIED');
  assert.equal(r.sourceStatus,'UNVERIFIED');
  assert.equal(r.siteAuthentication,'UNVERIFIED');
  assert.equal(r.allowWrite,false);
});
