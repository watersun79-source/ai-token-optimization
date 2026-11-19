import test from 'node:test';
import assert from 'node:assert/strict';
import { createConnectedReadGate } from '../experiments/oss-top10-safe-adoption/site_github_connected_read_gate.mjs';

test('new: Retry-After numeric 7200 seconds is honored beyond one hour', async () => {
  let now=100_000; let count=0;
  const gate=createConnectedReadGate({clock:()=>now});
  const reader=async()=>{count++;return {status:429,headers:{'Retry-After':'7200'}};};
  const first=await gate.observe(reader);
  assert.equal(first.nextAllowedAt,7_300_000);
  now=3_800_000;
  assert.equal((await gate.observe(reader)).status,'DEFERRED');
  assert.equal(count,1);
});

test('new: 403 reset epoch later than one hour is respected',async()=>{
  let now=1_800_000; let count=0;
  const gate=createConnectedReadGate({clock:()=>now});
  const reader=async()=>{count++;return {status:403,headers:{'x-ratelimit-remaining':'0','x-ratelimit-reset':String((1_800_000+7_200_000)/1000)}};};
  const first=await gate.observe(reader);
  assert.equal(first.nextAllowedAt,9_000_000);
  now=6_000_000;
  assert.equal((await gate.observe(reader)).status,'DEFERRED');
  assert.equal(count,1);
});

test('new: HTTP-date Retry-After later than one hour is honored',async()=>{
  const start=Date.UTC(2026,10,18,13,0,0);
  let now=start;let count=0;
  const gate=createConnectedReadGate({clock:()=>now});
  const reader=async()=>{count++;return {status:429,headers:{'Retry-After':'Wed, 18 Nov 2026 15:00:00 GMT'}};};
  const first=await gate.observe(reader);
  assert.equal(first.nextAllowedAt,start+7_200_000);
  now=start+3_900_000;
  assert.equal((await gate.observe(reader)).status,'DEFERRED');
  assert.equal(count,1);
});
