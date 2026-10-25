#!/usr/bin/env python3
"""Fail-closed offline GitHub schedule provenance; NOT native ChatGPT attestation.

Only the caller can authenticate supplied GitHub API run/job/log objects.
No provider calls, secrets, paid APIs, deployments or production mutations.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

WORKFLOW = ".github/workflows/ai-r16-hourly.yml"
JOB = "hourly-offline-audit"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
CHECKOUT = re.compile(r"\[command\]/usr/bin/git checkout --progress --force ([0-9a-f]{40})(?:\s|$)")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_LOG_CHARS = 2_000_000
SWARM = re.compile(r"R16_V81_SWARM=(\{[^\r\n]*\})")


def verify_schedule(run, jobs, log, *, workflow_sha, source_sha):
    """Check same-run metadata and offline logs; no native/provider attestation."""
    out = {"kind": "GITHUB_SCHEDULE_OFFLINE_ONLY_NOT_CHATGPT_NATIVE",
           "status": "UNVERIFIED", "reason": "MISSING_SCHEDULE_RUN",
           "run_id": None, "native_chatgpt_proven": False,
           "source_authenticated_here": False}
    if run is None:
        return out
    if not isinstance(run, dict):
        out["reason"] = "MALFORMED_RUN"
        return out
    if run.get("event") is None:
        out["reason"] = "MISSING_RUN_EVENT"
        return out
    if run["event"] != "schedule":
        out.update(status="NOT_APPLICABLE", reason="NOT_SCHEDULE_EVENT")
        return out
    run_id = run.get("id")
    if (type(run_id) is not int or run_id <= 0 or
            not isinstance(workflow_sha, str) or not isinstance(source_sha, str) or
            not SHA40.fullmatch(workflow_sha) or not SHA40.fullmatch(source_sha)):
        out["reason"] = "MISSING_RUN_ID_OR_EXPECTED_SHA"
        return out
    out["run_id"] = run_id
    if run.get("status") != "completed":
        out["reason"] = "RUN_NOT_COMPLETED"
        return out
    if run.get("conclusion") != "success":
        out.update(status="FAIL" if run.get("conclusion") else "UNVERIFIED",
                   reason="RUN_NOT_SUCCESSFUL")
        return out
    if (run.get("head_sha") != workflow_sha or run.get("head_branch") != "main"
            or run.get("path") != WORKFLOW):
        out.update(status="FAIL", reason="WRONG_WORKFLOW_OR_HEAD_SHA")
        return out
    if not isinstance(jobs, list):
        out["reason"] = "MISSING_JOB_METADATA"
        return out
    matches = [j for j in jobs if isinstance(j, dict) and
               j.get("name") == JOB and type(j.get("run_id")) is int and
               j.get("run_id") == run_id]
    if len(matches) != 1:
        out["reason"] = "JOB_NOT_UNIQUELY_LINKED_TO_RUN"
        return out
    job = matches[0]
    if type(job.get("id")) is not int or job["id"] <= 0:
        out["reason"] = "MISSING_JOB_ID"
        return out
    if job.get("status") != "completed":
        out["reason"] = "JOB_NOT_COMPLETED"
        return out
    if job.get("conclusion") != "success":
        out.update(status="FAIL" if job.get("conclusion") else "UNVERIFIED",
                   reason="JOB_NOT_SUCCESSFUL")
        return out
    if not isinstance(log, str) or not log or len(log) > MAX_LOG_CHARS:
        out["reason"] = "MISSING_OR_OVERSIZE_OFFICIAL_JOB_LOG"
        return out
    if CHECKOUT.findall(log) != [source_sha]:
        out["reason"] = "CHECKOUT_SHA_NOT_UNIQUELY_PROVEN"
        return out
    receipts = []
    for raw in SWARM.findall(log):
        try:
            receipts.append(json.loads(raw))
        except ValueError:
            out["reason"] = "MALFORMED_SWARM_RECEIPT"
            return out
    if len(receipts) != 2:
        out["reason"] = "SWARM_RECEIPT_COUNT_INVALID"
        return out
    input_hashes = []
    for mode, count, groups, workers in (("audit", 20, 2, 2), ("all", 100, 10, 4)):
        found = [r for r in receipts if isinstance(r, dict) and r.get("mode") == mode]
        if len(found) != 1:
            out["reason"] = "MISSING_OR_DUPLICATE_SWARM_RECEIPT"
            return out
        r = found[0]
        exact_ints = (("selected_roles", count), ("group_count", groups),
                      ("effective_worker_cap", workers), ("external_model_calls", 0),
                      ("external_provider_calls", 0), ("production_changes", 0))
        if (r.get("kind") != "ISOLATED_OFFLINE_SWARM_NOT_NATIVE" or
                any(type(r.get(k)) is not int or r[k] != v for k, v in exact_ints) or
                r.get("status") != "PASS" or
                r.get("status_counts") != {"PASS": count} or
                r.get("independent_serial_oracle_match") is not True or
                r.get("native_chatgpt_run_verified") is not False or
                r.get("same_run_github_slack_proven") is not False or
                r.get("original_v81_source_deployed") is not False):
            out.update(status="FAIL", reason="SWARM_RECEIPT_NOT_PASS")
            return out
        digest = r.get("input_sha256")
        if type(digest) is not str or SHA256.fullmatch(digest) is None:
            out.update(status="FAIL", reason="SWARM_INPUT_HASH_INVALID")
            return out
        input_hashes.append(digest)
    if input_hashes[0] != input_hashes[1]:
        out.update(status="FAIL", reason="FAST_FULL_INPUT_HASH_MISMATCH")
        return out
    required = ("R16_HOURLY_OFFLINE_RECEIPT_VALIDATED",
                "OFFLINE_SINGLE_PROCESS_100_RULE_CHECKS_NOT_100_LLM_MODELS",
                "Ran 10 tests", "Ran 8 tests",
                "C strict timestamp oracle: PASS 20/20")
    if not all(tag in log for tag in required):
        out["reason"] = "MISSING_TEST_OR_AUDIT_LOG_EVIDENCE"
        return out
    out.update(status="PASS", reason="GITHUB_SCHEDULE_LOG_CONSISTENT",
               checked_source_sha=source_sha)
    return out


def main():
    parser = argparse.ArgumentParser(description="Offline schedule evidence validator")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        obj = json.loads(args.input.read_text(encoding="utf8"))
        if not isinstance(obj, dict):
            raise ValueError("expected JSON object")
        result = verify_schedule(obj.get("run"), obj.get("jobs"), obj.get("log"),
                                 workflow_sha=obj.get("workflow_sha"),
                                 source_sha=obj.get("source_sha"))
    except (OSError, ValueError, TypeError):
        result = {"status": "UNVERIFIED", "reason": "MISSING_OR_INVALID_INPUT",
                  "native_chatgpt_proven": False}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return {"PASS": 0, "FAIL": 1, "UNVERIFIED": 2, "NOT_APPLICABLE": 3}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
