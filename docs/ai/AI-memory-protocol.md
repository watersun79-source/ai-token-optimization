# AI Persistent Memory Protocol
Updated: 2026-10-17
Slogan: ALWAYS ON · ALWAYS EVOLVING · MAXIMUM AVAILABLE CAPABILITY

## Source of truth
- Repository: https://github.com/watersun79-source/ai-token-optimization
- Working branch: ai/continuation-readonly-audit-2026-10-18
- Canonical custom instructions: docs/ai/AI-custom-instructions-ko-1500.md (1053 characters; verified 2026-10-17)
- Display copy: docs/ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md
- Memory index: docs/ai/PROJECT_MEMORY_INDEX.md
- Latest progress report: docs/ai/memory-optimization-progress-2026-10-17.md
- Slack progress channel: C0C9649RQAZ
- Activepieces project: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/

## Start every AI task
1. Use internet search for current information and cite reliable sources.
2. Read this protocol, PROJECT_MEMORY_INDEX.md, the latest GitHub progress report, and relevant recent Slack messages.
3. Check the current external state; saved notes may be stale.
4. Check Gemini and Claude access on each task. Use them only through a genuinely accessible free route; distinguish consumer web apps from API usage. Never claim a model was used without a real response.
5. Do not call APIs until free limits, billing state, and costs are verified. Do not purchase, upgrade, or reveal credentials.
6. Protect all production flows and the existing hourly automation. Test in disabled/unpublished drafts with sample data.

## End every meaningful task
Write a dated GitHub progress report and a concise Slack update. Include actual tools/providers used, links, test IDs and results, cost/API call count, cleanup, blockers, and the next goal. If a read or write fails, report the failure; never pretend it succeeded.

## ChatGPT deployment and limitations
The current 1053-character prompt is stored at:
https://github.com/watersun79-source/ai-token-optimization/blob/ai/continuation-readonly-audit-2026-10-18/docs/ai/AI-custom-instructions-ko-1500.md
On iOS, paste it into Settings > Customize ChatGPT > Custom Instructions with customization enabled. Saving the file does not change ChatGPT settings. Custom Instructions apply across chats when enabled, but GitHub and Slack history are not automatically injected into every conversation; retrieve them explicitly.

## Latest verification (2026-10-17)
- Historical note: an earlier prompt revision was 1108 characters. It has been superseded by the current 1053-character prompt; see the latest authoritative update below.
- This turn: internet research performed; GitHub protocol/index/prompt and Slack recent messages read. Gemini/Claude consumer-app generation not performed because the connected browser context is unavailable and prior API authentication/free billing status is unresolved. Paid API calls: 0.
- OpenAI official guidance confirms saved Custom Instructions apply across existing and new chats when enabled; this does not automatically inject GitHub/Slack records into each chat.

## Latest instruction sync (2026-10-17)
- Historical note: an earlier revision was 992 JavaScript characters. It has been superseded by the current 1053-character prompt.
- Every task now explicitly requires an actual attempt to use Gemini and Claude's free web apps; if no browser/app access is available, record the blocker and do not claim usage. Read GitHub and Slack at task start and write/read-back meaningful results at task end.
- Latest check: official web research and GitHub/Slack read-back performed. Gemini/Claude generation calls 0 because the browser connector has no originating browser context and API free/billing status remains unresolved. Paid API calls 0.

## Current blockers
- Gemini: a read-only model-list request succeeded once, but billing/free tier is unknown.
- Secondary Gemini API and Claude: previous read-only model-list requests failed HTTP 401; no generation calls were made.
- Activepieces Tables atomic uniqueness under concurrent runId creation remains unproven.
- Hosted Cloud support for a custom BARRIER piece remains unverified.
- The existing hourly automation and the currently verified enabled production flows must remain unchanged unless the user explicitly authorizes a necessary change.


## 2026-10-17 update — persistent memory loop
- Search current web sources on every task; cite reliable sources.
- Attempt Gemini and Claude through available free web apps or connected tools on each task. If access fails or credentials are invalid, report that plainly; do not claim they were used.
- Never call APIs until free quota, pricing, and billing state are verified. No payment/upgrades. Protect secrets.
- For important/AI tasks, read the GitHub memory index, protocol, latest progress and Slack channel C0C9649RQAZ before acting. At completion, write decisions, changed files/commit, test IDs/results, real AI usage, API/cost status, unresolved issues and next goal to both GitHub and Slack; read back to verify.
- External records are not automatically injected into every ChatGPT chat. Re-read them in new and existing chats when the task needs continuity.
- Preserve production Activepieces flows, hourly automation, and main branch; use a separate branch and mock tests.

## Gemini + Claude dual independent review (2026-10-17)
- For meaningful AI/project decisions, code, automation changes, troubleshooting, and important recommendations, obtain separate independent reviews from both Gemini and Claude when each is genuinely accessible through a free, cost-safe route.
- Give each reviewer the same task, evidence, constraints, and acceptance criteria independently; do not show Gemini's conclusions to Claude or Claude's conclusions to Gemini before their first-pass reviews.
- Compare both reviews against source evidence and tests. Produce a consensus list, disagreements, unsupported claims, risks, and a final decision. Do not treat majority agreement as proof.
- If either model cannot be accessed, report which one was unavailable and why; do not fabricate a review or mark the dual-review step complete.
- Free-first remains mandatory: do not call paid/uncertain APIs, spend credits, or change billing. Existing production flows and hourly automation remain protected. Implement dual-review orchestration only in a disabled/unpublished draft and validate with sample data before any production rollout.
- For trivial low-risk conversational tasks, avoid unnecessary repeated model calls; dual review is the default for meaningful project work, not a reason to waste tokens on every small exchange.


## Dual-review draft implementation (2026-10-17)
- Created Activepieces draft flow: AI · Gemini + Claude 독립·교차 검토 (비용 확인 전 초안), flow ID 1MAbLTS7HS9LjDRqq9l4b, URL https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/1MAbLTS7HS9LjDRqq9l4b.
- Flow has 6 steps: webhook trigger; Gemini independent first review; Claude independent first review; Gemini critiques Claude's first review; Claude critiques Gemini's first review; CODE step packages all four outputs.
- Static validation passed: 6/6 valid, 0 issues. Read-back structure confirms the draft is DISABLED and unpublished. No flow test, AI generation call, publish, or enable action was performed.
- Cost/access blockers: Google Gemini connection appears ACTIVE and model dropdown resolved, but ACTIVE status does not prove free quota. Direct Anthropic Claude model dropdown returned 0 options for the configured connection; the draft uses the configured Activepieces managed AI provider's Claude Sonnet model, whose billing/credits are not confirmed. Therefore do not test or publish this draft until cost and provider access are verified.
- Security blocker: webhook draft uses no authentication only for unpublished construction; before any publication, configure and verify Header Auth or another appropriate authentication method.
- The four AI actions are sequential in the flow, not simultaneous. The first two prompts are independent (neither sees the other's output); the following two steps cross-review each first-pass result.
- Official references checked: Activepieces AI providers https://www.activepieces.com/docs/admin-guide/guides/setup-ai-providers ; Gemini API pricing https://ai.google.dev/gemini-api/docs/pricing?hl=ko ; Claude API pricing https://platform.claude.com/docs/en/about-claude/pricing.


## Authoritative correction — 2026-10-17 15:02 KST
- Current canonical custom-instruction body is 1010 JavaScript characters and begins `AI — ALWAYS ON`. The display copy was synchronized to match. Older references to 992 or 1108 characters in historical notes are superseded and must not be treated as current.
- Both files were updated on branch `ai/continuation-readonly-audit-2026-10-18`; verify by reading them back. ChatGPT iOS Settings was not changed; the user must paste/save the canonical prompt manually.
- Priority remains: (1) GitHub + Slack for persistent ChatGPT memory; (2) Gemini + Claude free consumer-app collaboration. No paid API calls, purchases, or upgrades.


## Inventory correction — 2026-10-17 15:06 KST
- Current Activepieces read-only queries returned 3 ENABLED/published flows and 26 DISABLED flows. Older logs refer to 5 enabled production flows. Treat this as an unresolved state discrepancy, not as permission to enable/disable anything. Preserve all current statuses until the historical two flow IDs and intended state are reconciled.


## Priority continuation — 2026-10-17 15:22 KST
- Current canonical custom-instruction header is `AI — ALWAYS ON`; body length is 1053 JavaScript characters. Display copy must exactly match the body. The prompt now explicitly preserves current flow statuses until the historical 5-enabled vs current 3-enabled discrepancy is resolved.
- Automation prompt updated with this unresolved goal and safeguards; the hourly schedule and enabled state remain unchanged.
- Current Activepieces inventory read-only: 3 ENABLED/published, 26 DISABLED. Do not change states while reconciling history.

## Latest authoritative verification — 2026-10-17 15:22 KST
- Canonical and display prompt bodies were fetched again and are exactly identical at 1053 JavaScript characters. Both begin `AI — ALWAYS ON` and fit the 1,500-character Free/Go limit.
- Existing automation prompt was updated to carry forward the current blocker and safeguards; enabled state and hourly-on-the-hour Asia/Seoul schedule unchanged.
- Activepieces inventory remains 3 ENABLED/published and 26 DISABLED. Historical count of 5 enabled flows is unresolved; no statuses were changed.
- Slack update posted and verified by reading recent channel history: https://chatgpt-mor9047.slack.com/archives/C0C9649RQAZ/p1792218123952119

## Authoritative continuation correction — 2026-10-18 09:34 KST
- Project name in current user-facing text is **AI**; the legacy directory/file names containing `AI` remain for backward-compatible links and are not a reason to rename or move files automatically.
- Current canonical custom-instruction file was read back at 1,230 characters including its count/header line; the body is stated as 1,230 characters and fits the 1,500-character limit. Do not claim the ChatGPT iOS Settings were changed: only GitHub files were changed; user must manually save custom instructions in Settings if desired.
- Current Activepieces connector inventory now returns 10 flows: 3 enabled/published production flows and 7 disabled test/mock flows. The older 7-flow and 29-flow inventory entries are historical snapshots from different connector scope/time; the current direct read is authoritative for this session. No flow status was changed.
- Current structural checks: `AI 3AI 협업` 7/7 valid; `Gemini + Claude 협업 비서 (비용 확인 필요)` 4 valid + 1 intentionally skipped; `TEST ONLY · Concurrent Child Join E2E` 3 flows/table checked, zero issues. These checks do not prove real provider parallelism.
- Hourly automation `AI` remains enabled, Asia/Seoul, every hour on the hour. Do not duplicate or change it.
- Hard cost gate: no paid model APIs. Never make a model-provider call unless the exact route is verified to be within a free allowance with no billing risk. Connection status and public free-tier pricing are not proof of the user's remaining quota. No provider calls were made in this audit.
- Persistent continuity loop: read this protocol, `PROJECT_MEMORY_INDEX.md`, latest execution report, and Slack channel `C0C9649RQAZ`; after meaningful changes, update GitHub and Slack, then read both back. If a connector is unavailable, record that limitation rather than claiming it worked.
- Remaining blockers: account-specific free quota/billing cannot be inspected through the current connected tools; browser connector has no originating browser context; production Gemini/Claude execution remains sequential and must not be switched to unproven parallel orchestration.

### Character-count correction — 2026-10-18
- Read-back comparison confirms canonical and display custom-instruction files are byte-for-byte identical (same Git blob SHA `8011eca50e723a123709f3868335bb968984998b`). The file declares `문자 수: 1230`; counting the normalized body after removing that header yields 1,229 JavaScript UTF-16 code units. Both are under the 1,500-character limit. Do not claim ChatGPT Settings were changed automatically.
