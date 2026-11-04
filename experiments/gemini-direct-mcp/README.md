# Gemini direct private MCP

The hosted path is ChatGPT → the existing owner-private Sites MCP gateway → the existing bearer-protected Render free runner → Google's official Gemini REST API. Y700 and the user's phone are not execution hosts. The fixed generation model is `gemini-3.5-flash-lite`.

## Boundaries

- Only `/healthz` is public. All runner operations require the bridge bearer. Key registration, evidence preparation and review also require the bound Sites owner actor.
- `/api-key/register` accepts one key through the private same-origin password form, never through MCP arguments. It verifies only the fixed model's metadata with one GET and does not generate text or establish the key's project, billing tier or remaining quota.
- `gemini_prepare_free_api_run` records already independently observed private evidence references for the allowlisted project. It is an operator assertion, not a provider attestation. Supply it only after actual key/project binding, Free tier, unlinked billing and the same Pacific day's model quota have been observed. Evidence expires after 15 minutes.
- `gemini_review` accepts only `request_id` and non-sensitive `prompt`. A fresh, owner/key/model/project-bound evidence record permits one generation attempt. No paid project, model fallback, tools, search, proxy, redirect or automatic retry is supported.
- Claiming the SQLite evidence budget is atomic, shared with the existing request ledger and precedes network execution. Repeated request IDs return the recorded result; conflicting prompts or uncertain requests are blocked. Reusing the same source references cannot restore a consumed evidence budget.
- A child process receives secrets only through a private stdin pipe. A 35-second total host deadline bounds DNS/TLS/body handling; output is capped at 64 KiB. Parent exit kills the child on Linux. Only a validated STOP response receives `PASS_REAL_GEMINI_API_RESPONSE`; timeout, partial response and uncertainty remain unverified.
- Keys use no-follow, owner-only 0600 files in a 0700 directory. Raw keys, hashes, provider errors and auth codes are never returned to the page or MCP. Replacing a different registered key is denied. Status polling reads only local non-secret metadata/file attributes and never authenticates or generates.

## Live state

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
- https://antigravity.google/docs/faq/
