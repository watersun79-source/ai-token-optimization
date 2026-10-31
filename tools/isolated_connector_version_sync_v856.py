"""Offline-only AI BOT connector version snapshot gate (v8.5.6 candidate).

The caller must supply fresh observations from tools it actually invoked.
No plugin installation, cross-provider login, secret transfer, external API calls,
ChatGPT-wide chat hook, production changes, or automated deployment.
Grok Bot Control is always paused unless this policy is changed in source and
separately authorized. Runtime software version is not a plugin version.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from collections.abc import Mapping, Sequence

VERSION = "8.5.6-isolated-connector-inventory"
COMPONENTS = frozenset({
    "github", "slack", "context7", "replit", "exa", "neon", "render",
    "activepieces", "d1_memory", "grok_bot_control",
})
STATUSES = frozenset({"SESSION_READ_PASS", "TOOL_AVAILABLE", "UNVERIFIED", "PAUSED"})
SOURCES = frozenset({"connector_read", "tool_inventory", "registry_read"})
EVIDENCE = re.compile(r"^[a-zA-Z0-9._:-]{3,128}$")
VERSIONS = re.compile(r"^v?[0-9]+(?:\\.[0-9]+){1,3}(?:-[A-Za-z0-9.-]+)?$")


def _utc(t: str) -> datetime:
    if not isinstance(t, str):
        raise ValueError("INVALID_TIMESTAMP")
    try:
        parsed = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_TIMESTAMP") from exc
    if parsed.tzinfo is None:
        raise ValueError("NAIVE_TIMESTAMP")
    return parsed.astimezone(timezone.utc)


def reconcile_connector_versions(
    observations: Sequence[Mapping[str, object]], *, now: str,
    max_age_hours: int = 24,
) -> dict[str, object]:
    """Validate user-provided evidence metadata; *not* tool authentication.

    SESSION_READ_PASS only means the session's read call was observed. It does
    not prove hosted integration, inter-service sync, or unattended execution.
    Each record must name the actual caller-observed tool and evidence; a
    version is displayed only when separate version proof was supplied.
    """
    anchor = _utc(now)
    if type(max_age_hours) is not int or not 1 <= max_age_hours <= 168:
        raise ValueError("INVALID_MAX_AGE")
    if not isinstance(observations, (list, tuple)):
        raise ValueError("INVALID_OBSERVATIONS")
    entries: dict[str, dict[str, object]] = {}
    for entry in observations:
        if not isinstance(entry, Mapping) or set(entry) != {
            "component", "status", "source", "observed_at", "evidence", "version"
        }:
            raise ValueError("INVALID_RECORD_SHAPE")
        component, status, source = (entry[k] for k in ("component", "status", "source"))
        if component not in COMPONENTS or status not in STATUSES or source not in SOURCES:
            raise ValueError("INVALID_CONNECTOR_METADATA")
        if component in entries:
            raise ValueError("DUPLICATE_COMPONENT")
        observed = _utc(entry["observed_at"])
        if observed > anchor or anchor - observed > timedelta(hours=max_age_hours):
            raise ValueError("STALE_OR_FUTURE_EVIDENCE")
        evidence = entry["evidence"]
        if not isinstance(evidence, str) or not EVIDENCE.fullmatch(evidence):
            raise ValueError("INVALID_EVIDENCE")
        version = entry["version"]
        if version is not None and (
            not isinstance(version, str) or not VERSIONS.fullmatch(version)
            or status != "SESSION_READ_PASS" or source == "tool_inventory"
        ):
            raise ValueError("UNVERIFIED_VERSION")
        if component == "grok_bot_control" and status != "PAUSED":
            raise ValueError("GROK_CONNECTION_PAUSED")
        if status == "SESSION_READ_PASS" and source != "connector_read":
            raise ValueError("READ_WITHOUT_CONNECTOR")
        if status == "TOOL_AVAILABLE" and source != "tool_inventory":
            raise ValueError("TOOL_STATUS_WITHOUT_INVENTORY")
        entries[component] = {
            "status": status,
            "source": source,
            "observed_at": observed.isoformat(),
            "evidence": evidence,
            "reported_component_version": version,
            "live_cross_app_sync_verified": False,
            "plugin_binary_upgraded": False,
        }
    entries.setdefault("grok_bot_control", {
        "status": "PAUSED", "source": "registry_read",
        "observed_at": anchor.isoformat(), "evidence": "user.pause_grok",
        "reported_component_version": None,
        "live_cross_app_sync_verified": False,
        "plugin_binary_upgraded": False,
    })
    return {
        "registry_schema": VERSION,
        "scope": "ISOLATED_METADATA_ONLY",
        "components": dict(sorted(entries.items())),
        "session_read_pass": sum(v["status"] == "SESSION_READ_PASS" for v in entries.values()),
        "production_changed": False,
        "external_paid_calls": 0,
        "unattended_automation_verified": False,
    }
