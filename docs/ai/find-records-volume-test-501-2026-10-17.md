# AI Find Records Volume Test — 501 Rows (2026-10-17)

## Scope
- Flow: MOCK ONLY · Scheduled Sequential Coordinator Draft
- Flow ID: EoQdyZftEyejxh4P85K5S
- URL: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/EoQdyZftEyejxh4P85K5S
- Environment: Activepieces TESTING; sample/mock data only.
- Provider calls: Gemini 0, Claude 0, OpenAI 0.

## Test evidence
- Run ID: U1Hqc2j98hqZuYEb3zNZf
- Test status: SUCCEEDED.
- Target step: step_1 — Read synthetic reviewer events / Tables Find Records.
- ap_get_run confirmed step_1 status SUCCEEDED and outputCount=501.
- All 501 synthetic rows were inserted into AI Coordinator Results (MOCK ONLY) using batches of 50.
- Cleanup was split into safe batches because record search returns at most 500 records per query. First pass found 500 and deleted 250; follow-up found 251, deleted 251; final query returned 0.
- Final table counts: AI Run Registry (MOCK ONLY) = 0; AI Coordinator Results (MOCK ONLY) = 0; AI Parallel Results (MOCK ONLY) = 14.
- Flow validation after cleanup: 21/21 valid, 0 invalid. Two informational notes are intentional empty router fallbacks.
- Five protected production flows remain ENABLED/published. Existing hourly automation remains enabled with unchanged hourly schedule.

## Result
PASS — the flow's Find Records step returned all 501 rows in this Cloud sample-data test. This supersedes the earlier uncertainty for the 101/201-row cases. It does not prove behavior for arbitrarily large tables, and it does not solve atomic unique/upsert race safety on runId.

## Tool limit note
An earlier attempt to insert 501 rows in one orchestration script exceeded the per-script tool-call budget after 201 inserts. Those 201 partial rows were immediately deleted and verified absent. The successful test was then split across multiple calls. No 501-row flow test was run during the aborted attempt.

## Next goals
1. Investigate native atomic uniqueness/upsert support for runId; do not claim race-free behavior without proof.
2. Verify official hosted Cloud support for custom pieces exposing Waitpoints BARRIER.
3. Keep new flow unpublished/disabled until all relevant safety and concurrency conditions are proven.
