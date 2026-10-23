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
  // Date.parse silently normalizes impossible dates (e.g. Feb 30 to Mar 2).
  // Validate every calendar/time component before computing a UTC instant.
  const time = v => {
    if (typeof v !== 'string' || v.length > 48) return null;
    const m = /^([12]\d{3})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?(Z|([+-])(\d{2}):(\d{2}))$/.exec(v);
    if (!m) return null;
    const year = +m[1], month = +m[2], day = +m[3];
    const hour = +m[4], minute = +m[5], second = +m[6];
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    const monthDays = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if (month < 1 || month > 12 || day < 1 || day > monthDays[month - 1] ||
        hour > 23 || minute > 59 || second > 59) return null;
    const zoneHour = m[10] === undefined ? 0 : +m[10];
    const zoneMinute = m[11] === undefined ? 0 : +m[11];
    if (zoneHour > 23 || zoneMinute > 59) return null;
    const offset = m[8] === 'Z' ? 0 : (m[9] === '+' ? 1 : -1) * (zoneHour * 60 + zoneMinute);
    // BigInt nanoseconds preserve exact ordering for 1–9 digit fractions.
    // This result is used only for comparisons; it is never JSON-serialized.
    const fractionNs = BigInt((m[7] || '0').padEnd(9, '0'));
    return BigInt(Date.UTC(year, month - 1, day, hour, minute, second)) * 1000000n
      - BigInt(offset) * 60000000000n + fractionNs;
  };
  const slot = time(request.scheduled_for);
  if (slot === null || !/T\d\d:00:00(?:\.0+)?(?:Z|[+-]\d\d:\d\d)$/.test(request.scheduled_for))
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
  if (start === null || end === null || !(slot <= start && start <= end && end < slot + 3600000000000n))
    return result('Run timestamps inconsistent');
  // Only these exact verified connector names are allowed. The alias spelling
  // can differ between ChatGPT scheduled Work and ordinary connected chats.
  const checks = {
    current_handoff: {
      tools:['mcp__GitHub__fetch_file','mcp__codex_apps__github_fetch_file'],
      locator:'docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md',pattern:/^[a-f0-9]{40}$/
    },
    slack_thread: {
      tools:['mcp__Slack__slack_read_thread','mcp__codex_apps__slack_slack_read_thread'],
      locator:'C0C9649RQAZ/1792416391.631669',pattern:/^\d{10}\.\d{6}$/
    },
  };
  const calls = Array.isArray(request.tool_calls) ? request.tool_calls : [];
  if (calls.length > 1024) return result('Too many tool calls in untrusted evidence payload');
  const seen = new Set(), invocations = new Set();
  for (const c of calls) {
    // Reject inherited keys like constructor, toString, and __proto__.
    if (!c || typeof c !== 'object' || Array.isArray(c) || typeof c.target !== 'string' ||
        !Object.prototype.hasOwnProperty.call(checks, c.target) || seen.has(c.target)) continue;
    const cfg = checks[c.target], ts = time(c.observed_at);
    if (c.origin !== 'official_task_tool_call' || c.run_id !== original.run_id ||
        !cfg.tools.includes(c.tool) || c.locator !== cfg.locator || c.success !== true ||
        typeof c.version !== 'string' || !cfg.pattern.test(c.version) ||
        typeof c.invocation_id !== 'string' || !c.invocation_id ||
        invocations.has(c.invocation_id) || ts === null ||
        ts < start || ts > end) continue;
    seen.add(c.target); invocations.add(c.invocation_id);
  }
  const missing = Object.keys(checks).filter(k => !seen.has(k));
  if (missing.length) return result('Same-run tool-call evidence missing', {missing});
  return result('FORMAT_MATCH_ONLY: caller-supplied logs are not independently authenticated', {
    format_check: 'PASS', required_targets: [...seen], authenticity: 'UNVERIFIED',
  });
};
