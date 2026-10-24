# AI BOT v8.1 speed optimization — isolated only (2026-10-24)
- Prototype: `v81_speed_orchestrator.py` + `test_v81_speed_orchestrator.py`.
- SHA fingerprint binds catalog, evidence, isolated source HEAD. Cache of passing local offline checks exists **only inside the same process**; no cross-hour persistent cache or CI-attested deployment.
- Run the 20-rule fast audit before the 100-rule regression on a cache miss; a change to input or HEAD forces rerun. Any non-PASS fails closed. Advisory `plan_ci` requires caller to independently authenticate exact SHA and CI result; never trusts `last_run_time`.
- Exact read keys deduplicated, independent reads overlapped with at most 4 local threads; requested order reconstructible, failures propagate. No real GitHub/Slack app calls from this script.
- Summary excludes unchanged PASS statuses, always includes FAIL/ERROR/UNVERIFIED. Never claims official native task evidence.
- Host benchmark compares *real local Python rule evaluation* vs same-process cached skip. Separate query-latency example uses explicit 6ms **synthetic I/O**, not real app/network timing. Reported speedup is not total ChatGPT speed or CI job speed.
- Existing standalone fast/full GitHub CI jobs remain independent and parallel. Their startup and checkout costs are not optimized. Existing main, :15 GitHub schedule, ChatGPT :00 task, Activepieces and Slack operations unmodified.
- No private original ZIP, provider secrets, paid API, deploy, workflow schedule or new cloud resources.
