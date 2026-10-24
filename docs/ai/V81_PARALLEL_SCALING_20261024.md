# AI BOT v8.1: isolated 4→128 scale experiment (2026-10-24)

## Scope
- **No production change**: user ChatGPT hourly :00 task, GitHub :15 cron, main, pinned source, Slack/Activepieces operations and paid services untouched.
- Previous `v81_adaptive_parallel.py` remains 4→8→16 with safe default 4. This new `v81_parallel_scale_experiment.py` tests 4,8,16,32,64,128 **offline local threads only** in existing public `ubuntu-latest` GitHub runner.
- Every stage executes 128 distinct task keys with simulated 1ms / 8ms waiting, or 2000× SHA256 local CPU hashes. Times are **real hosted execution times on synthetic I/O** and local CPU workload, not live app/network speed.
- Only an offline-only `OfflineAdaptiveScaling` can opt into >16; stage promotion after two successful saturated batches. Error causes safe reduction; 429/permission resets to 4. No auto retry and no secret/error echo. Existing production provider cap not raised.
- Measure median, best, actual peak inflight, complete successes/error count, CPU count, meminfo, peak RSS. 128 concurrent threads are not 128 vCPUs or separate AI bots.
- GitHub API has layered limits, including shared secondary concurrent-request cap 100, but this **does not** imply an available app-specific 100 concurrency budget. Slack has method/workspace tier limits; this experiment makes zero provider requests.
- Official runner: https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- Official GitHub limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- Official Slack limits: https://docs.slack.dev/apis/web-api/rate-limits/
- Recommendation: choose knee where doubling tier no longer offers useful median gain in representative workload, and **do not** apply tier >4 to live connected apps without provider-specific verified quota, backoff and provenance; CPU-bound tasks should follow actual 4-vCPU capacity, not thread count.
