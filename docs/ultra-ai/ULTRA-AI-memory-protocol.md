# ULTRA AI Persistent Memory Protocol
Updated: 2026-10-17
Slogan: ALWAYS ON · ALWAYS EVOLVING · MAXIMUM AVAILABLE CAPABILITY

## Purpose
Use an external, versioned memory store so project context can be recovered across ChatGPT conversations. This is a retrieval-and-writeback workflow, not a claim that ChatGPT automatically injects GitHub/Slack history into every new chat.

## Source of truth
- GitHub repository: https://github.com/watersun79-source/ai-token-optimization
- Working branch: ultra-ai/progress-2026-10-17
- Canonical custom instructions (887 characters): docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md
- Duplicate display copy: docs/ultra-ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md
- Slack progress channel ID: C0C9649RQAZ
- Latest Slack connection-audit note: https://chatgpt-mor9047.slack.com/archives/C0C9649RQAZ/p1792197750397039
- Activepieces project: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/

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
The 887-character prompt is stored at:
https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md
On iOS, open Settings > Customize ChatGPT > Enable customization and paste the prompt into Custom Instructions. Saving the file in GitHub does not itself change ChatGPT settings. Custom Instructions apply across chats when configured, but they do not rewrite old messages or guarantee automatic retrieval of repository history.

## Current verified state (2026-10-17)
- Five named production flows remain ENABLED/published: ULTRA AI 3AI 협업; ChatGPT + Gemini 협업 (API 결제 필요); ULTRA AI 비서; Slack; Gemini + Claude 협업 비서 (비용 확인 필요).
- Mock coordinator draft EoQdyZftEyejxh4P85K5S is DISABLED and unpublished. Validation: 21/21 steps valid, 0 invalid; two informational empty-router fallback notes. Do not enable or publish without separate verified tests.
- Mock tables: ULTRA AI Run Registry (MOCK ONLY) = 0 rows; ULTRA AI Coordinator Results (MOCK ONLY) = 0 rows; ULTRA AI Parallel Results (MOCK ONLY) = 14 rows. The 14 rows are retained test history, not production AI results.
- Find Records volume tests: 101 rows → outputCount 101; 201 rows → outputCount 201; 501 rows → outputCount 501 (run U1Hqc2j98hqZuYEb3zNZf). All test rows were deleted and follow-up searches returned 0.
- Late-arrival recovery was tested with sample data (Slack run Q68QOU6BW81R0qEGcZGmB). Atomic uniqueness under concurrent runId creation remains unproven.
- Provider connection audit: Google Gemini read-only List Models succeeded once; billing tier remains unknown. The secondary Google Gemini api connection failed with HTTP 401 invalid API key. Anthropic Claude read-only List Models failed with HTTP 401 invalid x-api-key. No generation call was made.
- Activepieces Max Concurrent Jobs is a per-project setting; do not set it to 1 in the shared project because it could affect five protected production flows.
- Waitpoints BARRIER is an engine/piece API concept, but no built-in visual flow action was found; hosted Cloud custom-piece installation is unverified.
- Existing hourly automation titled ULTRA AI remains enabled with unchanged Asia/Seoul hourly-on-the-hour schedule. Recheck current state before claiming it is still active.
- Gemini/Claude/OpenAI generation calls in the latest validation: 0.

## Reporting rule
Use statuses DONE / PARTIAL / BLOCKED. Never claim global completion while an access, billing, or test blocker remains.
