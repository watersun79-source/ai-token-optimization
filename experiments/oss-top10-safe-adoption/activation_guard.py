"""Fail-closed gate for PR #30 isolated OSS adapters.

Reads only verified lock blobs and an advisory snapshot. No network, SDK import,
model/API calls, writes, or actual vendor activation. Local mock dry-runs remain legal.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA = "OSS_TOP10_ACTIVATION_GUARD_V1"
SOURCE_HEAD = "be5bbae7725369db97215c8e5888136ab6e4a68c"
SOURCE_RUN = 43299315660
BLOCKED = frozenset({"activepieces", "openhands", "crewai", "letta"})
CLEAN = frozenset({"langgraph", "mem0", "langfuse", "agent-framework", "openai-agents"})
ALL = BLOCKED | CLEAN | {"flowise"}
LOCKS = ROOT / "locks"
EVIDENCE = ROOT / "activation_security_evidence.json"


class SecurityBlock(ValueError):
    """No authorization when the evidence is absent, stale, vulnerable or unverified."""


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_evidence(path: Path = EVIDENCE) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SecurityBlock("SECURITY_EVIDENCE_MISSING_OR_INVALID") from error


def verify_evidence(evidence: dict, *, locks_dir: Path = LOCKS) -> dict:
    if not isinstance(evidence, dict) or evidence.get("schema") != SCHEMA:
        raise SecurityBlock("INVALID_SECURITY_EVIDENCE_SCHEMA")
    if (evidence.get("source") != "GITHUB_ACTIONS_OFFICIAL_ADVISORY_CLIENTS"
            or evidence.get("audit_run_id") != SOURCE_RUN or evidence.get("audit_head") != SOURCE_HEAD):
        raise SecurityBlock("STALE_OR_UNVERIFIED_SECURITY_EVIDENCE")
    records = evidence.get("projects")
    if not isinstance(records, dict) or set(records) != ALL:
        raise SecurityBlock("INCOMPLETE_SECURITY_COVERAGE")

    decisions = {}
    for name in sorted(ALL):
        row = records[name]
        if not isinstance(row, dict):
            raise SecurityBlock("INVALID_SECURITY_RECORD:" + name)
        if name == "flowise":
            if row != {"status": "BLOCKED_EOL", "archive": True}:
                raise SecurityBlock("FLOWISE_END_OF_LIFE_BYPASS")
            decisions[name] = {"status": "BLOCKED_EOL", "activation_allowed": False,
                               "license": "UNVERIFIED", "known_advisories": None}
            continue
        lock_name, sha = row.get("lock_file"), row.get("git_blob_sha")
        if (not isinstance(lock_name, str) or not lock_name.startswith(name + "-")
                or "/" in lock_name or "\\" in lock_name or ".." in lock_name):
            raise SecurityBlock("LOCK_IDENTITY_INVALID:" + name)
        if (not isinstance(sha, str) or len(sha) != 40
                or any(c not in "0123456789abcdef" for c in sha)):
            raise SecurityBlock("EXPECTED_SHA_INVALID:" + name)
        try:
            actual = git_blob_sha((locks_dir / lock_name).read_bytes())
        except OSError as error:
            raise SecurityBlock("LOCK_UNAVAILABLE:" + name) from error
        if actual != sha:
            raise SecurityBlock("LOCK_CHANGED_REAUDIT_REQUIRED:" + name)
        count, license_state = row.get("known_advisories"), row.get("license_state")
        if type(count) is not int or count < 0:
            raise SecurityBlock("ADVISORY_COUNT_UNKNOWN:" + name)
        if license_state not in ("DECLARED_METADATA_ONLY", "REVIEW", "UNVERIFIED"):
            raise SecurityBlock("LICENSE_STATUS_UNKNOWN:" + name)
        if name in BLOCKED:
            if (count < 1 or row.get("status") != "BLOCKED_VULNERABILITY"
                    or not isinstance(row.get("advisory_ids"), list)
                    or not row["advisory_ids"]):
                raise SecurityBlock("KNOWN_VULNERABILITY_UNBLOCK_ATTEMPT:" + name)
            status = "BLOCKED_VULNERABILITY"
        else:
            if (count != 0 or row.get("status") != "OFFLINE_ONLY"
                    or license_state != "DECLARED_METADATA_ONLY"):
                raise SecurityBlock("CLEAN_SDK_EVIDENCE_DRIFT:" + name)
            status = "OFFLINE_ONLY_NOT_APPROVED"
        decisions[name] = {
            "status": status, "activation_allowed": False,
            "license": license_state, "known_advisories": count,
            "lock_git_blob_sha": actual,
        }
    return {
        "schema": SCHEMA, "source_head": SOURCE_HEAD, "source_security_run": SOURCE_RUN,
        "projects": decisions, "blocked_vulnerable": sorted(BLOCKED),
        "runtime_activations": 0, "provider_calls": 0, "production_writes": 0,
    }


def status_snapshot() -> dict:
    return verify_evidence(load_evidence())


def require_activation_allowed(project: str, *, action: str = "enable") -> None:
    """Explicit deny for ALL live SDK actions, even for advisory-clean candidates."""
    snapshot = status_snapshot()  # Fail closed if the evidence or lock drifts.
    if project not in snapshot["projects"]:
        raise SecurityBlock("UNKNOWN_SDK_BLOCKED")
    if action not in ("enable", "install", "start", "invoke", "deploy", "connect", "publish"):
        raise SecurityBlock("UNKNOWN_ACTION_BLOCKED")
    raise SecurityBlock("ACTIVATION_DENIED:" + project + ":" + snapshot["projects"][project]["status"])
