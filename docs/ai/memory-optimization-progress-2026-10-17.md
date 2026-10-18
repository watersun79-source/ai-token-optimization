# AI Memory Optimization Progress — 2026-10-17

## Status
PARTIAL — the prompt, memory protocol, project index, and progress logging have been updated and verified. The ChatGPT Settings UI has not been changed. Gemini/Claude generation was not run because a genuinely free usable route is not verified.

## Completed and verified
- Read the existing GitHub protocol, memory index, canonical prompt, and recent Slack history.
- Optimized the prompt to 987 JavaScript characters, below the ChatGPT Free/Go 1,500-character limit.
- Canonical prompt updated: docs/ai/AI-custom-instructions-ko-1500.md (commit 3a4c1b8caad5ccad51b74dd42d953b5851d9a40f).
- Display copy updated: docs/ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md (commit 0156fc2a448899008322e457b8ce0a5470a5260f).
- Memory protocol streamlined: docs/ai/AI-memory-protocol.md (commit 878da856d9752b6f4dcc90e6a5a1fca169f6ba72).
- Memory index synchronized to the 1108-character prompt and new audit: docs/ai/PROJECT_MEMORY_INDEX.md (latest commit 9c34aefdcce4be7a6da65a91bac0d7cea616935b).
- Official Activepieces concurrency/BARRIER review recorded: docs/ai/activepieces-concurrency-barrier-audit-2026-10-17.md (commit da2930e9e6e4214bf18d1e2605bfd6a1e4acb6c8).
- Progress report: docs/ai/memory-optimization-progress-2026-10-17.md.
- Re-read canonical prompt, display copy, protocol, and index from branch ai/continuation-readonly-audit-2026-10-18. All reflect 1108 characters and current links.
- Slack prompt status posted: https://chatgpt-mor9047.slack.com/archives/C0C9649RQAZ/p1792198239072319
- Slack Activepieces audit posted: https://chatgpt-mor9047.slack.com/archives/C0C9649RQAZ/p1792198331019489
- Official docs confirm Activepieces BARRIER is an engine/piece API capability; custom/private piece management is documented as a paid feature. The public Tables action list does not establish atomic upsert/unique-key guarantees. Tables product docs state up to 10,000 rows per table. This is documented, not an executed concurrency test.
- Activepieces connections list OpenAI, Google Gemini, Google Gemini api, Slack, and Anthropic Claude as ACTIVE. This status alone does not prove provider authentication or successful generation.
- Previous read-only diagnostics: primary Gemini model-list request succeeded once but billing/free tier is unknown; secondary Gemini API and Claude model-list requests returned HTTP 401. No generation call was made in this task.
- Connected browser access returned an error because this session lacks an originating connected-browser context; therefore Gemini/Claude consumer websites could not be operated from this workflow.

## Cost and safety
- Gemini/Claude generation calls: 0
- Paid API calls: 0
- Purchases/upgrades: 0
- Production flow changes: 0
- Existing hourly automation changes: 0
- No secrets were read or published.

## Limitation
Custom Instructions apply across chats when enabled, but GitHub/Slack history is not automatically injected into each chat. The user must paste the 1108-character prompt into ChatGPT Settings > Customize ChatGPT > Custom Instructions. This session cannot directly change that settings UI.

## This run's continuation (2026-10-17)
- Re-read canonical prompt, protocol, index, recent Slack messages, and official OpenAI/Gemini/Claude web documentation.
- Canonical prompt verified as 1108 JavaScript characters, within the 1,500-character limit. The previous display copy/index/protocol had stale 992-character references; this continuation synchronizes them to the current canonical version.
- Internet sources: OpenAI Custom Instructions FAQ; Google Gemini Apps limits; Anthropic Claude plan information. No Gemini or Claude generation calls were made because the browser connector has no originating browser context and API free/cost status is unresolved.
- Costs: paid API calls 0; purchases/upgrades 0; production-flow edits 0; hourly automation edits 0.

## Continued optimization (2026-10-17, latest pass)
- Revised canonical prompt to explicitly attempt actual free-web-app use of Gemini and Claude on every task and require GitHub + Slack retrieval at task start and write/read-back at task end.
- Canonical/display prompt exact body: 992 JavaScript characters, <= 1,500; canonical and display copy synced.
- GitHub protocol, memory index, and this report updated to reflect the current prompt revision.
- Internet: OpenAI official Custom Instructions FAQ, Google Gemini Apps limits, and Anthropic Claude plan info checked. Gemini/Claude generation calls 0 due no connected-browser context and unresolved API free/billing status; paid API calls 0.
- Production flows changed: 0; hourly automation changed: 0; purchases/upgrades: 0.

## Remaining blockers / next goal
1. User must paste the prompt into ChatGPT Settings to activate it globally.
2. A connected browser context or working free provider integration is needed to actually use Gemini and Claude consumer apps in this workflow. Do not retry known invalid API credentials or call potentially billable APIs.
3. Continue official documentation research and safe mock-only validation of Activepieces race prevention; keep production flows and the existing hourly automation unchanged.


## 2026-10-17 — Gemini + Claude independent/cross-review draft
- Created new Activepieces draft AI · Gemini + Claude 독립·교차 검토 (비용 확인 전 초안), flow ID 1MAbLTS7HS9LjDRqq9l4b: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/1MAbLTS7HS9LjDRqq9l4b
- Steps: Gemini first-pass review and Claude first-pass review receive the same request independently; Gemini then critiques Claude's first pass; Claude critiques Gemini's first pass; a code step packages all four results.
- Validation passed: 6/6 steps valid, 0 issues. Flow structure was read back; status is DISABLED and published=false. No live flow test or AI generation was run; no paid API calls or credit spend; no publish/enable.
- Provider verification: Gemini connection status ACTIVE and model options resolve, but free quota/billing remains unverified. Direct Claude connection returned 0 model options. The draft uses the existing Activepieces-managed Claude Sonnet provider, but its cost/credit status is unknown. Keep the draft untested until free/cost-safe access is confirmed.
- Safety: current webhook has authType none in the unpublished draft only. Header Auth or another appropriate method must be configured before publication. Existing enabled production flows and the hourly Asia/Seoul automation were not changed.
- Official docs checked: https://www.activepieces.com/docs/admin-guide/guides/setup-ai-providers ; https://ai.google.dev/gemini-api/docs/pricing?hl=ko ; https://platform.claude.com/docs/en/about-claude/pricing.

## Next goal
1. Confirm a genuinely free Gemini/Claude execution route and billing/credits without generating content. If impossible, use consumer web apps manually when accessible and keep automated flow disabled.
2. Configure webhook authentication in the draft and validate without running AI calls.
3. Only after explicit cost-safe confirmation, run one clearly labelled sample test; read back results and document cost/API call counts.


## Priority continuation — 2026-10-17 15:06 KST
- Re-read GitHub protocol/index/latest report and Slack channel before acting.
- Current Activepieces inventory: 3 enabled/published, 26 disabled. Historical records refer to 5 enabled production flows. No state changes; reconciliation required.
- Automation `AI` confirmed enabled; hourly-on-the-hour Asia/Seoul schedule unchanged.
- Gemini/Claude free consumer-app response: not accessed this run because no connected browser/app session was available. Provider generation calls 0; paid API calls 0; no credentials changed.


## Priority continuation — 2026-10-17 15:22 KST
- Internet checked: OpenAI's official Custom Instructions page says instructions apply across existing and new chats after being saved; Free/Go limit is 1,500 characters. OpenAI Memory docs say memory does not retain every detail. Sources: https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions and https://help.openai.com/en/articles/8590148-memory-in-chatgpt.
- Updated canonical instructions to `AI — ALWAYS ON`, corrected the false assumption that five flows are currently enabled, and added a do-not-change-statuses safeguard. Prompt body is 1053 JavaScript characters.
- Updated existing automation prompt only; title `AI`, enabled state, and hourly-on-the-hour Asia/Seoul schedule unchanged.
- Activepieces read-only inventory: 3 ENABLED/published, 26 DISABLED; five-enabled historical records remain unresolved. No flow changes.
- Gemini/Claude consumer apps unavailable in this run because the connected browser requires an originating browser context. Generation calls 0; paid API calls 0; no credential changes.
- Next: verify canonical/display body match, write/read-back current run report in GitHub and Slack, continue ID reconciliation without status changes, and only attempt Gemini/Claude through a real free route.

- Slack update posted and read back: https://chatgpt-mor9047.slack.com/archives/C0C9649RQAZ/p1792218123952119
