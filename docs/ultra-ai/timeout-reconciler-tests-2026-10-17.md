# ULTRA AI Timeout Reconciler — 2026-10-17

## New draft
- Flow: `MOCK ONLY · Registry Timeout Reconciler Draft`
- ID: `Xyg0njk3QC8GBJltQpRnO`
- URL: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/Xyg0njk3QC8GBJltQpRnO
- Folder: `ULTRA AI MOCK Parallel`
- Trigger configuration: native Schedule cron `*/15 * * * *`, timezone `Asia/Seoul`.
- Current state: unpublished draft, disabled. The schedule is configured but is NOT active while the flow is disabled/unpublished.
- Timeout threshold: 10 minutes.
- Behavior: read up to 100 run registry records; skip `MERGE_READY`, `MERGE_CONFLICT`, and already-`TIMED_OUT` rows; identify stale partial/incomplete rows; loop over candidates and update their status to `TIMED_OUT`, recording the detection timestamp.

## Test result (synthetic test data only)
- Test run: `PfKtBkTJO7e8a6rpE9XHV`
- Result: SUCCEEDED in TESTING.
- Synthetic stale row `ultra-timeout-stale-final-20261017` (age 123 minutes) was identified and updated to `TIMED_OUT`.
- Synthetic recent row `ultra-timeout-recent-final-20261017` remained `MERGE_PARTIAL`.
- A preceding scanner test `FMBLVu8tW6qWr0yclEhFL` found exactly one stale candidate out of two test rows, proving the age threshold logic after fixing the cell lookup.
- All test calls used synthetic table records; no real AI provider calls, paid API calls, or external HTTP requests were made.

## Cleanup and safety verification
- Both temporary timeout-test rows were deleted.
- Run registry row count restored to 0.
- Coordinator input table row count is 0.
- Existing mock results table remains at 14 rows.
- Solution validation: `ULTRA AI MOCK Parallel`, 2 flows, all connections valid, 0 issues.
- All five production flows remain ENABLED and published; no production flow was changed or run.
- Existing hourly automation schedule was not changed.

## Known limits
1. The timeout reconciler has not been enabled; its schedule is only configured in the draft. Real scheduled execution is not yet verified.
2. Timeout handling is based on the registry's `updatedAt`. The coordinator currently sets this to the triggering row's creation timestamp, and the timeout flow updates it when marking a run timed out.
3. The run registry is not concurrency-atomic: simultaneous first events for the same `runId` may still create duplicate registry rows. Sequential duplicate events were tested and reused the existing row.
4. Real table-trigger delivery, late reviewer result policy after `TIMED_OUT`, and concurrent-run races remain to be tested before any production rollout.
5. Keep the flow unpublished/disabled until a deliberate mock test plan passes. No paid upgrades, live AI calls, production flow edits, or changes to the user's existing hourly schedule.

Last updated: 2026-10-17.
