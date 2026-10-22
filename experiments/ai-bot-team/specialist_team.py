"""Ten offline specialty checks for a ChatGPT in-chat workflow.

No outbound I/O, no provider models, no GitHub/Slack/Activepieces changes.
Every result is a deterministic suggestion/check, not a live task completion.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

ROLES = (
    "memory_recovery", "scheduled_audit", "auto_debug", "code_verification",
    "open_source_research", "automation_design", "cost_security", "github_management",
    "cross_model_review", "ai_optimization",
)
ALLOW_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"}
SECRET_PATTERNS = (r"sk-[A-Za-z0-9_-]{15,}", r"gh[pousr]_[A-Za-z0-9_]{20,}",
                   r"(?i)(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"]?\S{10,}")


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _list(v: Any, max_items: int = 30) -> list:
    if not isinstance(v, list) or len(v) > max_items:
        raise ValueError("expected a bounded list")
    return v


def run_role(name: str, data: dict[str, Any]) -> dict[str, Any]:
    if name not in ROLES or not isinstance(data, dict):
        raise ValueError("invalid role or input")
    if name == "memory_recovery":
        # Checks supplied snapshots only, not actual ChatGPT saved memory.
        snapshots = _list(data.get("snapshots", []))
        hashes = [_hash(x["content"]) for x in snapshots if isinstance(x, dict)
                  and isinstance(x.get("content"), str) and x.get("content")]
        result = {"snapshots_read": len(hashes), "content_sha256": hashes,
                  "restored_chatgpt_memory": False}
    elif name == "scheduled_audit":
        record = data.get("record", {})
        if not isinstance(record, dict):
            raise ValueError("record must be an object")
        # Never bless a fabricated or self-reported platform execution ID.
        official = record.get("official_run_id")
        allowed = (isinstance(official, str) and official.strip() and
                   record.get("platform_supplied_id") is True and
                   record.get("same_run_raw_logs_verified") is True)
        result = {"source_claimed_official_id": bool(official), "raw_evidence_fields_present": bool(allowed),
                  "independently_proven_by_offline_check": False,
                  "verdict": "NEEDS_PLATFORM_INDEPENDENT_VERIFICATION"}
    elif name == "auto_debug":
        error = str(data.get("error", ""))[:4000].casefold()
        mapping = (("modulenotfounderror", "check_dependency_in_sandbox"),
                   ("syntaxerror", "parse_and_fix_syntax_in_sandbox"),
                   ("permission denied", "check_permissions_without_bypass"),
                   ("timeout", "inspect_existing_timeout_logs"),
                   ("assertionerror", "reproduce_specific_failing_test"))
        diagnosis = next((v for k, v in mapping if k in error), "collect_reproducible_error_evidence")
        result = {"diagnostic_action": diagnosis, "code_changed": False}
    elif name == "code_verification":
        code = data.get("python_source", "")
        if not isinstance(code, str) or len(code) > 20000:
            raise ValueError("invalid source")
        try:
            ast.parse(code)
            parses = True
        except SyntaxError:
            parses = False
        result = {"python_syntax_ok": parses, "source_sha256": _hash(code),
                  "executed_code": False, "test_suite_executed": False}
    elif name == "open_source_research":
        projects = _list(data.get("projects", []))
        result = {"metadata_entries": len(projects), "candidate_names": [p["name"] for p in projects
                  if isinstance(p, dict) and isinstance(p.get("name"), str)
                  and p.get("license") in ALLOW_LICENSES][:20],
                  "licenses_checked_against_live_upstream": False}
    elif name == "automation_design":
        steps = _list(data.get("steps", []))
        ids = [s.get("id") for s in steps if isinstance(s, dict)]
        unique = len(ids) == len(steps) and all(isinstance(s, str) and s for s in ids)
        edges = [s.get("after") for s in steps if isinstance(s, dict)]
        valid_edges = unique and all(x is None or x in ids for x in edges)
        graph = {s["id"]: s.get("after") for s in steps if isinstance(s, dict) and "id" in s}
        def has_cycle() -> bool:
            for node in graph:
                path = set()
                while node is not None and node in graph:
                    if node in path:
                        return True
                    path.add(node)
                    node = graph[node]
            return False
        acyclic = bool(valid_edges) and not has_cycle()
        result = {"plan_valid": acyclic and bool(steps), "steps": len(steps),
                  "published_or_modified_flow": False}
    elif name == "cost_security":
        sample = str(data.get("sample", ""))[:10000]
        has_secrets = any(re.search(p, sample) for p in SECRET_PATTERNS)
        result = {"possible_secret_detected": has_secrets,
                  "provider_execution_requested": data.get("provider_call", False) is True,
                  "provider_execution_allowed": False, "credentials_exposed": False}
    elif name == "github_management":
        repo = str(data.get("repository", ""))
        ref = str(data.get("ref", ""))
        result = {"valid_repo_format": bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)),
                  "valid_ref_format": bool(re.fullmatch(r"[A-Za-z0-9_./-]+", ref)) and ".." not in ref,
                  "github_network_calls": 0, "commits_written": 0}
    elif name == "cross_model_review":
        reviews = _list(data.get("reviews", []))
        # A supplied string is NOT independent provider model execution.
        claims = [x.get("finding") for x in reviews if isinstance(x, dict)
                  and x.get("finding") in ("agree", "disagree", "uncertain")]
        result = {"review_records": len(claims), "conflict_in_supplied_reviews":
                  "agree" in claims and "disagree" in claims,
                  "independent_model_calls": 0, "provider_responses_proven": False}
    else:  # ai_optimization
        tasks = _list(data.get("tasks", []), 100)
        items = [s.strip() for s in tasks if isinstance(s, str) and s.strip()]
        unique = list(dict.fromkeys(items))
        result = {"input_tasks": len(items), "unique_tasks": len(unique),
                  "duplicate_tasks_omitted": len(items) - len(unique),
                  "measured_token_saving": False, "model_performance_measured": False}
    return {"role": name, "mode": "OFFLINE_REFERENCE_ONLY", "result": result,
            "external_model_calls": 0, "external_writes": 0}


DEMO = {
    "memory_recovery": {"snapshots": [{"content": "AI project, memory index source"}]},
    "scheduled_audit": {"record": {"official_run_id": "unverified-self-id"}},
    "auto_debug": {"error": "ModuleNotFoundError: example"},
    "code_verification": {"python_source": "x = 1\n"},
    "open_source_research": {"projects": [{"name": "illustrative-lib", "license": "MIT"}]},
    "automation_design": {"steps": [{"id": "research", "after": None},
                                    {"id": "verify", "after": "research"}]},
    "cost_security": {"sample": "test mode", "provider_call": False},
    "github_management": {"repository": "example/repository", "ref": "test-sandbox"},
    "cross_model_review": {"reviews": [{"finding": "agree"}, {"finding": "disagree"}]},
    "ai_optimization": {"tasks": ["run tests", "run tests", "read source"]},
}


def run_all(sample: dict[str, dict] | None = None) -> dict[str, Any]:
    inputs = DEMO if sample is None else sample
    if set(inputs) != set(ROLES):
        raise ValueError("exactly ten role payloads required")
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {name: pool.submit(run_role, name, inputs[name]) for name in ROLES}
        outcomes = [futures[name].result() for name in ROLES]
    return {"mode": "OFFLINE_REFERENCE_ONLY", "role_count": len(outcomes),
            "roles": outcomes, "external_model_calls": 0, "external_writes": 0,
            "chatgpt_unattended_execution_verified": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=(*ROLES, "all"), default="all")
    args = parser.parse_args()
    try:
        result = run_all() if args.role == "all" else run_role(args.role, DEMO[args.role])
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    except (ValueError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
