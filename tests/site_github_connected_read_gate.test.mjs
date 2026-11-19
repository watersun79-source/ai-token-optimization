import test from 'node:test';
import assert from 'node:assert/strict';
import { createConnectedReadGate } from '../experiments/oss-top10-safe-adoption/site_github_connected_read_gate.mjs';

const SHA = 'a'.repeat(40);
const good = () => ({status: 200, data: {number: 30, head: {sha: SHA}}});

// New cases only. No existing Python/SDK/PR30 tests are invoked here.
test('no connected reader means zero provider calls and fail-closed', async () => {
  const gate = createConnectedReadGate({clock: () => 1000});
  const x = await gate.observe();
  assert.equal(x.reason, 'CONNECTED_READER_REQUIRED');
  assert.equal(x.attempts, 0);
  assert.equal(x.allowWrite, false);
  assert.equal(x.allowRetry, false);
});

test('one successful callback cannot prove Site/native success and is deduplicated', async () => {
  let calls = 0, now = 1000;
  const gate = createConnectedReadGate({clock: () => now});
  const cb = async (request) => {
    calls++;
    assert.deepEqual(request, {repository: 'watersun79-source/ai-token-optimization', pull_request: 30, method: 'GET'});
    return good();
  };
  const x = await gate.observe(cb);
  assert.equal(x.status, 'OBSERVED_UNVERIFIED');
  assert.equal(x.sha, SHA);
  assert.equal(x.operationalClearance, 'BLOCKED');
  assert.equal((await gate.observe(cb)).status, 'DEFERRED');
  assert.equal(calls, 1);
  now += 180001;
  assert.equal((await gate.observe(cb)).status, 'OBSERVED_UNVERIFIED');
  assert.equal(calls, 2);
});

test('403 primary rate limit blocks and defers until reset without a second request', async () => {
  let calls = 0, now = 1_800_000;
  const gate = createConnectedReadGate({clock: () => now});
  const cb = () => {calls++; return {status: 403, headers: {'x-ratelimit-remaining':'0', 'x-ratelimit-reset': String((now+900_000)/1000)}};};
  const x = await gate.observe(cb);
  assert.equal(x.status, 'BLOCKED');
  assert.equal(x.reason, 'RATE_LIMIT_EXHAUSTED');
  assert.equal(x.nextAllowedAt, now+900_000);
  now += 100_000;
  assert.equal((await gate.observe(cb)).status, 'DEFERRED');
  assert.equal(calls, 1);
});

test('429 Retry-After respects cooldown and no automatic retry', async () => {
  let calls=0;
  const gate = createConnectedReadGate({clock: () => 100_000});
  const cb = () => {calls++; return {status: 429, headers: {'Retry-After':'700'}}};
  const x=await gate.observe(cb);
  assert.equal(x.nextAllowedAt, 800_000);
  assert.equal((await gate.observe(cb)).reason,'COOLDOWN_ACTIVE');
  assert.equal(calls,1);
});

test('parallel caller burst is collapsed to exactly one callback', async () => {
  let calls=0;
  const gate=createConnectedReadGate({clock: () => 300000});
  const reader=async () => {calls++; await new Promise(resolve=>setImmediate(resolve)); return good();};
  const outcomes=await Promise.all(Array.from({length:64},()=>gate.observe(reader)));
  assert.equal(calls,1);
  assert.equal(outcomes.length,64);
  assert.ok(outcomes.every(x=>x.status==='OBSERVED_UNVERIFIED'));
});

test('provider rejected call is redacted and throttled', async () => {
  let calls=0;
  const gate=createConnectedReadGate({clock: () => 500000});
  const reader=()=>{calls++;throw Error('Bearer secret-should-never-appear');};
  const x=await gate.observe(reader);
  assert.equal(x.reason,'PROVIDER_CALL_FAILED');
  assert.ok(!JSON.stringify(x).includes('secret-should-never-appear'));
  assert.equal((await gate.observe(reader)).status,'DEFERRED');
  assert.equal(calls,1);
});

test('identity or SHA mismatch cannot promote a read', async () => {
  const gate=createConnectedReadGate({clock: () => 600000});
  const x=await gate.observe(async () => ({status:200,data:{number:31,head:{sha:SHA}}}));
  assert.equal(x.reason,'PROVIDER_IDENTITY_OR_SHA_UNVERIFIED');
  assert.equal(x.allowWrite,false);
});

test('malformed headers do not throw or leak secrets', async () => {
  const gate=createConnectedReadGate({clock: () => 200000});
  const x=await gate.observe(async () => ({status:403,headers:{get(){throw Error('secret-stored');}}}));
  assert.equal(x.status,'BLOCKED');
  assert.equal(x.reason,'PROVIDER_DENIED');
  assert.ok(!JSON.stringify(x).includes('secret-stored'));
});

test('invalid clock blocks before reader is called', async () => {
  const gate=createConnectedReadGate({clock: () => NaN});
  let calls=0;
  const x=await gate.observe(()=>{calls++;return good();});
  assert.equal(x.reason,'CLOCK_INVALID');
  assert.equal(calls,0);
});
