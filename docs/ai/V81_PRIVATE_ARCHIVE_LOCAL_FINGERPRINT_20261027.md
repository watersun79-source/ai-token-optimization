# AI BOT v8.1 — local-only private archive verification (2026-10-27)

## New evidence (incremental; not a deployment)
- A previously unexamined user Library ZIP was opened **locally only**; its embedded original v8.1 archive has SHA-256 `8c06d103af54d119c31ed927e0266a6d15dab4d9e24036cd2974e9b76739035a`, matching the fingerprint already committed in `experiments/r16-bot-runtime/v81_source_parity.py`.
- Embedded archive: 154 entries, total declared uncompressed bytes 384,859; no encrypted, symlink, traversal, or otherwise unsafe entries found in the local structural audit.
- All **10/10** mapped original source members match the independently recorded SHA-256 values in the parity script. No ZIP entry was extracted or executed, and no private source or fixture bytes were uploaded.
- Reviewed one concrete difference: original `utc_strict_oracle.js` uses a working-directory-relative fixture and lacks the isolated branch's `__dirname` fixture pin, no-follow open and strict fixture row/header checks. The isolated implementation already retains this hardening; **no source replacement** was made.
- This verifies original archive **identity and 10 member fingerprints**, not full byte-for-byte parity of the isolated source. Previously reported 3 EXACT / 5 DIFFERENT / 2 ABSENT remain unresolved as deployment parity. `full_v81_deployed=false`.
- No claims of ChatGPT native scheduled-run success. Official per-run ID/status and same-run GitHub/Slack ledger remain **UNVERIFIED**.

## Scope and safety
- This report contains no private ZIP bytes, source code, fixture data, credentials, or personal information.
- Source comparison and archive inspection were local-only. No production writes, deployment, secret upload, or paid calls.
- Existing ChatGPT hourly :00 task, GitHub main / :15 cron / checkout pin, Slack, Activepieces and secrets are unchanged by this checkpoint.

## Next
Review one remaining original-vs-isolated source mismatch locally and retain any proven hardening. Make a minimal isolated-branch code change only if a reproducible defect is demonstrated; avoid re-running previously passing tests at the same SHA.
