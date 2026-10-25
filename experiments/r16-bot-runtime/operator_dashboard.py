#!/usr/bin/env python3
"""Render the isolated operator dashboard from current execution evidence."""
from __future__ import annotations

import json
import os
import subprocess
import sys


def build_summary(swarm: dict, parity: dict) -> list[str]:
    failed = swarm.get("failed_or_unknown_roles", [])
    counts = parity.get("counts", {})
    unresolved = parity.get("unresolved_difference_count", "UNVERIFIED")

    if failed:
        next_action = "Fix only the failed/unknown IDs on this isolated branch."
    elif unresolved == 0:
        next_action = (
            "All source differences are reviewed; verify original deployment and "
            "native per-run ledger separately."
        )
    else:
        next_action = (
            f"Review {unresolved} unresolved source differences without uploading "
            "private source bytes."
        )

    return [
        "# AI BOT v8.1 · Isolated Operator Dashboard",
        "",
        "| Field | Verified result |",
        "| --- | --- |",
        f'| Offline rule execution | {swarm.get("status", "UNVERIFIED")} |',
        f'| Executed rule count | {swarm.get("selected_roles", "UNVERIFIED")} |',
        f'| Local worker count | {swarm.get("effective_worker_cap", "UNVERIFIED")} |',
        f'| Failed/unknown IDs | {", ".join(failed) if failed else "None in offline fixture"} |',
        (
            "| Source fingerprints | "
            f'EXACT {counts.get("EXACT", "UNVERIFIED")} / '
            f'DIFFERENT {counts.get("DIFFERENT", "UNVERIFIED")} / '
            f'ABSENT {counts.get("ABSENT", "UNVERIFIED")} |'
        ),
        f'| Reviewed source differences | {parity.get("reviewed_difference_count", "UNVERIFIED")} |',
        f"| Unresolved source differences | {unresolved} |",
        "| Original v8.1 production deployment | NOT VERIFIED |",
        "| ChatGPT native unattended run | UNVERIFIED |",
        "",
        "## Next operational action",
        next_action,
        "",
        "Offline synthetic execution is not a real external LLM or native ChatGPT task.",
    ]


def main() -> int:
    from v81_source_parity import compare

    result = subprocess.run(
        [sys.executable, "v81_swarm.py", "--mode", "all", "--workers", "4"],
        capture_output=True,
        text=True,
    )
    prefix = "R16_V81_SWARM="
    line = next((s for s in result.stdout.splitlines() if s.startswith(prefix)), None)
    if not line:
        raise SystemExit("No full BOT result; refuse to publish success")
    swarm = json.loads(line[len(prefix):])
    summary = build_summary(swarm, compare())
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
        handle.write("\n".join(summary) + "\n")
    if result.returncode != 0 or swarm.get("status") != "PASS":
        raise SystemExit("Full BOT execution did not pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
