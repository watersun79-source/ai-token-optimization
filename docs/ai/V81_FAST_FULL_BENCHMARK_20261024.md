# AI R16 v8.1 — isolated fast-audit vs full-regression experiment

## Invariants

- No changes to \`main\`, existing GitHub hourly :15 cron, ChatGPT hourly :00 scheduled task, Activepieces, Slack or Oracle.
- Public repository, **standard** \`ubuntu-latest\` only. No large runners, cloud VM, paid APIs, secrets, artifacts, deployments or external LLM calls.
- Branch-only workflow \`v81-fast-full-isolated.yml\` has **no schedule trigger** and \`contents: read\`.
- The real v8.1 ZIP stays outside this public repository; it must not be uploaded with old private connector snapshots or sensitive metadata.
- This experiment reuses the **82 old non-native rules** from pinned R16 GitHub source \`a551e6ecc290f625432aba7ce2f7c23cc6117a30\` and separately ports the **18 v8.1 local synthetic replacement functions**. It is a **v8.1-compatible isolated adapter**, *not an exact byte-for-byte copy or full deployment of the user-owned v8.1 ZIP*.

## Two independent CI jobs

1. **fast-audit:** tests only S01–S10 + E01–E10, 20 checks, 10 using local synthetic fixture; no Java/Node receipt measurement required. Runs new negative tests.
2. **full-regression:** measures Python 22/22, Java 20/20, JS 20/20 from pinned original source using \`measure_runtime.py\`, runs original Python \`test_runtime\` and new 10 targeted tests, then validates **all 100** rules (82 unchanged snapshot/receipt checks + 18 synthetic replacements).

Both jobs measure medians/p95 of **Python rule-evaluation only** with 150 in-process iterations. GitHub job duration also includes VM setup, checkout and testing, and is not the same as Python timing. Side-by-side numbers from separate jobs are descriptive; VM load varies and cannot prove general speedups without repeated independent runs.

Security/provenance scope:
- v8.1 local fixture PASS **does not authenticate** a native ChatGPT unattended scheduled execution or same-run GitHub/Slack calls.
- 100 BOT roles are NOT 100 independent LLMs.
- CI success = only this isolated GitHub branch code worked; it does NOT change or prove the existing live GitHub cron's v8.1 deployment.
- Logs include exact GitHub run ID, checked source SHA, \`event=push\`, pass counts, median/p95 with explicit mode, and \`native_run_proven:false\`.

## Reproduction

\`\`\`bash
cd experiments/r16-bot-runtime
python3 -m unittest -q test_v81_split_bench
python3 v81_split_bench.py --mode audit --repeats 150
python3 measure_runtime.py
python3 -m unittest -q test_runtime test_v81_split_bench
python3 v81_split_bench.py --mode all --repeats 150
\`\`\`

The local **original v8.1 ZIP** was separately SHA-256 verified as
\`8c06d103af54d119c31ed927e0266a6d15dab4d9e24036cd2974e9b76739035a\`.
Its 48 Python tests and 20/100 exact bridge modes were verified in a separate, non-GitHub environment. **Do not attribute that local timing to the 4 vCPU GitHub VM.**
