# Isolated Activepieces Fan-out/Join Test Plan — 2026-10-18

## Purpose

Prove **Activepieces engine-level concurrent child-flow execution and join behavior** without calling Gemini, Claude, OpenAI, or any external API. This is separate from the existing cloud project and must not change its flows, connections, secrets, or hourly automation.

## Verified facts

- Activepieces' official engine Router implementation at https://github.com/activepieces/activepieces/blob/3d0b6ef9/packages/engine/src/lib/handler/router-executor.ts awaits each matching branch in a `for` loop. Router matching is sequential, not a fan-out solution.
- The built-in `@activepieces/piece-subflows` action `streamCsvToSubflows` is documented by its current action schema as dispatching a child flow for each CSV batch with bounded concurrency. It requires a published target flow whose trigger is `Callable Flow`; rows per batch are 1–10,000.
- The official Waitpoints documentation describes a BARRIER that waits for dispatched batches to report back: https://www.activepieces.com/docs/install/architecture/waitpoints
- The official Subflows action schema was read through Activepieces discovery; no connection is required for `streamCsvToSubflows`.
- The current ChatGPT execution container has Node.js and Python but **does not have Docker or Podman installed**. Therefore the isolated Activepieces engine test cannot be executed inside this session.
- The connected browser context is unavailable, and account-level credits/billing and external provider quotas remain unreadable. No AI-generation API has been called.

## Why this is the safest candidate

The current Cloud project policy is to leave test flows disabled/unpublished. But `streamCsvToSubflows` requires its child Callable Flow to be published and enabled, so publishing a test child inside the existing project would violate that policy. Use a separate local self-hosted instance instead. The official Docker Compose setup is documented at https://www.activepieces.com/docs/install/options/docker-compose and requires Docker Compose v2, at least 2 vCPU and 4 GB RAM (Windows requires WSL2). The local installation defaults to the free edition; do not add a paid license.

## Test design — synthetic data only

### 1. Start a separate local instance

- Use the official Activepieces self-hosting guide. Review the deployment script/config before running it; do not reuse the production Cloud credentials or secrets.
- Keep the instance local (for example, `http://localhost:8080`) and create a separate test administrator.
- Do not import production flows, production connections, or API keys.

### 2. Create a child flow in the local instance

- Trigger: `Callable Flow`.
- Step: a short Code step that captures `startedAt = Date.now()`, waits about 2 seconds, then returns a synthetic job ID plus `startedAt` and `endedAt`.
- No external HTTP calls, AI pieces, secrets, database writes, or Slack messages.
- Publish and enable this child flow **only in the isolated local instance**, because the parent Subflows action requires a published Callable Flow.

### 3. Create a parent test flow in the local instance

- Trigger: a test-only webhook or the builder's test trigger.
- Action: `Subflows → Stream CSV to Subflows`.
- Upload this synthetic CSV as the action's file input:

```csv
jobId,delayMs
mock-A,2000
mock-B,2000
```

- Set rows per batch to `1`, delimiter to comma, and select the local child flow.
- This creates two child runs. It does not call any AI provider.

### 4. Run and verify

Record the parent run ID and both child run IDs. In run history, compare the child `startedAt` / `endedAt` values:

- **Pass for concurrency:** the two 2-second child execution windows overlap materially, and the parent resumes/completes after both child runs report.
- **Fail or inconclusive:** child windows are sequential, only one child run exists, a child fails, or the parent does not wait for both. Save the run IDs and error details; do not move to real AI calls.
- The parent run duration by itself is supporting evidence only; child timestamps and run statuses are the primary evidence.
- Repeat the synthetic test three times to exclude a one-off scheduling result.

### 5. Cost and cleanup

- Expected AI/provider API calls: 0.
- Expected paid API calls: 0.
- Do not add provider credentials or test real Gemini/Claude/OpenAI calls until account credit balance and provider-side billing/quota are verified.
- Keep this test instance and its flows separate from the existing Cloud project. After capturing evidence, stop the local test instance or keep it isolated; do not alter the existing hourly automation.

## Completion gate for production adaptation

Do not adapt the production AI workflow until all of these are true:

1. The isolated synthetic child-flow test proves concurrent overlap and join behavior in three runs.
2. Activepieces account plan/remaining credits are verified in Platform Admin → Usage and Billing and Subscription.
3. External provider quotas and billing state are independently verified for any provider that would be called.
4. A separate draft-only design is reviewed against the existing production flow; no existing flow, connection, schedule, main branch, or secret is modified.

## Current status

- Test design: prepared.
- Actual isolated engine execution: blocked because Docker/Podman is unavailable in the current execution environment; it must run on a machine with Docker Compose v2.
- Current Cloud flow inventory: 7 flows (3 enabled/published, 4 disabled/draft); unchanged.
- Existing hourly automation: enabled and unchanged.
- Gemini/Claude consumer-app responses in this turn: 0.
- AI generation API calls: 0; paid API calls: 0; purchases/upgrades: 0.

## CORRECTION — 2026-10-18: CSV dispatcher is fire-and-forget

A source review of the official Activepieces pull request https://github.com/activepieces/activepieces/pull/14281 found that `Stream CSV to Subflows` dispatches bounded-concurrency child runs but explicitly has **no fan-in**. Therefore it cannot prove that the parent waits for child completion. Any earlier wording in this document that implied the CSV action itself joins child runs is superseded by this correction.

The corrected join-test candidate is a parent Code step in a separate local instance that starts two local mock child-flow webhook requests concurrently with `Promise.all` and waits for both responses. This remains a test design only: the local webhook URL shape and worker-to-app network path must be verified, and no actual run has been performed. If the local Code sandbox cannot reach the local child endpoints, stop and record the failure; never use production endpoints as a fallback.

Verified facts remain: Router branches are sequential; no AI/provider calls were made; the current execution environment has no Docker/Podman; production Cloud flows and the hourly automation remain unchanged.


## CORRECTION — 2026-10-18: Waitpoints are not a generic BARRIER

A fresh read of the current official Waitpoints documentation (https://www.activepieces.com/docs/install/architecture/waitpoints) shows that the documented waitpoint types are `DELAY` and `WEBHOOK`; it does not document a generic `BARRIER` type or a built-in parent fan-in action. The earlier statement in this plan that a BARRIER waits for dispatched batches was incorrect and is superseded by this correction.

The Sub Flows schema exposes `Call Flow` with a `Wait for Response` option, but its target Callable Flow must be published and enabled. That is incompatible with the rule that all Cloud test flows remain disabled/unpublished, so do not enable or publish the Cloud draft for this experiment. The existing Cloud draft remains unchanged.

The last three TESTING runs of the existing disabled/unpublished `MOCK ONLY · Promise.all 병렬 합류 검증기` passed synthetic in-code checks (run IDs: `RJdLgqGLJztcN0l8rQ41c`, `Bn6KY0PUmiu85EtdpS3h3`, `dEhaqSdQck9l095fH1CLU`). Each run recorded overlapping mock branch windows (~1.2 seconds), 10/10 join scenarios and 8/8 payload-contract cases. This proves only `Promise.all` concurrency and merge logic inside one Code step; it does **not** prove Activepieces engine-level subflow concurrency or a parent waiting for separate child runs.

Current verified status: the isolated engine-level fan-out/join test is still blocked by the lack of Docker/Podman in this execution environment. Do not claim the engine-level test is complete. AI/provider calls 0; external network calls from the tested Code step 0; paid API calls 0; production flows and hourly automation unchanged.


## SOURCE REVIEW — 2026-10-18: What Call Flow actually waits for

Reviewed the official source at https://github.com/activepieces/activepieces/blob/860ce5b87c43856549586ee7b44007ba0937efdf/packages/pieces/core/subflows/src/lib/actions/call-flow.ts and https://github.com/activepieces/activepieces/blob/860ce5b87c43856549586ee7b44007ba0937efdf/packages/pieces/core/subflows/src/lib/actions/stream-csv-to-flow.ts.

- `Call Flow` with `Wait for Response = true` creates a `WEBHOOK` waitpoint, registers the parent run to wait on it, and passes a callback URL to the child dispatch. The parent resumes when the child returns a response. This is a documented single-call request/response pattern.
- `Stream CSV to Subflows` dispatches batches using `fanOutBatches` with `MAX_IN_FLIGHT = 5`, but calls `dispatchToSubflow` with `failParentOnFailure: false` and no callback URL or waitpoint. Its awaited loop concerns dispatching batches, not awaiting child result payloads. Do not use it as a parent-result join.
- The Router engine source at https://github.com/activepieces/activepieces/blob/3d0b6ef9/packages/engine/src/lib/handler/router-executor.ts executes matching branch children in a `for` loop with `await flowExecutor.execute(...)`, so Router branches are sequential.
- Therefore the built-in patterns confirmed so far are: sequential Router; one Call Flow with optional child-response wait; or bounded-concurrency fire-and-forget CSV dispatch. No built-in generic parallel multi-child fan-in was proven by these sources.

Safe next design to investigate: two independently dispatched child flows write synthetic result records under a unique request ID; a parent-side wait/poll or callback aggregator verifies both results before integration. This is architecture only, not yet validated. Before implementing, verify whether the current Activepieces Cloud exposes an appropriate callback/wait mechanism and atomic/idempotent record operations. Do not change the live Cloud flows, publish drafts, or use provider APIs.


## NEXT CANDIDATE — synchronous webhook fan-out/join (not yet run)

The current Webhook piece schema gives a more concrete isolated test candidate:
- Each local child flow uses `Catch Webhook`, performs only a synthetic delay/result, then `Return Response`.
- A local parent Code step attempts two HTTP POST requests concurrently with `Promise.all` to the children’s synchronous webhook URLs (the documented `/sync` mode), and validates that both response payloads arrive before the parent step completes.
- The Webhook action guidance says only synchronous `/sync` requests receive a `Return Response`; ordinary webhook calls are not sufficient to prove parent waiting. Official piece schema was read through Activepieces piece discovery on 2026-10-18.
- This is still a candidate, not a verified procedure: first confirm the local URL format from the local builder and confirm the Code runner can reach the local server. Use only loopback/local addresses in a separate self-hosted instance. If either prerequisite fails, stop; do not publish a Cloud test flow, use a public tunnel, or fall back to production endpoints.
- Success requires three runs showing both child runs overlapping, both HTTP responses containing the expected synthetic IDs, and the parent returning only after both results. Record parent and child run IDs and timestamps. AI/provider calls and paid calls must remain zero.

## Shared-table join caveat

The current Tables piece schema exposes Create Record(s), Find Records and Update Record, but no documented atomic upsert/unique-key operation in the exposed action list. Create Record(s) is append-only and not idempotent. Therefore a shared-table requestId join must not be treated as race-safe or idempotent without separate proof; prefer the synchronous webhook response experiment above for the first isolated engine test.


## SOURCE REVIEW — 2026-10-18: Local webhook test has a network-boundary prerequisite

Reviewed the official Activepieces network-security documentation at https://github.com/activepieces/activepieces/blob/860ce5b87c43856549586ee7b44007ba0937efdf/docs/install/architecture/network-security.mdx.

- The documented default for user-code egress is `AP_NETWORK_MODE=UNRESTRICTED`; `STRICT` blocks loopback and private addresses from Code-step user code unless explicitly allow-listed.
- This does **not** establish the setting used by the user's hosted Cloud project, nor does it establish that a local Code sandbox can reach a local webhook endpoint. Do not infer either from the documentation.
- The proposed local Code-step → `/sync` webhook test has a hard prerequisite: inspect the isolated self-hosted instance's own network mode and verify the endpoint path from that instance's configuration before attempting a request. Do not weaken network security or add an allow-list entry merely to make the test pass.
- If the test requires changing network security settings, exposing a public tunnel, or using production Cloud endpoints, stop and report the blocker rather than proceeding.
- No network request, flow publish, configuration change, or provider API call was performed as part of this source review.

This narrows the next action: the local engine environment must exist first, and its network mode/endpoint reachability must be confirmed before running the synthetic test. Docker/Podman is still unavailable in the current execution environment, so the engine-level test remains unexecuted.


## SOURCE REVIEW — 2026-10-18: Synchronous webhook response semantics and timeout

Reviewed the official Activepieces webhook runtime notes at https://github.com/activepieces/activepieces/blob/860ce5b87c43856549586ee7b44007ba0937efdf/brain/knowledge/eventing-webhooks/webhooks.md.

- The official route inventory distinguishes `/:flowId/sync` (blocking request/response), `/:flowId` (async queue-and-return), `/:flowId/draft/sync`, and `/:flowId/draft`. A normal asynchronous webhook returning HTTP 200 means the request was queued, not that the flow finished.
- The documented default `AP_WEBHOOK_TIMEOUT_SECONDS` is 30 seconds. A synchronous request can return 408 if the flow has not provided a response by then. Therefore the synthetic test must use short delays (e.g. 1–2 seconds), no Delay piece that pauses/requeues the flow, and an explicit Return Response step; keep the complete test well below the timeout.
- A successful synchronous HTTP response alone is insufficient proof that two child runs overlapped. The test must also capture both child run IDs and execution timestamps from run history, confirm their intervals overlap, and confirm the parent received both expected response payloads before completing. If any of these cannot be observed, mark the run inconclusive rather than pass.
- The `/sync` route documentation does not prove the exact URL shown by a specific local builder, nor prove that the Code sandbox can reach it. Those remain local-instance prerequisites.
- No webhook request or flow run was triggered during this source review. No Cloud flow was published or modified, and no AI/provider API or paid call was made.


## RECHECK — 2026-10-18: Current cloud inventory and local runner availability

Read-only recheck performed after the source reviews:
- Activepieces returned exactly 7 flows: 3 ENABLED/published (`AI 3AI 협업`, `Slack`, `Gemini + Claude 협업 비서 (비용 확인 필요)`) and 4 DISABLED/unpublished drafts. No flow status was changed.
- The mock-only `Promise.all` flow still validates with 2/2 valid steps and no validation issues.
- Its five latest TESTING runs all report `SUCCEEDED`; the three most recent are `dEhaqSdQck9l095fH1CLU` (2.7s), `Bn6KY0PUmiu85EtdpS3h3` (4.7s), and `RJdLgqGLJztcN0l8rQ41c` (3.2s). These are synthetic Code-step harness runs, not evidence of separate Activepieces child-flow execution.
- The current execution container was checked again: Node.js v22.16.0 and Python 3.13.5 are present; `docker`, `podman`, and `nerdctl` are not available on PATH. No local Activepieces engine can be started using those runtimes in this environment.
- The existing hourly `AI` automation remains enabled with its hourly-on-the-hour schedule. It was read, not modified.
- No flow was published/enabled/disabled, no provider API was called, and no paid usage or purchase occurred during this recheck.

Status remains: mock validation passed; engine-level fan-out/join not executed. The next real progress requires access to a separate host/runtime with Docker Compose v2 or another already-running isolated self-hosted Activepieces instance. Without that external runtime, repeating mock-only runs would not close the actual verification gap.


## READ-ONLY RECHECK — 2026-10-18: Current AI collaboration flow is sequential

The connected Activepieces flow-structure tool was used read-only for the current enabled production flows. No flow was run or modified.

- `AI 3AI 협업` (`kt2N9yCVA3dLkFiNPSMsH`) has the configured step chain: ChatGPT draft → Gemini independent review → Claude independent review → final answer integration → HTTP response → Slack notification. The steps are linked as successive `next` relationships, not parallel branches.
- `Gemini + Claude 협업 비서 (비용 확인 필요)` (`drNhxMhmCo3A0rKV0OhIZ`) has a skipped OpenAI draft followed by Gemini draft/review → Claude review/final answer → HTTP response. It is also sequential; skipping the OpenAI step does not make Gemini and Claude concurrent.
- The disabled mock harness remains a single Code step using in-memory synthetic Promise.all. Its successful runs test JavaScript Promise.all/timing/merge contracts only; they do not exercise either production flow's AI pieces or Activepieces child-flow fan-out/join.
- Consequence: current enabled collaboration is sequential in the observed structure. Parallel AI calls are **not implemented/proven** in the inspected production flows. Do not call the enabled production webhook to test this because it could invoke paid/provider APIs and send Slack messages.
- Security note: flow-structure output can include webhook authentication configuration. Do not copy auth header values, connection identifiers/secrets, or credentials into documentation, logs, or chat replies. No such values were added to this GitHub update.
- No provider API calls, flow executions, flow status changes, or production edits were performed during this read-only inspection.

Next safe decision gate: do not modify production until an isolated execution environment is available and provider billing/quotas are confirmed. First validate actual concurrent child-flow request/response behavior using synthetic payloads in a separate local instance; then design a separate draft-only production migration for review.


## READ-ONLY VALIDATION — 2026-10-18

After inspecting the two enabled AI collaboration flows, ran Activepieces validation only (not execution):
- `AI 3AI 협업`: valid, 7/7 steps valid, 0 issues.
- `Gemini + Claude 협업 비서 (비용 확인 필요)`: valid, 4 valid steps, 1 intentionally skipped step, 0 invalid steps, 0 issues.
- Validation means the configured flow schema is accepted; it does not prove provider credentials/quotas, actual API cost, runtime success, or parallel execution.
- No changes were made to either flow, and neither flow was executed.
