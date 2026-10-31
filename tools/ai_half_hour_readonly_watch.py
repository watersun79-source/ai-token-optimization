"""Read-only, public GitHub evidence checks. Never calls a native ChatGPT task.

The three probes verify source metadata, offline CI metadata, and issue tracking.
They cannot establish a ChatGPT-native scheduled-run outcome.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

REPO = "watersun79-source/ai-token-optimization"
API = f"https://api.github.com/repos/{REPO}"


def fetch_json(path: str) -> Any:
    if not path.startswith("/") or "//" in path:
        raise ValueError("Unsupported GitHub API path")
    request = urllib.request.Request(
        API + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-half-hourly-readonly-probe",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


def probe(name: str, path: str, interpret: Callable[[Any], dict]) -> dict:
    try:
        result = interpret(fetch_json(path))
        return {"name": name, **result}
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError, OSError) as exc:
        # A public-API failure is a missing observation, not proof of remote failure.
        kind = type(exc).__name__
        return {"name": name, "verdict": "UNVERIFIED", "detail": f"public API unavailable ({kind})"}


def check_source(data: Any) -> dict:
    sha = data["sha"]
    if not isinstance(sha, str) or len(sha) != 40:
        raise ValueError("Invalid commit SHA")
    return {"verdict": "OBSERVED", "detail": f"main HEAD {sha}", "source_sha": sha}


def check_audit(data: Any) -> dict:
    scheduled = next((r for r in data["workflow_runs"] if r.get("event") == "schedule"), None)
    if not scheduled:
        return {"verdict": "UNVERIFIED", "detail": "No scheduled R16 audit in response"}
    run_id = scheduled["id"]
    status = scheduled.get("status", "unknown")
    conclusion = scheduled.get("conclusion")
    verdict = "OFFLINE_CI_PASS" if status == "completed" and conclusion == "success" else "OFFLINE_CI_PENDING_OR_FAIL"
    return {
        "verdict": verdict,
        "detail": f"R16 scheduled run {run_id}, status={status}, conclusion={conclusion}",
        "run_url": scheduled.get("html_url", ""),
    }


def check_native_issue(data: Any) -> dict:
    # Issue metadata alone does not authenticate any actual native execution.
    state = data["state"]
    return {
        "verdict": "TRACKER_ONLY",
        "detail": f"Issue #8 {state}; updated_at={data.get('updated_at', 'unknown')}",
        "native_run_proof": "UNVERIFIED",
    }


def run_report(fetch: Callable[[str], Any] | None = None) -> dict:
    global fetch_json
    original_fetch = fetch_json
    if fetch is not None:
        fetch_json = fetch
    try:
        checks = [
            probe("main_sha", "/commits/main", check_source),
            probe("r16_offline_ci", "/actions/workflows/ai-r16-hourly.yml/runs?per_page=15", check_audit),
            probe("native_provenance_issue", "/issues/8", check_native_issue),
        ]
    finally:
        fetch_json = original_fetch
    return {
        "observed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "runner_id": os.environ.get("GITHUB_RUN_ID", "LOCAL"),
        "execution_kind": "GITHUB_ACTIONS_READONLY_NOT_NATIVE_CHATGPT",
        "native_per_run_success": "UNVERIFIED",
        "external_model_calls": 0,
        "external_writes": 0,
        "checks": checks,
    }


def format_summary(report: dict) -> str:
    rows = [
        "## AI BOT · 30분 독립 증거 점검",
        "",
        f"- 실행: `{report['runner_id']}` / `{report['observed_at_utc']}`",
        "- 범위: GitHub 공개 API 읽기 3개 (ChatGPT 예약 실행 아님)",
        "- Native 예약 성공: **UNVERIFIED**",
        "- 외부 모델 호출·원격 쓰기: **0건**",
        "",
        "| 검사 | 판정 | 실제 관찰 |",
        "|---|---|---|",
    ]
    for row in report["checks"]:
        detail = str(row["detail"]).replace("|", "/").replace("\n", " ")
        rows.append(f"| {row['name']} | {row['verdict']} | {detail} |")
    rows.append("")
    return "\n".join(rows)


def main() -> None:
    report = run_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as stream:
            stream.write(format_summary(report))


if __name__ == "__main__":
    main()
