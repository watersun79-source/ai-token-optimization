# AI R16 v8.1 — Local provenance guard (isolated)

This branch adds an offline-only verifier for v8.1 result JSON and a CI regression suite.
It does **not** install v8.1 on GitHub's existing scheduled audit, nor change ChatGPT's hourly scheduled task, Activepieces, Groq, or credentials.

- `scripts/v81_provenance_gate.py`: accepts an existing **local** v8.1 `bridge.execute(..., 'all')` JSON report. Strictly checks 100 unique rule IDs, all-pass statuses, 18 explicitly synthetic replacements, source-hash shapes and fail-closed provenance claims.
- `tests/test_v81_provenance_gate.py`: synthetic **unit tests**. Passing them does not execute all v8.1 rules, authenticate GitHub jobs, or prove native ChatGPT app operations.
- The user-owned v8.1 ZIP was previously verified in a separate local environment: SHA-256 `8c06d103af54d119c31ed927e0266a6d15dab4d9e24036cd2974e9b76739035a`; 48 Python tests passed, 100 offline rules passed. **The ZIP and user evidence files are not copied into this public repository.**
- Previous main scheduled job at `2026-10-24 08:35 / 09:53 Asia/Seoul`: GitHub `event=schedule` and job logs verified; those runs use v7-compatible 82 PASS / 18 UNVERIFIED logic, distinct from local v8.1. CI events are not ChatGPT native app ledgers.
- New GitHub workflow is restricted to this isolated branch, read-only, no external LLM, no cron, no secrets, no deployment.

Execute locally:
```bash
python3 -m unittest discover -s tests -p test_v81_provenance_gate.py -v
python3 scripts/v81_provenance_gate.py /path/to/bridge/all_result.json
```
Even a valid local JSON file remains **self-reported and unauthenticated**. Separate same-run GitHub/Slack tool-call proof remains UNVERIFIED.

Oracle Cloud: explicitly excluded at user's request.
