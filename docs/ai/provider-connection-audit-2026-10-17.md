# AI Provider Connection Audit — 2026-10-17

## Scope
Read-only connection inventory and model-list checks in the existing Activepieces project. No prompt was sent for generation. No provider API token generation occurred.

## Findings
- Project connections inventory reported five connections with status ACTIVE: OpenAI, Google Gemini, Google Gemini api, Slack, Anthropic Claude. A status label alone does not prove the credentials work.
- Connection labelled Google Gemini: one read-only List Models action returned “completed” and a model-list payload. This confirms the credential responded to a model-list request at least once; it does not confirm whether subsequent generation would be free or paid.
- Connection labelled Google Gemini api: read-only List Models failed with HTTP 401, “API key not valid. Please pass a valid API key.” No generation was attempted.
- Connection labelled Anthropic Claude: read-only List Models failed with HTTP 401, “invalid x-api-key.” No generation was attempted.
- The ChatGPT plugin search did not find a dedicated Gemini or Claude plugin. Activepieces does contain provider pieces and connections.
- The user previously purchased a US$5 Claude API balance, which is paid balance rather than proof of free API access. The active connection currently fails authentication, so it cannot be used until repaired.
- Google Gemini connection billing tier remains unknown. A working model-list request is not proof that generation is free.

## Safety / cost
- Gemini generation calls: 0.
- Claude generation calls: 0.
- OpenAI generation calls: 0.
- No secrets or API keys were read, printed or changed.
- No production flow was edited or run.
- Existing hourly automation unchanged.

## Required manual repair
1. In Activepieces Cloud, open the current project and go to Connections.
2. Reconnect/edit “Anthropic Claude” with a valid Anthropic Console API key. Never paste the key into chat or GitHub.
3. If the second Gemini connection is still needed, repair “Google Gemini api”; keep the first “Google Gemini” connection unchanged until its billing tier is confirmed.
4. Before any generation call, verify the intended account/project's free-tier or paid-credit policy. Do not treat the US$5 Claude balance as free.
5. After repairing, run one short, low-token test only after the free/credit policy is explicitly verified, then record actual response, run ID and costs.

## Evidence
- Activepieces read-only List Models for Google Gemini succeeded once.
- Activepieces read-only List Models for Google Gemini api failed 401.
- Activepieces read-only List Models for Anthropic Claude failed 401.
