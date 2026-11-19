import test from 'node:test';
import assert from 'node:assert/strict';
import { createSiteHostCollector, ORIGINAL_SITE_PROJECT_ID } from '../experiments/oss-top10-safe-adoption/site_host_collector_bridge.mjs';

const HEAD = 'b6247c697157126c381feab9abfd0799b25a1571';
const result = () => ({result:{pull_request:{number:30,head_sha:HEAD,state:'open',merged:false}}});

test('missing host binding blocks with zero external requests and no fallback',async()=>{
  const x=await createSiteHostCollector({projectId:ORIGINAL_SITE_PROJECT_ID}).readOnce();
  assert.equal(x.status,'BLOCKED');
  assert.equal(x.reason,'SITE_HOST_CONNECTED_READER_NOT_AVAILABLE');
  assert.equal(x.source.connectedReaderInvocations,0);
  assert.equal(x.allowUnauthenticatedFallback,false);
  assert.equal(x.allowWrite,false);
});

test('wrong original Site identity blocks before injected reader',async()=>{
  let count=0;
  const x=await createSiteHostCollector({projectId:'fake-project',hostReadPr:async()=>{count++;return result();}}).readOnce();
  assert.equal(x.reason,'SITE_PROJECT_ID_MISMATCH');
  assert.equal(count,0);
});

test('host reader is correctly scoped to PR #30 but cannot establish Site trust',async()=>{
  let count=0;
  const instance=createSiteHostCollector({projectId:ORIGINAL_SITE_PROJECT_ID, clock:()=>1000,
    hostReadPr:async args=>{count++; assert.deepEqual(args,{repo_full_name:'watersun79-source/ai-token-optimization',pr_number:30});return result();}});
  const x=await instance.readOnce();
  assert.equal(count,1);
  assert.equal(x.status,'UNVERIFIED');
  assert.equal(x.source.sha,HEAD);
  assert.equal(x.stages.debug,'UNVERIFIED');
  assert.equal(x.stages.verify,'SKIP');
  assert.equal(x.siteRuntimeAuthentication,'UNVERIFIED');
  assert.equal(x.operationalClearance,'BLOCKED');
  assert.equal(x.allowWrite,false);
  const second=await instance.readOnce();
  assert.equal(second.status,'DEFERRED');
  assert.equal(count,1);
});

test('host read failure is redacted and remains blocked with no retry',async()=>{
  let count=0;
  const collector=createSiteHostCollector({projectId:ORIGINAL_SITE_PROJECT_ID,clock:()=>1000,hostReadPr:async()=>{count++;throw Error('SECRET-TOKEN-DO-NOT-LOG');}});
  const x=await collector.readOnce();
  assert.equal(x.status,'BLOCKED');
  assert.equal(x.reason,'PROVIDER_CALL_FAILED');
  assert.ok(!JSON.stringify(x).includes('SECRET-TOKEN'));
  assert.equal((await collector.readOnce()).status,'DEFERRED');
  assert.equal(count,1);
});

test('64 concurrent Site calls merge into one provider callback in process',async()=>{
  let count=0;
  const collector=createSiteHostCollector({projectId:ORIGINAL_SITE_PROJECT_ID,clock:()=>1000,hostReadPr:async()=>{
    count++;await new Promise(done=>setImmediate(done));return result();
  }});
  const x=await Promise.all(Array.from({length:64},()=>collector.readOnce()));
  assert.equal(count,1);
  assert.ok(x.every(v=>v.status==='UNVERIFIED'&&v.allowWrite===false));
});

test('invalid GitHub PR identity does not unlock next stage',async()=>{
  const collector=createSiteHostCollector({projectId:ORIGINAL_SITE_PROJECT_ID,clock:()=>1000,
    hostReadPr:async()=>({result:{pull_request:{number:31,head_sha:HEAD,state:'open',merged:false}}})});
  const x=await collector.readOnce();
  assert.equal(x.status,'BLOCKED');
  assert.equal(x.stages.analysis,'SKIP');
  assert.equal(x.operationalClearance,'BLOCKED');
});
