import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { buildCompletionRequest, preflight, validateHost } from './neon_gateway_preflight_v841.mjs';

const valid = 'https://br-test-api.ai.c-3.ap-southeast-1.aws.neon.tech';
const token = 'SYNTHETIC_SHOULD_NEVER_LEAK_IN_OUTPUT';

test('allow legitimate branch-scoped Neon HTTPS base host', () => {
  assert.deepEqual(validateHost(valid + '/'), {
    ok: true, endpoint: valid + '/v1',
  });
});

test('reject non-https and lookalike hosts fail closed', () => {
  for (const url of [
    'http://br-test-api.ai.c-3.ap-southeast-1.aws.neon.tech',
    valid + '.attacker.invalid', 'https://evil.neon.tech',
    'https://neon.tech', 'https://user:pass@br-test-api.ai.c-3.ap-southeast-1.aws.neon.tech',
    valid + ':8443', valid + '/v1', valid + '?key=secret',
    valid + '#fragment', '//br-test-api.ai.c-3.ap-southeast-1.aws.neon.tech',
    '', 'hello',
  ]) assert.equal(validateHost(url).ok, false, url);
});

test('gpt-5-mini uses max_completion_tokens and one fixed input only', () => {
  const q = buildCompletionRequest();
  assert.equal(q.model, 'gpt-5-mini');
  assert.equal(q.max_completion_tokens, 256);
  assert.equal(Object.hasOwn(q, 'max_tokens'), false);
  assert.equal(q.messages.length, 2);
  assert.equal(q.messages[1].content, 'What is Neon?');
});

test('Free plan is NOT eligible despite a scoped credential and correct env', () => {
  const s = preflight({
    NEON_AI_GATEWAY_TOKEN: token,
    NEON_AI_GATEWAY_BASE_URL: valid,
  }, { verifiedPlan: 'free', credentialScopeVerified: true });
  assert.equal(s.status, 'BLOCKED_FOR_LIVE_CALL');
  assert.equal(s.local_token_env_present, true);
  assert.equal(s.paid_plan_eligible, false);
  assert.equal(s.prepaid_credits_verified, false);
  assert.equal(s.real_model_calls, 0);
  assert.equal(s.network_calls, 0);
  assert.ok(!JSON.stringify(s).includes(token));
});

test('missing secret blocks and never leaks credentials into errors', () => {
  const s = preflight({ NEON_AI_GATEWAY_BASE_URL: valid }, {
    verifiedPlan: 'launch', credentialScopeVerified: true,
  });
  assert.equal(s.local_token_env_present, false);
  assert.equal(s.status, 'BLOCKED_FOR_LIVE_CALL');
});

test('non-verified plan remains blocked for all valid-looking env values', () => {
  const s = preflight({NEON_AI_GATEWAY_BASE_URL: valid,NEON_AI_GATEWAY_TOKEN: token}, {
    credentialScopeVerified: true,
  });
  assert.equal(s.paid_plan_eligible, false);
  assert.equal(s.status, 'BLOCKED_FOR_LIVE_CALL');
});

test('eligible paid plan alone is not proof of prepaid balance or real success', () => {
  const s = preflight({NEON_AI_GATEWAY_BASE_URL: valid,NEON_AI_GATEWAY_TOKEN: token}, {
    verifiedPlan: 'scale',credentialScopeVerified: true,
  });
  assert.equal(s.status, 'ELIGIBILITY_ONLY_NOT_LIVE_VERIFIED');
  assert.equal(s.prepaid_credits_verified, false);
  assert.equal(s.real_model_calls, 0);
});

test('missing Neon scope blocks despite a paid plan and credentials', () => {
  const s = preflight({NEON_AI_GATEWAY_BASE_URL: valid,NEON_AI_GATEWAY_TOKEN: token}, {
    verifiedPlan: 'launch',credentialScopeVerified: false,
  });
  assert.equal(s.status, 'BLOCKED_FOR_LIVE_CALL');
});

test('the standalone self-test emits offline evidence without secrets', () => {
  const file = fileURLToPath(new URL('./neon_gateway_preflight_v841.mjs', import.meta.url));
  const out = execFileSync(process.execPath, [file, '--self-test'], {
    encoding: 'utf8',
    env: { PATH: process.env.PATH || '' },
  });
  const line = out.trim();
  assert.match(line, /^NEON_V841_PREFLIGHT_JSON=/);
  const probe = JSON.parse(line.split('=', 2)[1]);
  assert.equal(probe.test_passed, true);
  assert.equal(probe.paid_plan_eligible, false);
  assert.equal(probe.network_calls, 0);
  assert.equal(probe.real_model_calls, 0);
  assert.ok(!out.includes('SYNTHETIC_PLACEHOLDER'));
});
