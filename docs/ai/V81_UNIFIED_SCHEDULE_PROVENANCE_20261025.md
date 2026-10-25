# Unified GitHub schedule provenance correlation (isolated)

This offline tool accepts externally supplied GitHub run/job/log objects.
It cannot authenticate that the supplied objects came from GitHub; **the
calling assistant must first independently fetch the official API run and
job objects and the raw job log through the connected GitHub provider**.

It verifies matching numeric run IDs, \`event=schedule\`, job success,
exact main workflow SHA, exact checkout SHA, unique unified JSON receipt,
canonical SHA-256, Python 23 + Java 20 + JS 20 + C11 20, FAST 20 and
FULL 100, 31 fail-closed regression tests, runner context linkage and
the previous offline audit marker.

It deliberately refuses to treat a successful offline receipt as proof
of native ChatGPT unattended tool calls. The hardcoded false flags are
preserved regardless of reported GitHub success.

Usage after obtaining authorized original data:

\`python3 v81_unified_schedule_provenance.py --input local-github-evidence.json\`

The JSON must have keys:
\`run\` (official GitHub run object), \`jobs\` (official job list),
\`log\` (raw log), \`workflow_sha\` (expected main commit SHA) and
\`source_sha\` (expected checked-out pinned commit SHA).

Offline tests are synthetic fixtures only and are not independent API
authentication. No GitHub main / :15 schedule / ChatGPT :00 task /
Activepieces / Slack / paid LLM configuration is changed.
