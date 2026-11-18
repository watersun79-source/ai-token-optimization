/**
 * Isolated GitHub read gate for a future ChatGPT Site integration.
 *
 * Never uses fetch, credentials, SDKs or GitHub APIs itself. A trusted Site
 * runtime must supply its own connected-app reader as executable code, NOT
 * from an untrusted JSON claim. Its identity cannot be authenticated here.
 *
 * Neither 200 nor an imported reader may clear Site/native provenance gates.
 * No write, retry loop, global permission modification or deployment path.
 */

const FIXED_REQUEST = Object.freeze({
  repository: 'watersun79-source/ai-token-optimization',
  pull_request: 30,
  method: 'GET',
});
const MIN_REFRESH_MS = 180_000;
const DEFAULT_DENIAL_MS = 300_000;
const MAX_BACKOFF_MS = 3_600_000;
const SHA = /^[a-f0-9]{40}$/;

function finiteInt(value) {
  if (typeof value === 'number' && Number.isSafeInteger(value)) return value;
  if (typeof value === 'string' && /^\d{1,15}$/.test(value)) return Number(value);
  return null;
}

function getHeader(headers, name) {
  if (!headers || (typeof headers !== 'object' && typeof headers !== 'function')) return null;
  try {
    if (typeof headers.get === 'function') {
      const answer = headers.get(name);
      return typeof answer === 'string' ? answer : null;
    }
    const key = Object.keys(headers).find(x => x.toLowerCase() === name);
    return key && typeof headers[key] === 'string' ? headers[key] : null;
  } catch {
    return null;
  }
}

function cooldownFor(response, now) {
  const seconds = finiteInt(getHeader(response.headers, 'retry-after'));
  const reset = finiteInt(getHeader(response.headers, 'x-ratelimit-reset'));
  let delay = DEFAULT_DENIAL_MS;
  if (seconds !== null) delay = Math.max(delay, seconds * 1000);
  if (reset !== null && reset * 1000 > now) delay = Math.max(delay, reset * 1000 - now);
  return Math.min(MAX_BACKOFF_MS, delay);
}

function verdict(status, reason, {nextAllowedAt = null, sha = null, attempts = 0} = {}) {
  return Object.freeze({
    schema: 'PR31_SITE_GITHUB_READ_GATE_V1', status, reason,
    sha, nextAllowedAt, attempts,
    siteAuthentication: 'UNVERIFIED', siteRuntimeIntegration: 'UNVERIFIED',
    nativeGoal: 'UNVERIFIED', operationalClearance: 'BLOCKED',
    writes: 0, allowRetry: false, allowWrite: false,
  });
}

/**
 * Per-process gate; independent workers/tabs need a separate trusted shared
 * lease. No cross-process locking or official Sites runtime is asserted.
 */
export function createConnectedReadGate({clock = Date.now} = {}) {
  if (typeof clock !== 'function') throw new TypeError('clock must be a function');
  let nextAllowedAt = 0;
  let active = null;

  async function invoke(reader, now) {
    if (typeof reader !== 'function') {
      return verdict('BLOCKED', 'CONNECTED_READER_REQUIRED');
    }
    if (now < nextAllowedAt) {
      return verdict('DEFERRED', 'COOLDOWN_ACTIVE', {nextAllowedAt});
    }
    try {
      // Exactly one call to the injected reader; no raw authorization or URL.
      const response = await reader(FIXED_REQUEST);
      if (!response || typeof response !== 'object') {
        nextAllowedAt = now + DEFAULT_DENIAL_MS;
        return verdict('BLOCKED', 'PROVIDER_RESULT_INVALID', {nextAllowedAt, attempts: 1});
      }
      if (response.status === 403 || response.status === 429) {
        nextAllowedAt = now + cooldownFor(response, now);
        const remaining = getHeader(response.headers, 'x-ratelimit-remaining');
        return verdict('BLOCKED', remaining === '0' ? 'RATE_LIMIT_EXHAUSTED' : 'PROVIDER_DENIED',
                       {nextAllowedAt, attempts: 1});
      }
      if (response.status !== 200) {
        nextAllowedAt = now + DEFAULT_DENIAL_MS;
        return verdict('BLOCKED', 'UNEXPECTED_PROVIDER_STATUS', {nextAllowedAt, attempts: 1});
      }
      const sha = response.data?.head?.sha;
      if (typeof sha !== 'string' || !SHA.test(sha) || response.data?.number !== 30) {
        nextAllowedAt = now + DEFAULT_DENIAL_MS;
        return verdict('BLOCKED', 'PROVIDER_IDENTITY_OR_SHA_UNVERIFIED', {nextAllowedAt, attempts: 1});
      }
      // Even a well-formed 200 is not a Site/native provenance proof.
      nextAllowedAt = now + MIN_REFRESH_MS;
      return verdict('OBSERVED_UNVERIFIED', 'CONNECTED_READER_PROVENANCE_UNVERIFIED',
                     {nextAllowedAt, sha, attempts: 1});
    } catch {
      // Never leak tokens, secret URLs, exception text or provider responses.
      nextAllowedAt = now + DEFAULT_DENIAL_MS;
      return verdict('BLOCKED', 'PROVIDER_CALL_FAILED', {nextAllowedAt, attempts: 1});
    }
  }

  return Object.freeze({
    observe(reader) {
      const now = clock();
      if (!Number.isSafeInteger(now) || now < 0) {
        return Promise.resolve(verdict('BLOCKED', 'CLOCK_INVALID'));
      }
      if (active !== null) return active;
      // Set before the injected reader can run so parallel callers coalesce.
      const pending = Promise.resolve().then(() => invoke(reader, now));
      active = pending;
      void pending.finally(() => { if (active === pending) active = null; });
      return pending;
    },
  });
}
