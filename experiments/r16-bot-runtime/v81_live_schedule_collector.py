#!/usr/bin/env python3
"""Read-only official GitHub Actions schedule evidence collector.

Requires GH_TOKEN with actions:read. Never attests native ChatGPT runs.
Only allowlisted GET requests; no secrets, model APIs or production writes.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess

from v81_unified_schedule_provenance import verify, WORKFLOW

REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
LOG_LIMIT = 2_000_000
RUNS_LIMIT = 20


class GitHubReadError(Exception):
    pass


def gh_read(endpoint):
    """Fetch allowlisted GitHub GET paths without exposing token/errors."""
    if not isinstance(endpoint, str) or not endpoint.startswith("/repos/"):
        raise GitHubReadError("INVALID_ENDPOINT")
    if not (endpoint.endswith("/logs") or endpoint.endswith("/jobs?per_page=100") or
            endpoint.endswith("/runs?event=schedule&per_page=20")):
        raise GitHubReadError("ENDPOINT_NOT_ALLOWLISTED")
    if not os.environ.get("GH_TOKEN"):
        raise GitHubReadError("GITHUB_READ_TOKEN_UNAVAILABLE")
    try:
        proc = subprocess.run(
            ["gh", "api", "--method", "GET", "-H",
             "Accept: application/vnd.github+json", endpoint],
            capture_output=True, text=True, timeout=35, check=False)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        raise GitHubReadError("GITHUB_API_UNAVAILABLE") from None
    if proc.returncode:
        raise GitHubReadError("GITHUB_API_GET_FAILED")
    if len(proc.stdout) > LOG_LIMIT:
        raise GitHubReadError("GITHUB_RESPONSE_OVERSIZE")
    return proc.stdout


def unverified(reason, *, run_id=None, status="UNVERIFIED"):
    return {
        "kind": "GITHUB_SCHEDULE_LIVE_READ_ONLY_COLLECTOR",
        "status": status, "reason": reason,
        "run_id": run_id,
        "official_github_api_get_attempted": False,
        "native_chatgpt_run_verified": False,
        "same_run_github_slack_proven": False,
        "external_model_calls": 0, "production_changes": 0,
    }


def _json_obj(fetch, endpoint, label):
    raw = fetch(endpoint)
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        raise GitHubReadError("MALFORMED_" + label) from None
    if not isinstance(value, dict):
        raise GitHubReadError("INVALID_" + label)
    return value


def collect(fetch, repository, workflow_sha, source_sha):
    """Verify same-run API objects; fetch is real gh_read or a test double."""
    if (type(repository) is not str or REPOSITORY.fullmatch(repository) is None or
        type(workflow_sha) is not str or SHA40.fullmatch(workflow_sha) is None or
        type(source_sha) is not str or SHA40.fullmatch(source_sha) is None):
        return unverified("INVALID_REPOSITORY_OR_SHA")
    base = "/repos/" + repository
    try:
        data = _json_obj(fetch, base + "/actions/runs?event=schedule&per_page=20", "RUN_LIST")
        runs = data.get("workflow_runs")
        if not isinstance(runs, list) or len(runs) > RUNS_LIMIT:
            return unverified("RUN_LIST_INVALID")
        relevant = [r for r in runs if isinstance(r, dict) and
                    r.get("event") == "schedule" and
                    r.get("path") == WORKFLOW and r.get("head_branch") == "main"]
        if not relevant:
            return unverified("NO_OFFICIAL_SCHEDULE_RUN")
        if any(type(r.get("run_number")) is not int for r in relevant):
            return unverified("RUN_NUMBER_INVALID")
        latest_number = max(r["run_number"] for r in relevant)
        latest = [r for r in relevant if r["run_number"] == latest_number]
        if len(latest) != 1:
            return unverified("LATEST_SCHEDULE_AMBIGUOUS")
        run = latest[0]
        rid = run.get("id")
        if type(rid) is not int or rid <= 0:
            return unverified("RUN_ID_INVALID")
        if run.get("head_sha") != workflow_sha:
            return unverified("EXPECTED_NEW_SCHEDULE_NOT_OBSERVED",
                              run_id=rid, status="NOT_APPLICABLE")
        if run.get("status") != "completed":
            return unverified("LATEST_SCHEDULE_STILL_RUNNING", run_id=rid)
        jobs_obj = _json_obj(fetch, base + "/actions/runs/" + str(rid) +
                            "/jobs?per_page=100", "JOBS")
        jobs = jobs_obj.get("jobs")
        if not isinstance(jobs, list) or not jobs or len(jobs) > 100:
            return unverified("OFFICIAL_JOBS_MISSING", run_id=rid)
        named = [j for j in jobs if isinstance(j, dict) and
                 j.get("name") == "hourly-offline-audit" and
                 type(j.get("run_id")) is int and j["run_id"] == rid]
        if len(named) != 1:
            return unverified("OFFICIAL_JOB_NOT_UNIQUE", run_id=rid)
        jid = named[0].get("id")
        if type(jid) is not int or jid <= 0:
            return unverified("OFFICIAL_JOB_ID_INVALID", run_id=rid)
        if named[0].get("status") != "completed":
            return unverified("OFFICIAL_JOB_STILL_RUNNING", run_id=rid)
        if named[0].get("conclusion") != "success":
            return {
                **unverified("OFFICIAL_JOB_FAILED" if named[0].get("conclusion")
                             else "OFFICIAL_JOB_CONCLUSION_MISSING", run_id=rid),
                "status": "FAIL" if named[0].get("conclusion") else "UNVERIFIED",
            }
        log = fetch(base + "/actions/jobs/" + str(jid) + "/logs")
        if not isinstance(log, str) or not log or len(log) > LOG_LIMIT:
            return unverified("OFFICIAL_LOG_MISSING_OR_OVERSIZE", run_id=rid)
        checked = verify(run, jobs, log, workflow_sha=workflow_sha, source_sha=source_sha)
        return {
            "kind": "GITHUB_SCHEDULE_LIVE_READ_ONLY_COLLECTOR",
            "status": checked["status"], "reason": checked["reason"],
            "run_id": rid, "job_id": jid,
            "evidence_sha256": checked.get("evidence_sha256"),
            "official_github_api_get_attempted": True,
            "native_chatgpt_run_verified": False,
            "same_run_github_slack_proven": False,
            "external_model_calls": 0, "production_changes": 0,
        }
    except GitHubReadError as exc:
        return unverified(str(exc))


def main():
    parser = argparse.ArgumentParser(description="Read-only GitHub schedule probe")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--expected-workflow-sha", required=True)
    parser.add_argument("--expected-source-sha", required=True)
    args = parser.parse_args()
    result = collect(gh_read, args.repository,
                     args.expected_workflow_sha, args.expected_source_sha)
    print("R16_V81_LIVE_SCHEDULE_CHECK=" +
          json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
