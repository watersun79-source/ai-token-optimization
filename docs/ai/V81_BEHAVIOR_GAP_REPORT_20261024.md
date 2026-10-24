# AI BOT v8.1 — original ZIP vs isolated compatibility adapter (2026-10-24)

## Read-only original behavior / isolated GitHub CI

- User's original v8.1 ZIP SHA-256: `8c06d103af54d119c31ed927e0266a6d15dab4d9e24036cd2974e9b76739035a`, checksum verified locally.
- Original local Python source (after restoring the archived CSV test dependency): 40/40 unit tests PASS. Original Java and JS timestamp oracle: 20/20 each on the archive's 20 TSV cases. These are offline original-source tests, **not authenticated unattended platform proof**.
- GitHub branch: `ai/r16-v81-fast-full-ci-20261024`, SHA `848a8a41a05d3f4cfd0322046464cb39db34e351`; [CI run #40052414334](https://github.com/watersun79-source/ai-token-optimization/actions/runs/40052414334), `event=push`, both jobs `conclusion=success`.
- GitHub fast job: source parity tests 8/8, compatibility/oracle tests 14/14, fixture rules 20/20. Full job: source parity tests 8/8, compatibility/oracle tests 36/36, cross-language 22 Python + 20 Java + 20 JS, compatibility rules 100/100.
- Source SHA parity (10 files): 3 EXACT, 5 DIFFERENT, 2 ABSENT. This number has **not** been changed or presented as full source parity.
- New public test `test_v81_behavior_oracle.py`: on invented fixture inputs only, 29 mutation cases × 18 replacement rule outputs (522 role-case comparisons), plus 18 clean baseline checks. Source expectations came from independently executing the private original `replacement_bots.py`, without uploading original source or private data.
- In 27/29 scenarios, per-rule outcomes match the original. In 2 Unicode-decimal timestamp scenarios the original Python `\\d` accepts fullwidth/Arabic decimal digits, but the compatibility adapter's `[0-9]` correctly rejects them for `L07` and `L08`. Both deviations are explicit in the tests; this is a **security hardening, not byte-for-byte behavioral parity**.
- Five SHA differences: `runner.py` and `catalog.json` use original offline replacement integration versus the existing repo's 82 legacy rules and the adapter's synthetic reimplementation; `UtcStrictOracle.java`, `utc_strict_oracle.js`, `test_runtime.py` differ bytewise even though the tested timestamp fixture outcomes pass. **Broader equivalence beyond tested vectors is unverified.**
- Two absent SHA-mapped files: `replacement_bots.py` and `fixture_SYNTHETIC.json`. Neither original archive nor user-specific synthetic fixture copied to public GitHub. Adapter uses its own synthetic-only substitute.
- GitHub benchmark on #40052414334: median audit 0.067 ms (20 selected rules); full 2.0762 ms (100 rules), 150 repeats each, **in-process compatibility adapter only**, not original ZIP or end-to-end run cost.
- Scheduled native ChatGPT per-run GitHub/Slack tool-call ledger: UNVERIFIED. Real 100 independent LLM processes: not claimed.

## Protection invariants

No writes to `main`, no changes to existing GitHub `:15` schedule, no changes to ChatGPT `:00` scheduled automation, no Activepieces/Slack production changes, no model APIs, paid services, secrets or new Oracle Cloud resources.

## Next safe improvement

Keep original v8.1 private. Use an authenticated, isolated private runner to execute the original archive with independent reference fixtures and compare complete 100-role output schemas, not just the 18 replacement checks. Do not automatically mark original ZIP fully deployed or modify scheduled operation on the strength of fixture results.
