/**
 * v8.4.1 -- Neon AI Gateway fail-closed OFFLINE preflight.
 * No HTTP, Neon SDK calls, external models, secret output or environment writes.
 * "credential present" does NOT prove the credential is valid or billable models are available.
 *
 * Operator-supplied plan cannot verify a Neon billing balance. The actual plan and
 * prepaid credits must be read from an authoritative Neon account source.
 */
const MODEL = 'gpt-5-mini';
const MAX_COMPLETION_TOKENS = 256;

export function validateHost(baseURL) {
  if (typeof baseURL !== 'string' || !baseURL.trim()) {
    return { ok: false, reason: 'BASE_URL_MISSING' };
  }
  let url;
  try {
    url = new URL(baseURL);
  } catch {
    return { ok: false, reason: 'BASE_URL_INVALID' };
  }
  const host = url.hostname.toLowerCase();
  if (url.protocol !== 'https:' || url.username || url.password ||
      url.port || url.search || url.hash || (url.pathname !== '/' && url.pathname !== '') ||
      !/^br-[a-z0-9-]+-api\.ai\.[a-z0-9.-]+\.neon\.tech$/.test(host)) {
    return { ok: false, reason: 'BASE_URL_NOT_BRANCH_SCOPED_NEON_HTTPS_HOST' };
  }
  return { ok: true, endpoint: 'https://' + host + '/v1' };
}

export function buildCompletionRequest() {
  return {
    model: MODEL,
    messages: [
      { role: 'system', content: 'You are a helpful assistant.' },
      { role: 'user', content: 'What is Neon?' },
    ],
    max_completion_tokens: MAX_COMPLETION_TOKENS,
  };
}

export function preflight(env, { verifiedPlan = 'UNVERIFIED', credentialScopeVerified = false } = {}) {
  const host = validateHost(env?.NEON_AI_GATEWAY_BASE_URL);
  const tokenPresent = typeof env?.NEON_AI_GATEWAY_TOKEN === 'string' &&
    env.NEON_AI_GATEWAY_TOKEN.trim().length > 0;
  const planEligible = ['launch', 'scale'].includes(String(verifiedPlan).toLowerCase());
  const liveReady = host.ok && tokenPresent && planEligible && credentialScopeVerified;
  return {
    version: '8.4.1',
    check: 'NEON_GATEWAY_OFFLINE_PREFLIGHT',
    status: liveReady ? 'ELIGIBILITY_ONLY_NOT_LIVE_VERIFIED' : 'BLOCKED_FOR_LIVE_CALL',
    gateway_url_syntax_valid: host.ok,
    gateway_url_reason: host.ok ? 'PASS' : host.reason,
    local_token_env_present: tokenPresent,
    credential_scope_readback_verified: credentialScopeVerified,
    plan_from_connected_neon: verifiedPlan,
    paid_plan_eligible: planEligible,
    prepaid_credits_verified: false,
    configured_model: MODEL,
    configured_max_completion_tokens: MAX_COMPLETION_TOKENS,
    real_model_calls: 0,
    network_calls: 0,
    paid_usage_performed: false,
    // Do not return the bearer credential, env dump, or an OAuth authorization header.
  };
}

if (process.argv[1] && import.meta.url === new URL('file://' + process.argv[1]).href) {
  const selfTest = process.argv.includes('--self-test');
  const result = selfTest
    ? preflight({
        NEON_AI_GATEWAY_TOKEN: 'SYNTHETIC_PLACEHOLDER',
        NEON_AI_GATEWAY_BASE_URL: 'https://br-test-api.ai.c-3.ap-southeast-1.aws.neon.tech',
      }, { verifiedPlan: 'free', credentialScopeVerified: true })
    : preflight(process.env, { verifiedPlan: 'UNVERIFIED', credentialScopeVerified: false });
  if (selfTest) {
    result.probe = 'FAKE_TOKEN_NO_REAL_GATEWAY_CONTACT';
    result.test_passed = result.gateway_url_syntax_valid &&
      !result.paid_plan_eligible && result.network_calls === 0 && result.real_model_calls === 0;
  }
  console.log('NEON_V841_PREFLIGHT_JSON=' + JSON.stringify(result));
  if (selfTest && !result.test_passed) process.exitCode = 1;
}
