# AI BOT v8.5.0 isolated candidate — selected project memory

**Status:** isolated proof only. Do **not** merge/deploy to production. No ChatGPT-wide transcript interception, no native ChatGPT always-on listeners, no real external model calls.

## What the user explicitly authorized

Persist **selected** AI project goals or task results (not raw chat, files, credentials, or all messages) and restore them through a Neon test branch. Existing AI BOT v8.1 private Site, Cloudflare D1, Neon main, original ChatGPT hourly schedules, Render, Activepieces, Slack, and GitHub main remain untouched.

- Neon project: `autumn-frog-53985417`
- Original **protected** Neon main branch: `br-solitary-firefly-azge9w3x`
- Isolated test branch: `br-billowing-union-azaxxi5p` (`test-chatgpt-selective-memory-20261101`)
- Database: `aibot_isolated`
- Isolated schema table: `public.isolated_project_memory_v85`
- GitHub branch: `ai/v85-neon-selective-memory-20261101`

## Call-bound design

An authorized project event source calls `save_selected_event(execute, event, test_branch_id="br-billowing-union-azaxxi5p")`. The event is a strict object containing **exactly** `selected`, `record_id`, `project_key`, `kind`, `title`, `body`. Without explicit `selected: true`, the event is skipped without DB I/O. Only `goal` and `task_result` kinds are eligible; transcripts are skipped. A safe caller can pass the returned record identifiers into `restore_project_records` for the same project key. Missing/suspicious credential markers, unexpected fields, bad identifiers, oversized data, and control characters fail closed.

`execute` is an adapter to parameterized PostgreSQL queries, **not** an unrestricted chatbot SQL generator. SQL identifiers are fixed in source. Avoid passing user-controlled database URLs or DB owner credentials. Use a restricted test-branch role only. Never point the adapter to main: branch ID argument protects against accidental main selection, but must also be enforced independently in the actual connection configuration and operator permissions.

PostgreSQL schema is available as `CREATE_TABLE_TEST_BRANCH_ONLY` in the module. The table is created **only on the Neon test branch**. `record_id` is unique; inserts use `ON CONFLICT DO NOTHING`. A repeated identical request returns `ALREADY_EXISTS`, while a reused ID with different content fails readback (no silent overwrite). `restore_project_records` checks the content SHA-256 before returning and filters on project key.

## Real isolated Neon connector test (2026-11-01 KST)

Connector `run_sql` was called with **explicit** `project_id`, `branch_id=br-billowing-union-azaxxi5p` and `database_name=aibot_isolated` for every operation.

1. `CREATE TABLE IF NOT EXISTS public.isolated_project_memory_v85 (...)` returned success.
2. One SQL INSERT for two synthetic records returned two rows:
   - `synthetic-goal-v85-20261101-01` — SHA-256 `957373978a872a179b386f312205e7983f97baf2c784e8f544fb23409dbf56e7`.
   - `synthetic-result-v85-20261101-01` — SHA-256 `c45e75860068f15f4c5f7ee6ec23f88ed3c10b0aae036a95492237e6673d3876`.
3. A separate SELECT on that test branch returned **2 matching rows** including full content/digests.
4. Repeating the same goal INSERT returned **0 rows**, confirming idempotent `ON CONFLICT DO NOTHING` behavior for the fixture.

This proves **real Neon connector SQL write and independent readback**, *not* that the GitHub Python adapter itself has logged into Neon, nor an automatic full ChatGPT chat-to-Neon sync. Python adapter tests use a fake parameterized executor; deploy integration awaits verified restricted credentials, source connector authentication and the user's permission for production changes.

## Offline regression

The repository's existing `.github/workflows/validate.yml` runs `python -m unittest discover -s tests -v` for PRs into main. `tests/test_isolated_selective_memory_v85.py` covers consent, rejected chat kinds, SQL parameterization, readback, duplicates, hash mismatch, secret rejection, branch guard, project scoping and range limits. Official CI pass must be confirmed by a matching run and HEAD SHA; local/offline test success does not prove native scheduled ChatGPT execution.

## Version and protection

- Isolated candidate: `v8.5.0-isolated-candidate`; **not a production upgrade** or Neon/PostgreSQL engine upgrade.
- Main/source, D1 v8.1 protected Site, existing four ChatGPT automations, and operating Render/Activepieces flows are unchanged.
- No connection secrets are retrieved, embedded, forwarded to ChatGPT, or saved to public GitHub. No paid AI calls.
- Neon Free compute/storage consumption and remaining included quota must be assessed before repeated tests; avoid periodic wakeups.
