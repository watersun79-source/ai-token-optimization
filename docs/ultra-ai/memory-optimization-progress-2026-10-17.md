# ULTRA AI Memory Optimization Progress — 2026-10-17

## Status
PARTIAL — the canonical custom-instructions prompt was optimized and written to GitHub. The ChatGPT settings UI was not modified, and Gemini/Claude were not called for generation because free access is not verified.

## Goal
Improve cross-chat continuity using a versioned GitHub source of truth, Slack progress logs, internet research, and honest checks of Gemini/Claude availability, while remaining free-first.

## Completed and verified
- Read the current custom-instructions file, memory protocol, project memory index, and latest Slack channel history.
- Optimized the canonical prompt from 887 to 987 JavaScript characters, remaining below the 1,500-character Free/Go limit.
- Updated canonical file: docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md
- Synchronized display copy: docs/ultra-ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md
- Canonical commit: c0c493cf15d95f49122b1a9c05b6dfbf6f87fb61
- Display-copy commit: 0156fc2a448899008322e457b8ce0a5470a5260f
- Confirmed the repository default branch is main; the project working branch is ultra-ai/progress-2026-10-17. GitHub fetch_file calls must use that full branch name, not just "ultra-ai" or "progress-2026-10-17".
- Internet sources checked: OpenAI Custom Instructions FAQ, Gemini app limits and API pricing, Claude plan information and API billing.
- Activepieces connection inventory returned five entries marked ACTIVE: OpenAI, Google Gemini, Google Gemini api, Slack, Anthropic Claude. ACTIVE is a stored connection status, not proof that provider authentication or generation works.
- Slack history confirms Google Gemini read-only model-list request succeeded previously, billing tier unknown; secondary Gemini API and Claude read-only model-list requests failed HTTP 401. No generation call was made in this task.

## Cost and safety
- Paid API calls: 0
- Gemini/Claude generation calls: 0
- Purchases/upgrades: 0
- Production flow changes: 0
- Existing hourly automation changes: 0
- No credentials or secrets were read or published.

## Important limitation
Custom Instructions apply across chats when enabled, but repository and Slack records are not automatically injected into every chat. The user must paste the 987-character prompt into ChatGPT Settings > Customize ChatGPT > Custom Instructions. At the beginning of future ULTRA AI tasks, retrieve GitHub protocol/index/latest log and relevant Slack history; at the end, write back meaningful results.

## Remaining blockers / next goal
1. Reconfirm provider availability through a genuinely free consumer app or safe connected tool; do not retry known invalid API credentials repeatedly.
2. Verify Activepieces table uniqueness/concurrency and hosted Cloud BARRIER/custom-piece support from official documentation, without changing production flows or the existing hourly automation.
3. Verify updated canonical and duplicate prompt files by fetching both from branch ultra-ai/progress-2026-10-17 and recounting the prompt.
4. Update the memory index/protocol with the new 987-character count, then post a concise Slack status note if the Slack write tool allows it.
