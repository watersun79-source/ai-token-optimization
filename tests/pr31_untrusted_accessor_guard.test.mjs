import test from 'node:test';
import assert from 'node:assert/strict';
import {checkUpstreamSourceState,guardedSiteRead} from '../experiments/oss-top10-safe-adoption/site_source_upstream_guard.mjs';
const missing = Object.defineProperty({},'github_source_states',{get(){throw new Error('getter');}});
const fresh=()=>({github_source_states:{schedule:{status:'PASS',stale:false},isolated:{status:'PASS',stale:false}}});
test('untrusted root getter must yield a blocked verdict, not throw',()=>{
  const r=checkUpstreamSourceState(missing, 1000);
  assert.equal(r.status,'BLOCKED');assert.equal(r.reason,'SOURCE_STATE_ACCESS_FAILED');
});
test('untrusted nested source accessor must not invoke collector',async()=>{
  const x=fresh();Object.defineProperty(x.github_source_states.schedule,'last_error',{get(){throw new Error('nested');}});
  let count=0;const r=await guardedSiteRead({snapshot:x,clock:()=>1000,hostCollector:{readOnce(){count++;}}});
  assert.equal(r.status,'BLOCKED');assert.equal(r.reason,'SOURCE_STATE_ACCESS_FAILED');assert.equal(count,0);
});
test('untrusted collector method getter must fail closed without invocation',async()=>{
  const collector=Object.defineProperty({},'readOnce',{get(){throw Error('getter');}});
  const r=await guardedSiteRead({snapshot:fresh(),clock:()=>1000,hostCollector:collector});
  assert.equal(r.status,'BLOCKED');assert.equal(r.reason,'SITE_HOST_COLLECTOR_ACCESS_FAILED');
});

test('host collector getter is read only once before invoking',async()=>{
  let reads=0, invoked=0;
  const collector={get readOnce(){reads++;return async function(){invoked++;return {status:'BLOCKED'};};}};
  const r=await guardedSiteRead({snapshot:fresh(),clock:()=>1000,hostCollector:collector});
  assert.equal(reads,1);assert.equal(invoked,1);assert.equal(r.status,'BLOCKED');
  assert.equal(r.operationalClearance,'BLOCKED');
});
