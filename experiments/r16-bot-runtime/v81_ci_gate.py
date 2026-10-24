#!/usr/bin/env python3
"""Fail-closed isolated CI full-regression selector; not a native ChatGPT scheduler.
Only GitHub push commits changing an exact allowlist of markdown documentation
can skip the already-tested full 100-rule job. Every uncertainty triggers full.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SHA = re.compile(r"^[a-f0-9]{40}$")
DOCS_ONLY = frozenset({
    "docs/ai/V81_SOURCE_PARITY_20261024.md",
    "docs/ai/V81_FAST_FULL_BENCHMARK_20261024.md",
    "docs/ai/V81_SPEED_OPTIMIZATION_20261024.md",
    "docs/ai/V81_FAST_POLICY_20261024.md",
})

def decision(event, before, head, parent, paths) -> dict:
    """Input paths must be from checkout's own Git diff, not self-reported.
    NEVER cache independent CI outcomes or native ChatGPT app results here.
    """
    reason = "unknown_input"
    run_full = True
    if event != "push":
        reason = "manual_or_unknown_event"
    elif not all(isinstance(s, str) and SHA.fullmatch(s) for s in (before, head, parent)):
        reason = "invalid_sha_or_unavailable_parent"
    elif before != parent:
        reason = "multi_commit_or_incomplete_history"
    elif not isinstance(paths, list) or not paths or any(not isinstance(p, str) or not p for p in paths):
        reason = "empty_or_untrusted_diff"
    elif all(p in DOCS_ONLY for p in paths):
        run_full, reason = False, "docs_only_single_commit"
    else:
        reason = "code_workflow_or_unknown_file_changed"
    return {
        "kind": "ISOLATED_CI_GATE_NOT_NATIVE",
        "run_full": run_full, "reason": reason,
        "changed_files": len(paths) if isinstance(paths, list) else None,
        "native_chatgpt_attested": False,
    }

def checkout_decision(event, before, head, root: Path = ROOT):
    """Use local, immutable Git tree; any subprocess problem => full."""
    try:
        parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=root, check=True,
                                capture_output=True, text=True, timeout=10).stdout.strip()
        actual_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                                     capture_output=True, text=True, timeout=10).stdout.strip()
        if actual_head != head or before != parent:
            return decision(event, before, head, parent, [])
        names = subprocess.run(["git", "diff", "--no-renames", "--name-only", "-z",
                                parent, actual_head], cwd=root, check=True,
                               capture_output=True, timeout=10).stdout
        changed = [os.fsdecode(p) for p in names.split(b"\0") if p]
        return decision(event, before, head, parent, changed)
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return decision(event, before, head, "", [])

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--event",default=os.getenv("GITHUB_EVENT_NAME","unknown"))
    p.add_argument("--before",default=os.getenv("V81_PUSH_BEFORE",""))
    p.add_argument("--head",default=os.getenv("GITHUB_SHA",""))
    a=p.parse_args()
    result=checkout_decision(a.event,a.before,a.head)
    print("R16_V81_FAST_GATE="+json.dumps(result,sort_keys=True))
    output=os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output,"a",encoding="utf-8") as f:
            f.write("run_full="+str(result["run_full"]).lower()+"\n")
            f.write("reason="+result["reason"]+"\n")
    summary=os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as f:
            f.write("\n### Isolated adaptive CI gate\n")
            f.write("- Full regression: "+("RUN" if result["run_full"] else "SKIP")+"\n")
            f.write("- Reason: "+result["reason"]+"\n")
            f.write("- Native ChatGPT provider evidence: UNVERIFIED\n")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
