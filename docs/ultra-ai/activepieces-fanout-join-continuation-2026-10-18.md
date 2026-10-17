# Activepieces Fan-out/Join Continuation — 2026-10-18

## Current verified state
- Existing hourly automation `AI` remains enabled, timezone Asia/Seoul, scheduled every hour on the hour. Do not create a duplicate or change the schedule.
- Activepieces project currently lists 7 flows: 3 enabled/published production flows and 4 disabled/unpublished test drafts. No flow status was changed in this pass.
- `MOCK ONLY · Promise.all 병렬 합류 검증기` (`jRWo1ktjzHHgoLcrPSyzx`) validates 2/2 steps with no configuration issues. It remains disabled and unpublished.
- Read-back of run `dEhaqSdQck9l095fH1CLU` shows synthetic-only execution: overlapping mock branch timestamps, 10/10 join scenarios, 8/8 payload-contract tests, zero external AI calls, and zero external network calls. The output explicitly limits this to Promise.all inside one Code step, not engine-level child-flow concurrency.
- No production flow was run or edited. No AI generation, paid API call, purchase, or upgrade was made.

## Official Sub Flows schema findings
Sources checked 2026-10-18:
- https://www.activepieces.com/pieces/subflows
- https://www.activepieces.com/docs/build-pieces/piece-reference/large-file-streaming

The official Sub Flows integration is documented as open source and included on every plan. Its actions are:
- `Call Flow`: invokes one published/enabled Callable Flow; optionally waits for that single child to send `Return Response`.
- `Stream CSV to Subflows`: fans CSV batches out with bounded concurrency, but its public action description does not promise a joined result payload from every child.
- `Return Response`: sends one response to a waiting Call Flow caller.

Therefore, neither the existing mock nor the documented single-child wait action establishes a generic engine-level multi-child fan-out + wait-for-all join. A real isolated runtime test is still required.

## Exact next validation
1. Keep all existing production flows and the hourly automation unchanged.
2. Obtain access to an isolated Activepieces engine/runtime where Docker Compose v2 (or an already-running isolated instance) is available; do not weaken network security or expose public tunnels.
3. Create only disabled/unpublished synthetic child-flow drafts until a permitted isolated test environment is available.
4. In the isolated runtime, execute two child flows with distinct run IDs and short delays. Capture child run IDs, start/end timestamps, both returned payloads, and parent completion timestamp.
5. Pass only if child execution intervals overlap, both payloads are present, and the parent finishes after both responses; repeat three times. No Gemini, Claude, OpenAI, or other billable API calls.
6. Record run IDs and exact output, then read the report back. Do not label the task complete until this runtime-level proof passes.

## Blocker
The current tool environment does not provide a Docker/Podman runtime, and the connected Activepieces tools do not expose an isolated engine endpoint. Consequently, engine-level concurrency remains unverified. Do not publish the cloud test drafts as a workaround.


## Additional execution-path research (2026-10-18)
- Official self-host docs require Docker Compose v2 and at least 2 vCPU / 4 GB RAM for the standard four-container setup: https://www.activepieces.com/docs/install/options/docker-compose
- The current GitHub repository is public. GitHub documents standard GitHub-hosted Actions runners as free for public repositories: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- This creates a possible isolated CI runner path without using the user's local machine or Activepieces Cloud production project. However, no workflow was created or run in this pass; the exact engine-level fan-out/join integration test still needs to be implemented and reviewed before a CI run can be treated as proof.
- Do not run an unverified workflow that merely boots the engine and then claim fan-out/join is proven. The test must create or import two synthetic Callable Flow children, dispatch both from an isolated parent, capture each distinct run ID and start/end timestamps, assert overlapping intervals and both results, and assert parent completion occurs after both results.
- A public GitHub runner may be free for standard runner minutes, but this does not guarantee that all other dependencies are free. Keep the test isolated, use no AI provider credentials, do not upload secrets, and do not publish or modify Activepieces Cloud flows.


## API/bootstrap investigation (2026-10-18, follow-up)
Official endpoint docs and upstream source were checked:
- Create Flow API: https://www.activepieces.com/docs/endpoints/flows/create documents `POST /api/v1/flows` and explicitly requires an API key generated in the admin console.
- Flow Run read API: https://www.activepieces.com/docs/endpoints/flow-runs/get documents `GET /api/v1/flow-runs/{id}` with run status, start/finish times, parentRunId, and step outputs.
- Upstream import implementation: https://github.com/activepieces/activepieces/blob/860ce5b87c43856549586ee7b44007ba0937efdf/packages/server/api/src/app/flows/flow/flow.controller.ts handles `IMPORT_FLOW` as a flow operation.
- A public example repository contains an importable flow JSON, but its example uses a real Outlook OAuth connection and is unsuitable for this synthetic test; it will not be reused or imported.

### Consequence / next safe implementation step
The proposed isolated GitHub Actions runner cannot safely assume it has a local Activepieces API key. No user key is available in this project context, and no secret should be added to a public repository. Do not put an API key in code, logs, or GitHub commits. The test implementation must either bootstrap a disposable local instance through a documented UI/auth flow inside the runner, or use a documented keyless local test mechanism verified from upstream source. If neither can be implemented without guessing, stop and report the specific bootstrap blocker instead of running a false-positive mock.

### Acceptance criteria remain unchanged
A real test must execute two separate child-flow engine runs concurrently, capture distinct child run IDs and start/finish times, prove overlapping execution intervals, return both distinct synthetic payloads, and prove the parent does not finish before both child results arrive. Repeat three times. No provider APIs, secrets, production-flow changes, or weakening of network security.


## Upstream E2E test baseline found (2026-10-18, follow-up)
- Upstream Activepieces has an integration fixture at https://github.com/activepieces/activepieces/blob/860ce5b87c43856549586ee7b44007ba0937efdf/packages/server/api/test/integration/ce/flows/flow-run/execute-flow-e2e.test.ts
- The fixture builds a real worker/engine test environment and a real Callable Flow → Code → Return Response child, plus a webhook parent using Call Flow with waitForResponse: true. It also demonstrates a webhook parent returning the child response.
- This is a better implementation baseline than reverse-engineering public API bootstrapping. It is upstream's own test harness, but the inspected fixture is single-child; it does not prove concurrent fan-out/join.
- Next engineering step: use this fixture pattern in an isolated test branch/harness and add two distinct child flows plus a parent dispatcher that launches both concurrently and waits for both. The assertion must inspect separate child run records/timestamps and the merged result; don't mark passing from Promise.all mock-only behavior. Do not modify Activepieces upstream or production Cloud flows.


## Exact fan-out semantics confirmed from upstream source (2026-10-18, follow-up)
Source read directly: https://github.com/activepieces/activepieces/blob/860ce5b87c43856549586ee7b44007ba0937efdf/packages/pieces/core/subflows/src/lib/actions/stream-csv-to-flow.ts and https://github.com/activepieces/activepieces/blob/860ce5b87c43856549586ee7b44007ba0937efdf/packages/pieces/core/subflows/src/lib/fan-out.ts
- `Stream CSV to Subflows` uses `MAX_IN_FLIGHT = 5`, so it has bounded concurrent dispatch.
- The action awaits `dispatchToSubflow` requests and returns `{ rowsProcessed, batchesDispatched }`; it does not wait for the child flow runs to finish or aggregate their response payloads. Its official architecture decision calls it fire-and-forget.
- Therefore it is valid for concurrent dispatch, but it is not a fan-out + wait-for-all-results join primitive. Do not use it as evidence of joined child outputs.
- The upstream E2E suite also has a separate test for concurrent independent flow-run executions, but that alone is not a parent/child fan-out-and-join test.

## Design decision needed before claiming engine-level join
The existing native primitives establish two different capabilities: (a) one Call Flow can wait for one child's Return Response, and (b) Stream CSV to Subflows can concurrently dispatch many child runs without waiting for their final outputs. They do not establish native parallel calls with all child results joined.
A viable implementation must test an explicit orchestrator that concurrently invokes two synchronous child webhook endpoints and awaits both responses, or implement a custom piece that does the equivalent using supported server context. It must run inside an isolated E2E engine harness, not as a same-step Promise.all mock. Verify network policy, sync timeout, and parent/child run IDs before choosing an implementation. No production flow has been changed.


## Callback/waitpoint implementation detail checked (2026-10-18, follow-up)
Raw upstream source at pinned commit was inspected for `call-flow.ts`, `respond.ts`, and `common.ts`:
- `Call Flow` creates a WEBHOOK waitpoint only when `waitForResponse` is enabled, builds a resume URL from that waitpoint, and calls `context.run.waitForWaitpoint(waitpoint.id)` before dispatching the child.
- Each `Call Flow` action execution is tied to its own parent run ID and its own waitpoint. On resume, it reads `context.resumePayload.body` and returns that one child response.
- Child `Return Response` reads the callback URL stored for the child run and posts the response to that URL. The common dispatcher sends each child run through `POST ${apiUrl}/v1/webhooks/${flowId}` with the parent run ID and optional callback URL.
- This source confirms the one-child wait/resume mechanism; it does not prove that a single parent run can safely create and await multiple waitpoints concurrently. That specific runtime behavior must be tested in the upstream E2E harness before implementing a custom parallel-join piece.
- The webhook controller path guessed in this pass returned 404 at the pinned raw URL, so no route semantics are claimed from that file. No production code or cloud flows were changed.

### Narrow next experiment (not yet run)
Extend the existing upstream E2E test fixture with two Callable Flow children that return distinct payloads and a purpose-built parent orchestration step. First test whether two waitpoints can coexist under one parent run and resume independently; assert distinct child run IDs, callback correlation, parent suspension until both responses, and no dropped/duplicate callbacks. If the engine's resume model cannot support multiple waitpoints in one run, implement the join as an explicit coordinator that tracks child IDs/results outside the parent step and resumes once all children complete. Do not claim either design works until the real worker/engine E2E assertions pass.


## Upstream E2E suite scope verified more precisely (2026-10-18)
The pinned `execute-flow-e2e.test.ts` was queried for the exact test bodies:
- `handles concurrent flow run executions without jobs getting stuck` starts five independent runs with `Promise.all(flowRunService.start(...))`, then polls each run until terminal status. It does not create parent-child relationships and does not join child outputs.
- `executes parent → child subflow with wait-for-response in test step mode` proves one child response is resumed into the parent step.
- Existing waitpoint tests cover loop iterations and a DELAY followed by a WEBHOOK pause in sequence. They do not establish two concurrently pending waitpoints for one parent run.
- The E2E file itself states prerequisites: the engine must be built (including `cache/v7/common/main.js`), Bun must be available for piece installation, and the in-memory Redis test environment is started automatically. The API package script is `npm run test-ce-command` / Vitest integration tests, but this environment has not executed it.

This narrows the acceptance gap: no test in the inspected suite currently demonstrates two child flow runs dispatched by one parent, both child results correlated and joined, and parent completion only after both results. Next implementation must add exactly that E2E test and run it in a real upstream workspace/CI runner; source inspection alone is not runtime proof.
