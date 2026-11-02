# AI BOT Version Progress Board (isolated development)

This is an **offline** component-scoped progress reconciler. It does **not**
run on each ChatGPT message, auto-change ChatGPT schedules, or authenticate
CI or deployments itself.

## Shared memory

The authenticated ChatGPT app already stores the board under
`project.ai-bot.progress`, which is linked from the stable alias
`project.ai-bot.version-head`. These are *storage keys*, not release numbers.

Progress is recorded per component: operations, isolated GitHub development,
Rust, evidence guard, Site, Render, Neon, Activepieces, ChatGPT automations.
Phases are source/evidence-specific. Changes require D1
`memory_write(expected_version=...)` with real server-side compare-and-swap.

## Offline engine (no external calls)

```bash
cd experiments/version-progress
python3 -m unittest -v test_progress_tracker.py
python3 progress_tracker.py --board board.json --observation evidence.json \
  --expected-version 1 --record-version 1 --output candidate.json
```

The offline command **never writes the D1 board**. The orchestrating ChatGPT
tool call must fetch the current record, independently verify the provider
receipt and exact SHA/CI/deploy/run provenance, call the pure reconciler,
then perform server-enforced CAS and readback. A provided boolean is not
proof of an authentic provider result; do not treat synthetic fixtures as
live evidence.

## Safety

- Version and progress are separate; memory record revision is not software version.
- A local or GitHub CI pass does not mean ChatGPT native unattended execution.
- Production promotion needs authorization and actual deployment and live proof.
- Do not merge main, change existing scheduled tasks, operating Activepieces,
  Render, Neon, Site, credentials, or make paid model calls.
- If no new independently authenticated evidence: NO_UPDATE.
