#!/usr/bin/env python3
"""PR #31 isolated collection of schedule workflow runs with runner GitHub token.

No Site calls, no provider fallbacks, no retries, no repo commits, no D1 writes.
Runner invokes only when gated to our repo's PR #31. Only an allowlisted summary
of real GitHub Actions run data is saved in a short-lived CI artifact.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORY = "watersun79-source/ai-token-optimization"
WORKFLOW = "ai-r16-hourly.yml"
ENDPOINT = (
    f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/"
    f"{WORKFLOW}/runs?event=schedule&per_page=10"
)
SCOPE = "PR31_AUTHENTICATED_GITHUB_SCHEDULE_SNAPSHOT_V1"


def transform(payload: object) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise ValueError("malformed API payload")
    # Ignore untrusted/descriptive API payload fields, including actor details.
    sanitized = []
    for item in payload["workflow_runs"][:10]:
        if not isinstance(item, dict):
            raise ValueError("malformed workflow run")
        run_id = item.get("id")
        sha = item.get("head_sha")
        if (not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0
                or not isinstance(sha, str) or len(sha) != 40
                or any(c not in "0123456789abcdef" for c in sha)
                or item.get("event") != "schedule"):
            raise ValueError("untrusted workflow run identity")
        sanitized.append({
            "id": run_id,
            "sha": sha,
            "status": item.get("status") if item.get("status") in ("queued", "in_progress", "completed", "waiting", "pending", "requested") else "unverified",
            "conclusion": item.get("conclusion") if item.get("conclusion") in ("success", "failure", "cancelled", "skipped", "timed_out", "neutral", "action_required", "stale") else None,
            "created_at": item.get("created_at") if isinstance(item.get("created_at"), str) and len(item["created_at"]) <= 40 else None,
        })
    canonical = json.dumps(sanitized, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema": SCOPE,
        "source": "GitHub Actions ephemeral runner, authenticated GET",
        "repository": REPOSITORY,
        "workflow": WORKFLOW,
        "observed_count": len(sanitized),
        "runs_sha256": hashlib.sha256(canonical).hexdigest(),
        "runs": sanitized,
        "site_runtime_integration": "UNVERIFIED",
        "site_source_deployed": False,
        "native_schedule_goal": "UNVERIFIED",
        "operational_write_allowed": False,
    }


def main() -> int:
    token = os.environ.get("GH_TOKEN", "")
    if (not token or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
            or os.environ.get("GITHUB_EVENT_NAME") != "pull_request"):
        print("BLOCKED: repository/event/ephemeral token precondition absent")
        return 2
    try:
        req = Request(ENDPOINT, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pr31-isolated-schedule-collector",
        }, method="GET")
        with urlopen(req, timeout=15) as response:
            if response.status != 200:
                raise ValueError("unexpected API response")
            data = response.read(256_001)
        if len(data) > 256_000:
            raise ValueError("API response too large")
        result = transform(json.loads(data))
        target = Path("pr31_schedule_runs.json")
        target.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        # Artifact is the only intended write, not the repository.
        print(f"PR31_AUTHENTICATED_SCHEDULE_GET PASS count={result['observed_count']} sha256={result['runs_sha256']}")
        for rec in result["runs"][:3]:
            print(f"SCHEDULE_RUN id={rec['id']} status={rec['status']} conclusion={rec['conclusion']}")
        print("SITE_RUNTIME_AUTH=UNVERIFIED SITE_DEPLOYED=false OPERATIONS_NO_WRITE=true")
        return 0
    except (HTTPError, URLError, ValueError, json.JSONDecodeError, OSError, TimeoutError) as exc:
        # Never print token, URL with secrets, response body or exception text.
        code = exc.code if isinstance(exc, HTTPError) else "UNVERIFIED"
        print(f"PR31_AUTHENTICATED_SCHEDULE_GET BLOCKED http_status={code}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
