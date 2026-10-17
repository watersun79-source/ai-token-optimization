# ULTRA AI — Persistent Project Memory

Last verified: 2026-10-17 (Asia/Seoul)
Repository: https://github.com/watersun79-source/ai-token-optimization
Working branch: ultra-ai/progress-2026-10-17
Activepieces project: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/
Memory protocol: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/ULTRA-AI-memory-protocol.md
Coordinator log: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/scheduled-sequential-coordinator-tests-2026-10-17.md
Volume test log: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/find-records-volume-test-501-2026-10-17.md
Provider connection audit: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/provider-connection-audit-2026-10-17.md
Official capability review: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/official-capabilities-review-2026-10-17.md
Memory optimization progress: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/memory-optimization-progress-2026-10-17.md
Activepieces concurrency/BARRIER audit: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/activepieces-concurrency-barrier-audit-2026-10-17.md
Canonical custom instructions (987 characters): https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md
Duplicate display copy (987-character prompt): https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md

## Operating contract
- ULTRA AI loop: ANALYZE → CHECK → OPTIMIZE → EXECUTE → VERIFY → DEBUG → AUTO-FIX → RE-VERIFY → REPORT → NEXT GOAL.
- Korean informal, concise; use tables/progress indicators for status; distinguish verified, unknown and failed.
- Use internet for current/source-sensitive work; cite reliable sources.
- Check Gemini and Claude availability for every task; use both only when actually accessible through a free, cost-safe route. Never claim use without an observed call and response.
- GitHub is the durable project record for memory, decisions, prompts and tests; Slack tracks status, blockers and next goals. Update both after meaningful work.
- Free-first: no unverified/paid API calls, purchases, upgrades or uncertain billing.
- Never reveal or commit secrets, API keys, tokens or webhook credentials.
- Protect production flows, existing connections and hourly automation. New flow changes stay in disabled/unpublished drafts until independently verified.
- Use sample data only when live execution could incur cost or alter production; label sample tests clearly and clean temporary data afterward.
- On new chats, retrieve this index, protocol, latest progress log, and latest Slack ULTRA AI messages. On existing chats, use visible context and don't pretend external history is loaded if it isn't.
- Every report includes actual evidence, costs/API calls, cleanup, blockers and next actionable goal.

## Current state (verified 2026-10-17)
- Existing automation ULTRA AI enabled; schedule unchanged: hourly on the hour, Asia/Seoul.
- Five protected production Activepieces flows remain ENABLED/published; not edited or run.
- Mock-only coordinator draft EoQdyZftEyejxh4P85K5S is unpublished/disabled; latest validation 21/21 valid, 0 invalid, two informational empty-router fallback notes.
- Sample tests cover MERGE_READY, MERGE_CONFLICT, PROCESSED archival, TIMED_OUT handling, empty-table behavior and late-arrival recovery.
- Find Records volume tests: 101→101, 201→201, 501→501 (run U1Hqc2j98hqZuYEb3zNZf). All TESTING/sample data; all inserted rows deleted and follow-up searches returned 0.
- Final table counts: temporary registry 0 rows; temporary coordinator input 0 rows; prior mock results table 14 rows.
- Provider audit: Google Gemini read-only List Models succeeded once; billing tier unknown. Secondary Google Gemini api and Anthropic Claude connections failed read-only model-list authentication with HTTP 401 invalid key. No generation call made.
- Max Concurrent Jobs is project-wide; do not set it to 1 in the shared project because it could affect the five protected production flows.
- Unresolved: atomic unique/upsert/race safety in Tables; behavior beyond 501 records; hosted Cloud custom piece availability for BARRIER; Claude credential repair; Gemini free-tier/billing confirmation.
- Current optimization: canonical prompt and display copy synchronized to 987 characters. GitHub updates verified for both. ChatGPT Settings UI has not been modified; user must paste the prompt.
- Latest optimization task: Gemini/Claude generation calls 0; paid API calls 0; production flows and hourly automation unchanged.
- Official Activepieces review: BARRIER exists at the engine/piece API level; custom/private piece management is documented as paid at platform level. The public Tables action list does not establish atomic upsert/unique-key behavior. Table product page states up to 10,000 rows. See the concurrency/BARRIER audit.

## Official references
- ChatGPT Custom Instructions: https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions
- ChatGPT Memory: https://help.openai.com/en/articles/8590148-memory-and-projects
- ChatGPT Projects: https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt/
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini app limits: https://support.google.com/gemini/answer/16275805
- Claude API and subscription are separate: https://support.anthropic.com/en/articles/9876003-estoy-suscrito-a-un-plan-de-pago-de-claude-ai-por-que-tengo-que-pagar-por-separado-por-el-uso-de-la-api-en-console
- Activepieces Tables in flows: https://www.activepieces.com/docs/tables/in-flows
- Activepieces Find Records source: https://github.com/activepieces/activepieces/blob/main/packages/pieces/core/tables/src/lib/actions/find-records.ts
- Activepieces concurrency settings: https://www.activepieces.com/docs/admin-guide/guides/manage-concurrency
- Activepieces Flow Control: https://www.activepieces.com/docs/build-pieces/piece-reference/flow-control
- Activepieces Waitpoints: https://www.activepieces.com/docs/install/architecture/waitpoints

## Notes
- ChatGPT Free/Go custom-instruction limit: 1,500 characters. Canonical prompt is 987 characters by JavaScript string length.
- GitHub/Slack are persistence aids, not guaranteed automatic synchronization to every chat. Custom Instructions must be pasted into Settings by the user; this session did not directly change the Settings UI.
