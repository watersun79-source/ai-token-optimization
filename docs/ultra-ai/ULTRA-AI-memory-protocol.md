# AI Persistent Memory Protocol
Updated: 2026-10-17
Slogan: ALWAYS ON · ALWAYS EVOLVING · MAXIMUM AVAILABLE CAPABILITY

## Source of truth
- Repository: https://github.com/watersun79-source/ai-token-optimization
- Working branch: ultra-ai/progress-2026-10-17
- Canonical custom instructions: docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md (1010 characters; verified 2026-10-17)
- Display copy: docs/ultra-ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md
- Memory index: docs/ultra-ai/PROJECT_MEMORY_INDEX.md
- Latest progress report: docs/ultra-ai/memory-optimization-progress-2026-10-17.md
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
The 992-character prompt is stored at:
https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md
On iOS, paste it into Settings > Customize ChatGPT > Custom Instructions with customization enabled. Saving the file does not change ChatGPT settings. Custom Instructions apply across chats when enabled, but GitHub and Slack history are not automatically injected into every conversation; retrieve them explicitly.

## Latest verification (2026-10-17)
- Canonical prompt is 1108 JavaScript characters and remains under the 1,500-character Go/Free limit; display copy was synchronized and read-back verification is pending.
- This turn: internet research performed; GitHub protocol/index/prompt and Slack recent messages read. Gemini/Claude consumer-app generation not performed because the connected browser context is unavailable and prior API authentication/free billing status is unresolved. Paid API calls: 0.
- OpenAI official guidance confirms saved Custom Instructions apply across existing and new chats when enabled; this does not automatically inject GitHub/Slack records into each chat.

## Latest instruction sync (2026-10-17)
- Canonical and display prompt synchronized to 992 JavaScript characters, under the 1,500-character limit.
- Every task now explicitly requires an actual attempt to use Gemini and Claude's free web apps; if no browser/app access is available, record the blocker and do not claim usage. Read GitHub and Slack at task start and write/read-back meaningful results at task end.
- Latest check: official web research and GitHub/Slack read-back performed. Gemini/Claude generation calls 0 because the browser connector has no originating browser context and API free/billing status remains unresolved. Paid API calls 0.

## Current blockers
- Gemini: a read-only model-list request succeeded once, but billing/free tier is unknown.
- Secondary Gemini API and Claude: previous read-only model-list requests failed HTTP 401; no generation calls were made.
- Activepieces Tables atomic uniqueness under concurrent runId creation remains unproven.
- Hosted Cloud support for a custom BARRIER piece remains unverified.
- The existing hourly automation and five protected production flows must remain unchanged unless the user explicitly authorizes a necessary change.


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
- Current canonical custom-instruction body is 1010 JavaScript characters and begins `ULTRA AI — ALWAYS ON`. The display copy was synchronized to match. Older references to 992 or 1108 characters in historical notes are superseded and must not be treated as current.
- Both files were updated on branch `ultra-ai/progress-2026-10-17`; verify by reading them back. ChatGPT iOS Settings was not changed; the user must paste/save the canonical prompt manually.
- Priority remains: (1) GitHub + Slack for persistent ChatGPT memory; (2) Gemini + Claude free consumer-app collaboration. No paid API calls, purchases, or upgrades.
