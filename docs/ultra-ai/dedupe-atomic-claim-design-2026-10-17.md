# ULTRA AI — Safe Atomic Duplicate Prevention Design
Date: 2026-10-17 (Asia/Seoul)
Status: DESIGN ONLY — no production flow, table, connection, or concurrency setting changed.

## Problem
The current Activepieces Tables action set exposes Find Records, Create Record(s), and Update Record, but the public user-facing action list does not establish an atomic unique-key/upsert operation for arbitrary `runId`. A `Find Records → Create Record` sequence is vulnerable to a race: two concurrent runs can both observe no registry row and both create one.

## Recommended pattern to validate in an isolated environment
Use a storage engine that enforces a unique constraint on an idempotency key and supports a single atomic claim operation. A PostgreSQL-compatible example:

1. Create a dedicated registry table with `run_id TEXT PRIMARY KEY` (or a UNIQUE constraint) plus `status`, `attempt`, `lease_until`, `created_at`, and `updated_at`.
2. Before any external side effect, claim the run in one SQL statement, e.g. `INSERT ... ON CONFLICT (run_id) DO NOTHING RETURNING run_id`.
3. If the statement returns a row, this execution owns the first claim and may proceed. If it returns no row, treat it as duplicate/already claimed and do not repeat side effects.
4. On success, atomically update status to `COMPLETED`. On failure, define an explicit retry policy. If using a lease, reclaim only with a conditional update that proves the previous lease expired; do not blindly delete a claim.
5. Make downstream side effects idempotent where possible. A registry alone cannot make an unrelated external API call and a database update one distributed transaction.
6. Test simultaneous duplicate run IDs, distinct run IDs, worker failure after claim, retry after lease expiry, and cleanup in a separate database/schema with synthetic data only. Require one winner for the same key and no missing winner for distinct keys.

## Why this is only a proposal
- No database/provider was provisioned or called.
- No Activepieces project action was attempted in this run because the required `ap_set_project_context` initializer is not exposed in the available tool runtime.
- A free/paid tier, connection availability, and the user's entitlement to a PostgreSQL-compatible store have not been verified. Do not create a service, add a secret, or make a paid call without checking those facts.
- Activepieces Tables' 501-row Find Records sample test passed, but that is a volume test, not proof of atomic uniqueness.

## BARRIER finding
Official Activepieces docs describe `BARRIER` as a waitpoint type used through the piece API (`ctx.run.createWaitpoint` / `ctx.run.waitForWaitpoint`). This is not proof that the current Cloud project has a built-in visual BARRIER action. Official platform-level custom/private piece management is documented as a paid feature; the exact project entitlement remains unverified. Keep the coordinator draft disabled/unpublished.

## Evidence and official references
- Activepieces Tables actions: https://www.activepieces.com/pieces/tables
- Activepieces waitpoints: https://www.activepieces.com/docs/install/architecture/waitpoints
- Activepieces flow control piece API: https://www.activepieces.com/docs/build-pieces/piece-reference/flow-control
- Activepieces custom/private pieces (paid feature): https://www.activepieces.com/docs/admin-guide/guides/manage-pieces
- Activepieces project-wide maximum concurrent jobs: https://www.activepieces.com/docs/admin-guide/guides/structure-projects
- PostgreSQL INSERT / ON CONFLICT semantics: https://www.postgresql.org/docs/19/sql-insert.html

## Safety conditions
- Do not set shared project concurrency to 1; it could affect the five protected production flows.
- Do not edit or publish production flows, activate mock drafts, test production webhooks, or change the hourly schedule.
- Do not infer free API access from a successful model-list request.
- No paid API calls, purchases, upgrades, or secret output/commit.
