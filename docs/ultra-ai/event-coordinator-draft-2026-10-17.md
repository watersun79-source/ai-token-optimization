# ULTRA AI Event Coordinator Draft — 2026-10-17

## Standing authorization and operating boundary
The user stated “항상 허용” (standing permission to continue). Treat this as permission to proceed autonomously with routine, reversible, free/mock-only project work and to save progress in GitHub and Slack. It does not authorize paid upgrades, external AI API calls before free entitlement is verified, exposure of secrets, destructive changes to production, or changing the existing hourly schedule.

## New isolated mock-only artifacts
Folder: `ULTRA AI MOCK Parallel`

- Table: `ULTRA AI Coordinator Results (MOCK ONLY)`
  - Internal ID: `ge4PyrJ77kNCnmrTRyu93`
  - External ID: `5DMPAHHiKFE2h9v9oGFE3`
  - Verified row count after cleanup: 0.
- Flow: `MOCK ONLY · Result Event Coordinator Draft`
  - ID: `48Zs1ORE6orHkB3hc4bwE`
  - URL: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/48Zs1ORE6orHkB3hc4bwE
  - Status: draft, unpublished, disabled.
  - Trigger: Activepieces Tables new-record event on the isolated mock table.
  - Steps: find rows by the triggered runId, validate synthetic results, deduplicate identical reviewer results, flag conflicts, and return `MERGE_READY`, `MERGE_PARTIAL`, `MERGE_INCOMPLETE`, or `MERGE_CONFLICT`.
  - No timeout, polling, persistence of final merge state, or live AI execution is implemented.

## Tests performed (Activepieces TESTING, synthetic trigger payloads only)
- Run `UtrD3qcFxqhbec7rv6ZXk`: one Claude result → `MERGE_PARTIAL`; no Gemini result; `aiCallsMade=0`.
- Run `Y5AIwUdJu6pQHzBqV2LKO`: no result rows → `MERGE_INCOMPLETE`; `aiCallsMade=0`.
- Both tests SUCCEEDED in about 1.7–2.3 seconds.
- Temporary synthetic row ID `kcNUCDULOwUgq5DuCFR5w` deleted.
- Isolated coordinator table returned to 0 rows.
- Existing mock results table remains at 14 rows.
- Folder validation: 1 flow, all connections valid, 0 issues.
- New flow remains unpublished; this does not prove a real table-created event fires end-to-end.

## Protected production state
Five production flows remain ENABLED and published:
- `ULTRA AI 3AI 협업` — `kt2N9yCVA3dLkFiNPSMsH`
- `ChatGPT + Gemini 협업 (API 결제 필요)` — `hgPVOZQYdFTezhoZ6wj5j`
- `ULTRA AI 비서` — `yRqt1nbG4ZqiIkDX72vhN`
- `Slack` — `vtRwEYmcwDTunBZut265G`
- `Gemini + Claude 협업 비서 (비용 확인 필요)` — `drNhxMhmCo3A0rKV0OhIZ`

All production flows remain untouched. Existing hourly automation remains unchanged. Do not claim its hourly runs are healthy without fresh run evidence.

## Next work
1. Investigate a free, supported way to persist merge state idempotently without creating duplicate status records.
2. Design an isolated run registry with explicit deadlines and a timeout/reconciliation pass; test missing, delayed, duplicate, conflicting, malformed, and late results.
3. Check whether a real table-created event can be tested safely without enabling a production flow. Keep draft unpublished until a test plan passes.
4. Keep all API calls at zero, no paid upgrades, no external HTTP/webhooks, and no Slack notifications from Activepieces test flows.
5. Save every meaningful change and test result to this GitHub branch and the project's Slack channel.

Last updated: 2026-10-17.
