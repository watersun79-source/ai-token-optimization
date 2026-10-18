# AI Continuous Improvement — 2026-10-18 09:12 KST

## Run identity
- Report ID: AI-2026-10-18-0912-KST-readonly-project-context
- This is a report ID, not an Activepieces run ID.
- Working branch: ultra-ai/progress-2026-10-17; main unchanged.

## Start-of-run reads
- Read ULTRA-AI-memory-protocol.md, PROJECT_MEMORY_INDEX.md, latest detailed execution report, canonical custom instructions, and recent Slack channel C0C9649RQAZ messages.
- Confirmed branch name: `ultra-ai/progress-2026-10-17`. Bare ref `ultra-ai` is not an existing branch; this was the cause of earlier 404 reads using that ref.

## Read-only Activepieces inventory
- Re-listed current project flows: 10 total; 3 ENABLED/published and 7 DISABLED.
- Enabled: AI 3AI 협업 (kt2N9yCVA3dLkFiNPSMsH), Slack (vtRwEYmcwDTunBZut265G), Gemini + Claude 협업 비서 (drNhxMhmCo3A0rKV0OhIZ).
- Disabled flows remain unchanged: bMKzPS0kb73NtEDQbq9D5, 4a8OSFX1yERP6TZ9D0Hob, 4BrtUZsKexpdxjIpWMtYR, Jsux341MqsaxUlrGFue1x, jRWo1ktjzHHgoLcrPSyzx, ll4Z64nfOgzsspJFaL17s, ixaHvPgxca1aNXSPSCfPW.
- Current list repeats the prior 10-flow result. Historical snapshots of 7 and 29 flows and an older 5-enabled count remain unexplained.

## Additional investigation and diagnosis
- Searched the working repository's indexed code for historical flow IDs `hgPVOZQYdFTezhoZ6wj5j` and `yRqt1nbG4ZqiIkDX72vhN`, and for the old 29-flow/5-enabled phrases. All searches returned zero results. GitHub connector code search only covers the default branch, so this is not evidence that the IDs never existed.
- Listed repository branches: `main`, `ultra-ai/progress-2026-10-17`, and three unrelated test/fix branches. No additional obvious historical memory branch was present.
- Activepieces MCP tool catalogue exposes `ap_list_flows` and flow readers, but no project-context setter or project-list reader. Current tool call can list flows but cannot independently prove which project the connector context targets.
- Official Activepieces List Projects and List Flows endpoints require an API key and explicit projectId. User explicitly prohibits paid/uncertain API calls, and no known-safe credential-free read route is available in this tool context. No API call was made. This is the current blocker.
- Official Activepieces MCP Tools Reference says `ap_list_flows` lists flows in the current project; it does not expose a project ID in the tool result. Therefore, do not infer cross-project identity from the list alone.

## Consumer AI access
- Browser connector list_tabs failed: connected browser access requires the originating browser context.
- Gemini independent consumer-app response: 0; Claude independent consumer-app response: 0 (login required). No claim of use.

## Official documentation checked
- Activepieces MCP tools reference: https://www.activepieces.com/docs/mcp/tools
- Activepieces List Projects: https://www.activepieces.com/docs/endpoints/projects/list
- Activepieces List Flows: https://www.activepieces.com/docs/endpoints/flows/list
- OpenAI Custom Instructions FAQ: https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions
- Official docs show that project/flow REST reads require an API key; do not create calls until cost/billing and credential use are safe. OpenAI Free/Go custom instructions allow up to 1,500 characters.

## Safety and cost
- AI generation API calls: 0; paid API calls: 0; purchases/upgrades: 0.
- Flow edits/status changes/runs: 0; schedule changes: 0; credentials/secrets touched: 0.
- main branch unchanged; no production flow or concurrency setting modified.

## Next goal
1. Use an authenticated, non-billable Activepieces UI or a read-only MCP action that explicitly exposes project identity; do not guess or call REST endpoints with unknown credentials.
2. Trace the historical inventory from old report contents/commit history beyond default-branch code search. Do not change any flow status.
3. Continue only with consumer Gemini/Claude routes that return a real response without paid API usage.
4. Save and read back each meaningful GitHub and Slack record.