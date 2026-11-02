# Rust PR #27 - Production Readiness Gate (isolated review)

This branch remains a local-only prototype. Its offline tests never prove real production authentication or live deployment.

| Gate | Current evidence | Promotion verdict |
| --- | --- | --- |
| Local CI Rust compile, fmt, clippy, tests, CLI synthetic CAS | Official GitHub Actions for exact HEAD | PASS for isolated scope only |
| Local network boundary | src/main.rs binds to 127.0.0.1:8765 | SOURCE CHECK ONLY |
| Operator identity and service authorization | No authenticated production identity/role enforcement | BLOCK / UNVERIFIED |
| Production transport | No verified TLS gateway receipt | BLOCK / UNVERIFIED |
| Production secrets and least privilege | No hosted secrets boundary audit/receipt | BLOCK / UNVERIFIED |
| Immutable release, authorized rollout | Draft PR, no approved deploy receipt | BLOCK |
| Pinned rollout + matched source and CI SHAs | CI SHA known; actual deployed artifact absent | BLOCK |
| Rollback binary/backup and real restoration rehearsal | No rollback artifact and completed rehearsal proof | BLOCK |
| Actual hosted health and provider readback | Only local health endpoint/CI checks | BLOCK |
| Existing task IDs, main, credentials and paid calls | No changes made by this review | PASS for change scope only |

## Offline no-promotion guard

Run cargo test under experiments/rust-isolated-runtime/Cargo.toml: promotion_guard tests reject missing provider identity, RBAC/role policy, TLS boundary, rollback rehearsal, pinned CI SHA mismatches, absent live readback, and changed task protections.

Command: cargo run --manifest-path experiments/rust-isolated-runtime/Cargo.toml --bin promotion_guard -- --check evidence.json

Input JSON assertions are NOT independently authenticated. The CLI deliberately exits nonzero and never grants a deployment even if all fields contain nonempty strings; all-complete synthetic input only yields INDEPENDENT_PROVIDER_REVIEW_REQUIRED.

## Required next step before any real promotion

Separately obtain independently verifiable provider identity and role permissions, a TLS gateway audit, least-privilege secret boundary review, approved immutable release artifact/CI SHA matching, rollback artifact with rehearsed restoration receipt, real hosted health receipt, and explicit authorization. Verify all receipts using authorized provider connectors, not user-supplied booleans. Schedule/main/production changes remain prohibited without targeted approval.

No provider calls, no external model API, no secrets, no D1 writes, no operating site deployment are added by this guard.
