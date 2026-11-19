/**
 * PR31 isolated safety gate for a Site host collector (NOT deployed Site code).
 * Consumes source-state observations only to DENY/DEFER requests, never to
 * attest Site authentication or authorize operational writes.
 * No fetch, tokens, cross-process lease, persistent state, or auto retry.
 */

const REPO = 'watersun79-source/ai-token-optimization';
const SCHEDULE_PREFIX = `https://api.github.com/repos/${REPO}/actions/workflows/ai-r16-hourly.yml/runs`;

function refusal(status, reason, retryAt = null) {
  return Object.freeze({
    schema: 'PR31_SITE_UPSTREAM_SOURCE_GUARD_V1', status, reason,
    nextRetryAt: retryAt,
    siteAuthentication: 'UNVERIFIED', nativeGoal: 'UNVERIFIED',
    operationalClearance: 'BLOCKED', allowRetry: false, allowWrite: false,
    externalMutations: 0,
  });
}

function checkedReset(reset) {
  if (typeof reset !== 'number' && !(typeof reset === 'string' && /^\d{1,12}$/.test(reset))) return null;
  const n = Number(reset);
  if (!Number.isSafeInteger(n) || n <= 0 || !Number.isSafeInteger(n * 1000)) return null;
  return n * 1000;
}

/** Consume the sync_status github_source_states as UNTRUSTED deny-only input. */
function inspectUpstreamSourceState(snapshot, now) {
  if (!Number.isSafeInteger(now) || now < 0) return refusal('BLOCKED', 'CLOCK_INVALID');
  const sources = snapshot?.github_source_states;
  const schedule = sources?.schedule;
  const isolated = sources?.isolated;
  if (!schedule || !isolated || typeof schedule !== 'object' || typeof isolated !== 'object') {
    return refusal('BLOCKED', 'SOURCE_STATE_MISSING');
  }
  const fault = schedule.last_error;
  if (fault?.http_status === 403 && fault?.reason === 'PRIMARY_RATE_LIMIT' &&
      fault?.authentication === 'NONE' && fault?.remaining === 0) {
    // No trust is gained from a timestamp; even after reset a fresh official
    // authenticated source read is mandatory before future operations.
    const reset = checkedReset(fault.reset);
    const pinned = typeof fault.endpoint === 'string' &&
      (fault.endpoint === SCHEDULE_PREFIX || fault.endpoint.startsWith(SCHEDULE_PREFIX + '?'));
    if (!pinned) return refusal('BLOCKED', 'UPSTREAM_403_ENDPOINT_UNVERIFIED');
    if (reset !== null && now < reset) return refusal('DEFERRED', 'UPSTREAM_PRIMARY_RATE_LIMIT', reset);
    return refusal('BLOCKED', 'UPSTREAM_STALE_REQUIRES_FRESH_EVIDENCE');
  }
  if (isolated.status !== 'PASS' || isolated.stale !== false) {
    return refusal('BLOCKED', 'UPSTREAM_BACKOFF_OR_STALE');
  }
  if (schedule.status !== 'PASS' || schedule.stale !== false) {
    return refusal('BLOCKED', 'SCHEDULE_SOURCE_NOT_FRESH');
  }
  // PASS here is an input sanity check, NOT a proof of Site/native auth.
  return refusal('UNVERIFIED', 'READ_PERMITTED_ONLY_IN_AUTHORIZED_ISOLATED_HOST');
}

/** Fail closed on accessor/proxy errors from untrusted source-state objects. */
export function checkUpstreamSourceState(snapshot, now) {
  try { return inspectUpstreamSourceState(snapshot, now); }
  catch { return refusal('BLOCKED', 'SOURCE_STATE_ACCESS_FAILED'); }
}

/** Attach before an existing PR31 site_host_collector_bridge readOnce(). */
export async function guardedSiteRead({snapshot, hostCollector, clock = Date.now} = {}) {
  let now;
  try { now = clock(); } catch { return refusal('BLOCKED', 'CLOCK_INVALID'); }
  const preflight = checkUpstreamSourceState(snapshot, now);
  if (preflight.status !== 'UNVERIFIED') return preflight;
  let readOnce;
  try { readOnce = hostCollector?.readOnce; }
  catch { return refusal('BLOCKED', 'SITE_HOST_COLLECTOR_ACCESS_FAILED'); }
  if (typeof readOnce !== 'function') {
    return refusal('BLOCKED', 'SITE_HOST_COLLECTOR_MISSING');
  }
  try {
    const result = await readOnce.call(hostCollector);
    // A host-supplied result cannot promote Site/operational permissions.
    if (!result || typeof result !== 'object') return refusal('BLOCKED', 'COLLECTOR_RESULT_INVALID');
    const sourceStatus = ['BLOCKED', 'DEFERRED', 'UNVERIFIED'].includes(result.status)
      ? result.status : 'UNVERIFIED';
    const reason = sourceStatus === 'BLOCKED' ? 'HOST_COLLECTOR_BLOCKED'
      : sourceStatus === 'DEFERRED' ? 'HOST_COLLECTOR_DEFERRED'
      : 'HOST_COLLECTOR_RESULT_NOT_OPERATING_PROOF';
    return Object.freeze({ ...refusal(sourceStatus, reason), sourceStatus });
  } catch {
    return refusal('BLOCKED', 'HOST_COLLECTOR_FAILED');
  }
}
