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


## Candidate runtime proof design (2026-10-18, implementation planning)
A narrow, production-isolated proof should use the existing upstream E2E harness and real worker/database, not Activepieces Cloud drafts and not Code-step localhost fetches:
1. Create two separate enabled/published Callable Flow fixtures, each with a unique input token and a small controlled delay before Return Response. Keep the test entirely in the E2E fixture database.
2. Add a test-only trusted piece action (or equivalent server-side test orchestrator) that dispatches both children through the supported synchronous webhook route using the upstream server HTTP client and starts both requests before awaiting either. Do not weaken Code sandbox network restrictions or allow-list loopback.
3. Each child returns a distinct result containing its token and timestamps. Query the E2E database for the two distinct child flow-run rows and record their actual start/finish times. Capture the parent's step output and terminal finish time.
4. Assert: exactly two child runs were created; tokens/results match their respective child; child intervals overlap; parent output contains both results; parent finish time is not earlier than either child finish time; errors/timeouts fail the test; repeat three times.
5. Validate endpoint path, sync webhook timeout, child run correlation, and whether the trusted test piece can reach the local app through the test context before choosing the final implementation. The pinned E2E setup binds a local ephemeral port, but this environment cannot run Docker/Bun and has no direct GitHub checkout/Actions dispatch tool, so these runtime assumptions remain untested here.

### Execution environment check
- Checked the available local runtime: Node.js and Git are present; Docker, Podman, and Bun executables are absent.
- Attempted to query the public upstream repository with Git; outbound DNS/network is unavailable in this execution container. The GitHub connector can read/write the user's documentation repository but does not expose an Actions workflow dispatch operation in the available tool set.
- Therefore, this environment cannot honestly run the Activepieces upstream E2E suite. Do not treat a newly written workflow or source-only test sketch as a passing runtime result. The documented candidate design is a plan, not a completed test.


## Follow-up service/API feasibility check (2026-10-18)
- Inspected the pinned `flow-run-service.ts` method contract. `flowRunService.start()` creates/queues a run with optional `parentRunId` and `failParentOnFailure`, then returns the newly created run record. It is not a synchronous helper that waits for a completed child response. That means a test orchestrator using the service alone must separately poll/query run completion and join results; simply awaiting `start()` would be a false positive.
- Rechecked the user's Activepieces Cloud flow inventory. The same three published production flows remain ENABLED; all four test/mock flows remain DISABLED and unpublished. No flow was edited, enabled, disabled, or run during this pass.
- The intended proof still requires upstream E2E worker execution and run-row assertions. This session has no Bun/Docker runtime and no Actions dispatch capability, so no actual engine test was executed. No paid AI API calls were made.


## Activepieces Cloud test-mode execution results (2026-10-18)
Two existing disabled, unpublished MOCK ONLY flows were run in the Activepieces TESTING environment using supplied synthetic trigger data. No publish/enable operation was performed and no production flow was changed.

1. `MOCK ONLY · Promise.all 병렬 합류 검증기` (`jRWo1ktjzHHgoLcrPSyzx`), run ID `868iKHC0B0WyNtuTEXdKv`, status SUCCEEDED. Both synthetic branch starts recorded at 0 ms; both completions at 1202 ms; total elapsed 1202 ms (not ~2400 ms). Timing assertions passed. 10/10 join cases passed; 8/8 branch contract cases passed. Output explicitly limits this evidence to Promise.all concurrency within a single CODE step, not engine-level subflow/Router concurrency.
2. `MOCK ONLY · Result Merge Harness` (`Jsux341MqsaxUlrGFue1x`), run ID `LREVoMU0FFj06rqzJwkYl`, status SUCCEEDED. Supplied synthetic Gemini/Claude payloads merged as `MOCK_MERGE_OK`; both were validated and preserved. 8/8 contract cases passed. Output explicitly says this does not prove engine-level concurrency, persistent atomicity, or live AI execution.

These are real Activepieces TESTING-mode run records with mock trigger data, not production/live trigger tests. They are useful unit/contract evidence only; the requested engine-level concurrent child-flow completion/join E2E remains unproven. No external AI/network calls were made by either test.


## Repeatability check and production architecture finding (2026-10-18)
- Repeated the disabled/unpublished synthetic concurrency test three times using Activepieces TESTING runs and then fetched each run record:
  - `Kg1ikFjKjl88eCqXJFJS7`: SUCCEEDED, timing overlap true, 10/10 join scenarios, 8/8 contracts, 1204 ms.
  - `BilHfarPmZiW2Iqs7dwic`: SUCCEEDED, timing overlap true, 10/10 join scenarios, 8/8 contracts, 1203 ms.
  - `w3beLx8xbT77tMR4amo1h`: SUCCEEDED, timing overlap true, 10/10 join scenarios, 8/8 contracts, 1205 ms.
  These repeat runs establish reproducibility of the same in-step synthetic Promise.all test only, not engine-level child-flow fan-out/join.
- Inspected the current enabled production flow `AI 3AI 협업` (`kt2N9yCVA3dLkFiNPSMsH`): its configured sequence is ChatGPT draft → Gemini review → Claude review → final integration → HTTP response → Slack notification. Flow validation is valid (7/7 steps). This is a sequential chain, not parallel Gemini/Claude execution.
- Inspected `Gemini + Claude 협업 비서 (비용 확인 필요)` (`drNhxMhmCo3A0rKV0OhIZ`): Gemini draft/self-review → Claude review/final answer → return response; OpenAI draft step is skipped. Validation reports valid with one intentionally skipped step. This also does not currently demonstrate parallel Gemini/Claude execution.
- Activepieces lists active project connections for Google Gemini and Anthropic Claude, but connection presence does not establish free quota or price. No live AI flow was run to avoid possible paid calls.
- Current tool catalog has no GitHub Actions workflow-dispatch action. Existing production flows and hourly automation were not changed. No test flow was published or enabled.


## Actual merge-input failure-path tests (2026-10-18)
Ran the existing disabled/unpublished MOCK ONLY merge flow's CODE step with additional supplied test payloads, then fetched each execution result:
- Gemini missing, Claude valid: run `TVIJiVIwfTmMhJgt3DDY4`, SUCCEEDED; merge state `MOCK_MERGE_PARTIAL`; Gemini error `MISSING`; Claude preserved as valid.
- Both missing: run `ooBqpXE8nwCXV637BtggT`, SUCCEEDED; merge state `MOCK_MERGE_INCOMPLETE`; both errors `MISSING`.
- Both malformed: run `CS04QBj9SpApMABJIpnga`, SUCCEEDED; merge state `MOCK_MERGE_INVALID`; Gemini `BAD_OUTER_STATUS`, Claude `NOT_OBJECT`.
All three runs executed the embedded 8-case contract suite successfully and reported zero external AI/network calls. These are failure-path checks of the merge code with sample trigger data, not engine-level child-flow fan-out/join proof.


## Native Activepieces fan-out/join capability assessment (2026-10-18)
- Current upstream Sub Flows piece exposes three relevant primitives: Callable Flow trigger, Call Flow (one child; optional wait for its Return Response), and Stream CSV to Subflows (bounded fan-out but explicitly fire-and-forget; it does not return each child result to the parent).
- Therefore neither repeated sequential Call Flow steps nor Stream CSV to Subflows alone establishes a native two-child concurrent wait-all join. Router is not accepted as a concurrency proof because source review of the router executor found branch execution awaited sequentially.
- Safe implementation paths to evaluate next: (A) a purpose-built trusted server-side Activepieces piece/action that creates two distinct waitpoints, dispatches both child runs before awaiting either, and correlates each callback to its own waitpoint; (B) a durable result-table/barrier design with idempotency keys, child completion writes, parent polling/deadline, and atomic finalization. Option B requires careful persistence/race testing and cannot be approximated by arbitrary fixed delays. Do not publish or enable either design until it has isolated test coverage.
- Upstream developer search also surfaced issue #13141 describing stale/retry callbacks cross-wiring results in multi-child waitpoint use. This reinforces the need to test unique waitpoint/run correlation and retry handling, not just elapsed-time overlap.
- No new production changes were made. The engine-level fan-out/join remains open; evidence currently covers synthetic in-step concurrency and merge failure handling only.


## Activepieces validation sweep (2026-10-18, read-only)
Validated all 7 currently listed flows with the Activepieces validator. Results: 
- `AI 3AI 협업`: valid, 7/7 steps, 0 invalid, 0 skipped.
- `Slack`: valid, 2/2 steps, 0 invalid, 0 skipped.
- `Gemini + Claude 협업 비서 (비용 확인 필요)`: valid, 4 valid / 1 intentionally skipped / 0 invalid.
- `MOCK ONLY · Result Merge Harness`: valid, 2/2 steps.
- `MOCK ONLY · Promise.all 병렬 합류 검증기`: valid, 2/2 steps.
- `AI JSON 검증 테스트 전용`: valid, 3/3 steps.
- `TEST ONLY · JSON 출력 검증기`: valid, 2/2 steps.
Validation is structural/configuration validation only; it does not prove live concurrency or run any AI provider calls. No flows were edited, enabled, or published during this sweep. The three enabled/published production flows remain in their prior state; all four test flows remain disabled and unpublished.

## Acceptance gates before claiming completion
1. Two real child runs must be dispatched before waiting on either result (not Promise.all over synthetic local functions and not sequential Call Flow steps).
2. Each child has a distinct run ID and distinct waitpoint/correlation ID; deliberately reverse completion order and verify outputs cannot cross-wire.
3. Parent remains waiting until both child responses are terminal; verify correct aggregation on success and explicit partial/error output on one child failure.
4. Inject duplicate and delayed retry callbacks; confirm idempotency and that stale callbacks cannot satisfy another child's waitpoint.
5. Enforce deadline/timeout and cancellation behavior; prove no stuck PAUSED parent or orphaned children.
6. Repeat the engine-level E2E at least 3 times and inspect actual parent/child run records, timing intervals, statuses, and returned payloads.
7. Only after all gates pass may a separate production rollout be considered; this current work did not change production.


## Production flow step-settings audit (2026-10-18, read-only)
Read the full step settings for the enabled/published flow `AI 3AI 협업` (flow ID `kt2N9yCVA3dLkFiNPSMsH`). The actual configured dependency chain is:
1. `step_1` ChatGPT draft (`@activepieces/piece-openai / ask_chatgpt`).
2. `step_2` Gemini review (`@activepieces/piece-google-gemini / generate_content`), with prompt referencing `step_1` output.
3. `step_3` Claude review (`@activepieces/piece-ai / askAi`), with prompt referencing `step_1` output but structurally placed after step_2.
4. `step_4` OpenAI integration, referencing both `step_2` and `step_3` outputs.
5. HTTP response, then Slack notification.
The current flow therefore runs ChatGPT → Gemini → Claude → integration sequentially. Even though the two reviewer prompts independently reference the initial draft, the step graph makes Claude wait for Gemini. This is direct configuration evidence, not an inference from the display name.

## Runtime capability blocker and safe next move
The available Activepieces action inventory has no built-in generic fork/join action that concurrently dispatches two arbitrary steps and joins their returned payloads. Sub Flows Call Flow is one child per action; Stream CSV fan-out is for CSV batches and does not collect each child's completed response into a parent result. Existing workflow editor API can add Router branches, but source review found router branch execution sequential. Thus a no-code edit to the production chain cannot safely produce true concurrent reviewers with wait-all semantics.

Do not change the production flow to “fire-and-forget” children unless a durable result barrier is designed and tested; doing so without a join could integrate missing/late reviews. The required next implementation is a tested custom Activepieces piece/server-side coordinator with per-child correlation/waitpoints, or a durable, idempotent result table/barrier with timeout and retry semantics. This is not implemented or deployed yet. No live AI calls, flow edits, publishes, or enables occurred during this audit.
