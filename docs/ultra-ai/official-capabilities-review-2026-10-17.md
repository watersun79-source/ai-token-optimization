# ULTRA AI — Official Capability Review (2026-10-17)

## ChatGPT custom instructions and memory
- Official OpenAI help: https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions
- OpenAI states custom instructions are applied across chats, including existing conversations, and Free/Go users have a 1,500-character limit.
- The 859-character Korean prompt is saved at https://github.com/watersun79-source/ai-token-optimization/blob/ultra-ai/progress-2026-10-17/docs/ultra-ai/CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md.
- The assistant did not change ChatGPT Settings UI directly; user must paste it into Settings > Personalization > Custom Instructions. Once saved there, OpenAI's stated behavior is that it applies across chats.
- Persistent external memory is a separate layer: use GitHub memory index and Slack status, then retrieve them at the start of a chat. This is not the same as automatic ChatGPT Memory synchronization.

## Gemini and Claude
- Plugin discovery in ChatGPT on 2026-10-17 returned no dedicated Gemini or Anthropic Claude ChatGPT app/plugin.
- Gemini app free limits: https://support.google.com/gemini/answer/16275805
- Gemini API pricing/free tier: https://ai.google.dev/gemini-api/docs/pricing
- Anthropic confirms Claude chat subscriptions and Claude Console/API are separate products: https://support.anthropic.com/en/articles/9876003-estoy-suscrito-a-un-plan-de-pago-de-claude-ai-por-que-tengo-que-pagar-por-separado-por-el-uso-de-la-api-en-console
- Therefore, an app's free access does not prove a workflow's API call is free. No Gemini/Claude provider call was made in this turn; do not claim otherwise. Keep API calls disabled until the account's free usage and billing status are explicitly verified.

## Activepieces Tables and pagination
- Official Tables flow docs: https://www.activepieces.com/docs/tables/in-flows
- Official Find Records implementation: https://github.com/activepieces/activepieces/blob/main/packages/pieces/core/tables/src/lib/actions/find-records.ts
- Find Records has an optional Limit field whose description says an empty limit returns all records. The current implementation sends `limit ?? 999999999` and `cursor: undefined` to the API, then returns `response.body.data` without iterating a `next` cursor. The server's effective behavior for large result sets must be tested in the actual Cloud project; do not assert an exact 100-row cap from the action alone.
- The Tables feature documentation describes records as rows and cells with a uniqueness constraint on (projectId, fieldId, recordId), not a unique constraint on arbitrary `runId`. This does not provide evidence of atomic uniqueness for the registry's runId. Concurrent first-writer race remains unproven.
- Recommended next step: a disposable, mock-only >100-record test, with cleanup and row counts checked before and after. Do not run it against production flows.

## Waitpoints / BARRIER
- Official architecture docs: https://www.activepieces.com/docs/install/architecture/waitpoints
- Official Flow Control docs: https://www.activepieces.com/docs/build-pieces/piece-reference/flow-control
- BARRIER is a supported waitpoint type in the engine; docs describe pieces creating waitpoints via `ctx.run.createWaitpoint` and `ctx.run.waitForWaitpoint`.
- The discovered built-in Subflows action catalog did not expose a visual BARRIER action. This implies a custom piece/action may be needed; hosted Cloud installation/availability of such a custom piece was not verified. Do not invent an action name or call internal endpoints.

## Current test state
- Mock coordinator `EoQdyZftEyejxh4P85K5S`: 21/21 valid, 0 invalid, two informational empty-fallback notes; draft/disabled.
- Sample late-arrival recovery is documented in Slack run `Q68QOU6BW81R0qEGcZGmB`; all provider API calls remained 0.
- Mock registry 0 rows; mock coordinator input 0 rows; existing mock results table remains at 14 rows.
- Five protected production flows remain enabled/published; hourly automation schedule unchanged.
