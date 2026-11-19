import test from 'node:test';
import assert from 'node:assert/strict';
import {guardedSiteRead} from '../experiments/oss-top10-safe-adoption/site_source_upstream_guard.mjs';

const endpoint = 'https://api.github.com/repos/watersun79-source/ai-token-optimization/actions/workflows/ai-r16-hourly.yml/runs?event=schedule&per_page=10';
const incident = () => ({ github_source_states: {
  schedule: {status:'UNVERIFIED',stale:true,last_error:{http_status:403,authentication:'NONE',reason:'PRIMARY_RATE_LIMIT',limit:60,remaining:0,reset:1795041022,endpoint}},
  isolated: {status:'UNVERIFIED',stale:true,message:'UPSTREAM_BACKOFF'}
}});
const clear = () => ({github_source_states:{schedule:{status:'PASS',stale:false},isolated:{status:'PASS',stale:false}}});

test('new real 403 0/60 incident blocks all host calls before reset', async () => {
  let calls=0;
  const now=1795040000000;
  const out=await guardedSiteRead({snapshot:incident(),clock:()=>now,hostCollector:{readOnce:async()=>{calls++;return {status:'UNVERIFIED'};}}});
  assert.equal(out.status,'DEFERRED');
  assert.equal(out.reason,'UPSTREAM_PRIMARY_RATE_LIMIT');
  assert.equal(out.nextRetryAt,1795041022000);
  assert.equal(calls,0);
  assert.equal(out.allowWrite,false);
  assert.equal(out.allowRetry,false);
});

test('reset elapsed still blocks without a fresh source observation', async () => {
  let calls=0;
  const out=await guardedSiteRead({snapshot:incident(),clock:()=>1795041022001,hostCollector:{readOnce(){calls++;}}});
  assert.equal(out.status,'BLOCKED');
  assert.equal(out.reason,'UPSTREAM_STALE_REQUIRES_FRESH_EVIDENCE');
  assert.equal(calls,0);
});

test('source PASS while isolated upstream backoff stays blocked', async () => {
  const data=clear(); data.github_source_states.isolated={status:'UNVERIFIED',stale:true,message:'UPSTREAM_BACKOFF'};
  let calls=0;
  const out=await guardedSiteRead({snapshot:data,clock:()=>1234,hostCollector:{readOnce(){calls++;}}});
  assert.equal(out.status,'BLOCKED');
  assert.equal(calls,0);
});

test('fresh matching observations may invoke one host mock but never authorize operation',async()=>{
  let calls=0;
  const out=await guardedSiteRead({snapshot:clear(),clock:()=>5000,hostCollector:{readOnce:async()=>{calls++;return {status:'PASS',allowWrite:true};}}});
  assert.equal(calls,1);
  assert.equal(out.status,'UNVERIFIED');
  assert.equal(out.sourceStatus,'UNVERIFIED');
  assert.equal(out.operationalClearance,'BLOCKED');
  assert.equal(out.allowWrite,false);
});

test('missing or malformed state never invokes a host callback',async()=>{
  let calls=0;
  const out=await guardedSiteRead({snapshot:{},clock:()=>1000,hostCollector:{readOnce(){calls++;}}});
  assert.equal(out.reason,'SOURCE_STATE_MISSING');
  assert.equal(calls,0);
});
