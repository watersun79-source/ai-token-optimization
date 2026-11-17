/**
 * v1.0.4 targeted offline in-host guard regression.
 * Run: node --test test_inhost_offline_guard.mjs
 * Built-in Node modules only. Never calls real connected tools or the network.
 * Do not change the production module's enabled:false; test activation is in memory only.
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';

const source = readFileSync(new URL('./inhost_readonly_bundle_DISABLED.mjs', import.meta.url), 'utf8');
const digest = (s) => createHash('sha256').update(s).digest('hex');
const EXPECTED_SOURCE_SHA = '763f0dc372ba5d1b7656c2accb597793eadafe386f948f67b2e3905b3e895338';
assert.equal(digest(source), EXPECTED_SOURCE_SHA, 'refuse unreviewed module bytes');
assert.equal(source.split('enabled: false').length, 2, 'one disabled gate required');
const TASK = '6ae8db67fef081919af59fecbf162552';
const RUN = '749bfbc9-73b8-8324-808c-5e3bf7d0592b';
const EVENT = 'github.pr30.1605ec459634f37cf5c30d7c3eba8b0ff5e8757de609e90326481e652e58fa33';
const HEAD = 'b6247c697157126c381feab9abfd0799b25a1571';

function peek(status = 'completed', overrides = {}) {
  const last = { id: RUN, recorded_status: status, scheduled_for: '2026-11-17T01:00:00Z',
    started_at: '2026-11-17T01:03:37Z', completed_at: status === 'completed' ? '2026-11-17T01:04:19Z' : null };
  const result = { run_id: RUN, scheduled_for: last.scheduled_for, created_at: '2026-11-17T01:04:18Z',
    completed_at: last.completed_at, content_text: '', content_truncated: false,
    requires_user_action: false, is_failure_message: false, ...overrides };
  return { automations: [{ id: TASK, is_enabled: true, timing_mode: 'exact_schedule',
    default_timezone: 'Asia/Seoul', run_details: { last_run: last, latest_result: result } }] };
}
function d1(rev = 17, overrides = {}) {
  const event = { event_key: EVENT, observed_at: '2026-11-15T06:57:30.992Z',
    observation: { head_sha: HEAD, security_run_id: 43679644021, security_conclusion: 'success' } };
  return { found: true, receipt_status: 'PASS', record_version: rev,
    record: { content_sha: rev === 18 ? 'e530a6361e8ce3657a9f270c56840018def83e14798e5b55427634c9ab6dc7a9' : 'd573de1ee07d1fa68924728e6c549d4ade44d1e8a995c3a6b09d4d75b82c6dd5',
      updated_at: '2026-11-16T21:30:42.987Z',
      value: JSON.stringify({ latest_evolution_cycle: event, canary_secret: 'CANARY_DO_NOT_LEAK' }) },
    ...overrides };
}
async function isolated({ enabled = false, peekValue = peek(), d1Value = d1(), exposeTools = true } = {}) {
  let peekCalls = 0, d1Calls = 0;
  const output = [];
  const fake = Object.freeze({
    mcp__Automations__peek: async (args) => { peekCalls++; assert.deepEqual(JSON.parse(JSON.stringify(args)), { jawbone_id: TASK }); return peekValue; },
    mcp__AI_________memory_read: async (args) => { d1Calls++; assert.deepEqual(JSON.parse(JSON.stringify(args)), { key: 'automation.evolving-ai.github-toolkit', history: false }); return d1Value; }
  });
  const sandbox = Object.create(null);
  sandbox.text = (s) => output.push(s);
  if (exposeTools) sandbox.tools = fake;
  // The only gate change is in-memory; the committed source is never edited.
  const script = enabled ? source.replace('enabled: false', 'enabled: true') : source;
  await vm.runInNewContext('(async () => {\n' + script + '\n})()', sandbox, { timeout: 2000 });
  assert.equal(output.length, 1, 'one sanitized result');
  assert.ok(output[0].startsWith('IN_HOST_READONLY '), 'expected typed result');
  const parsed = JSON.parse(output[0].slice('IN_HOST_READONLY '.length));
  assert.equal(parsed.verdict.auth, 'AUTH_UNVERIFIED');
  assert.equal(parsed.verdict.remote_write, 'NO_WRITE');
  assert.ok(peekCalls <= 1 && d1Calls <= 1, 'at most one read of each fake tool');
  assert.equal(output[0].includes('CANARY_DO_NOT_LEAK'), false, 'no raw secret leakage');
  return { parsed, peekCalls, d1Calls };
}

test('disabled source: zero mock calls', async () => {
  const r = await isolated();
  assert.equal(r.parsed.verdict.status, 'BLOCKED');
  assert.deepEqual([r.peekCalls, r.d1Calls], [0, 0]);
});
test('in-memory enable without capabilities fails closed', async () => {
  const r = await isolated({ enabled: true, exposeTools: false });
  assert.equal(r.parsed.verdict.reason, 'HOST_READ_CAPABILITY_UNAVAILABLE');
  assert.deepEqual([r.peekCalls, r.d1Calls], [0, 0]);
});
test('new completion, unchanged revision/event: NO_UPDATE with evidence controls', async () => {
  const r = await isolated({ enabled: true });
  assert.equal(r.parsed.verdict.status, 'NO_UPDATE');
  assert.deepEqual([r.peekCalls, r.d1Calls], [1, 1]);
});
test('r18 with unchanged event: UNVERIFIED, not NO_UPDATE; independent SHA', async () => {
  const r = await isolated({ enabled: true, d1Value: d1(18) });
  assert.equal(r.parsed.verdict.status, 'UNVERIFIED');
  assert.equal(r.parsed.verdict.reason, 'D1_REV_CHANGED_EVENT_UNCHANGED_CAUSE_UNVERIFIED');
  assert.equal(r.parsed.verdict.record_revision_changed, true);
  assert.equal(r.parsed.verdict.causal_attribution_verified, false);
  assert.equal(r.parsed.normalized_sha256, digest(JSON.stringify(r.parsed.normalized)));
  assert.deepEqual([r.peekCalls, r.d1Calls], [1, 1]);
});
test('in-progress gate: no D1 read, still UNVERIFIED', async () => {
  const r = await isolated({ enabled: true, peekValue: peek('in_progress') });
  assert.equal(r.parsed.verdict.status, 'UNVERIFIED');
  assert.deepEqual([r.peekCalls, r.d1Calls], [1, 0]);
});
test('truncated completed report fails closed before D1', async () => {
  const r = await isolated({ enabled: true, peekValue: peek('completed', { content_truncated: true }) });
  assert.equal(r.parsed.verdict.status, 'BLOCKED');
  assert.equal(r.parsed.verdict.reason, 'PEEK_RESULT_INCOMPLETE_OR_ACTION_REQUIRED');
  assert.deepEqual([r.peekCalls, r.d1Calls], [1, 0]);
});
