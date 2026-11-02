# AI BOT Rust isolated runtime (prototype)

This is a **Rust-first isolated local control-plane prototype**. It does not replace production AI BOT v8.1 or deploy to Render/Neon/Activepieces/ChatGPT.

- `cargo run -- --once`: local process receipt; intentionally reports native ChatGPT and provider sync as `UNVERIFIED`.
- `cargo run -- --serve`: optional loopback-only HTTP service, `127.0.0.1:8765/healthz` and `/status`. Never bound to a public address.
- `cargo run -- --event schedule` or `--event workflow_dispatch`: keep scheduled GitHub runs distinct from dispatch.
- `cargo run -- --native-check RUN RESULT SCHEDULED_EPOCH STARTED_EPOCH COMPLETED_EPOCH`: records-only consistency gate; even a match cannot attest a native-to-provider execution.

No dependencies, paid LLM calls, secrets, remote writes, model API calls, or production state updates. GitHub CI validates only this isolated program. Before a production Rust rollout: verify hosted runtime, authentication, external MCP run ledger, rollback plan, and obtain separate authorization for protected operating configuration changes.

Validation: `cargo fmt -- --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test`. Tested build status must come from an actual CI job on the exact commit SHA.
