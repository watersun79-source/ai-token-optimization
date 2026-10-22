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
