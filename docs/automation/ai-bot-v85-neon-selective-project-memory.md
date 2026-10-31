# AI BOT v8.5.0 isolated candidate — selected project memory

**Connector bridge v8.5.3 isolated candidate (without external DB credentials):**
`tools/isolated_neon_chat_turn_bridge_v853.py` creates an opt-in
**plan** for the already connected ChatGPT Neon SQL tool. Its target is
hard pinned to the existing disposable TEST branch and database. Dynamic
goal/result strings are expressed as hexadecimal UTF-8 decoding, never
raw SQL text interpolation. It creates a single idempotent INSERT and a
separate project-scoped SELECT; the host must call the tool twice using
the supplied exact `project_id`, `branch_id`, and `database_name`
arguments, then pass the raw responses through
`validate_neon_connector_results`. Any mismatch is a failure.
No password, API key or PostgreSQL login role is required for **connected
Neon tool calls** in the currently authorized ChatGPT session.

This is **NOT** automatic ChatGPT-wide message capture or proof that the
Python module runs as a background service. The application only works
when an authorized ChatGPT project turn actually selects a record,
sends the tool calls and verifies the returned rows. Offline GitHub CI
proves code safety; real Neon connector SQL calls must be observed
separately. The hosted Python PostgreSQL adapter still awaits the
restricted TEST role `aibot_v85_memory_test_rw` and does not fall
back to owner credentials.

**Latest isolated patch:** v8.5.2 candidate adds a test-only guarded SQL
executor and a *fresh, read-only* target preflight. It checks PostgreSQL
`current_database()`, `current_user`, and the exact SHA-256 of an
existing **synthetic** marker record previously written only to the
disposable Neon test branch. Each approved query rechecks those facts on
the **same database connection and transaction** before INSERT or SELECT.
The caller passes a trusted, restricted, TLS-enabled `connect()`
factory; no DSN/password is stored in GitHub. If proof is absent,
mismatched, or the test-only role is not active, operations fail closed.

The expected role name is `aibot_v85_memory_test_rw`. **Do not
programmatically create this role or transfer credentials** without an
explicitly authorized isolated-branch setup and verified free quota.
This code is currently verified with offline mock PostgreSQL connections
only. Its connection to the hosted Neon branch remains **UNVERIFIED**.
The synthetic marker is public, **not a secret or authentication
credential**; cloned branches could contain it, so strict DB role
permissions, TLS, Neon API branch verification and restricted grants
remain required for a true end-to-end connection.

**Previous isolated patch:** v8.5.1 candidate blocks executor scope mismatch before I/O.
Trusted executor must supply fixed `bound_project_id`, `bound_branch_id`, and
`bound_database_name` from authenticated connection configuration. This is
an **advisory local fail-closed defense**, not cryptographic proof of the
underlying connection. Actual credentials must still be least-privilege
and restricted to the disposable test branch. Four regression tests cover
wrong/missing scope and unapproved branch. Version is only test-verified if
exact remote PR SHA and CI pass are independently read back.

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
