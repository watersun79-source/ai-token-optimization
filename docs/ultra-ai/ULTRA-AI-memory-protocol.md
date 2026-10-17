# ULTRA AI Persistent Memory Protocol
Updated: 2026-10-17
Slogan: ALWAYS ON · ALWAYS EVOLVING · MAXIMUM AVAILABLE CAPABILITY

## Purpose
Use an external, versioned memory store so project context can be recovered across ChatGPT conversations. This is a retrieval-and-writeback workflow, not a claim that ChatGPT automatically injects GitHub/Slack history into every new chat.

## Source of truth
- GitHub repository: https://github.com/watersun79-source/ai-token-optimization
- Working branch: ultra-ai/progress-2026-10-17
- Custom instructions: docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md
- Slack progress channel ID: C0C9649RQAZ
- Slack latest known note: https://chatgpt-mor9047.slack.com/archives/C0C9649RQAZ/p1792197218712819
- Activepieces project: https://cloud.activepieces.com/projects/Fr9OAsxi4FbSVLZkexYi/

## Start-of-task bootstrap
1. Read this protocol and the latest progress/status note from GitHub.
2. Search Slack channel C0C9649RQAZ for the latest note matching ULTRA AI and the current work item.
3. Check current external state before relying on any saved status; saved notes may be stale.
4. Identify constraints: free-first, no paid API calls before cost/billing verification, never expose secrets, do not change protected production flows or existing hourly automation without explicit necessity.
5. Use the internet for current information. Attempt Gemini and Claude through an actually available consumer app or connected tool when possible. A model catalog entry is not proof of authenticated access, free usage, or successful inference. If no safe free route is verified, report the blocker and do not call a possibly billable API.

## End-of-task writeback
For meaningful project tasks, write a dated update to GitHub and post a concise Slack note. Record:
- goal and scope
- actual tools/providers used (distinguish catalog availability from real model response)
- files/flows changed and links
- test IDs, expected vs actual results, cleanup verification
- cost status and whether any API inference occurred
- unresolved risks/blockers and the next concrete goal
Do not store API keys, passwords, auth tokens, or other secrets in GitHub or Slack.

## ChatGPT instruction deployment
The <=1500-character prompt is stored at:
https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md
On iOS: Settings -> Customize ChatGPT -> Enable customization -> paste the prompt into Custom Instructions. Saving the file in GitHub does not itself change ChatGPT settings. Custom Instructions apply across chats when configured, but they do not rewrite old messages or guarantee automatic retrieval of repository history.

## Current verified state (2026-10-17)
- GitHub prompt file exists on branch ultra-ai/progress-2026-10-17; previous recorded prompt count was 916 characters before this revision.
- Activepieces currently lists 27 flows. Five named production flows remain ENABLED/published: ULTRA AI 3AI 협업; ChatGPT + Gemini 협업 (API 결제 필요); ULTRA AI 비서; Slack; Gemini + Claude 협업 비서 (비용 확인 필요).
- Mock coordinator draft EoQdyZftEyejxh4P85K5S is DISABLED and unpublished. Other mock/test flows are disabled. Do not enable or publish them without separate verified tests.
- Mock tables: ULTRA AI Run Registry (MOCK ONLY) = 0 rows; ULTRA AI Coordinator Results (MOCK ONLY) = 0 rows; ULTRA AI Parallel Results (MOCK ONLY) = 14 rows. The 14 rows are retained test history, not production AI results.
- Activepieces AI model catalog includes Gemini and Claude model names under provider activepieces, but this alone does not prove free inference or direct Google/Anthropic credentials. No Gemini/Claude API inference was made in the latest status check.
- Existing hourly automation titled ULTRA AI was last recorded enabled with Asia/Seoul schedule hourly at minute 0. Recheck current state before claiming it is still active; do not change its schedule.
- Known engineering blockers for mock coordinator: late-arrival recovery, atomic uniqueness under concurrent runs, and pagination above 100 rows are not fully proven. Waitpoints BARRIER is documented as an engine/piece API concept; do not assume there is a supported visual flow action without verifying the exact installed action.

## Reporting rule
Use statuses DONE / PARTIAL / BLOCKED. Never claim global completion while an access, billing, or test blocker remains.