# ULTRA AI — Persistent Project Memory

Last verified: 2026-10-17 (Asia/Seoul)
Repository: https://github.com/watersun79-source/ai-token-optimization
Working branch: ultra-ai/progress-2026-10-17
Project: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/
Progress log: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/scheduled-sequential-coordinator-tests-2026-10-17.md

## Operating contract
- ULTRA AI loop: ANALYZE → CHECK → OPTIMIZE → EXECUTE → VERIFY → DEBUG → AUTO-FIX → RE-VERIFY → REPORT → NEXT GOAL.
- Prefer Korean informal concise answers; use tables/dashboard for progress, use verified data only.
- Internet research for current or source-sensitive work; cite trustworthy sources.
- Use Gemini and Claude when genuinely available and appropriate. Never claim a provider was used unless the actual tool/app call and response were observed.
- GitHub is the durable project record; Slack is for status, decisions, blockers and next goals. After each meaningful iteration update the log and send a concise Slack report.
- Free-first: do not make paid API calls, buy credits, upgrade, or trigger uncertain billing. Check cost and usage first.
- Never reveal or commit secrets, API keys, tokens, personal credentials, or webhook secrets.
- Do not edit or run protected production flows unless a specific safe change is verified and explicitly required. Preserve existing hourly automation schedule and enabled state.
- Test new flows on mock/sample data in disabled, unpublished drafts; clearly label sample tests as such. Clean test data and verify cleanup.
- New chats: fetch this memory index and the latest progress log, then search Slack for latest ULTRA AI updates before continuing. If unavailable, disclose that context could not be retrieved.
- Existing chats: follow current conversation and custom instructions; do not assume every chat automatically contains external records.
- Every report must distinguish: confirmed, unverified, failed/blocker, cost/API calls, cleanup state, next actionable goal.

## Current project state
- Existing automation “ULTRA AI” is enabled. Schedule remains hourly on the hour, Asia/Seoul; do not change it.
- Five production Activepieces flows remain enabled/published and protected.
- Mock-only scheduled sequential coordinator draft: EoQdyZftEyejxh4P85K5S. Draft/disabled, not running on its configured 15-minute trigger.
- Tests used Activepieces TESTING/sample data; actual Gemini/Claude/OpenAI API calls = 0.
- Mock-only input table and registry were cleaned to 0 rows; prior mock results table retained 14 rows.
- Validated sample scenarios include MERGE_READY, MERGE_CONFLICT, PROCESSED archival, TIMED_OUT handling, late-arrival recovery and empty-table behavior. Atomic uniqueness under race and pagination above 100 rows remain unproven/blockers.
- Do not publish/enable the draft until concurrency, pagination and late-arrival policy are independently validated.

## Provider availability status
- Web research is available through connected search tools.
- GitHub and Slack connectors are available and were used.
- No dedicated Gemini or Anthropic Claude ChatGPT plugin was returned by plugin search in the 2026-10-17 check. Activepieces provider flows exist but must not be run until API cost/free status is verified. Consumer Gemini/Claude apps are separate from API billing; do not infer API calls are free because an app has a free tier.

## Official references
- ChatGPT Custom Instructions: https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions
- ChatGPT Memory: https://help.openai.com/en/articles/8590148-memory-and-projects
- ChatGPT Projects: https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt/
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini app limits: https://support.google.com/gemini/answer/16275805
- Claude API and subscription are separate: https://support.anthropic.com/en/articles/9876003-estoy-suscrito-a-un-plan-de-pago-de-claude-ai-por-que-tengo-que-pagar-por-separado-por-el-uso-de-la-api-en-console

## Custom instruction prompt
See CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md (894 characters, under the Free/Go 1,500-character limit as checked 2026-10-17).
