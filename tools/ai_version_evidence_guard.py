"""Read-only, provider-free evidence classification for AI BOT releases.

This module never runs a model, invokes a provider, changes schedules, or promotes
code. A caller must supply independently retrieved records with their provenance.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Mapping


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def _record(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def evaluate(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Classify evidence conservatively, never treating CI as production proof.

    Output deliberately separates provider connection, read-only API availability,
    scheduled GitHub run, API collection, ChatGPT native run, and release scope.
    """
    observed = _time(snapshot.get("observed_at"))
    connection = _record(snapshot.get("activepieces_github_connection"))
    watcher = _record(snapshot.get("read_only_watcher"))
    schedule = _record(snapshot.get("last_schedule_run"))
    collector = _record(snapshot.get("hosted_collector"))
    native = _record(snapshot.get("native_run"))
    release = _record(snapshot.get("candidate_release"))

    conn_status = str(connection.get("status", "UNVERIFIED")).upper()
    if conn_status == "ACTIVE":
        github_connection = "PASS_CONNECTED_CONFIG_ONLY"
    elif conn_status in ("INACTIVE", "DISABLED", "REVOKED"):
        github_connection = "FAIL_CONFIG_NOT_ACTIVE"
    else:
        github_connection = "UNVERIFIED"

    # Read-only code cannot prove *dispatch* permissions, even on API HTTP 200.
    github_read = "PASS_READ_ONLY_HTTP" if watcher.get("github_api_http_status") == 200 else "UNVERIFIED"
    github_dispatch_permissions = "UNVERIFIED_READ_ONLY_WATCH"
    configured_blocker = str(watcher.get("github_dispatch_blocker", ""))
    static_false_warning = (
        watcher.get("is_read_only") is True
        and github_connection == "PASS_CONNECTED_CONFIG_ONLY"
        and configured_blocker == "NO_ACTIVEPIECES_GITHUB_CONNECTION"
    )

    collected_at = _time(collector.get("observed_at"))
    attempted = collector.get("successful_reads")
    total = collector.get("total_reads")
    failed = collector.get("failed_reads")
    http_code = collector.get("http_code")
    if http_code == 403 or (isinstance(failed, int) and failed > 0):
        collector_status = "UNVERIFIED_LATEST_FAILED"
    elif not (isinstance(attempted, int) and isinstance(total, int) and total > 0):
        collector_status = "UNVERIFIED"
    elif attempted != total or failed != 0:
        collector_status = "UNVERIFIED_PARTIAL"
    elif not observed or not collected_at or collected_at > observed or observed - collected_at > timedelta(minutes=30):
        collector_status = "UNVERIFIED_STALE"
    else:
        collector_status = "PASS_BOUNDED_READS_ONLY"

    event = schedule.get("event")
    scheduled_created = _time(schedule.get("created_at"))
    if event != "schedule":
        scheduled_status = "UNVERIFIED_NOT_A_SCHEDULE_EVENT"
    elif schedule.get("status") != "completed" or schedule.get("conclusion") != "success":
        scheduled_status = "UNVERIFIED_NOT_SUCCESSFUL"
    elif not observed or not scheduled_created or scheduled_created > observed:
        scheduled_status = "UNVERIFIED_TIMESTAMPS"
    elif observed - scheduled_created > timedelta(minutes=85):
        scheduled_status = "WARN_LAST_SCHEDULE_STALE"
    else:
        scheduled_status = "PASS_RECENT_GITHUB_SCHEDULE_ONLY"

    # Native evidence needs matching IDs *and* a same-run external call ledger.
    native_id = native.get("run_id")
    native_status = (
        "PASS_SAME_NATIVE_RUN"
        if isinstance(native_id, str) and bool(native_id.strip())
        and native_id == native.get("external_ledger_native_run_id")
        and native.get("status") == "completed"
        and native.get("external_ledger_verified") is True
        else "UNVERIFIED"
    )

    # GitHub CI alone never promotes a draft branch to live production.
    can_promote = all(release.get(k) is True for k in (
        "merged", "authorized", "deploy_live", "live_health_verified",
        "rollback_ready", "official_ci_sha_matched",
    ))
    return {
        "activepieces_github_connection": github_connection,
        "github_read_only_api": github_read,
        "github_dispatch_permission": github_dispatch_permissions,
        "false_disconnected_warning_detected": static_false_warning,
        "hosted_github_collector": collector_status,
        "github_schedule": scheduled_status,
        "chatgpt_native_same_run": native_status,
        "release_promotion": "PASS_AUTHORIZED_PRODUCTION_GATES" if can_promote else "BLOCK_NO_PRODUCTION_PROOF",
        "candidate_software_version": release.get("version") if isinstance(release.get("version"), str) else None,
    }
