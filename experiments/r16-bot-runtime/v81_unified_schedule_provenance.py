#!/usr/bin/env python3
"""Strict, offline correlation of supplied GitHub schedule metadata and unified logs.

Caller MUST fetch and authenticate real GitHub API run/job/log independently.
Fixtures, workflow env variables and output JSON are not API attestations.
No HTTP calls, secrets, model APIs, production writes or scheduled tasks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

WORKFLOW = ".github/workflows/ai-r16-hourly.yml"
JOB = "hourly-offline-audit"
KIND = "GITHUB_UNIFIED_SCHEDULE_PROVENANCE_OFFLINE"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
CHECKOUT = re.compile(r"\[command\]/usr/bin/git checkout --progress --force ([0-9a-f]{40})(?:\s|$)")
RECEIPT_PREFIX = "R16_V81_UNIFIED_EVIDENCE="
COUNTS = {"python": 23, "java": 20, "js": 20, "c": 20}
LIMIT = 2_000_000


def verify(run, jobs, log, *, workflow_sha, source_sha):
    result = {
        "kind": KIND, "status": "UNVERIFIED",
        "reason": "MISSING_OFFICIAL_GITHUB_INPUT",
        "run_id": None,
        "github_api_inputs_authenticated_here": False,
        "native_chatgpt_run_verified": False,
        "same_run_github_slack_proven": False,
    }
    def stop(status, reason):
        result.update(status=status, reason=reason)
        return result

    if not isinstance(run, dict):
        return stop("UNVERIFIED", "MISSING_OR_MALFORMED_RUN")
    if run.get("event") is None:
        return stop("UNVERIFIED", "EVENT_MISSING")
    if run["event"] != "schedule":
        return stop("NOT_APPLICABLE", "NOT_SCHEDULE")
    rid = run.get("id")
    if (type(rid) is not int or rid <= 0 or
        type(workflow_sha) is not str or SHA40.fullmatch(workflow_sha) is None or
        type(source_sha) is not str or SHA40.fullmatch(source_sha) is None):
        return stop("UNVERIFIED", "EXPECTED_IDS_OR_SHA_INVALID")
    result["run_id"] = rid
    if run.get("status") != "completed":
        return stop("UNVERIFIED", "RUN_NOT_COMPLETED")
    if run.get("conclusion") != "success":
        return stop("FAIL" if run.get("conclusion") is not None else "UNVERIFIED",
                    "RUN_NOT_SUCCESS")
    if (run.get("head_sha") != workflow_sha or run.get("head_branch") != "main" or
        run.get("path") != WORKFLOW):
        return stop("FAIL", "RUN_WORKFLOW_OR_SHA_MISMATCH")

    if not isinstance(jobs, list):
        return stop("UNVERIFIED", "JOBS_MISSING")
    match = [j for j in jobs if isinstance(j, dict) and j.get("name") == JOB and
             j.get("run_id") == rid and type(j.get("run_id")) is int]
    if len(match) != 1:
        return stop("UNVERIFIED", "JOB_NOT_UNIQUELY_LINKED_TO_RUN")
    job = match[0]
    if type(job.get("id")) is not int or job["id"] <= 0:
        return stop("UNVERIFIED", "JOB_ID_INVALID")
    if job.get("status") != "completed":
        return stop("UNVERIFIED", "JOB_NOT_COMPLETED")
    if job.get("conclusion") != "success":
        return stop("FAIL" if job.get("conclusion") is not None else "UNVERIFIED",
                    "JOB_NOT_SUCCESS")
    if not isinstance(log, str) or len(log) > LIMIT or not log:
        return stop("UNVERIFIED", "RAW_JOB_LOG_MISSING_OR_OVERSIZE")
    pins = CHECKOUT.findall(log)
    if pins != [source_sha]:
        return stop("UNVERIFIED", "CHECKOUT_NOT_UNIQUELY_MATCHED")
    if "R16_HOURLY_OFFLINE_RECEIPT_VALIDATED" not in log:
        return stop("UNVERIFIED", "PRIOR_AUDIT_NOT_PROVEN")
    if "Ran 31 tests" not in log:
        return stop("UNVERIFIED", "REGRESSION_GUARDS_NOT_PROVEN")
    lines = [line.split(RECEIPT_PREFIX, 1)[1].strip()
             for line in log.splitlines() if RECEIPT_PREFIX in line]
    if len(lines) != 1:
        return stop("UNVERIFIED", "UNIFIED_RECEIPT_MISSING_OR_DUPLICATE")
    try:
        evidence = json.loads(lines[0])
    except (TypeError, ValueError):
        return stop("UNVERIFIED", "UNIFIED_RECEIPT_MALFORMED")
    if not isinstance(evidence, dict):
        return stop("UNVERIFIED", "UNIFIED_RECEIPT_NOT_OBJECT")
    digest = evidence.get("evidence_sha256")
    if type(digest) is not str or SHA256.fullmatch(digest) is None:
        return stop("UNVERIFIED", "EVIDENCE_HASH_MISSING")
    unsigned = {k: v for k, v in evidence.items() if k != "evidence_sha256"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest() != digest:
        return stop("FAIL", "EVIDENCE_HASH_MISMATCH")
    if (evidence.get("format") != "V81_OFFLINE_UNIFIED_EVIDENCE_V1" or
        evidence.get("scope") != "ISOLATED_LOCAL_OFFLINE_NOT_NATIVE_PLATFORM" or
        evidence.get("status") != "PASS"):
        return stop("FAIL", "EVIDENCE_STATUS_OR_SCOPE_MISMATCH")
    if evidence.get("languages") != COUNTS or type(evidence.get("language_total")) is not int or evidence["language_total"] != 83:
        return stop("FAIL", "POLYGLOT_RESULTS_MISMATCH")
    group = evidence.get("local_swarm")
    if not isinstance(group, dict) or any(
            type(group.get(k)) is not int or group[k] != n
            for k, n in (("fast_pass", 20), ("full_pass", 100),
                         ("groups", 10), ("worker_cap", 4))):
        return stop("FAIL", "SWARM_RESULTS_MISMATCH")
    if group.get("independent_serial_oracle_match") is not True or \
            type(group.get("input_sha256")) is not str or \
            SHA256.fullmatch(group["input_sha256"]) is None:
        return stop("FAIL", "SWARM_ORACLE_UNVERIFIED")
    fields_false = ("native_chatgpt_run_verified", "same_run_github_slack_proven",
                    "github_api_run_verified", "runner_context_officially_authenticated")
    if any(evidence.get(k) is not False for k in fields_false):
        return stop("FAIL", "UNAUTHORIZED_EXTERNAL_ATTESTATION")
    fields_zero = ("external_model_calls", "production_changes", "real_external_llm_agents")
    if any(type(evidence.get(k)) is not int or evidence[k] != 0 for k in fields_zero):
        return stop("FAIL", "UNAUTHORIZED_EXTERNAL_WORK")
    env = evidence.get("runner_context_self_reported")
    if not isinstance(env, dict) or env.get("github_run_id") != str(rid) or \
            env.get("github_sha") != workflow_sha or env.get("github_event") != "schedule":
        return stop("FAIL", "RUNNER_ENV_DIFFERENT_OFFICIAL_RUN")
    sources = evidence.get("source_sha256")
    if not isinstance(sources, dict) or not sources or any(
            type(x) is not str or SHA256.fullmatch(x) is None
            for x in sources.values()):
        return stop("FAIL", "SOURCE_HASHES_MISSING")
    result.update(status="PASS", reason="SUPPLIED_GITHUB_RUN_JOB_LOG_AND_SHA_CONSISTENT",
                  evidence_sha256=digest, source_sha=source_sha,
                  counts=dict(COUNTS), local_swarm_pass=100)
    return result


def main():
    parser = argparse.ArgumentParser(description="Offline unified scheduled-run verification")
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("expected object")
        output = verify(data.get("run"), data.get("jobs"), data.get("log"),
                        workflow_sha=data.get("workflow_sha"),
                        source_sha=data.get("source_sha"))
    except (OSError, ValueError, TypeError, OverflowError):
        output = {"kind": KIND, "status": "UNVERIFIED",
                  "reason": "MALFORMED_OR_UNAVAILABLE_INPUT",
                  "native_chatgpt_run_verified": False}
    print(json.dumps(output, sort_keys=True, ensure_ascii=False))
    return {"PASS": 0, "FAIL": 1, "UNVERIFIED": 2, "NOT_APPLICABLE": 3}[output["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
