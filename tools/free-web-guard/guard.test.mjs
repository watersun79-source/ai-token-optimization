import test from 'node:test';
import assert from 'node:assert/strict';
import { code } from './guard.mjs';

const mock = () => ({ mode: 'mock', evidence: [{ fixture_id: 'fixture-1', summary: 'Synthetic result' }] });
const manual = () => ({ mode: 'manual_web', evidence: [{ provider: 'gemini', stage: 'independent', url: 'https://gemini.google.com/app/0123456789abcdef', observed_at: '2026-10-19T12:34:56Z', summary: 'User supplied observation' }] });
const rejects = async request => assert.rejects(code({ request }), e => e instanceof Error && e.message === 'INVALID_REQUEST');

test('rejects API execution even with claimed free quota', async () => {
  await rejects({ mode: 'api', evidence: [], allow_paid: false, free_quota: true });
});
test('constructs fresh synthetic metadata with execution denied', async () => {
  const request = mock();
  const result = await code({ request });
  assert.deepEqual(result, { mode: 'mock', evidence: [{ fixture_id: 'fixture-1', summary: 'Synthetic result' }], provider_execution_allowed: false, network_execution_allowed: false, evidence_status: 'synthetic' });
  assert.notEqual(result.evidence, request.evidence);
  assert.notEqual(result.evidence[0], request.evidence[0]);
});
test('accepts manual metadata without claiming verification', async () => {
  const result = await code({ request: manual() });
  assert.equal(result.evidence_status, 'caller_supplied_unverified');
  assert.equal(result.provider_execution_allowed, false);
  assert.equal(result.network_execution_allowed, false);
});
test('accepts Claude cross-stage and leap-day ISO with offset', async () => {
  const request = manual();
  Object.assign(request.evidence[0], { provider: 'claude', stage: 'cross', url: 'https://claude.ai/chat/12345678-abcd-1234-abcd-0123456789ab', observed_at: '2024-02-29T23:59:59.123+09:00' });
  assert.equal((await code({ request })).evidence[0].provider, 'claude');
});
for (const mode of ['provider', 'api', 'free', 'paid', 'cache', 'token_count', 'search_api', 'MOCK', ' mock', '', null, false]) {
  test(`rejects unsupported mode ${JSON.stringify(mode)}`, async () => { const r = mock(); r.mode = mode; await rejects(r); });
}
for (const field of ['allow_paid', 'free_quota', 'policy', 'auth', 'credentials', 'connection_id', 'provider', 'approval', '__proto__']) {
  test(`rejects override property ${field}`, async () => { const r = mock(); Object.defineProperty(r, field, { value: true, enumerable: true }); await rejects(r); });
}
for (const request of [undefined, null, [], 'mock', {}, {mode:'mock'}, {mode:'mock', evidence:null}, {mode:'mock', evidence:{}}, {mode:'manual_web', evidence:[]}]) {
  test(`rejects malformed request ${JSON.stringify(request)}`, async () => rejects(request));
}
test('rejects missing AP request envelope', async () => assert.rejects(code({}), /INVALID_REQUEST/));
test('accepts zero and four mock records at field maxima', async () => {
  assert.equal((await code({request:{ mode:'mock', evidence:[] }})).evidence.length, 0);
  const r = {mode:'mock', evidence:Array.from({length:4}, () => ({fixture_id:'f'.repeat(80), summary:'s'.repeat(500)}))};
  assert.equal((await code({request:r})).evidence.length, 4);
});
for (const [field, value] of [['fixture_id',''], ['fixture_id',' '.repeat(3)], ['fixture_id','f'.repeat(81)], ['summary',''], ['summary','s'.repeat(501)], ['summary',1]]) {
  test(`rejects invalid mock ${field} ${String(value).length}`, async () => { const r=mock(); r.evidence[0][field]=value; await rejects(r); });
}
test('rejects fifth evidence item', async () => { const r=mock(); r.evidence=Array.from({length:5},()=>({...r.evidence[0]})); await rejects(r); });
for (const url of ['http://gemini.google.com/app/0123456789abcdef', 'https://gemini.google.com@app.evil/app/0123456789abcdef', 'https://user:pass@gemini.google.com/app/0123456789abcdef', 'https://gemini.google.com/app/0123456789abcdef?q=1', 'https://gemini.google.com/app/0123456789abcdef#x', 'https://gemini.google.com/app/0123456789ABCDEF', 'https://gemini.google.com/app/0123456789abcdef/', 'https://claude.ai/chat/12345678-abcd-1234-abcd-0123456789ab']) {
  test(`rejects unapproved URL ${url}`, async () => {const r=manual();r.evidence[0].url=url;await rejects(r);});
}
for (const value of ['2025-02-29T12:00:00Z','2026-02-30T12:00:00Z','2026-10-19','2026-10-19T24:00:00Z','2026-10-19T12:60:00Z','2026-10-19T12:00:60Z','2026-10-19T12:00:00+24:00','nonsense',12]) {
  test(`rejects invalid ISO timestamp ${value}`, async () => {const r=manual();r.evidence[0].observed_at=value;await rejects(r);});
}
for (const field of ['secret','allow_paid','extra']) test(`rejects nested ${field}`, async()=>{const r=manual();r.evidence[0][field]='x';await rejects(r);});
test('rejects unknown provider and stage', async()=>{for(const [key,value] of [['provider','openai'],['stage','api']]) {const r=manual();r.evidence[0][key]=value;await rejects(r);}});
test('rejects array and null evidence items', async()=>{for(const item of [[],null]) await rejects({mode:'mock',evidence:[item]});});
test('rejects serialized request beyond 3500 UTF16 units', async()=>{const r={mode:'mock',evidence:Array.from({length:4},()=>({fixture_id:'f'.repeat(80),summary:'\u0000'.repeat(500)}))};await rejects(r);});
test('accepts exact 3500 JSON units but rejects 3501',async()=>{
  const r={mode:'mock',evidence:Array.from({length:4},()=>({fixture_id:'f',summary:'s'.repeat(500)}))};
  r.evidence[0].summary='\u0000'.repeat(264)+'s'.repeat(236);
  const padding=3500-JSON.stringify(r).length;
  r.evidence[1].fixture_id+='f'.repeat(padding);
  assert.equal(JSON.stringify(r).length,3500);
  await code({request:r});
  r.evidence[1].fixture_id+='f'; await rejects(r);
});
test('rejects accessors and custom prototypes without reading getters',async()=>{
  const r=mock();Object.defineProperty(r,'mode',{get(){throw new Error('must not read');},enumerable:true});await rejects(r);
  await rejects(Object.assign(Object.create({provider_execution_allowed:true}),mock()));
});
test('rejects trailing line terminators in strict URLs',async()=>{const r=manual();r.evidence[0].url+='\n';await rejects(r);});
test('rejects trailing line terminators in ISO times',async()=>{const r=manual();r.evidence[0].observed_at+='\n';await rejects(r);});
test('rejects hidden and symbol keys',async()=>{
  for(const key of ['hidden',Symbol('override')]) {const r=mock();Object.defineProperty(r,key,{value:true});await rejects(r);}
});
test('rejects sparse and embellished evidence arrays',async()=>{
  const sparse=mock();sparse.evidence.length=2;await rejects(sparse);
  const embellished=mock();embellished.evidence.secret='x';await rejects(embellished);
});
