# AI Bot Team — isolated no-cost proof of concept

A **3-role collaboration prototype**. It is runnable today with Python 3.10+ and **no third-party packages, credentials, background jobs, provider API, or network calls**. It never touches existing GitHub main, ChatGPT scheduled jobs, or Activepieces production flows.

## Quick start

```bash
python3 bot_team.py --task "AI 봇 협업" --sources examples/sources.json
python3 -m unittest discover -s tests -v
```

- `ResearchBot`: checks the *provided* reference metadata, deduplicates sources, and matches tags. **It does not browse the web or verify the claims in references.**
- `BuilderBot`: creates a safe, reviewable proposed action list. **It neither writes code nor modifies external projects.**
- `VerifierBot`: blocks missing evidence, unapproved action types, production targets, source lineage mismatches, and provider calls. Verdict only covers **structural offline policy checks**.
- `audit_sha256`: deterministic SHA-256 for report payload (not a signature or independent execution proof).

**Not yet**: LLM-backed autonomous research/development, connection to Gemini/Claude/ChatGPT, unattended execution, operating-environment integration or empirical accuracy benchmarking. Integrate later only with known-zero-cost local models or independently verified free quota, in a sandbox with explicit permissions. Never interpret local PASS as scheduled ChatGPT unattended success.

Design references (no dependency): Python `concurrent.futures` docs, LangGraph MIT open-source architecture. Source metadata in `examples/sources.json` is example input, not independently audited evidence.


## ChatGPT private plugin (2026-10-22)

A private **AI 3봇 협업** ChatGPT skill plugin was created from this offline prototype. When the plugin is available and active, ChatGPT **may** select its three-role instruction workflow for relevant AI-project prompts; it is not an always-running local Python hook, and it does not guarantee automatic selection in every existing/new conversation. The current session has not yet independently confirmed the plugin's invocation in a newly opened chat.

In an eligible ChatGPT conversation use plain language: `AI 프로젝트 코드 오류 분석하고 검증해`; to target the plugin, select `@AI 3봇 협업` if available. The plugin contains instructions and offline scripts, **no remote MCP server, provider API access, scheduled task, or independent Gemini/Claude/ChatGPT models**. It can use previously connected apps when available and authorized in the chat, but no such operation is implied by merely creating the plugin.

Run the deterministic local router (not a ChatGPT callback):

```bash
python3 chat_router.py --task "AI 봇 협업 개선" --sources examples/sources.json
python3 -m unittest discover -s tests -v
```

Direct chat is chosen for messages without explicit AI-project keyword matches; project work selects the three-role workflow. This classifier is a **demo heuristic**, not ChatGPT's internal tool or skill auto-invocation policy. Returning PASS means the proposed sandbox collaboration satisfies offline guards, not a real LLM response or real external system modifications.
