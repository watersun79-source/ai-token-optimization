# ULTRA AI Registry Upsert Tests — 2026-10-17

## New mock-only state persistence
The draft flow `MOCK ONLY · Result Event Coordinator Draft` was extended to persist merge status in an isolated registry table.

- Flow: `48Zs1ORE6orHkB3hc4bwE`
- URL: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/48Zs1ORE6orHkB3hc4bwE
- Folder: `ULTRA AI MOCK Parallel`
- Registry table: `ULTRA AI Run Registry (MOCK ONLY)`
  - Internal ID: `K00AjPcx1xhUyDBfbV3Xr`
  - External ID: `Z94wVxMwv2YpISZYYJ4Vr`
- Flow behavior: find registry row by runId; if found, update it; if absent, create one. The router uses a non-empty-list check and an empty-list check.
- Folder validation after changes: `ok=true`, 1 flow, 0 issues.
- Flow is still a draft/unpublished and disabled; it has not been promoted to production.

## Synthetic tests
All ran in Activepieces TESTING with mocked table-trigger payloads. They do not prove that a real table event fires or that any live AI provider is called.

| Scenario | Run ID | Outcome |
|---|---|---|
| Empty results; create registry row | `Zah7Qam9CKcEhYpaBVjDM` | SUCCEEDED; `MERGE_INCOMPLETE`; created one registry row |
| Existing row; update registry row | `ahYTrPoinXUAPqLQOY5Kx` | SUCCEEDED; updated old status to `MERGE_INCOMPLETE` |
| Duplicate event for same runId | `390LWtyLpcS33CpGXvdoq` | SUCCEEDED; existing row updated, no second row created |
| Earlier partial reviewer sample | `UtrD3qcFxqhbec7rv6ZXk` | SUCCEEDED; `MERGE_PARTIAL` |
| Earlier no-results sample | `Y5AIwUdJu6pQHzBqV2LKO` | SUCCEEDED; `MERGE_INCOMPLETE` |

All reported `aiCallsMade=0` where returned by the merge step. Exact repeated event test found and updated the existing row by runId, demonstrating idempotent upsert behavior within this mock flow.

## Cleanup verified
- Temporary registry records deleted after tests.
- Registry table row count: 0.
- Coordinator input table row count: 0.
- Existing parallel results table row count: 14.
- All five protected production flows remain ENABLED and published; no production flow was edited or run.
- The current mock coordinator remains unpublished and disabled.
- Existing hourly automation schedule unchanged.

## Limitations and next steps
1. A genuine event-driven table trigger has not been proven in a live run because the flow remains unpublished/disabled.
2. No timeout/reconciliation sweep is implemented yet; absent results remain `MERGE_INCOMPLETE` until a later event causes the coordinator to re-evaluate that run.
3. Race conditions between two simultaneous first events could still create duplicate registry rows because Activepieces Tables does not enforce a unique constraint on `runId` in this design. The flow handles sequential duplicate events, but does not yet prove atomic concurrency safety.
4. Build a separate scheduled reconciliation/timeout flow and test late-result handling, duplicate run registry rows, malformed payloads, and race conditions in mock-only mode.
5. Keep all real AI/API calls at zero until free entitlement is verified. Do not upgrade, change production flows, alter the hourly schedule, or send Slack messages from test flows.

Last updated: 2026-10-17.
