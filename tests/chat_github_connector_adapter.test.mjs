import test from 'node:test';
import assert from 'node:assert/strict';
import {createChatGithubAdapter, fromSanitizedSnapshot, REPO, PR_NUMBER} from '../experiments/oss-top10-safe-adoption/chat_github_connector_adapter.mjs';

const HEAD = 'b6247c697157126c381feab9abfd0799b25a1571';
const snapshot = () => ({provider: 'mcp__GitHub__fetch_pr', call_count: 1, repository: REPO,
  number:PR_NUMBER, head_sha:HEAD, state:'open', merged:false});
const connector = () => ({result:{pull_request:{number:PR_NUMBER, head_sha:HEAD, state:'open', merged:false}}});

test('actual connector-shaped result passes through gate without Site/native success', async () => {
  let observed = 0;
  const adapter = createChatGithubAdapter({clock:()=>1000, fetchPr:async input=>{
    observed++; assert.deepEqual(input,{repo_full_name:REPO,pr_number:PR_NUMBER}); return connector();
  }});
  const out = await adapter.observe();
  assert.equal(observed,1);
  assert.equal(out.connectedReaderInvocations,1);
  assert.equal(out.sha,HEAD);
  assert.equal(out.status,'OBSERVED_UNVERIFIED');
  assert.equal(out.siteAuthentication,'UNVERIFIED');
  assert.equal(out.nativeGoal,'UNVERIFIED');
  assert.equal(out.operationalClearance,'BLOCKED');
  assert.equal(out.actualGithubHttpStatus,null);
  assert.equal(out.allowWrite,false);
});

test('read-cooldown prevents second call to actual connector callback', async () => {
  let observed = 0;
  const adapter = createChatGithubAdapter({clock:()=>1000,fetchPr:async()=>{observed++;return connector();}});
  await adapter.observe();
  const out = await adapter.observe();
  assert.equal(out.status,'DEFERRED');
  assert.equal(observed,1);
});

test('no connector callback invokes zero tools and stays blocked', async () => {
  const out=await createChatGithubAdapter({clock:()=>1000}).observe();
  assert.equal(out.status,'BLOCKED');
  assert.equal(out.reason,'CONNECTED_READER_REQUIRED');
  assert.equal(out.connectedReaderInvocations,0);
});

test('bad PR number does not become a GitHub success', async () => {
  const adapter=createChatGithubAdapter({clock:()=>1000,fetchPr:async()=>({result:{pull_request:{number:31,head_sha:HEAD,state:'open',merged:false}}})});
  const x=await adapter.observe();
  assert.equal(x.status,'BLOCKED');
  assert.equal(x.reason,'UNEXPECTED_PROVIDER_STATUS');
  assert.equal(x.allowRetry,false);
});

test('invalid SHA from connector blocks without claiming authentication', async () => {
  const adapter=createChatGithubAdapter({clock:()=>1000,fetchPr:async()=>({result:{pull_request:{number:30,head_sha:'X',state:'open',merged:false}}})});
  const x=await adapter.observe();
  assert.equal(x.status,'BLOCKED');
  assert.equal(x.reason,'PROVIDER_IDENTITY_OR_SHA_UNVERIFIED');
});

test('connector exception redacted and no automatic retry', async () => {
  let count=0;
  const adapter=createChatGithubAdapter({clock:()=>1000,fetchPr:async()=>{count++;throw Error('Bearer PRIVATE');}});
  const x=await adapter.observe();
  assert.equal(x.reason,'PROVIDER_CALL_FAILED');
  assert.ok(!JSON.stringify(x).includes('PRIVATE'));
  assert.equal((await adapter.observe()).status,'DEFERRED');
  assert.equal(count,1);
});

test('untrusted replay wrong repository performs zero callback invocations', async () => {
  const s=snapshot();s.repository='not-the-repo';
  const x=await fromSanitizedSnapshot(s,{clock:()=>1000}).observe();
  assert.equal(x.connectedReaderInvocations,0);
  assert.equal(x.reason,'CONNECTED_READER_REQUIRED');
});

test('valid sanitized snapshot is local replay, not a live connected tool call', async () => {
  const x=await fromSanitizedSnapshot(snapshot(),{clock:()=>1000}).observe();
  assert.equal(x.status,'OBSERVED_UNVERIFIED');
  assert.equal(x.connectorAuthProvenance,'UNVERIFIED_LOCAL_ADAPTER');
  assert.equal(x.actualGithubHttpStatus,null);
});

test('64 simultaneous adapter invocations collapse to one connected reader callback', async () => {
  let count=0;
  const adapter=createChatGithubAdapter({clock:()=>1000,fetchPr:async()=>{
    count++; await new Promise(done=>setImmediate(done)); return connector();
  }});
  const out=await Promise.all(Array.from({length:64},()=>adapter.observe()));
  assert.equal(count,1);
  assert.ok(out.every(x=>x.status==='OBSERVED_UNVERIFIED'));
});
