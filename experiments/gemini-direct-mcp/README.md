# Gemini direct private MCP

The hosted path is ChatGPT → the existing owner-private Sites MCP gateway → the existing bearer-protected Render free runner → Google's official Gemini REST API. Y700 and the user's phone are not execution hosts. The fixed generation model is `gemini-3.5-flash-lite`.

Google AI Studio authorization keys use the `AQ.` public prefix and are sent only in the `x-goog-api-key` header. The private registration form and both Python validators accept that prefix with 16–253 ASCII letters, digits, underscores or hyphens after the dot, while retaining the existing 16–256-character non-dot key format. Extra dots, whitespace and control characters are rejected. Syntax acceptance is not authentication, project binding, Free-tier or quota verification. The public prefix is also detected and rejected in model prompts and model output. Tests use unmistakably synthetic strings; no chat-provided credential is used.

The host browser's automated credential prompt was rejected by automatic approval review because it labels API-key registration as sign-in. Do not relabel the form as a login, retry automated collection, use the clipboard, read page secrets or bypass that rejection through another surface. Use the existing private manual form under the user's control. A credential pasted into chat must not be copied into tests, reports or model arguments.

## Boundaries

- Only `/healthz` is public. All runner operations require the bridge bearer. Key registration, evidence preparation and review also require the bound Sites owner actor.
- `/api-key/register` accepts one key through the private same-origin password form, never through MCP arguments. It verifies only the fixed model's metadata with one GET and does not generate text or establish the key's project, billing tier or remaining quota.
- `gemini_prepare_free_api_run` records already independently observed private evidence references for the allowlisted project. It is an operator assertion, not a provider attestation. Supply it only after actual key/project binding, Free tier, unlinked billing and the same Pacific day's model quota have been observed. Evidence expires after 15 minutes.
- `gemini_review` accepts only `request_id` and non-sensitive `prompt`. A fresh, owner/key/model/project-bound evidence record permits one generation attempt. No paid project, model fallback, tools, search, proxy, redirect or automatic retry is supported.
- Claiming the SQLite evidence budget is atomic, shared with the existing request ledger and precedes network execution. Repeated request IDs return the recorded result; conflicting prompts or uncertain requests are blocked. Reusing the same source references cannot restore a consumed evidence budget.
- A child process receives secrets only through a private stdin pipe. A 35-second total host deadline bounds DNS/TLS/body handling; output is capped at 64 KiB. Parent exit kills the child on Linux. Only a validated STOP response receives `PASS_REAL_GEMINI_API_RESPONSE`; timeout, partial response and uncertainty remain unverified.
- Keys use no-follow, owner-only 0600 files in a 0700 directory. Raw keys, hashes, provider errors and auth codes are never returned to the page or MCP. Replacing a different registered key is denied. Status polling reads only local non-secret metadata/file attributes and never authenticates or generates.

## Live state

Registration failures are distinct from never having attempted registration. Five historical Site requests to `/api-key/register` returned HTTP 503 on 2026-11-04; their upstream Google reason was discarded by the earlier implementation and remains unknown. Do not label those events as missing user input or infer a Google 401/403 from the Site's 503.

The fixed metadata GET now classifies failures using a small static code allowlist, numeric HTTP status, and narrowly validated Google ErrorInfo reasons. No raw provider body, message, header, account, project, key or key hash is reported. The local 0600 `api-registration.json` stores only result, fixed code, provider HTTP status and observation time. `api_connection.last_registration` exposes only that sanitized record. A failed metadata check still stores no key/auth/free evidence and consumes no generation budget. Missing diagnostics do not prove that no prior attempt happened, especially after an ephemeral runtime restart.

The private Site returns only the same fixed error codes and renders them in Korean. It never retries registration automatically. Ask the user only for the non-secret error classification when more information is needed; never ask them to paste a key into chat.

Both existing private Sites poll read-only status every 30 seconds while visible and online. `api_connection` separates key presence, recorded metadata authentication, Free evidence, readiness and actual response time. Cached CLI installation metadata remains a separately labelled legacy view. Readiness is not proof of a Gemini response or a provider quota guarantee.

The current free Render service has an ephemeral filesystem. The SQLite budget persists across process restarts on that filesystem, but a platform restart/redeploy can erase keys and the ledger. Missing state closes the gate; do not automatically re-register, re-arm or retry an uncertain prior run. This is not persistent secret storage or a 24/7 service guarantee. No paid disk, service upgrade or billing account is provisioned.

## Deployment and tests

Keep auto-deploy disabled, the existing service's free plan, existing bridge secret and private Site audiences. Docker context: `experiments/gemini-direct-mcp`; Dockerfile: `experiments/gemini-direct-mcp/Dockerfile`. Set only `GEMINI_API_ALLOWED_PROJECT_ID` to the independently observed dedicated Free project. Never put a provider key in Git, environment inspection output, a URL or a chat.

The Docker image copies `adapter.py`, `server.py`, `http_server.py`, `api_runtime.py` and `gemini_direct.py`. Offline unit tests use fixtures and process/transport doubles, and do not establish Google authentication, quota or inference. Existing native schedules, other services and GitHub main are untouched.

Google ended consumer Gemini CLI Login with Google on 2026-06-18. The installed CLI 0.66.0 and the standalone adapter contract in `ADAPTER.md` are historical installation metadata, not the hosted inference route. Consumer Antigravity CLI wrappers are not used.

Official references:

- https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals
- https://aistudio.google.com/api-reference/generate-content
- https://aistudio.google.com/docs/pricing
- https://aistudio.google.com/docs/billing
- https://aistudio.google.com/docs/api-key
- https://discuss.ai.google.dev/t/new-aq-auth-key-returns-401-unauthenticated-access-token-type-unsupported-with-google-genai/186891
- https://antigravity.google/docs/faq/
