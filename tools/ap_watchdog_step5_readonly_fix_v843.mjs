// Isolated candidate for Activepieces read-only watchdog step_5.
// Original source: connected Activepieces flow NAlirnBqHcQJ9nSuLzHii.
// Only two descriptive output strings changed. NOT deployed/published.
// This module is copy-compatible with an Activepieces CODE step after separate authorization.
// AI BOT v8.1 independent read-only watchdog; never dispatch/write or claim native attestation.
export const code = async (inputs) => {
  const is200 = x => x === 200 || x === '200';
  const isSha = x => typeof x === 'string' && /^[a-f0-9]{40}$/.test(x);
  const decode = v => { if (typeof v !== 'string') return v; try { return JSON.parse(v); } catch { return null; } };
  const raw = decode(inputs.scheduleBody);
  const schedule = raw && typeof raw === 'object' && Array.isArray(raw.workflow_runs) ? raw.workflow_runs : [];
  const latest = schedule[0] || null;
  const main = inputs.mainHead, isolated = inputs.isolatedHead;
  const workflowState = inputs.workflowState;
  const apiOk = [inputs.mainHttp,inputs.workflowHttp,inputs.scheduleHttp,inputs.isolatedHttp].every(is200);
  const shaOk = isSha(main) && isSha(isolated);
  const workflowOk = workflowState === 'active';
  const createdMs = latest ? Date.parse(latest.created_at) : NaN;
  const ageMin = Number.isFinite(createdMs) ? Math.round((Date.now()-createdMs)/60000) : null;
  const validLatest = !!latest && Number.isInteger(latest.id) && latest.event === 'schedule'
    && isSha(latest.head_sha) && Number.isFinite(createdMs)
    && ageMin >= -5 && latest.head_sha === main;
  const recent = validLatest && ageMin <= 85;
  let status='UNVERIFIED', reason='INVALID_API_OR_EVIDENCE';
  if(apiOk && shaOk && workflowOk && validLatest) {
    status = recent ? 'PASS' : 'WARN';
    reason = recent ? 'RECENT_GITHUB_SCHEDULE_RUN_OBSERVED' : 'GITHUB_SCHEDULE_GAP_OVER_85_MIN';
  } else if (apiOk && shaOk && workflowOk && schedule.length === 0) {
    status='WARN'; reason='NO_GITHUB_SCHEDULE_RUN_FOUND';
  } else if(apiOk && workflowState !== 'active') {
    status='WARN'; reason='GITHUB_WORKFLOW_NOT_ACTIVE';
  }
  return {
    kind:'AI_BOT_V81_INDEPENDENT_READONLY_WATCH_V1',
    status,reason,workflow_state:workflowState||'UNVERIFIED',
    scheduled_run_id:validLatest?latest.id:null,
    scheduled_run_event:latest?.event||null,
    scheduled_run_status:latest?.status||null,
    scheduled_run_conclusion:latest?.conclusion||null,
    scheduled_run_age_minutes:ageMin,
    schedule_head_sha:validLatest?latest.head_sha:null,
    main_head_sha:isSha(main)?main:null,
    isolated_head_sha:isSha(isolated)?isolated:null,
    api_http_200:apiOk,
    branch_sha_valid:shaOk,
    duplicate_dispatch_count:0,
    github_dispatch_executed:false,
    github_dispatch_blocker:'READ_ONLY_WATCHDOG_NO_DISPATCH_CONFIGURED',
    native_chatgpt_run_proven:false,
    same_native_run_github_slack_proven:false,
    remote_writes:0,
    external_llm_calls:0,
    next:'Read-only watchdog does not dispatch CI. Verify GitHub scheduled runs separately from the :30 recovery flow. Active GitHub connection metadata does not prove workflow_dispatch permission; preserve main and ChatGPT schedule.'
  };
};