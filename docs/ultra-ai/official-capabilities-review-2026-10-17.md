# ULTRA AI — Official Capability Review (2026-10-17)

## ChatGPT custom instructions and memory
- Official OpenAI help: https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions
- OpenAI states custom instructions are applied across chats, including existing conversations, and Free/Go users have a 1,500-character limit.
- Canonical 887-character Korean prompt: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/ULTRA-AI-custom-instructions-ko-1500.md
- The assistant did not change ChatGPT Settings UI directly; user must paste it into Settings > Customize ChatGPT > Enable customization > Custom Instructions. Once saved there, OpenAI's stated behavior is that it applies across chats.
- Persistent external memory is a separate layer: use GitHub memory protocol/index and Slack status, then retrieve them at the start of a chat.

## Gemini and Claude
- Plugin discovery in ChatGPT on 2026-10-17 returned no dedicated Gemini or Anthropic Claude ChatGPT app/plugin.
- Activepieces provider connections exist, but actual credential checks are mixed: Google Gemini read-only List Models succeeded once; secondary Google Gemini api returned HTTP 401 invalid API key; Anthropic Claude returned HTTP 401 invalid x-api-key.
- No Gemini/Claude generation call was made; Gemini billing tier is unknown and Claude connection must be repaired. See https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/provider-connection-audit-2026-10-17.md
- Gemini app free limits: https://support.google.com/gemini/answer/16275805
- Gemini API pricing/free tier: https://ai.google.dev/gemini-api/docs/pricing
- Anthropic confirms Claude chat subscriptions and Claude Console/API are separate products: https://support.anthropic.com/en/articles/9876003-estoy-suscrito-a-un-plan-de-pago-de-claude-ai-por-que-tengo-que-pagar-por-separado-por-el-uso-de-la-api-en-console

## Activepieces Tables and pagination
- Official Tables flow docs: https://www.activepieces.com/docs/tables/in-flows
- Official Find Records implementation: https://github.com/activepieces/activepieces/blob/main/packages/pieces/core/tables/src/lib/actions/find-records.ts
- Find Records has an optional Limit field whose description says an empty limit returns all records. The implementation sends limit ?? 999999999 and cursor undefined to the API, then returns response.body.data without iterating a next cursor.
- Sample volume tests in the Cloud project: 101→101 (run 23OiaT74UbUlYEwgMG2pC); 201→201 (run 67gFJzZanE68mLswLpMQn); 501→501 (run U1Hqc2j98hqZuYEb3zNZf). Each succeeded in TESTING; all temporary rows were deleted and follow-up searches returned 0. Full details: https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/find-records-volume-test-501-2026-10-17.md
- These results verify at least 501 rows in the current Cloud project; larger volumes are not tested.
- Tables feature docs describe uniqueness on (projectId, fieldId, recordId), not a unique constraint on arbitrary runId. Atomic uniqueness for registry runId is not established; concurrent first-writer race remains unproven.

## Concurrency and queueing
- Official guide: https://www.activepieces.com/docs/admin-guide/guides/manage-concurrency
- Max Concurrent Jobs is a per-project setting. When reached, new runs queue and retry until a slot opens.
- This is not documented as per-flow concurrency. Setting it to 1 in the shared project could serialize all flows, including five protected production flows, so do not change it as a mock-only fix.
- The connected Activepieces tool catalog does not expose a project concurrency-settings action. No setting was changed.

## Waitpoints / BARRIER
- Official architecture docs: https://www.activepieces.com/docs/install/architecture/waitpoints
- Official Flow Control docs: https://www.activepieces.com/docs/build-pieces/piece-reference/flow-control
- BARRIER is a supported waitpoint type in the engine; docs describe pieces creating waitpoints via ctx.run.createWaitpoint and ctx.run.waitForWaitpoint.
- Built-in Subflows action catalog did not expose a visual BARRIER action. A custom piece/action may be needed; hosted Cloud installation/availability was not verified. Do not invent an action name or call internal endpoints.

## Current test state
- Mock coordinator EoQdyZftEyejxh4P85K5S: 21/21 valid, 0 invalid, two informational empty-fallback notes; draft/disabled.
- Mock registry 0 rows; mock coordinator input 0 rows; existing mock results table remains at 14 rows.
- Five protected production flows remain enabled/published; hourly automation schedule unchanged.
