# ULTRA AI Late-Arrival Recovery Test — 2026-10-17

## Scenario
A run was previously marked `TIMED_OUT`, then both Gemini and Claude synthetic results became available in the result table. The coordinator was re-run with a mock trigger event for the same runId.

## Test
- Coordinator flow: `MOCK ONLY · Result Event Coordinator Draft` (`48Zs1ORE6orHkB3hc4bwE`)
- Test run: `BZUKpce1OoVUkDb9uiUyv`
- Environment: Activepieces TESTING; mock trigger data only.
- Before: registry status `TIMED_OUT`; two valid synthetic reviewer rows.
- Merge step output: `MERGE_READY`, Gemini valid, Claude valid, 2 rows, 0 duplicates, 0 malformed rows, `aiCallsMade=0`.
- Registry update step changed existing row from `TIMED_OUT` to `MERGE_READY`; it did not create a new registry row.
- Result: SUCCEEDED in 1.9s.

## Cleanup
- Deleted synthetic Gemini/Claude result rows `x9L1Ud3nRttm1aQngabcK` and `P547kDF3dJRBqVsEQpAMp`.
- Deleted temporary registry row `QtqqM4CCeJ65FrKvOc8rt`.
- Verified afterward: registry table 0 rows; coordinator result table 0 rows; original mock results table 14 rows.

## What this proves / does not prove
- Proves in sample-data testing that the coordinator can recalculate a timed-out run and restore it to `MERGE_READY` when both valid reviewer results exist, using the existing registry row.
- Does NOT prove real Table trigger delivery, real scheduled execution, real AI provider calls, or concurrent atomicity. Both new mock flows remain unpublished and disabled.
- No paid API calls, live AI calls, external HTTP/webhooks, or production flow edits.

## Current draft links
- Coordinator: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/48Zs1ORE6orHkB3hc4bwE
- Timeout reconciler: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/Xyg0njk3QC8GBJltQpRnO
- GitHub branch: https://github.com/watersun79-source/ai-token-optimization/tree/ultra-ai/progress-2026-10-17

Last updated: 2026-10-17.
