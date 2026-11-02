# AI BOT Rust isolated runtime and version guard (prototype)

This is a **Rust-first isolated local control plane**. It does **not** replace operating AI BOT v8.1 or deploy to Render, Neon, Activepieces or ChatGPT. Existing scheduled tasks and GitHub main stay unchanged.

## Rust control plane

- `cargo run -- --once`: offline process receipt; native ChatGPT and provider sync are `UNVERIFIED`.
- `cargo run -- --serve`: loopback-only HTTP at `127.0.0.1:8765/healthz` and `/status`.
- `cargo run -- --event schedule` and `--event workflow_dispatch`: keep different GitHub trigger types distinct.
- `cargo run -- --native-check RUN RESULT SCHEDULED_EPOCH STARTED_EPOCH COMPLETED_EPOCH`: internal consistency only; no external same-run attestation.

## Rust cross-chat version/progress guard (offline only)

`src/bin/version_guard.rs` ports the isolated progress reconciler into the same Rust package as a separate binary:

```bash
cargo run --bin version_guard -- --reconcile board.json observation.json 7 7
```

It reads two local JSON files; stdout is `{"status":"UPDATE|NO_UPDATE","candidate_board":{...},"remote_write_performed":false}`. A stale expected/actual D1 record revision fails closed. The binary rejects unrecognized components/gates, stale or timezone-naive receipts, unauthenticated-source assertions, unproven production version promotions, and runtime PASS without a provider receipt. Its bounded/deduplicated change history does not itself trigger any chat or scheduler.

The `authenticated_source` field and `runtime_proof` booleans are **caller assertions**, not independently verified authentication. A real authorized ChatGPT orchestrator must read `project.ai-bot.version-head` and `project.ai-bot.progress`, verify provider SHA, CI, deployment, native run IDs and external ledger through connected tools, then use server-side `memory_write(expected_version=...)/readback`. No Rust process here holds secrets or writes D1. Historical GitHub CI must never be treated as native ChatGPT unattended execution.

Dependencies: `serde_json` and `chrono` (MIT OR Apache-2.0). No paid AI/model API.

## Tests and safety

```bash
cargo fmt --manifest-path experiments/rust-isolated-runtime/Cargo.toml -- --check
cargo clippy --manifest-path experiments/rust-isolated-runtime/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path experiments/rust-isolated-runtime/Cargo.toml
```

GitHub CI on the exact current branch SHA is authoritative for Rust compilation, not this README. Even a passing CI proves only isolated code correctness, not hosted runtime, D1 integration, Activepieces operations or schedule-triggered ChatGPT execution. Production migration needs separate permissions, provider readback, secrets handling and rollback proof.
