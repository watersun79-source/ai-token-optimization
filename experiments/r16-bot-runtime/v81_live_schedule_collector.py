#!/usr/bin/env python3
"""Read-only official GitHub Actions schedule evidence collector.

Requires GH_TOKEN with actions:read. Never attests native ChatGPT runs.
Only allowlisted GET requests; no secrets, model APIs or production writes.
"""
from __future__ import annotations
import argparse
import base64
import json
import os
import re
import subprocess

from v81_unified_schedule_provenance import verify, WORKFLOW

REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
API_PATH = re.compile(
    r"/repos/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/"
    r"(?:actions/(?:runs\?event=schedule&per_page=20|"
    r"runs/[1-9][0-9]*/jobs\?per_page=100|"
    r"jobs/[1-9][0-9]*/logs)|"
    r"git/ref/heads/main|"
    r"contents/\.github/workflows/ai-r16-hourly\.yml\?ref=[a-f0-9]{40})\Z"
)


def valid_repository(value):
    return (type(value) is str and REPOSITORY.fullmatch(value) is not None
            and all(part not in (".", "..") for part in value.split("/")))
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
LOG_LIMIT = 2_000_000
RUNS_LIMIT = 20


class GitHubReadError(Exception):
    pass


def gh_read(endpoint):
    """Fetch allowlisted GitHub GET paths without exposing token/errors."""
    match = API_PATH.fullmatch(endpoint) if isinstance(endpoint, str) else None
    if match is None or not valid_repository(match.group(1) + "/" + match.group(2)):
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
    if (not valid_repository(repository) or
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



def resolve_main_target(fetch, repository):
    """Resolve main and pinned checkout using only two restricted official GETs.

    Query file contents at the resolved commit SHA, not a moving branch ref.
    No provider SDK beyond gh, no writes, no native ChatGPT attestation.
    """
    if not valid_repository(repository):
        raise GitHubReadError("INVALID_REPOSITORY")
    base = "/repos/" + repository
    obj = _json_obj(fetch, base + "/git/ref/heads/main", "MAIN_REF")
    target = obj.get("object")
    main_sha = target.get("sha") if isinstance(target, dict) else None
    if (obj.get("ref") != "refs/heads/main" or type(main_sha) is not str or
            SHA40.fullmatch(main_sha) is None):
        raise GitHubReadError("MAIN_REF_NOT_AUTHENTICATED")
    path = base + "/contents/.github/workflows/ai-r16-hourly.yml?ref=" + main_sha
    response = _json_obj(fetch, path, "MAIN_WORKFLOW")
    if (response.get("type") != "file" or
            response.get("path") != ".github/workflows/ai-r16-hourly.yml" or
            response.get("encoding") != "base64" or
            not isinstance(response.get("content"), str)):
        raise GitHubReadError("WORKFLOW_CONTENTS_UNVERIFIED")
    try:
        binary = base64.b64decode("".join(response["content"].split()), validate=True)
        if len(binary) > 100_000:
            raise ValueError("oversized workflow")
        workflow = binary.decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        raise GitHubReadError("WORKFLOW_ENCODING_INVALID") from None
    if not re.search(r"(?m)^\s*-\s*cron:\s*['\"]15 \* \* \* \*['\"]\s*$", workflow):
        raise GitHubReadError("PROTECTED_HOURLY_CRON_MISMATCH")
    pins = re.findall(r"(?m)^\s+ref:\s*([0-9a-f]{40})\s*$", workflow)
    if len(pins) != 1:
        raise GitHubReadError("PINNED_SOURCE_NOT_UNIQUE")
    return main_sha, pins[0]


def main():
    parser = argparse.ArgumentParser(description="Read-only GitHub schedule probe")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--expected-workflow-sha", default=None)
    parser.add_argument("--expected-source-sha", default=None)
    args = parser.parse_args()
    completed_gets = []
    def observed_get(path):
        payload = gh_read(path)
        completed_gets.append(path)
        return payload
    if (args.expected_workflow_sha is None) != (args.expected_source_sha is None):
        result = unverified("EXPECTED_SHA_PAIR_REQUIRED")
    elif args.expected_workflow_sha is not None:
        result = collect(observed_get, args.repository,
                         args.expected_workflow_sha, args.expected_source_sha)
        result["target_resolution"] = "EXPLICIT_SHA_ARGUMENTS"
    else:
        try:
            main_sha, pinned_sha = resolve_main_target(observed_get, args.repository)
            result = collect(observed_get, args.repository, main_sha, pinned_sha)
            result["target_resolution"] = "OFFICIAL_MAIN_REF_AND_PINNED_WORKFLOW"
            result["expected_workflow_sha"] = main_sha
            result["expected_source_sha"] = pinned_sha
        except GitHubReadError as exc:
            result = unverified(str(exc))
    if completed_gets:
        result["official_github_api_get_attempted"] = True
    print("R16_V81_LIVE_SCHEDULE_CHECK=" +
          json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
