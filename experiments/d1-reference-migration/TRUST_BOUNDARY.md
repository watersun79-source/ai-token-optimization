# Isolated D1 signed-evidence and crash recovery contract

**Status: experimental test fixture only. No production transport or credential.**
This module is NOT wired to the ChatGPT Automations API, MCP D1, Render, or GitHub Actions writes.

## Authentication boundary
- `trusted_adapter.py` verifies nonce/challenge-bound HMAC receipts for exact key, purpose,
  revision, opaque source content_sha, complete value digest, issuer, audience and CAS request ID.
- A verifier key must be provided independently; the incoming receipt cannot choose it.
- **Real D1 MCP `content_sha` is NOT an HMAC or proof of independent service authentication.**
  The only issuer in the new CI tests is a *synthetic test authority*. No official provider
  proves it can issue these receipts; production source attestation remains UNVERIFIED.
- The default adapter rejects writes. The isolated write flag is for synthetic fixture
  tests only; future production wiring is NOT authorized by this PR.

## Recovery and rollback
- `prepare` verifies historical snapshots via existing `plan_migration`, authenticates
  the current source, and writes a full-value, HMAC-protected immutable local journal
  **before** simulated CAS. File is created exclusively with owner-only permissions,
  fsync'd, never silently deleted, and read with no-follow checks.
- `apply` requires a matching source revision, original value, opaque source receipt,
  and a previously valid journal. It performs CAS with an exact signed ACK and readback.
- `recover` is a **compensating CAS**: only an unchanged source or the exact migration
  candidate at source_revision+1 can be classified or restored. If a different writer
  advanced the revision or changed the candidate, recovery BLOCKS instead of overwriting.
  A lost write/rollback ACK can be resolved by independently signed readback.
- Rollback generates a NEW revision. It is not atomic undo, history deletion, or
  a substitute for real D1 durable journal, provider-specific auth, or backup approval.
- After a crash, recovery requires the original journal and trusted signing key from
  the **same isolated host**. Cross-host persistence and operational disaster recovery
  have NOT been validated.

## Tests
`python -m unittest discover -s tests -v` includes
`test_trusted_contract_ci.py` via the existing discovery shim.
Full additional adversarial tests were run separately in the isolated sandbox
(`test_trusted_adapter.py`); that extended module is NOT part of this PR.
All keys in these tests are conspicuously synthetic, never user or provider credentials.

**Promotion gates remain BLOCKED** pending independently authenticated provider origin,
nonproduction real-provider CAS/rollback tests, real storage durability review, and
separate explicit user deployment approval. No main merge, no D1 production writes,
no changes to the five existing native ChatGPT automations.
