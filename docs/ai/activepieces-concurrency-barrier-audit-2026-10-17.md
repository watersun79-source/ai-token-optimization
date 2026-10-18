# Activepieces Concurrency and BARRIER Support Audit — 2026-10-17

## Status
PARTIAL — official docs confirm the engine supports BARRIER waitpoints, but do not establish that a custom BARRIER piece can be installed in this user's Activepieces Cloud project. Atomic uniqueness for Tables runId records is not documented by the user-facing Tables action list.

## Official findings
1. Waitpoints support DELAY, WEBHOOK, and BARRIER. The BARRIER is an engine waitpoint type that waits for dispatched work/signals and resumes after the configured completion rule. Official docs: https://www.activepieces.com/docs/install/architecture/waitpoints
2. Piece authors use the piece API via ctx.run.createWaitpoint and ctx.run.waitForWaitpoint; this is not presented as a normal built-in visual flow action. Official docs: https://www.activepieces.com/docs/build-pieces/piece-reference/flow-control
3. The documented Tables actions include Create Record(s), Update Record, Get Record, Find Records, Delete Record(s), and Clear Table. The user-facing action list does not document an atomic upsert or arbitrary unique-key constraint. This is not proof no lower-level capability exists, only that it is not established by the public action list. Official docs: https://www.activepieces.com/pieces/tables
4. Activepieces' platform-level custom/private piece management documentation marks piece management as a paid feature. This is a blocker to assuming a custom BARRIER piece can be installed in the current free Cloud project without checking project entitlement. Official docs: https://www.activepieces.com/docs/admin-guide/guides/manage-pieces
5. Activepieces' official Tables product page says each table supports up to 10,000 rows. This is a documented product limit, not a concurrency guarantee. Official docs: https://www.activepieces.com/product/tables

## Practical conclusion
- Keep the coordinator flow unpublished/disabled.
- Do not use a Find Records → Create Record sequence as if it were atomic under concurrent runs; two simultaneous runs can both observe no row unless an actual locking/unique mechanism is proven.
- Do not set project-wide concurrency to 1 because that could change behavior of the five protected production flows.
- Do not assume custom BARRIER installation is available on the current Cloud plan.
- Continue with sample-only tests. No production flow, hourly automation, or provider connection was changed in this audit.

## Cost and tests
- Paid API calls: 0
- Gemini/Claude generation calls: 0
- Activepieces production flow changes: 0
- Existing hourly automation changes: 0
- This was a documentation review; no concurrency test was run.
