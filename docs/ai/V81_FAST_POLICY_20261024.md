# AI BOT v8.1 isolated Adaptive FAST mode — 2026-10-24

## Actual isolated CI integration
- Fast audit and full regression remain independent **parallel** jobs on code push, keeping the previous fast path.
- Fast job now runs `v81_speed_orchestrator.py --ci-fast`: 20 offline checks, immediately replayed with the identical sealed snapshot (20 duplicate checks avoided); a separate 150-iteration benchmark remains descriptive.
- Full job now executes a fail-closed gate from `v81_ci_gate.py`. If, and only if, GitHub push's `before` SHA equals checked-out `HEAD^`, Git HEAD matches trusted `GITHUB_SHA`, and **every changed path** is an exact allowlisted documentation path, the expensive original/100-rule full steps are skipped. Otherwise all full tests execute. Manual dispatch always executes full. No third-party actions, paid API or persistent CI cache.
- Checkout for full gate uses two commits and `persist-credentials: false`. Source and evidence checks remain mandatory on code changes. Gate/dispatch unit tests include real local throwaway Git repo commits and negative cases.
- No CI job success alone proves `100/100 PASS`: when gate says `docs_only_single_commit`, full job finishes successfully **without running its 100 checks**. Inspect the gate output/log before reporting.
- `batch_read` provides safe dedup+up-to-4-thread parallelization for independent caller-provided read-only operations. It does NOT connect live GitHub or Slack from Python; connector integration remains separate.
- `compact_report` suppresses unchanged PASS but preserves FAIL/ERROR/UNVERIFIED. Hash seals are in-process only. No native ChatGPT per-run attestation is inferred.
- Performance reporting distinguishes GitHub Actions job duration from Python rule latency and synthetic 6ms I/O. Keep earlier baseline CI #40066714288; compare actual new run logs with their separate SHA, event and gate decision.
- Existing single ChatGPT :00 reservation, GitHub main/:15 cron, Activepieces/Slack production, cloud accounts, credentials, private ZIP, and billing untouched.

## Manual test
```bash
cd experiments/r16-bot-runtime
python3 -m unittest -q test_v81_ci_gate test_v81_speed_orchestrator
python3 v81_speed_orchestrator.py --ci-fast  # requires GITHUB_SHA on CI
```

## Real workflow verification
- First isolated code-change push: Actions [40068842236](https://github.com/watersun79-source/ai-token-optimization/actions/runs/40068842236), SHA `bb79bdbcc6c7175e7488420b3fd3b73cb6b7ee3f`, fast and full jobs completed/success, gate `run_full=true`, verified from raw logs. This proves conditional full regression for changed runtime/workflow only, not native task success.
- This documentation-only append is a controlled experiment of the opposite gate branch. The next workflow run is expected to emit `reason=docs_only_single_commit, run_full=false` and skip actual 100-rule steps. Only confirmed CI logs, not this expectation, establish that result.
