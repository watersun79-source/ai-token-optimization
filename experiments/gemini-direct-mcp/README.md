# Gemini private MCP runner

Official Gemini CLI 0.66.0 is invoked through a private Sites MCP gateway and this bearer-protected Docker HTTP runner. Y700 and other user devices are not execution hosts.

Only `/healthz` is public. Every other route requires GEMINI_BRIDGE_KEY; auth and review also bind the Sites authenticated actor. Use a new isolated Render free web service with auto-deploy disabled, Docker context `experiments/gemini-direct-mcp` and repository-relative Dockerfile `experiments/gemini-direct-mcp/Dockerfile`. Never reuse an existing production service.

The Site holds the same bridge key as a secret and the exact returned onrender HTTPS origin. Google credentials never enter MCP tool arguments, logs, Git or this README. Official Google consent and CLI auth-code entry use secure browser authentication. The initial OAuth authorization URL is not a credential. Auth finish returns VERIFYING while bounded official ACP initialize/session-new checks run without a model prompt.

Authentication, free CLI quota, model generation, native ChatGPT tool exposure and scheduled delegation are separate states. Model generation stays blocked until independent, recent official CLI free-quota evidence is supplied through a private operator verification gate. No provider API keys, Vertex route or paid provider fallback are supported. One CLI invocation does not prove exactly one provider request. No native schedules are modified by this runner.

Root-owned system settings disable auto-memory, hooks and telemetry and cap model session turns at one. A verified explicit admin deny policy blocks all tools. No central policy directory is created. A free ephemeral instance is not a persistent credential vault or a 24/7 guarantee; restarts can require Google login again. No paid disk, paid service plan or paid model API has been provisioned by this source.

Local unit tests use process doubles, not real Google authentication or provider generations. See ADAPTER.md for the adapter contract. Run from this directory: `python3 -m unittest discover -s tests -v`.
