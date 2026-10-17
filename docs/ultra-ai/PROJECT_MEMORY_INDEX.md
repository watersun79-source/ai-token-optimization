# ULTRA AI — Persistent Project Memory

Last verified: 2026-10-17 (Asia/Seoul)
Repository: https://github.com/watersun79-source/ai-token-optimization
Working branch: ultra-ai/progress-2026-10-17
Activepieces project: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/
Coordinator log: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/scheduled-sequential-coordinator-tests-2026-10-17.md
Official capability review: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/official-capabilities-review-2026-10-17.md
Custom instructions (859 characters): https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md

## Operating contract
- ULTRA AI loop: ANALYZE → CHECK → OPTIMIZE → EXECUTE → VERIFY → DEBUG → AUTO-FIX → RE-VERIFY → REPORT → NEXT GOAL.
- Korean informal, concise; use tables/progress indicators for status; distinguish verified, unknown and failed.
- Use internet for current/source-sensitive work; cite reliable sources.
- For complex work, check both Gemini and Claude availability. Use both when actually connected and free/cost-safe. Never claim use without an observed call and response.
- GitHub is the durable project record for memory, decisions, prompts and tests; Slack tracks status, blockers and next goals. Update both after meaningful work.
- Free-first: no unverified/paid API calls, purchases, upgrades or uncertain billing.
- Never reveal or commit secrets, API keys, tokens or webhook credentials.
- Protect production flows, existing connections and hourly automation. New flow changes stay in disabled/unpublished drafts until independently verified.
- Use sample data only when live execution could incur cost or alter production; label sample tests clearly and clean temporary data afterward.
- On new chats, retrieve this index, latest progress log, and latest Slack ULTRA AI messages. On existing chats, use visible context and don't pretend external history is loaded if it isn't.
- Every report includes actual evidence, costs/API calls, cleanup, blockers and next actionable goal.

## Current state (verified 2026-10-17)
- Existing automation ULTRA AI enabled; schedule unchanged: hourly on the hour, Asia/Seoul.
- Five protected production Activepieces flows remain ENABLED/published; not edited or run.
- Mock-only coordinator draft: EoQdyZftEyejxh4P85K5S, unpublished/disabled; configured every 15 minutes but not running on an active schedule.
- Latest validation: 21/21 steps valid, 0 invalid; two informational notes about intentionally empty router fallback branches. Mock solution folder: 3 flows, 0 connection/table errors.
- Sample tests cover MERGE_READY, MERGE_CONFLICT, PROCESSED archival, TIMED_OUT handling, empty-table behavior and late-arrival recovery. Late-recovery sample run: Q68QOU6BW81R0qEGcZGmB; previous timeout run: qzDZAB9Wvleow6TOgPo7l.
- Find Records volume tests: 101 synthetic rows returned 101 (run 23OiaT74UbUlYEwgMG2pC); 201 synthetic rows returned 201 (run 67gFJzZanE68mLswLpMQn). Both were TESTING/sample-data runs; all inserted rows were deleted and follow-up queries returned 0. A separate attempt to insert 501 rows was interrupted after 201 rows by the orchestration tool call budget; those 201 partial rows were immediately deleted and verified gone. No 501-row flow test ran.
- Final table state: temporary registry 0 rows; temporary coordinator input 0 rows; prior mock results table remains at 14 rows.
- Actual Gemini/Claude/OpenAI API calls during these tests: 0.
- Unresolved: atomic unique/upsert/race safety in Tables; behavior beyond 201 records; whether a custom piece can be installed in hosted Cloud to expose BARRIER.

## Provider and connector availability
- Internet research tools, GitHub and Slack connectors available and used.
- Plugin search on 2026-10-17 returned no dedicated Gemini or Anthropic Claude ChatGPT plugin. Activepieces provider flows must not be run until API cost/free status is verified.
- Gemini consumer app access differs from Gemini API billing. Claude consumer app subscription differs from API Console billing. Do not call provider APIs until free access and billing status are verified.
- If Gemini/Claude cannot be directly called in this environment, report the blocker; do not use fake outputs or run production flows to simulate them.

## Official references
- ChatGPT Custom Instructions: https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions
- ChatGPT Memory: https://help.openai.com/en/articles/8590148-memory-and-projects
- ChatGPT Projects: https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt/
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini app limits: https://support.google.com/gemini/answer/16275805
- Claude API and subscription are separate: https://support.anthropic.com/en/articles/9876003-estoy-suscrito-a-un-plan-de-pago-de-claude-ai-por-que-tengo-que-pagar-por-separado-por-el-uso-de-la-api-en-console
- Activepieces Tables in flows: https://www.activepieces.com/docs/tables/in-flows
- Activepieces Find Records source: https://github.com/activepieces/activepieces/blob/main/packages/pieces/core/tables/src/lib/actions/find-records.ts
- Activepieces Flow Control: https://www.activepieces.com/docs/build-pieces/piece-reference/flow-control
- Activepieces Waitpoints: https://www.activepieces.com/docs/install/architecture/waitpoints

## Notes
- ChatGPT Free/Go custom-instruction limit: 1,500 characters. Prompt file is 859 characters by JS string length, under limit.
- GitHub/Slack are persistence aids, not guaranteed automatic synchronization to every chat. ChatGPT custom instructions should be pasted into Settings by the user; this session did not directly change the settings UI.
