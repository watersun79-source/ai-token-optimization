# GitHub AI automation pattern adopted — 2026-10-18

## Selected upstream pattern

Reviewed the official Activepieces repository and its automation-building guide:

- Upstream repository: https://github.com/activepieces/activepieces
- Guide: https://github.com/activepieces/activepieces/blob/860ce5b87c43856549586ee7b44007ba0937efdf/packages/server/api/src/assets/prompts/guides/build_flow.md
- Upstream guidance used: validate every trigger/step; test realistic and edge cases; inspect actual outputs rather than trusting a green status; repeat recurring-flow tests to catch reprocessing; distinguish mock-trigger evidence from a real event; do not publish until the flow is explicitly approved.
- GitHub Actions workflow already in this repository: `.github/workflows/validate.yml`. It runs deterministic Python and JavaScript regression checks without model-provider credentials.

## Applied in this branch

1. Added `cost_guard` to `config/policy.json`:
   - Paid model API calls are prohibited.
   - A provider call is blocked unless this account's free quota and no-billing route have been verified.
   - An active connection is not quota/billing evidence.
   - Record actual provider calls and costs.
2. Extended `tests/test_config.py` to enforce these rules in CI.
3. Preserved existing workflow triggers, the existing scheduled automation, Activepieces production flows, connections, secrets, and main branch. No provider API was called.

## Acceptance and verification

- Static change: implemented on branch `ai/github-automation-guardrails-main-2026-10-18`.
- Intended CI path: existing GitHub Actions workflow, which runs on pull requests to `main` and manual dispatch.
- This document and commits do not themselves prove that CI has run or passed. Verify the actual Actions run before merging.
- This policy check prevents accidental policy drift in the repository; it does not technically intercept API calls inside Activepieces. Provider-call enforcement still depends on the runtime following this policy and on account quota/billing being verified.
- No changes were made to production flow ordering. ChatGPT → Gemini → Claude remains sequential until true engine-level fan-out/join has been proven in an isolated test runtime.

## Sources

- Activepieces upstream: https://github.com/activepieces/activepieces
- Activepieces build-flow guide (pinned commit): https://github.com/activepieces/activepieces/blob/860ce5b87c43856549586ee7b44007ba0937efdf/packages/server/api/src/assets/prompts/guides/build_flow.md
- Existing repository CI: https://github.com/watersun79-source/ai-token-optimization/blob/ai/github-automation-guardrails-main-2026-10-18/.github/workflows/validate.yml
