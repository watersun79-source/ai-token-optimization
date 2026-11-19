import test from 'node:test';
import assert from 'node:assert/strict';
import {createChatGithubAdapter, fromSanitizedSnapshot} from '../experiments/oss-top10-safe-adoption/chat_github_connector_adapter.mjs';

const SHA = 'b6247c697157126c381feab9abfd0799b25a1571';
const snapshot = () => ({
  provider:'mcp__GitHub__fetch_pr', call_count:1,
  repository:'watersun79-source/ai-token-optimization',
  number:30, head_sha:SHA, state:'open', merged:false
});

test('sanitized replay must count ZERO real connected invocations', async () => {
  const out = await fromSanitizedSnapshot(snapshot(), {clock:()=>1000}).observe();
  assert.equal(out.connectedReaderInvocations, 0);
  assert.equal(out.replayOnly, true);
  assert.equal(out.simulatedReaderInvocations, 1);
  assert.equal(out.liveConnectorCallsByReplay, 0);
  assert.equal(out.allowWrite, false);
});

test('invalid replay is still labeled replay-only and zero live calls', async () => {
  const x=snapshot();x.repository='forged/repo';
  const out=await fromSanitizedSnapshot(x,{clock:()=>1000}).observe();
  assert.equal(out.connectedReaderInvocations,0);
  assert.equal(out.replayOnly,true);
  assert.equal(out.liveConnectorCallsByReplay,0);
  assert.equal(out.operationalClearance,'BLOCKED');
});

test('actual injected connector callback keeps original invocation count',async()=>{
  let count=0;
  const out=await createChatGithubAdapter({clock:()=>1000,fetchPr:async()=>{
    count++;
    return {result:{pull_request:{number:30,head_sha:SHA,state:'open',merged:false}}};
  }}).observe();
  assert.equal(count,1);
  assert.equal(out.connectedReaderInvocations,1);
  assert.notEqual(out.replayOnly,true);
});
