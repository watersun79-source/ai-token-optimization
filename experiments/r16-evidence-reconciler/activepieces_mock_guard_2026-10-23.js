// MOCK ONLY. Local, fail-closed metadata consistency checker.
// This step never calls GitHub, Slack, a model API, or a webhook.
export const code = async (inputs) => {
  const request = inputs && inputs.request;
  const result = (reason, more = {}) => ({
    status: 'UNVERIFIED', reason, official_success_verified: false,
    external_calls: 0, ...more,
  });
  if (!request || typeof request !== 'object' || Array.isArray(request))
    return result('Missing structured trigger payload');
  if (request.automation_id !== '6acb017062a08191a4136238b78b313a')
    return result('Protected ChatGPT automation ID mismatch');
  const time = v => typeof v === 'string' && /(?:Z|[+-]\d\d:\d\d)$/.test(v)
    ? Date.parse(v) : NaN;
  const slot = time(request.scheduled_for);
  if (!Number.isFinite(slot) || !/T\d\d:00:00(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(request.scheduled_for))
    return result('Invalid timezone-aware scheduled slot');
  const original = request.official_run;
  if (!original || typeof original !== 'object' ||
      original.origin !== 'official_task_run_details' ||
      typeof original.run_id !== 'string' || !original.run_id.trim())
    return result('Official per-run evidence is missing; latest_run_time is NOT proof');
  if (original.automation_id !== request.automation_id ||
      time(original.scheduled_for) !== slot ||
      !['completed','no_update'].includes(original.status))
    return result('Native run identity, slot, or terminal status mismatch');
  const start = time(original.started_at), end = time(original.completed_at);
  if (![start,end].every(Number.isFinite) || !(slot <= start && start <= end && end < slot + 3600000))
    return result('Run timestamps inconsistent');
  const checks = {
    current_handoff: {tool:'mcp__GitHub__fetch_file',locator:'docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md',pattern:/^[a-f0-9]{40}$/},
    slack_thread: {tool:'mcp__Slack__slack_read_thread',locator:'C0C9649RQAZ/1792416391.631669',pattern:/^\d{10}\.\d{6}$/},
  };
  const calls = Array.isArray(request.tool_calls) ? request.tool_calls : [];
  if (calls.length > 16) return result('Too many tool calls in untrusted evidence payload');
  const seen = new Set(), invocations = new Set();
  for (const c of calls) {
    // Reject inherited keys like constructor, toString, and __proto__.
    if (!c || typeof c !== 'object' || Array.isArray(c) || typeof c.target !== 'string' ||
        !Object.prototype.hasOwnProperty.call(checks, c.target) || seen.has(c.target)) continue;
    const cfg = checks[c.target], ts = time(c.observed_at);
    if (c.origin !== 'official_task_tool_call' || c.run_id !== original.run_id ||
        c.tool !== cfg.tool || c.locator !== cfg.locator || c.success !== true ||
        typeof c.version !== 'string' || !cfg.pattern.test(c.version) ||
        typeof c.invocation_id !== 'string' || !c.invocation_id ||
        invocations.has(c.invocation_id) || !Number.isFinite(ts) ||
        ts < start || ts > end) continue;
    seen.add(c.target); invocations.add(c.invocation_id);
  }
  const missing = Object.keys(checks).filter(k => !seen.has(k));
  if (missing.length) return result('Same-run tool-call evidence missing', {missing});
  return result('FORMAT_MATCH_ONLY: caller-supplied logs are not independently authenticated', {
    format_check: 'PASS', required_targets: [...seen], authenticity: 'UNVERIFIED',
  });
};
