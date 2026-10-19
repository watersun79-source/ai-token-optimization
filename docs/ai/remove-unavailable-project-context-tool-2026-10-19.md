# Correction: stop pursuing unavailable ap_set_project_context

Date: 2026-10-19 (Asia/Seoul)
Branch: ai/remove-missing-project-context-reference-2026-10-19

## Decision
Treat `ap_set_project_context` as unavailable in this connected runtime. Do not keep asking the user to find it, do not try to invoke it, and do not route around the missing tool by calling project-scoped actions speculatively. Use only tools actually exposed in the current session and verify the selected project from available evidence where possible.

## Evidence
- The current Activepieces tool registry was inspected in this session; it exposes project actions such as `ap_list_flows`, `ap_flow_structure`, `ap_list_runs`, and `ap_list_connections`, but no `ap_set_project_context`.
- GitHub code search for the exact name returned no results in the selected repository search.
- Recent Slack records document repeated absence and repeated unsuccessful attempts to recover the tool. Continuing to pursue it adds no value.
- Existing prior reports are historical evidence and were not rewritten or deleted.

## Changes
- Updated `docs/ai/AI-custom-instructions-ko-1500.md`.
- Updated `docs/ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md`.
- Added an explicit instruction: treat the unavailable tool as nonexistent for this runtime; never search for or call it again; use only exposed tools.
- The prompt copies are synchronized at 1,337 JavaScript characters, below the 1,500-character limit.
- Work was done on a separate branch; `main`, production flows, connections, and the existing hourly automation were not changed.

## Verification / limitations
- The two GitHub writes returned commit SHAs, but read-back verification is still required before calling the repository update fully verified.
- This does not remove a server-side tool: the tool is absent from the exposed registry already. It removes the instruction to keep pursuing it.
- ChatGPT Settings were not changed by this repository update. The user must paste/save the updated instruction in ChatGPT Settings if they want it active there.
- Provider API calls: 0. Paid API calls: 0. Purchases/upgrades: 0.
- Next: read both updated prompt files back from this branch and post/read back this correction in Slack.
