# AI Continuous Improvement & Memory Recovery — 2026-10-18 09:08 KST

## Run identity
- Local execution ID: AI-2026-10-18-0908-KST-memory-recovery (report ID, not an Activepieces run ID).
- Repository: watersun79-source/ai-token-optimization
- Branch: ultra-ai/progress-2026-10-17. Main untouched.

## Read evidence
- Read AI-memory-protocol.md, PROJECT_MEMORY_INDEX.md, memory-optimization-progress-2026-10-17.md, and activepieces-fanout-join-continuation-2026-10-18.md on the working branch.
- Read canonical AI-custom-instructions-ko-1500.md; it declares 1,173 characters and blob SHA 9481319cf792a6f2e85031b73bb45405c15eb300.
- Read recent Slack messages in C0C9649RQAZ.
- Activepieces read-only list returned 10 flows: 3 ENABLED/published and 7 DISABLED. No flow status was changed.
- The connector default branch is main. Ref ultra-ai alone returned 404; the actual existing working branch is ultra-ai/progress-2026-10-17. This explains earlier ref read failures, not the historical flow-count discrepancy.

## Current Activepieces inventory
Enabled/published:
- AI 3AI 협업 — kt2N9yCVA3dLkFiNPSMsH
- Slack — vtRwEYmcwDTunBZut265G
- Gemini + Claude 협업 비서 (비용 확인 필요) — drNhxMhmCo3A0rKV0OhIZ

Disabled:
- TEST ONLY · Join Child Worker — bMKzPS0kb73NtEDQbq9D5 (published, but disabled)
- TEST ONLY · Polling Join Parent — 4a8OSFX1yERP6TZ9D0Hob (draft)
- TEST ONLY · Concurrent Join Parent — 4BrtUZsKexpdxjIpWMtYR (draft)
- MOCK ONLY · Result Merge Harness — Jsux341MqsaxUlrGFue1x (draft)
- MOCK ONLY · Promise.all 병렬 합류 검증기 — jRWo1ktjzHHgoLcrPSyzx (draft)
- AI JSON 검증 테스트 전용 — ll4Z64nfOgzsspJFaL17s (draft)
- TEST ONLY · JSON 출력 검증기 — ixaHvPgxca1aNXSPSCfPW (draft)

## Discrepancy status
- Latest direct list: 10 flows, 3 enabled/published, 7 disabled.
- Earlier report: 7 flows (3 enabled + 4 disabled). Historical index/report: 29 flows (3 enabled + 26 disabled); an older note claims 5 enabled.
- Current inventory has three more disabled test/mock flows than the 7-flow snapshot. Exact cause and historical 29/5 snapshot remain unproven. Missing historical IDs remain unresolved; absence from search is not proof of deletion.
- The Activepieces tool catalogue did not expose the required project-context setter. No project setting was changed. Direct listing succeeded, but cross-project identity is not independently proven.

## Gemini / Claude
- Gemini consumer-app attempt yielded no real model response; interaction was blocked.
- Claude consumer-app attempt yielded no real model response; login was required.
- Actual independent model responses this run: 0. Provider API generation calls: 0.

## Official sources checked
- OpenAI Custom Instructions FAQ: https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions — confirms iOS Settings > Customize ChatGPT and a 1,500-character limit for Free/Go.
- Activepieces List Flows API: https://www.activepieces.com/docs/endpoints/flows/list
- Activepieces Get Flow API: https://www.activepieces.com/docs/endpoints/flows/get — API documentation distinguishes ENABLED/DISABLED status and published-version metadata.

## Costs, changes, tests
- Provider generation API calls: 0; paid API calls: 0; purchases/upgrades: 0.
- Activepieces flow edits/status changes/runs: 0; hourly schedule changes: 0.
- Secrets exposed or committed: 0; tests run: 0; temporary data created: 0.
- ChatGPT Settings UI could not be directly inspected. User must save canonical instructions in Settings with customization enabled.

## Blockers and next goal
1. Historical inventory count (29 total / 5 enabled in an older note) remains unexplained; keep all flows unchanged.
2. The Activepieces project-context setter is missing from available tools; verify project identity through a supported read-only method before any flow-related change.
3. Obtain an accessible free consumer-web route for Gemini and Claude; do not use APIs with unknown quota/billing.
4. Verify GitHub/Slack writes by reading both destinations back.
5. Preserve the existing hourly Asia/Seoul automation, enabled production flows, connections, credentials, main, and project concurrency settings.