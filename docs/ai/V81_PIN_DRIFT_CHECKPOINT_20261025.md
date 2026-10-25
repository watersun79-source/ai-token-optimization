# AI BOT v8.1 — checkout pin drift, read-only evidence checkpoint (2026-10-25 KST)

Scope: evidence only. Not a native ChatGPT run, a production change, or permission to edit main.

## Verified GitHub connector facts

- Allowed isolated branch `ai/r16-v81-fast-full-ci-20261024`: HEAD `9f544677cf7b036d052af47057c40a8dd570129c` at inspection, compare to same SHA `identical` (0 new commits). Previous passing isolated checks are not rerun.
- Current `main/.github/workflows/ai-r16-hourly.yml` has exactly one schedule cron: `15 * * * *`. Fetched blob SHA: `8ab4b2f4b462619335ae3d004775a1abe77b4a5e`.
- **PROTECTED PIN DRIFT**: user-designated immutable checkout `a551e6ecc290f625432aba7ce2f7c23cc6117a30`; current main workflow checkout `a88c7993c27404da43cba84a8f69e01a917315a6`. These are different. This checkpoint did not cause this change and does not adjudicate whether an external actor authorized it.
- Previous official schedule run `40062975033`, job `120780236235`: GitHub job metadata reports completed/success. Original job log at 2026-10-24 04:36 UTC confirms checkout/ref `a551e6ecc290f625432aba7ce2f7c23cc6117a30` and `R16_HOURLY_OFFLINE_RECEIPT_VALIDATED`.
- Current workflow's pinned SHA `a88c7993c27404da43cba84a8f69e01a917315a6` is a GitHub commit with message `feat(v8.1): SHA-bound offline swarm and four-language evidence coordinator` dated 2026-10-25 04:35:37 UTC. A newer schedule run ID/job/log using this pin has NOT been authenticated in this checkpoint.
- Source-parity file separately states private original ZIP is not available on the public runner, not full verbatim v8.1 deployment.
- No official ChatGPT native per-run ID/status with same-run original GitHub + Slack tool-call ledger has been authenticated; unattended ChatGPT outcome remains **UNVERIFIED**.

## Verdict and next permitted action

| Target | Result |
|---|---|
| :15 cron entry preserved as read | PASS |
| User-designated `a551e6ec...` checkout still pinned | FAIL (observed different SHA) |
| Older schedule run metadata / job / raw checkout log | PASS (offline only) |
| Latest schedule run + raw job provenance for current pin | UNVERIFIED |
| Native ChatGPT unattended same-run app calls | UNVERIFIED |
| Original private ZIP fully deployed | UNVERIFIED |

**Next:** obtain the latest official schedule run list (event=schedule) and raw checkout log using an authorized read-only GitHub API/connector path; compare run event, head_sha and checked-out source, and obtain explicit owner approval before contemplating any change to the protected main pin. Do not equate offline success to native ChatGPT. Do not run a synthetic replacement schedule or trigger main manually.

Evidence links:
- https://github.com/watersun79-source/ai-token-optimization/blob/main/.github/workflows/ai-r16-hourly.yml
- https://github.com/watersun79-source/ai-token-optimization/actions/runs/40062975033
- https://github.com/watersun79-source/ai-token-optimization/commit/a88c7993c27404da43cba84a8f69e01a917315a6
- https://github.com/watersun79-source/ai-token-optimization/issues/8

No changes to main, ChatGPT task, Activepieces, Slack, credentials, or any other branch. No paid/LLM calls.


## Incremental root-cause and guard verification — 2026-10-25 (KST)

### Confirmed causal commits on main (GitHub original patches)
1. [`9097914284baf4896919e850c49690737d5715f3`](https://github.com/watersun79-source/ai-token-optimization/commit/9097914284baf4896919e850c49690737d5715f3): `ref: a551e6ecc290f625432aba7ce2f7c23cc6117a30` → `353940b40b73b4001350ce07b323963bda14aa00` (2026-10-25 03:54:16 UTC).
2. [`923c281f82023cc6b49f3844bad17f508f1ab203`](https://github.com/watersun79-source/ai-token-optimization/commit/923c281f82023cc6b49f3844bad17f508f1ab203): `ref: 353940b40b73b4001350ce07b323963bda14aa00` → `a88c7993c27404da43cba84a8f69e01a917315a6` (2026-10-25 04:40:00 UTC).

These GitHub patches establish **what changed and when**, not whether its authors had user approval. GitHub `main` was not modified during this checkpoint.

### Authenticated GitHub run/job/raw log
- [Schedule run `40194229228`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/40194229228): `event=schedule`, `head_sha=923c281f82023cc6b49f3844bad17f508f1ab203`, `completed/success`; job `121171517112` `completed/success`. GitHub original job log at 2026-10-25 12:41:32 UTC confirms checkout `a88c7993c27404da43cba84a8f69e01a917315a6`, receipt `R16_HOURLY_OFFLINE_RECEIPT_VALIDATED`, and offline unified 4-language + 20/100-rule evidence. This is NOT native ChatGPT or user-approved pin parity.
- [Isolated push CI run `40194538442`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/40194538442): `head_sha=b2ea27548d0ddd4f043c951353a3ff1c6536969a`, `event=push`, `completed/success`. Fast job `121172526368` and full job `121172526618` both `completed/success`.
- Fast job raw log shows `R16_V81_LIVE_SCHEDULE_CHECK={"status":"UNVERIFIED","reason":"PROTECTED_PIN_DRIFT","protected_pin_policy":"FAIL",...}`. The separate guard reports the policy violation **without treating offline CI success as proof that the protected pin matches**.

### Only-authorized-branch patch and regression
- [`7d0a1566ff54621a76ff4a0e4a224079476d2cab`](https://github.com/watersun79-source/ai-token-optimization/commit/7d0a1566ff54621a76ff4a0e4a224079476d2cab): fail-closed optional `protected_source_sha` validation in the read-only collector; mismatch blocks schedule-read promotion; malformed policy and protected+manual pair fail closed.
- [`95f13be7e075500afe936923ba30029e0f73b61d`](https://github.com/watersun79-source/ai-token-optimization/commit/95f13be7e075500afe936923ba30029e0f73b61d): five negative/positive unit tests.
- [`b2ea27548d0ddd4f043c951353a3ff1c6536969a`](https://github.com/watersun79-source/ai-token-optimization/commit/b2ea27548d0ddd4f043c951353a3ff1c6536969a): isolated workflow invokes the collector with protected `a551e6ecc290f625432aba7ce2f7c23cc6117a30`; no main change.
- The detector is **PASS** (it correctly detected drift) while the **protected source policy is FAIL** (main still differs). Both facts must be reported together.

### Remaining actionable next target
Keep schedule and native ChatGPT distinct. User approval/provenance for the two main edits is still **UNVERIFIED**. Owner must explicitly decide whether the original protected pin should be restored or the protection rule should be changed; do not make either change without authorization. Private ZIP full deployment and trusted native per-run connected GitHub/Slack ledger remain UNVERIFIED.
