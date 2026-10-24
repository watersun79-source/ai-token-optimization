# AI BOT v8.1 speed optimization — isolated only (2026-10-24)
- Prototype: `v81_speed_orchestrator.py` + `test_v81_speed_orchestrator.py`.
- SHA fingerprint binds catalog, evidence, isolated source HEAD. Cache of passing local offline checks exists **only inside the same process**; no cross-hour persistent cache or CI-attested deployment.
- Fast job runs 20-rule audit ONLY because Java/Node receipts required for full 100 are not present. The existing *independent full-regression CI job* performs full tests after preparing receipts; a change to input or HEAD invalidates the fast cache. Any non-PASS fails closed. Advisory `plan_ci` requires caller to independently authenticate exact SHA and CI result; never trusts `last_run_time`.
- Exact read keys deduplicated, independent reads overlapped with at most 4 local threads; requested order reconstructible, failures propagate. No real GitHub/Slack app calls from this script.
- Summary excludes unchanged PASS statuses, always includes FAIL/ERROR/UNVERIFIED. Never claims official native task evidence.
- Host benchmark compares *real local 20-rule Python evaluation* vs same-process fast-result cached skip; no 100-rule claims from fast job. Separate query-latency example uses explicit 6ms **synthetic I/O**, not real app/network timing. Reported speedup is not total ChatGPT speed or CI job speed.
- Existing standalone fast/full GitHub CI jobs remain independent and parallel. Their startup and checkout costs are not optimized. Existing main, :15 GitHub schedule, ChatGPT :00 task, Activepieces and Slack operations unmodified.
- No private original ZIP, provider secrets, paid API, deploy, workflow schedule or new cloud resources.

- CI-driven fix: initial isolated push CI #40066451975 had fast-job failure because it attempted full 100 checks without Java/Python/JS receipts; full job itself passed. Fixed by keeping full 100 only in the existing full-regression job and explicit UNVERIFIED in fast cache.
