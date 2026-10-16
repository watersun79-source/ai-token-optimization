# ULTRA AI Barrier Investigation — 2026-10-17

## Decision
Do not use a guessed or undocumented barrier action in Activepieces Cloud. The Waitpoints page describes an engine-level BARRIER primitive and its internal piece-author API (`ctx.run.createWaitpoint` / `ctx.run.waitForWaitpoint`). The public Sub Flows piece catalog exposes only `Call Flow`, `Stream CSV to Subflows`, and `Return Response`. No supported user-facing Cloud barrier action was found in the exposed piece catalog.

Official references:
- Waitpoints architecture: https://www.activepieces.com/docs/install/architecture/waitpoints
- Sub Flows integration: https://www.activepieces.com/pieces/subflows
- Durable execution: https://www.activepieces.com/docs/install/architecture/durable-execution

## Mock-only join tests added to the evidence
All tests ran in Activepieces TESTING using synthetic input. They do not prove real trigger delivery or live AI provider calls.

| Scenario | Run ID | Result |
|---|---|---|
| No reviewer rows | `kBBTxEwp2lVyxsECXxD3d` | SUCCEEDED; `MERGE_INCOMPLETE`; 0 result rows |
| Claude only / Gemini missing | `qPulyuVVDtOkN1uFYtMq2` | SUCCEEDED; `MERGE_PARTIAL`; Claude valid, Gemini absent |
| Conflicting Gemini duplicate | `YSWiwcFWi7fW5MXeNJSVc` | SUCCEEDED; `MERGE_CONFLICT` |
| Identical Gemini duplicate | `hO7t0X4m0xMGel8aegCQ1` | SUCCEEDED; `MERGE_READY`; duplicate removed |
| Fan-out integration | `okPttnIcS3drLnO9J9JDx` | SUCCEEDED; 2 synthetic batches; first join already saw both results |

Every mock test reported `aiCallsMade: 0`.

## Cleanup and protection verification
- The synthetic partial-result row was deleted after testing.
- Result table `ULTRA AI Parallel Results (MOCK ONLY)` was verified back at 14 rows.
- All five production flows remained ENABLED and published; none was run or edited.
- Dispatcher remains unpublished; Join and Sink remain DISABLED.
- Existing `ULTRA AI` hourly automation schedule was not changed.

## Recommended supported fallback
Use a table-backed, event-driven coordinator rather than pretending a fixed delay is a barrier:
1. Each child flow writes one normalized result row keyed by a unique `runId` and reviewer.
2. A separate coordinator reacts to result-row creation (or a scheduled sweep) and checks the expected reviewer set, deduplicates exact repeats, and flags conflicts.
3. A separate timeout/reconciliation pass marks runs with missing reviewers as timed out/partial after an explicit deadline.
4. Keep the merge state machine idempotent; never overwrite a conflicting reviewer result silently.
5. Test all branches with synthetic data first; keep production flows untouched until a full test plan passes.

This fallback still needs an isolated coordinator/timeout flow and end-to-end mock tests. It is NOT yet implemented, published, or production-ready. Do not make real AI/API calls, external HTTP/webhook calls, paid upgrades, or Slack notifications from flows during this work.

## Direct links
- Activepieces Cloud: https://cloud.activepieces.com/
- Dispatcher: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/6H4aIpYiH11EQxT19DGYA
- Join: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/8SmBt6kUKHDbTrNcUvx9n
- Sink: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/c3fOAUS6aowwpdnsPoDN8

Last updated: 2026-10-17.
