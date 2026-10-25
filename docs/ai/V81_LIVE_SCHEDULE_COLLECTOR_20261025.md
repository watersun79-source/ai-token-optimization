# Read-only official GitHub schedule collector

The isolated FAST CI uses the scoped ephemeral github.token with
actions:read to query the official GitHub REST API using gh api.
Read-only GET endpoints: /actions/runs?event=schedule&per_page=20,
 /actions/runs/<run_id>/jobs?per_page=100, and /actions/jobs/<job_id>/logs.

Expected production workflow SHA:
923c281f82023cc6b49f3844bad17f508f1ab203.
Expected pinned source SHA:
a88c7993c27404da43cba84a8f69e01a917315a6.
The collector checks the latest schedule run on main, the linked
job and raw log, and the unified evidence SHA-256 and counters.

PASS = official GitHub offline scheduled-run evidence consistent.
NOT_APPLICABLE = the expected new schedule version has not fired.
UNVERIFIED = missing or incomplete API evidence.
FAIL = contradictory verified evidence, blocking isolated CI.
No outcome proves native ChatGPT unattended execution.

Mock tests have no network; actual GET occurs in isolated FAST CI.
No new recurring schedule; no change to GitHub main, :15 cron,
ChatGPT :00 task, Activepieces or Slack. No paid API or external LLM.
