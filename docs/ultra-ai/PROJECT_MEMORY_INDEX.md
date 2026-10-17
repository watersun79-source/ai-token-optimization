# AI — Persistent Project Memory

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
Canonical custom instructions (1010 characters): https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md
Duplicate display copy (1010-character prompt): https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md

## Operating contract
- AI loop: ANALYZE → CHECK → OPTIMIZE → EXECUTE → VERIFY → DEBUG → AUTO-FIX → RE-VERIFY → REPORT → NEXT GOAL.
- Korean informal, concise; use tables/progress indicators for status; distinguish verified, unknown and failed.
- Use internet for current/source-sensitive work; cite reliable sources.
- Check Gemini and Claude availability for every task; use both only when actually accessible through a free, cost-safe route. Never claim use without an observed call and response.
- GitHub is the durable project record for memory, decisions, prompts and tests; Slack tracks status, blockers and next goals. Update both after meaningful work.
- Free-first: no unverified/paid API calls, purchases, upgrades or uncertain billing.
- Never reveal or commit secrets, API keys, tokens or webhook credentials.
- Protect production flows, existing connections and hourly automation. New flow changes stay in disabled/unpublished drafts until independently verified.
- Use sample data only when live execution could incur cost or alter production; label sample tests clearly and clean temporary data afterward.
- On new chats, retrieve this index, protocol, latest progress log, and latest Slack AI messages. On existing chats, use visible context and don't pretend external history is loaded if it isn't.
- Every report includes actual evidence, costs/API calls, cleanup, blockers and next actionable goal.

## Current state (verified 2026-10-17)
- Existing automation AI enabled; schedule unchanged: hourly on the hour, Asia/Seoul.
- Five protected production Activepieces flows remain ENABLED/published; not edited or run.
- Mock-only coordinator draft EoQdyZftEyejxh4P85K5S is unpublished/disabled; latest validation 21/21 valid, 0 invalid, two informational empty-router fallback notes.
- Sample tests cover MERGE_READY, MERGE_CONFLICT, PROCESSED archival, TIMED_OUT handling, empty-table behavior and late-arrival recovery.
- Find Records volume tests: 101→101, 201→201, 501→501 (run U1Hqc2j98hqZuYEb3zNZf). All TESTING/sample data; all inserted rows deleted and follow-up searches returned 0.
- Final table counts: temporary registry 0 rows; temporary coordinator input 0 rows; prior mock results table 14 rows.
- Provider audit: Google Gemini read-only List Models succeeded once; billing tier unknown. Secondary Google Gemini api and Anthropic Claude connections failed read-only model-list authentication with HTTP 401 invalid key. No generation call made.
- Max Concurrent Jobs is project-wide; do not set it to 1 in the shared project because it could affect the five protected production flows.
- Unresolved: atomic unique/upsert/race safety in Tables; behavior beyond 501 records; hosted Cloud custom piece availability for BARRIER; Claude credential repair; Gemini free-tier/billing confirmation.
- Current optimization (2026-10-17): canonical prompt and display copy updated to 1010-character instruction body (within 1,500-character limit); both files read back and confirmed to include GitHub+Slack as first priority and free Gemini/Claude consumer apps as second priority. ChatGPT Settings UI has not been modified by this workflow; user must paste the prompt into Settings to apply it.
- Latest optimization task: Gemini/Claude generation calls 0; paid API calls 0; production flows and hourly automation unchanged.
- Official Activepieces review: BARRIER exists at the engine/piece API level; custom/private piece management is documented as paid at platform level. The public Tables action list does not establish atomic upsert/unique-key behavior. Table product page states up to 10,000 rows. See the concurrency/BARRIER audit.

## Latest cross-chat memory check (2026-10-17)
- Internet: OpenAI official Custom Instructions FAQ confirms instructions apply across chats including existing conversations when enabled, and Go/Free have a 1,500-character limit. Chat history/memory may not retain every detail; external GitHub/Slack records require explicit retrieval.
- Gemini/Claude: consumer-web-app generation was not performed this turn because the connected browser context is unavailable. Existing provider audit still shows Gemini free/billing status unknown and prior secondary Gemini/Claude API diagnostics HTTP 401. Generation calls 0; paid API calls 0.
- Slack recent history read successfully before this update; next action is post a concise sync/verification report after read-back.

## Latest memory optimization (2026-10-17)
- Canonical prompt and display copy synchronized to 992 JavaScript characters; exact body match verified in the continuation pass.
- Every task's procedure: internet search; actual attempt to use free Gemini and Claude web apps; read GitHub memory protocol/index/latest report and Slack channel C0C9649RQAZ; record results to both and read back. Do not pretend inaccessible models were used.
- Current provider blocker: no originating browser context for consumer web apps; previous secondary Gemini and Claude API diagnostics returned HTTP 401; free/billing state not verified. Generation calls 0; paid API calls 0.

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
- ChatGPT Free/Go custom-instruction limit: 1,500 characters. Canonical prompt is 992 characters by JavaScript string length.
- GitHub/Slack are persistence aids, not guaranteed automatic synchronization to every chat. Custom Instructions must be pasted into Settings by the user; this session did not directly change the Settings UI.


## 2026-10-17 — persistent memory optimization
- Custom instruction (1,108 characters): docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md
- Duplicate instruction copy: docs/ultra-ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md
- Memory loop protocol: docs/ultra-ai/ULTRA-AI-memory-protocol.md
- Operating rule: web search each task; attempt Gemini/Claude free access; GitHub is canonical memory, Slack C0C9649RQAZ is progress/error log; verify free/cost conditions before API calls; protect production flows, hourly automation and main.


## User authorization update (2026-10-17)
- User authorized changes and modifications for AI. Execute permitted repository/document improvements directly and verify by read-back.
- Authorization does not override the standing safeguards: free-first; no paid API calls, purchases or upgrades; no secrets in logs; protect the enabled hourly Asia/Seoul automation, five production Activepieces flows and main branch; do not claim inaccessible tools or models were used.
- Priority order: (1) GitHub + Slack persistence and optimization of ChatGPT memory; (2) Gemini + Claude collaboration via free consumer apps. If a paid route is presented, do not call paid APIs; try the consumer app free route and report any browser/login blocker accurately.
- Latest custom-instruction body: 1010 JavaScript characters, verified in both canonical and display-copy files. Settings UI still requires the user to paste/save it.

## Dual-review policy — Gemini + Claude (2026-10-17)
- Default for meaningful project work: Gemini and Claude each independently review the same evidence and criteria before either sees the other's review.
- Merge by checking evidence, tests, and explicit disagreements; report consensus, conflicts, risks, and final decision.
- If either is inaccessible, state the blocker and do not claim complete dual review. Free-first only; no uncertain/paid API calls or credit spending. Test orchestration in a disabled/unpublished draft; protect production flows and the hourly automation.


## Dual-review flow draft status (2026-10-17)
- Created disabled/unpublished Activepieces draft AI · Gemini + Claude 독립·교차 검토 (비용 확인 전 초안) (ID 1MAbLTS7HS9LjDRqq9l4b). It performs independent Gemini and Claude first-pass reviews from the same input, then each reviews the other's first-pass result, then packages all four outputs.
- Validation: 6/6 steps valid, 0 issues; structure re-read; draft remains DISABLED/unpublished. No AI generation/test call, publication, or enablement was performed.
- Gemini direct connection reports ACTIVE and its model dropdown resolves, but free quota/billing is unverified. Direct Claude model dropdown returned no options; the draft therefore references the configured Activepieces-managed Claude model, whose billing state is also unverified. No live test is allowed until cost-safe access is proven.
- The flow is sequential (not simultaneous); the first-pass prompts are independent. Before publishing, set webhook authentication (current draft's no-auth setting is not production-safe). Existing production flows and hourly automation were not changed.


## Current authoritative correction — 2026-10-17 15:02 KST
- Current custom-instruction body is 1010 JavaScript characters, begins `ULTRA AI — ALWAYS ON`, and is synchronized between canonical and display-copy files. Historical notes saying 992 or 1108 characters are superseded.
- Canonical: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md
- Display copy: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md
- iOS ChatGPT Settings was not changed. User must paste/save the canonical prompt manually.
- Priority: (1) GitHub + Slack memory persistence; (2) Gemini + Claude free consumer apps. Never call paid API or upgrade. Preserve hourly schedule and production flows.


## Latest verified execution
- Run: ULTRA-2026-10-17-1502-KST — https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/hourly-run-2026-10-17-1502.md
- Custom instruction canonical and display copy read back and compared: both 1010 JavaScript characters; exact body match; both begin `ULTRA AI — ALWAYS ON`.
- Slack summary was posted and read back in channel C0C9649RQAZ: https://chatgpt-mor9047.slack.com/archives/C0C9649RQAZ/p1792217008539979
- No paid API calls, purchases, upgrades, Activepieces changes, or schedule changes.
