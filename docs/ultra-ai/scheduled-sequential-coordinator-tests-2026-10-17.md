# ULTRA AI Scheduled Sequential Coordinator — Test Log 2026-10-17

## Flow
- Name: `MOCK ONLY · Scheduled Sequential Coordinator Draft`
- ID: `EoQdyZftEyejxh4P85K5S`
- URL: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/EoQdyZftEyejxh4P85K5S
- Trigger: native Schedule, `*/15 * * * *`, timezone `Asia/Seoul`.
- State: unpublished draft and disabled. Schedule is configured but not active.
- Validation: 20 steps, 20 valid, 0 invalid. Solution folder `ULTRA AI MOCK Parallel`: 3 flows, no connection/table issues.
- No real AI calls, no paid API calls, no external HTTP/webhooks, no Slack sends in flow tests.

## Implemented in draft
1. Read pending synthetic reviewer result rows with status `OK`.
2. Group by `runId`; validate mock contract; detect identical duplicates, conflicting same-reviewer responses, malformed data.
3. Process run groups sequentially inside one flow execution.
4. Upsert a run registry row.
5. Archive source events for `MERGE_READY` or `MERGE_CONFLICT` by changing their status to `PROCESSED`.
6. Sweep registry for partial/incomplete entries older than 10 minutes; set stale registry rows to `TIMED_OUT` and source events to `TIMED_OUT`.

## Successful sample-data tests
- `CjAqqJezIJxrR4ehLBKF4`: two reviewer rows → `MERGE_READY`; creates registry row.
- `7ToJ7jVafthq0sMUxJigf`: repeated scheduled scan → existing registry row updated; no new row for that runId.
- `I7hTCZXtjKoTZsagz7lk4`: completed source events both changed to `PROCESSED`.
- `TVGbOHecou8LNVNgmAJKX` and `jqXZQuXNQHe1Hant9vRdp`: conflicting Gemini duplicates → `MERGE_CONFLICT`; all related source rows archived as `PROCESSED`.
- `AbwcGaQDUepezJBFiDtTB`: stale partial row (250+ minutes) → registry `TIMED_OUT`, corresponding source row `TIMED_OUT`.
- `KSKKnPagZw1xkWrVIvXbE` and `p7rQdKkuYvCuKvIAg9pno`: empty tables processed safely, 0 runs and 0 timeout candidates.
- `loGEpgrO21v8Q21nsV7BL` and `gHjU4lLLXXipLfdqRib73`: simultaneous sample runs each succeeded and both saw the same registry row after the first creation. This does NOT prove atomic uniqueness; concurrency safety remains unproven.

## Cleanup verified
- Registry table `ULTRA AI Run Registry (MOCK ONLY)`: 0 rows.
- Coordinator input table `ULTRA AI Coordinator Results (MOCK ONLY)`: 0 rows.
- Existing table `ULTRA AI Parallel Results (MOCK ONLY)`: 14 rows retained.
- All temporary records from the above tests removed.
- Five protected production flows remain ENABLED and published; no production flow was edited or run.
- Existing hourly automation `ULTRA AI` remains enabled with unchanged `RRULE:FREQ=HOURLY;BYMINUTE=0;BYSECOND=0`, timezone Asia/Seoul. Its prompt was updated to include next steps; schedule and enabled state unchanged.

## Remaining blockers / next steps
1. Late-arrival recovery in the scheduled flow is not yet fully proven. Current event filter only reads status `OK`; once a row is marked `TIMED_OUT`, a late result needs a deliberate re-entry/reopen policy. Add and test this safely before any rollout.
2. Activepieces Tables does not yet have a proven atomic unique constraint/upsert on `runId`; simultaneous first events could theoretically create duplicate registry rows. Do not claim race-free behavior.
3. The 100-row read cap needs pagination or safe batching before large-scale use.
4. Official Waitpoints BARRIER docs exist at https://www.activepieces.com/docs/install/architecture/waitpoints, but the available Cloud piece catalog did not expose a supported barrier action in earlier discovery. Continue checking official docs and do not invent an action name.
5. Keep this flow unpublished/disabled until late-arrival handling, paging, and concurrency policy are verified. No paid upgrade, real AI call, external webhook, production flow edit, or existing hourly schedule change.

Last updated: 2026-10-17.
