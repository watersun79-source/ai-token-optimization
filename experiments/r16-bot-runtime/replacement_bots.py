"""Public synthetic-only 18-rule bridge; NOT the user's original ZIP source.

Reuses the audited v81_split_bench implementation. This module cannot attest
real ChatGPT, GitHub, Slack or Activepieces execution; never feed it secrets.
"""
from __future__ import annotations

import v81_split_bench as _adapter

BOT_CHECKS = dict(_adapter.CHECKS)
REPLACEMENTS = dict(_adapter.ORIGINAL_REPLACEMENT_NAMES)
assert len(BOT_CHECKS) == 18 and set(BOT_CHECKS) == set(REPLACEMENTS)


def classify_provenance(_record) -> str:
    """A local JSON object cannot prove an official remote run."""
    return "UNVERIFIED"


def check_all(snapshot) -> dict[str, str]:
    """Return LOCAL_PASS / FAIL / UNVERIFIED for explicit synthetic inputs only."""
    unknown = {role: "UNVERIFIED" for role in BOT_CHECKS}
    if not isinstance(snapshot, dict) or snapshot.get("source") != "synthetic_fixture":
        return unknown
    entries = snapshot.get("runs")
    if not isinstance(entries, list) or not entries:
        return unknown
    if any(not isinstance(item, dict) or item.get("source") != "synthetic_fixture"
           for item in entries):
        return unknown

    result = {}
    for role, fn in BOT_CHECKS.items():
        try:
            result[role] = "LOCAL_PASS" if fn(snapshot) else "FAIL"
        except (KeyError, ValueError, TypeError, AssertionError,
                AttributeError, OverflowError, RecursionError):
            result[role] = "UNVERIFIED"
    return result
