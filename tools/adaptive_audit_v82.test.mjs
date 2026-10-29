import test from "node:test";
import assert from "node:assert/strict";
import { VERSION, planAdaptiveAudit } from "./adaptive_audit_v82.mjs";
const A = "923c281f82023cc6b49f3844bad17f508f1ab203";
const B = "a88c7993c27404da43cba84a8f69e01a917315a6";
const now = "2026-10-30T00:00:00Z";
const valid = { runId: 55, workflow: "validate.yml", event: "push", headSha: A,
  status: "completed", conclusion: "success", createdAt: "2026-10-29T23:00:00Z" };
const base = { mainSha: A, pinnedSha: B, parity: "DIVERGED" };
function decide(extra = {}, config = {}) {
  return planAdaptiveAudit({ ...base, ...extra }, { now, ...config });
}
test("v8.2 and original resource guards", () => {
  assert.equal(VERSION, "8.2.2");
  const x = decide();
  assert.equal(x.guards.allowWrites, false);
  assert.equal(x.guards.allowDispatch, false);
  assert.equal(x.guards.allowPaidModels, false);
  assert.equal(x.guards.allowSlackSending, false);
  assert.equal(x.guards.nativeRunProven, false);
});
test("missing official main CI cannot be counted as success", () => {
  const x = decide();
  assert.equal(x.next, "VERIFY_OFFICIAL_MAIN_CI");
  assert.equal(x.mainCi.state, "UNVERIFIED");
});
test("main SHA mismatch fails closed", () => {
  const x = decide({ mainCi: { ...valid, headSha: B } });
  assert.equal(x.mainCi.reason, "SHA_MISMATCH");
  assert.equal(x.next, "VERIFY_OFFICIAL_MAIN_CI");
});
test("stale run requires new independent evidence", () => {
  const x = decide({ mainCi: { ...valid, createdAt: "2026-10-27T23:00:00Z" } });
  assert.equal(x.mainCi.reason, "STALE_RUN");
});
test("failed main CI escalates to isolated full debug", () => {
  const x = decide({ mainCi: { ...valid, conclusion: "failure" } });
  assert.equal(x.mode, "FULL");
  assert.equal(x.next, "DIAGNOSE_MAIN_CI_ON_ISOLATED_BRANCH");
});
test("fresh CI cannot erase divergent source parity", () => {
  const x = decide({ mainCi: valid });
  assert.equal(x.state, "REVIEW_SOURCE_PARITY");
  assert.equal(x.next, "COMPARE_MAIN_AND_PINNED_SOURCE");
});
test("caller-claimed parity cannot override different source SHA", () => {
  const x = decide({ mainCi: valid, parity: "EXACT", changedPaths: ["README.md"] });
  assert.equal(x.state, "REVIEW_SOURCE_PARITY");
  assert.equal(x.mode, "FULL");
  assert.equal(x.next, "VERIFY_SOURCE_PARITY_PROVENANCE");
});
test("matching metadata with identical SHA is only a reuse candidate", () => {
  const x = decide({ mainCi: valid, pinnedSha: A, parity: "EXACT", changedPaths: ["README.md"] });
  assert.equal(x.state, "REUSE_CANDIDATE");
  assert.equal(x.mode, "FAST");
  assert.equal(x.next, "VERIFY_OFFICIAL_MAIN_CI_BEFORE_REUSE");
});
test("missing changed paths fail closed, not low risk", () => {
  const x = decide({ mainCi: valid, pinnedSha: A, parity: "EXACT" });
  assert.equal(x.risk, "UNKNOWN");
  assert.equal(x.next, "VERIFY_CHANGED_PATHS");
});
test("workflow changes trigger full risk review", () => {
  const x = decide({ mainCi: valid, pinnedSha: A, parity: "EXACT",
    changedPaths: [".github/workflows/validate.yml"] });
  assert.equal(x.risk, "HIGH");
  assert.equal(x.mode, "FULL");
});
test("invented workflow name or future time is rejected", () => {
  let x = decide({ mainCi: { ...valid, workflow: "wrong.yml" } });
  assert.equal(x.mainCi.reason, "WORKFLOW_OR_EVENT_MISMATCH");
  x = decide({ mainCi: { ...valid, createdAt: "2026-10-31T01:00:00Z" } });
  assert.equal(x.mainCi.reason, "INVALID_RUN_CLOCK");
});
test("invalid input blocks and does not execute", () => {
  const x = planAdaptiveAudit({ mainSha: "wrong", pinnedSha: B }, { now });
  assert.equal(x.state, "BLOCKED");
  assert.equal(x.guards.allowWrites, false);
});
test("pinned offline evidence never certifies ChatGPT native", () => {
  const pinnedCi = { runId: 10, workflow: "ai-r16-hourly.yml",
    event: "workflow_dispatch", headSha: A, checkoutSha: B,
    status: "completed", conclusion: "success", createdAt: "2026-10-29T23:00:00Z" };
  const x = decide({ mainCi: valid, pinnedCi, parity: "EXACT" });
  assert.equal(x.pinnedCi.state, "MATCHED_METADATA");
  assert.equal(x.nativeStatus, "UNVERIFIED");
});

test("GitHub hourly head SHA and pinned checkout SHA are distinct evidence", () => {
  const pinnedCi = { runId: 101, workflow: "ai-r16-hourly.yml", event: "schedule",
    headSha: A, checkoutSha: B, status: "completed", conclusion: "success",
    createdAt: "2026-10-29T23:00:00Z" };
  assert.equal(decide({ pinnedCi }).pinnedCi.state, "MATCHED_METADATA");
  assert.equal(decide({ pinnedCi: { ...pinnedCi, checkoutSha: A } }).pinnedCi.reason,
    "PINNED_CHECKOUT_SHA_UNVERIFIED");
  assert.equal(decide({ pinnedCi: { ...pinnedCi, checkoutSha: undefined } }).pinnedCi.state,
    "UNVERIFIED");
});
test("validation workflow cannot claim unsupported schedule event", () => {
  const x = decide({ mainCi: { ...valid, event: "schedule" } });
  assert.equal(x.mainCi.reason, "WORKFLOW_OR_EVENT_MISMATCH");
  assert.equal(x.next, "VERIFY_OFFICIAL_MAIN_CI");
});
test("malformed run metadata is never an official attestation", () => {
  const spoofed = { ...valid, runId: -1 };
  const x = decide({ mainCi: spoofed, pinnedSha: A, parity: "EXACT", changedPaths: [] });
  assert.equal(x.mainCi.state, "UNVERIFIED");
  assert.notEqual(x.mode, "REUSE");
});

test("v8.2.2 invalid changed file lists cannot become low-risk evidence", () => {
  const candidate = { mainCi: valid, pinnedSha: A, parity: "EXACT" };
  for (const changedPaths of [
    [], ["README.md", null], ["README.md", ".github/workflows/x.yml", 42],
    ["./.github/workflows/a.yml"], ["../security/guard.mjs"],
    ["/security/guard.mjs"], ["docs\\..\\security\\guard.mjs"],
    Array.from({ length: 257 }, (_, i) => "docs/n" + i + ".md"),
  ]) {
    const x = decide({ ...candidate, changedPaths });
    assert.equal(x.risk, "UNKNOWN");
    assert.equal(x.state, "REVIEW_CHANGE_SCOPE");
    assert.equal(x.mode, "FULL");
  }
});
test("v8.2.2 canonical policy paths still escalate full review", () => {
  const x = decide({ mainCi: valid, pinnedSha: A, parity: "EXACT",
    changedPaths: ["README.md", "config/policy.json"] });
  assert.equal(x.risk, "HIGH");
  assert.equal(x.next, "RUN_OFFLINE_FULL_CHECK_ON_ISOLATED_BRANCH");
});
test("v8.2.2 MAIN_ONLY avoids unrelated pinned-source parity check", () => {
  const x = decide({ mainCi: valid, changedPaths: ["docs/notes.md"] },
    { validationScope: "MAIN_ONLY" });
  assert.equal(x.validationScope, "MAIN_ONLY");
  assert.equal(x.state, "REUSE_CANDIDATE");
  assert.equal(x.next, "VERIFY_OFFICIAL_MAIN_CI_BEFORE_REUSE");
  assert.equal(x.nativeStatus, "UNVERIFIED");
});
test("v8.2.2 default and unknown scopes must retain full source-parity gate", () => {
  for (const scope of [undefined, "UNSAFE", "CROSS_SOURCE"]) {
    const x = decide({ mainCi: valid, changedPaths: ["docs/notes.md"] },
      { validationScope: scope });
    assert.equal(x.validationScope, "CROSS_SOURCE");
    assert.equal(x.mode, "FULL");
    assert.equal(x.next, "COMPARE_MAIN_AND_PINNED_SOURCE");
  }
});
