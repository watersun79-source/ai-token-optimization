"""Fail-closed gate for PR #30 isolated OSS adapters.

Verifies current lock blobs and retains historical evidence for removed locks.
No network, SDK import, model/API calls, writes, or actual vendor activation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA = "OSS_TOP10_ACTIVATION_GUARD_V1"
SOURCE_HEAD = "be5bbae7725369db97215c8e5888136ab6e4a68c"
SOURCE_RUN = 43299315660
BLOCKED = frozenset({"activepieces", "openhands", "crewai", "letta"})
CLEAN = frozenset({"langgraph", "mem0", "langfuse", "agent-framework", "openai-agents"})
EXPECTED_BLOCKED = {
    "activepieces": (9, "UNVERIFIED", "87349e98abe1390dcdd9dd3df1d04b211629ae12"),
    "openhands": (13, "REVIEW", "cdfe11e6d879b60470535b193a3ea09a2c0a7303"),
    "crewai": (5, "UNVERIFIED", "ab95572ef7a898a7177245889e74d6588713698f"),
    "letta": (4, "REVIEW", "df29d0c5cc702d673891ab1656e3e6ca0c1bd6f3"),
}
ALL = BLOCKED | CLEAN | {"flowise"}
NPM_PROJECTS = frozenset({"activepieces", "letta"})
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
    try:
        entries = list(locks_dir.iterdir())
    except OSError as error:
        raise SecurityBlock("LOCK_INVENTORY_UNAVAILABLE") from error
    if (locks_dir.is_symlink() or {path.name for path in entries} != {name + "-pip.txt" for name in CLEAN}
            or any(path.is_symlink() or not path.is_file() for path in entries)):
        raise SecurityBlock("UNAPPROVED_LOCK_INVENTORY")

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
        suffix = "-package-lock.json.gz.b64" if name in NPM_PROJECTS else "-pip.txt"
        if lock_name != name + suffix:
            raise SecurityBlock("LOCK_IDENTITY_INVALID:" + name)
        if (not isinstance(sha, str) or len(sha) != 40
                or any(c not in "0123456789abcdef" for c in sha)):
            raise SecurityBlock("EXPECTED_SHA_INVALID:" + name)
        count, license_state = row.get("known_advisories"), row.get("license_state")
        if type(count) is not int or count < 0:
            raise SecurityBlock("ADVISORY_COUNT_UNKNOWN:" + name)
        if license_state not in ("DECLARED_METADATA_ONLY", "REVIEW", "UNVERIFIED"):
            raise SecurityBlock("LICENSE_STATUS_UNKNOWN:" + name)
        if name in BLOCKED:
            if (count, license_state, sha) != EXPECTED_BLOCKED[name]:
                raise SecurityBlock("IMMUTABLE_AUDIT_RESULT_CHANGED:" + name)
            if not row.get("license_unverified_examples"):
                raise SecurityBlock("LICENSE_UNKNOWN_EVIDENCE_MISSING:" + name)
            if license_state == "REVIEW" and not row.get("license_review_packages"):
                raise SecurityBlock("LICENSE_REVIEW_EVIDENCE_MISSING:" + name)
            if (count < 1 or row.get("status") != "BLOCKED_VULNERABILITY"
                    or not isinstance(row.get("advisory_ids"), list)
                    or not row["advisory_ids"]):
                raise SecurityBlock("KNOWN_VULNERABILITY_UNBLOCK_ATTEMPT:" + name)
            status = "BLOCKED_VULNERABILITY"
            lock_evidence = {"archived_lock_git_blob_sha": sha}
        else:
            try:
                actual = git_blob_sha((locks_dir / lock_name).read_bytes())
            except OSError as error:
                raise SecurityBlock("LOCK_UNAVAILABLE:" + name) from error
            if actual != sha:
                raise SecurityBlock("LOCK_CHANGED_REAUDIT_REQUIRED:" + name)
            if (count != 0 or row.get("status") != "OFFLINE_ONLY"
                    or license_state != "DECLARED_METADATA_ONLY"):
                raise SecurityBlock("CLEAN_SDK_EVIDENCE_DRIFT:" + name)
            status = "OFFLINE_ONLY_NOT_APPROVED"
            lock_evidence = {"lock_git_blob_sha": actual}
        decisions[name] = {
            "status": status, "activation_allowed": False,
            "license": license_state, "known_advisories": count,
            **lock_evidence,
        }
    return {
        "schema": SCHEMA, "source_head": SOURCE_HEAD, "source_security_run": SOURCE_RUN,
        "projects": decisions, "blocked_vulnerable": sorted(BLOCKED),
        "runtime_activations": 0, "provider_calls": 0, "production_writes": 0,
    }


def status_snapshot() -> dict:
    return verify_evidence(load_evidence())


def offline_ci_install_allowed(project: str) -> bool:
    snapshot = status_snapshot()
    if project not in snapshot["projects"]:
        raise SecurityBlock("UNKNOWN_SDK_BLOCKED")
    return snapshot["projects"][project]["status"] == "OFFLINE_ONLY_NOT_APPROVED"


def current_audit_matrix() -> dict:
    projects = status_snapshot()["projects"]
    return {"id": [name for name, row in projects.items() if "lock_git_blob_sha" in row]}


def require_activation_allowed(project: str, *, action: str = "enable") -> None:
    """Explicit deny for ALL live SDK actions, even for advisory-clean candidates."""
    snapshot = status_snapshot()  # Fail closed if the evidence or lock drifts.
    if project not in snapshot["projects"]:
        raise SecurityBlock("UNKNOWN_SDK_BLOCKED")
    if action not in ("enable", "install", "start", "invoke", "deploy", "connect", "publish"):
        raise SecurityBlock("UNKNOWN_ACTION_BLOCKED")
    raise SecurityBlock("ACTIVATION_DENIED:" + project + ":" + snapshot["projects"][project]["status"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Report eligibility for an isolated SDK smoke test.")
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument("--offline-ci", metavar="PROJECT")
    command.add_argument("--audit-matrix", action="store_true")
    options = parser.parse_args()
    if options.audit_matrix:
        print(json.dumps(current_audit_matrix(), separators=(",", ":")))
    else:
        print("true" if offline_ci_install_allowed(options.offline_ci) else "false")
