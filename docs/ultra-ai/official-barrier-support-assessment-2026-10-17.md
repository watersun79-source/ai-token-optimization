# Activepieces BARRIER Support Check — 2026-10-17

## Finding
The current public Activepieces Cloud piece catalog does not expose a built-in BARRIER action. BARRIER is a real waitpoint capability in the engine/schema, but the connected project catalog only exposes the normal Sub Flows actions. Do not claim a native configurable barrier is available in this project.

This is not quite the same as saying BARRIER is exclusively engine-internal: the official docs say piece authors use waitpoint hooks, and the core schema includes CreateBarrierRequest. However, the public Flow Control guide only demonstrates WEBHOOK and DELAY patterns. A custom-piece route for this project has not been verified as available on the free Cloud plan.

## Official evidence
1. Waitpoints architecture: https://www.activepieces.com/docs/install/architecture/waitpoints
   - Defines BARRIER and its signal/release model.
   - Marks POST /v1/waitpoints as Engine-only.
   - Mentions piece-author hooks ctx.run.createWaitpoint and ctx.run.waitForWaitpoint.
2. Flow Control piece reference: https://www.activepieces.com/docs/build-pieces/piece-reference/flow-control
   - Concrete examples cover WEBHOOK and DELAY; no BARRIER action recipe.
3. Flow Control catalog: https://www.activepieces.com/pieces/category/flow_control
   - Lists Delay, Sub Flows, Todos, Approval (Legacy); no BARRIER/Join action.
4. Connected project catalog query for @activepieces/piece-subflows:
   - Call Flow, Stream CSV to Subflows, Return Response; trigger Callable Flow.
   - No BARRIER action or trigger.
5. Core schema: https://github.com/activepieces/activepieces/blob/main/packages/core/execution/src/lib/flow-run/waitpoint/index.ts
   - CreateBarrierRequest contains policy/signals; waitpoint type includes BARRIER. This confirms runtime/schema support, not a builder action.
6. Private pieces documentation: https://www.activepieces.com/docs/build-pieces/sharing-pieces/private
   - States private piece sharing is available in paid editions. A custom piece is therefore not a verified free Cloud route here.

## This run
- Type: official docs, source schema, and connected catalog inspection.
- Activepieces test run ID: none; no flow execution was needed for this documentation check.
- Result: PASS — evidence gathered; free built-in BARRIER action not found.
- Activepieces flows/tables changed: 0.
- Provider API calls: 0.
- Paid upgrades: 0.
- Existing production flows and hourly schedule: unchanged.

## Prior mock evidence (retained)
- Fan-out run okPttnIcS3drLnO9J9JDx: SUCCEEDED, 47.0s, 9/9 steps; two synthetic batches. First Join already returned MERGE_READY, so delayed-result recovery is not proven.
- Conflict test YSWiwcFWi7fW5MXeNJSVc: MERGE_CONFLICT.
- Identical duplicate test hO7t0X4m0xMGel8aegCQ1: MERGE_READY, duplicate removed.
- Mock provider/API calls: 0.

## Blocker and next goal
Fixed delays/repeated Join calls are not a conditional barrier. No confirmed built-in free Cloud BARRIER action exists in the exposed catalog, and custom-piece availability on this plan is unverified.

Continue only in the MOCK ONLY folder: inspect supported Tables update/upsert actions; design an idempotent run registry plus deadline/reconciliation; test duplicate, conflict, delayed, malformed, missing, and late synthetic results; clean test rows afterward. Keep test flows disabled/unpublished, the original mock result table at 14 rows, production flows untouched, and the hourly schedule unchanged.

Last updated: 2026-10-17.
