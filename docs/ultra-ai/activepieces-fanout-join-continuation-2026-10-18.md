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
