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


## Protected-pin CI fail-closed exit gate — new isolated-only change

- Parent isolated HEAD: `6061368633ebea914e84a10986d8cd7451d52cf4`.
- GitHub original `main` commit patches reconfirm pin sequence `a551e6ecc290f625432aba7ce2f7c23cc6117a30` -> `353940b40b73b4001350ce07b323963bda14aa00` (commit `9097914284baf4896919e850c49690737d5715f3`) -> `a88c7993c27404da43cba84a8f69e01a917315a6` (commit `923c281f82023cc6b49f3844bad17f508f1ab203`). Both GitHub commits are attributed to account `watersun79-source`; the owner's explicit authorization remains UNVERIFIED.
- Discovered additional safety defect: isolated collector previously output `protected_pin_policy=FAIL` with top-level `status=UNVERIFIED`, but exited code 0, allowing a falsely green FAST job.
- Applied [`f69ef915193f891793704b85f2693fdd34f2a070`](https://github.com/watersun79-source/ai-token-optimization/commit/f69ef915193f891793704b85f2693fdd34f2a070), atomically modifying only `v81_live_schedule_collector.py` and `test_v81_live_schedule_collector.py`. New behavior: exit 1 if protected pin policy FAIL, while preserving `status=UNVERIFIED` for native attestation and exit 0 when protected pin matches. One positive regression added, existing mismatch CLI negative expectation corrected.
- Official [push Actions run `40195098743`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/40195098743) against exact head `f69ef915193f891793704b85f2693fdd34f2a070`: run **completed/failure, intentionally**. FAST job `121174125727`: **completed/failure**, solely because official read-only live schedule check detected protected pin mismatch. Original raw job log: `R16_V81_LIVE_SCHEDULE_CHECK` has `"reason":"PROTECTED_PIN_DRIFT"`, `"protected_pin_policy":"FAIL"`, `"status":"UNVERIFIED"` and `Process completed with exit code 1`. The collector unit suite printed `Ran 41 tests` and passed before the blocked live check.
- Same push run full regression job `121174125900`: **completed/success**, raw log confirms 100/100 local offline swarm PASS and Python/Java/JS/C isolated fixture evidence. It does NOT attest native ChatGPT or actual private v8.1 deployment.
- Separate guard-fast workflow of same SHA has independently verified passing fast job `121174125571`; do not treat this as permission to promote the failed protected-pin gate.

**Pass/fail interpretation:** detector behavior PASS; protected main pin policy FAIL; isolated full offline regressions PASS; trusted native unattended GitHub/Slack linkage UNVERIFIED. No rerun of previously successful identical SHA jobs.

**Safe next step:** do not modify main or the :15 schedule, checkout pin, ChatGPT :00 task, Activepieces, Slack or credentials. Seek explicit authorization before resolving main pin policy; after an authorized main change, verify GitHub official main workflow content and the next scheduled same-run original job checkout log. Retain the intentional red guard until protected pin parity is restored or explicit protected-baseline change is approved.


## SHA-only drift provenance checkpoint — new work (2026-10-25 KST)

**Purpose:** keep mismatch reporting fail-closed but include enough public, GitHub-authenticated SHA context to avoid redundant incident lookups. This does not fix or authorize a change to `main`.

- Isolated implementation commit [`f7b33f34786ca7882948903620ca395cc669fe46`](https://github.com/watersun79-source/ai-token-optimization/commit/f7b33f34786ca7882948903620ca395cc669fe46): safe typed `ProtectedPinDrift` retains `expected_source_sha`, `observed_source_sha`, `main_workflow_sha` in the `R16_V81_LIVE_SCHEDULE_CHECK` structured receipt. No credentials or file contents recorded, still `status=UNVERIFIED`, `protected_pin_policy=FAIL`, exit=1 on mismatch.
- Initial [push run `40195551696`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/40195551696) and [run `40195551766`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/40195551766) **FAILED** because one new positive test incorrectly asserted the already-existing successful `expected_source_sha` field must not be present. Raw failed job logs reproduce the exact assertion. This was a **new test defect**, not a protected pin mismatch being resolved.
- Exact one-line test correction committed as [`729b478716e6275d44e72900751526dc15c72955`](https://github.com/watersun79-source/ai-token-optimization/commit/729b478716e6275d44e72900751526dc15c72955). Correct positive path keeps its existing `expected_source_sha`; the new `observed_source_sha` and `main_workflow_sha` fields are drift-specific.
- Independently verified [official guarded CI run `40195649092`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/40195649092): event `push`, head `729b478716e6275d44e72900751526dc15c72955`, `completed/success`; jobs `121175788378` FAST `completed/success` and `121175870240` full `completed/success`. Raw fast job log: `Ran 70 tests`, `R16_V81_SWARM` FAST 20 PASS. Raw full job log: offline 100/100 PASS and `ISOLATED_OFFLINE_FAST_AND_FULL_ONLY=PASS`. This is not ChatGPT native proof.
- Independently verified [official source-pin policy CI run `40195649076`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/40195649076) at the **same SHA**: `completed/failure` by design (protected `main` checkout pin is different). Fast job `121175788459` raw output confirms unit suite `Ran 41 tests` PASS followed by structured `PROTECTED_PIN_DRIFT`, `expected_source_sha=a551e6ecc290f625432aba7ce2f7c23cc6117a30`, `observed_source_sha=a88c7993c27404da43cba84a8f69e01a917315a6`, `main_workflow_sha=923c281f82023cc6b49f3844bad17f508f1ab203`, exit=1. Full regression job `121175788232` `completed/success`, raw 100/100 PASS. The red policy gate is correct and **must not** be changed without owner approval.
- Main workflow at readback still uses `15 * * * *` and pinned checkout `a88c7993c27404da43cba84a8f69e01a917315a6`. Its protected original checkout remains `a551e6ecc290f625432aba7ce2f7c23cc6117a30`, so main parity remains **FAIL**. Official native ChatGPT same-run GitHub/Slack ledger remains **UNVERIFIED**; private v8.1 ZIP end-to-end deployment **UNVERIFIED**.

**Next one blocker:** owner approval or independent authorization record is required to reconcile main checkout pin; otherwise continue only safe isolated changes and per-run original read-only evidence. No modification of ChatGPT tasks, main, :15 cron, Activepieces, Slack, credentials, private ZIP or paid services.
