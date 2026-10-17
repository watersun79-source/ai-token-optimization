# ULTRA AI Scheduled Sequential Coordinator — Mock Verification (2026-10-17)

## Flow
- Name: `MOCK ONLY · Scheduled Sequential Coordinator Draft`
- ID: `EoQdyZftEyejxh4P85K5S`
- URL: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/EoQdyZftEyejxh4P85K5S
- Current state: unpublished draft, disabled. It is not executing on its configured schedule.
- Trigger configuration: Schedule `*/15 * * * *`, timezone `Asia/Seoul`.
- Validation: 21 steps, 21 valid, 0 invalid. Folder `ULTRA AI MOCK Parallel`: 3 flows, 0 connection/table issues.
- No live AI provider calls, paid API calls, external HTTP/webhooks, or test Slack messages.

## Architecture
1. Read pending coordinator result rows with status `OK`.
2. Read previously timed-out result rows.
3. Group by `runId`, validate synthetic reviewer payloads, deduplicate identical same-reviewer results, and detect conflicting same-reviewer results.
4. Process each run sequentially in one flow execution; update or create its registry row.
5. Mark result events `PROCESSED` for `MERGE_READY` or `MERGE_CONFLICT`.
6. Sweep registry rows; partial/incomplete runs older than 10 minutes become `TIMED_OUT`, and their source result events are marked `TIMED_OUT`.
7. If a new result arrives after timeout, the coordinator merges pending `OK` rows with earlier `TIMED_OUT` rows for the same runId. If both reviewer results are now available, the existing registry row returns to `MERGE_READY` and all included source rows become `PROCESSED`.

## Verified test evidence (sample data only)
- `CjAqqJezIJxrR4ehLBKF4`: two reviewer results grouped into one run; `MERGE_READY`.
- `I7hTCZXtjKoTZsagz7lk4`: successful result events changed to `PROCESSED`.
- `TVGbOHecou8LNVNgmAJKX` and `jqXZQuXNQHe1Hant9vRdp`: conflicting same-reviewer results produce `MERGE_CONFLICT`; all source rows marked `PROCESSED`.
- `AbwcGaQDUepezJBFiDtTB`: stale partial registry and its source event become `TIMED_OUT`.
- Late-arrival recovery:
  - `qzDZAB9Wvleow6TOgPo7l`: stale single-reviewer run became `TIMED_OUT`.
  - `Q68QOU6BW81R0qEGcZGmB`: a later complementary reviewer result was combined with the previously timed-out row; output `MERGE_READY`; existing registry row updated; both source rows marked `PROCESSED`.
- Empty-table regressions `KSKKnPagZw1xkWrVIvXbE`, `p7rQdKkuYvCuKvIAg9pno`, and `oOfjzLLLLOVFMzQPJUzTg`: successful, zero pending runs and zero timeout candidates.
- Concurrent test runs `loGEpgrO21v8Q21nsV7BL` and `gHjU4lLLXXipLfdqRib73`: one registry row was maintained in this sample. This does NOT prove database-level atomicity or rule out all races.

## Cleanup and safety
- After final tests: registry table row count 0; coordinator input table row count 0; original `ULTRA AI Parallel Results (MOCK ONLY)` remains at 14 rows.
- All five protected production flows remain ENABLED and published, untouched.
- New scheduled coordinator remains unpublished/disabled.
- Existing hourly ChatGPT automation remains enabled with its original hourly schedule; only its prompt was updated.

## Remaining limitations / next work
1. Activepieces Tables does not yet have a proven unique constraint or atomic upsert for `runId`; a concurrent first-run race remains theoretically possible. Keep the new flow disabled until official support or a safe concurrency guard is proven.
2. The new scheduled flow scans all pending and timed-out records without an explicit limit, but large-scale throughput and platform limits still need verification.
3. Real schedule-trigger delivery has not been proven because the flow is unpublished/disabled.
4. The mock data is intentionally synthetic; this does not prove Gemini/Claude provider execution or live trigger delivery.
5. Investigate official Waitpoints BARRIER / supported Cloud flow-control options without inventing actions or using undocumented endpoints.

Last updated: 2026-10-17.
