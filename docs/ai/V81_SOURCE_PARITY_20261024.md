# AI R16 v8.1 original archive ↔ isolated fast/full code parity

Goal: compare source bytes from user-owned local `AI_R16_v8_1_100BOT_local_router_verified.zip` and GitHub isolated branch.

Original ZIP SHA-256 (verified locally, CRC okay):
`8c06d103af54d119c31ed927e0266a6d15dab4d9e24036cd2974e9b76739035a`.

New isolated test `v81_source_parity.py` compares **ten** source-file SHA-256 digests:
- EXACT: `evidence.json`, `measure_runtime.py`, `utc_strict_oracle_cases.tsv` (3).
- DIFFERENT: `runner.py`, `catalog.json`, `UtcStrictOracle.java`, `utc_strict_oracle.js`, `test_runtime.py` (5).
- ABSENT on GitHub: `replacement_bots.py`, `fixture_SYNTHETIC.json` (2). The separate `v81_split_bench.py` is a reimplementation of 18 synthetic rule checks, **not** the original code.

The exact SHA value for each original local file is kept as a **fingerprint only**; no local ZIP content or user-specific original fixtures are copied to this public repository. The isolated test permits PARTIAL comparison to report honestly; `--require-verbatim` fails with exit 2 if any mapped file differs or is absent.

The existing compatibility CI previously reported synthetic 20/20 fast and 100/100 full PASS. **Those PASS counts do not show byte-identical original v8.1 deployment or authenticated ChatGPT/Slack operations.** This audit prevents that conflation.

This is an isolated GitHub branch **without cron** or production deployment. Preserve GitHub `main`, existing :15 Actions workflow, ChatGPT :00 automation and Activepieces operating flows. No model APIs, paid services, or new cloud services.

Safe follow-up: independently re-verify user-owned ZIP contents in private runtime, decide whether to keep original code private and test with private artifacts or explicitly authorize publishing sanitized source before changing any production workflow.

## 2026-10-24 isolated differential triage and minimal guard

The original local v8.1 ZIP was independently re-opened and its SHA-256 matched the existing anchored value. No user ZIP, original replacement_bots.py, or original synthetic fixture is published.

- Three exact inputs: evidence.json, measure_runtime.py, utc_strict_oracle_cases.tsv.
- Five intentionally different public files: runner.py / test_runtime.py apply fail-closed offline provenance and negative tests; catalog.json separates the 18 fixture-only replacements from native run claims; Java and JavaScript timestamp oracles enforce stricter fixture/header/row validation.
- Two intentionally absent private originals: replacement_bots.py and fixture_SYNTHETIC.json; the public v81_split_bench.py adapter is not those exact files.
- A newly reproduced **actual input-validation defect shared with the original**: E05 checks `isinstance(max_start_delay_seconds, int)`, which accepts Python `True` and `False` because booleans subclass integers. With zero start delay both are erroneously accepted. The isolated adapter now uses `type(delay) is int`, and a focused test verifies both booleans FAIL while integer zero PASS.
- Byte-level original parity remains **3 EXACT / 5 DIFFERENT / 2 ABSENT by design**. A passing simulated 100-role contract does not claim byte identity, provider API authorization, ChatGPT scheduled-run provenance, or production deployment.
- This targeted defensive improvement does not modify the original private archive or production main/:15/:00/Activepieces state. GitHub CI must independently verify fast-audit and full-regression jobs on this isolated commit.
