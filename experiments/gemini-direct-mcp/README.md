> Current provider policy, verified 2026-11-04: Google ended Gemini CLI consumer Login with Google (individual/free, Google AI Pro and Ultra) on 2026-06-18. See https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals . An installed CLI and successful private MCP status response do not prove model-service access. The model gate remains closed. The official Gemini API route requires separate verified Free-tier project credentials; none are configured here. Antigravity consumer wrappers are not a supported substitute (https://antigravity.google/docs/faq/).

# Gemini private MCP runner

Official Gemini CLI 0.66.0 is invoked through a private Sites MCP gateway and this bearer-protected Docker HTTP runner. Y700 and other user devices are not execution hosts.

Only `/healthz` is public. Every other route requires GEMINI_BRIDGE_KEY; auth and review also bind the Sites authenticated actor. Use a new isolated Render free web service with auto-deploy disabled, Docker context `experiments/gemini-direct-mcp` and repository-relative Dockerfile `experiments/gemini-direct-mcp/Dockerfile`. Never reuse an existing production service.

The Site holds the same bridge key as a secret and the exact returned onrender HTTPS origin. Google credentials never enter MCP tool arguments, logs, Git or this README. Official Google consent and CLI auth-code entry use secure browser authentication. The initial OAuth authorization URL is not a credential. Auth finish returns VERIFYING while bounded official ACP initialize/session-new checks run without a model prompt.

Authentication, free CLI quota, model generation, native ChatGPT tool exposure and scheduled delegation are separate states. Model generation stays blocked until independent, recent official CLI free-quota evidence is supplied through a private operator verification gate. No provider API keys, Vertex route or paid provider fallback are supported. One CLI invocation does not prove exactly one provider request. No native schedules are modified by this runner.

Root-owned system settings disable auto-memory, hooks and telemetry and cap model session turns at one. A verified explicit admin deny policy blocks all tools. No central policy directory is created. A free ephemeral instance is not a persistent credential vault or a 24/7 guarantee; restarts can require Google login again. No paid disk, paid service plan or paid model API has been provisioned by this source.

Local unit tests use process doubles, not real Google authentication or provider generations. See ADAPTER.md for the adapter contract. Run from this directory: `python3 -m unittest discover -s tests -v`.

## Live status semantics

Visible, online dashboard pages query metadata every 30 seconds without model generation. The backend collapses concurrent CLI version checks into one process and caches only that executable/home-specific observation for up to 300 seconds. Every status read still checks provider environment, gate and system controls. observed_at_utc is a status-observation time; runtime.verified_at_utc is the actual version verification time. authentication.last_verified_at is set only after an actual non-generation official ACP session succeeds. Missing evidence remains unverified. These reads do not prove live model inference, quota or scheduled delegation.
