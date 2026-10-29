/**
 * AI BOT v8.2.2 - evidence-bounded adaptive validation planner.
 * Pure offline logic. It never fetches, dispatches, publishes, or calls models.
 * CI records supplied by callers remain untrusted until independently checked.
 */
export const VERSION = "8.2.2";
const SHA = /^[a-f0-9]{40}$/;
const ALLOWED_EVENTS = Object.freeze({
  "validate.yml": new Set(["push", "pull_request", "workflow_dispatch"]),
  "ai-r16-hourly.yml": new Set(["schedule", "workflow_dispatch", "push"]),
});
const HOURS = 3_600_000;

function inspectRun(run, expectedSha, expectedWorkflow, now, hours, expectedCheckoutSha = null) {
  if (!run || typeof run !== "object") return { state: "UNVERIFIED", reason: "NO_OFFICIAL_RUN_EVIDENCE" };
  if (!Number.isSafeInteger(run.runId) || run.runId <= 0) return { state: "UNVERIFIED", reason: "INVALID_RUN_ID" };
  if (run.workflow !== expectedWorkflow || !ALLOWED_EVENTS[expectedWorkflow]?.has(run.event)) return { state: "UNVERIFIED", reason: "WORKFLOW_OR_EVENT_MISMATCH" };
  if (run.headSha !== expectedSha) return { state: "UNVERIFIED", reason: "SHA_MISMATCH" };
  // A pinned hourly audit is triggered at the main workflow SHA, but checks out another SHA.
  // Do not conflate GitHub run head_sha with checked-out source commit.
  if (expectedCheckoutSha && run.checkoutSha !== expectedCheckoutSha)
    return { state: "UNVERIFIED", reason: "PINNED_CHECKOUT_SHA_UNVERIFIED" };
  const stamp = Date.parse(run.createdAt);
  if (!Number.isFinite(stamp) || stamp > now + 120000) return { state: "UNVERIFIED", reason: "INVALID_RUN_CLOCK" };
  if (now - stamp > hours * HOURS) return { state: "UNVERIFIED", reason: "STALE_RUN" };
  if (run.status !== "completed") return { state: "UNVERIFIED", reason: "RUN_NOT_COMPLETED" };
  if (run.conclusion === "failure" || run.conclusion === "cancelled" || run.conclusion === "timed_out") {
    return { state: "FAILED", reason: "RUN_NOT_SUCCESSFUL", runId: run.runId };
  }
  if (run.conclusion !== "success") return { state: "UNVERIFIED", reason: "CONCLUSION_UNKNOWN" };
  return { state: "MATCHED_METADATA", reason: "CALLER_SUPPLIED_NOT_INDEPENDENTLY_ATTESTED", runId: run.runId };
}

export function planAdaptiveAudit(evidence, options = {}) {
  const now = Date.parse(options.now ?? new Date().toISOString());
  const ageHours = options.maxAgeHours ?? 24;
  const guards = Object.freeze({
    allowWrites: false,
    allowDispatch: false,
    allowPaidModels: false,
    allowSlackSending: false,
    changesMainOrPinnedSha: false,
    nativeRunProven: false,
  });
  const base = { version: VERSION, kind: "OFFLINE_ADAPTIVE_PLAN_NOT_EXECUTION",
    guards, nativeStatus: "UNVERIFIED", evidenceTrust: "CALLER_SUPPLIED_METADATA" };
  const sha1 = evidence?.mainSha, sha2 = evidence?.pinnedSha;
  if (!SHA.test(sha1 ?? "") || !SHA.test(sha2 ?? "") ||
      !Number.isFinite(now) || !Number.isFinite(ageHours) || ageHours <= 0 || ageHours > 168) {
    return { ...base, state: "BLOCKED", mode: "FAST", next: "CORRECT_INPUTS",
      reason: "INVALID_SHA_CLOCK_OR_AGE_LIMIT", mainCi: { state: "UNVERIFIED" },
      pinnedCi: { state: "UNVERIFIED" } };
  }
  // Incomplete, truncated, or non-canonical change lists cannot justify low risk.
  // Fail closed instead of dropping invalid paths (which could hide high-risk files).
  const suppliedPaths = evidence.changedPaths;
  const pathsComplete = Array.isArray(suppliedPaths) &&
    suppliedPaths.length > 0 && suppliedPaths.length <= 256 &&
    suppliedPaths.every(x => typeof x === "string" && x.length <= 512 &&
      x.length > 0 && !x.includes("\\") && !x.includes("\0") &&
      !x.startsWith("/") && x.split("/").every(part =>
        part.length > 0 && part !== "." && part !== ".."));
  const paths = pathsComplete ? suppliedPaths : null;
  // Missing or untrusted change scope is unknown, never silently treated as low risk.
  const risk = paths === null ? "UNKNOWN" :
    paths.length > 10 || paths.some(x =>
      x.startsWith(".github/workflows/") || x.startsWith("config/") ||
      x.startsWith("security/") || x.startsWith("tools/ai_memory_bridge")) ? "HIGH" :
    paths.some(x => x.startsWith("tools/") || x.startsWith("tests/")) ? "MEDIUM" : "LOW";
  const mainCi = inspectRun(evidence.mainCi, sha1, "validate.yml", now, ageHours);
  const pinnedCi = inspectRun(evidence.pinnedCi, sha1, "ai-r16-hourly.yml", now, ageHours, sha2);
  const parity = ["EXACT", "DIVERGED", "UNKNOWN"].includes(evidence.parity) ?
    evidence.parity : "UNKNOWN";
  // The default CROSS_SOURCE audit must preserve the pinned-source comparison.
  // MAIN_ONLY is a distinct planning scope and never authorizes skipping tests.
  const validationScope = options.validationScope === "MAIN_ONLY" ? "MAIN_ONLY" : "CROSS_SOURCE";
  let state = "NEEDS_EVIDENCE", mode = "FAST", next = "VERIFY_OFFICIAL_MAIN_CI",
      reason = mainCi.reason;
  if (mainCi.state === "FAILED") {
    state = "REQUIRES_ISOLATED_DEBUG"; mode = "FULL";
    next = "DIAGNOSE_MAIN_CI_ON_ISOLATED_BRANCH"; reason = "MAIN_CI_FAILED";
  } else if (mainCi.state === "MATCHED_METADATA") {
    if (validationScope === "CROSS_SOURCE" && sha1 !== sha2) {
      state = "REVIEW_SOURCE_PARITY"; mode = "FULL";
      next = parity === "EXACT" ? "VERIFY_SOURCE_PARITY_PROVENANCE" : "COMPARE_MAIN_AND_PINNED_SOURCE";
      reason = "SOURCE_PARITY_NOT_INDEPENDENTLY_VERIFIED";
    } else if (risk === "UNKNOWN") {
      state = "REVIEW_CHANGE_SCOPE"; mode = "FULL";
      next = "VERIFY_CHANGED_PATHS"; reason = "CHANGE_SCOPE_NOT_SUPPLIED";
    } else if (risk === "HIGH") {
      state = "REVIEW_HIGH_RISK"; mode = "FULL";
      next = "RUN_OFFLINE_FULL_CHECK_ON_ISOLATED_BRANCH"; reason = "RISK_BASED_ESCALATION";
    } else {
      // This module cannot fetch official run provenance. Matching caller metadata
      // may suggest a reuse candidate, but MUST NOT itself authorize skipping tests.
      state = "REUSE_CANDIDATE"; mode = "FAST";
      next = "VERIFY_OFFICIAL_MAIN_CI_BEFORE_REUSE";
      reason = "UNATTESTED_METADATA_CANNOT_AUTHORIZE_REUSE";
    }
  }
  return { ...base, state, mode, next, reason,
    mainCi, pinnedCi, risk, parity, validationScope, mainSha: sha1, pinnedSha: sha2 };
}
