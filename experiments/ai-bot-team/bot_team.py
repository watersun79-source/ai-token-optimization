"""Offline three-bot collaboration prototype; no network, provider API, or writes.

ResearchBot -> BuilderBot -> VerifierBot. This is a deterministic proof of
orchestration, NOT a live LLM agent or a substitute for source verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ALLOWED_ACTIONS = (
    "review_supplied_references",
    "draft_isolated_proposal",
    "run_local_tests",
    "request_review_before_integration",
)
ALLOWED_HOSTS = {"github.com", "docs.python.org"}
MAX_EVIDENCE_BYTES = 32_768
MAX_SOURCES = 25


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_url(url: Any) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return (parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS
            and not parsed.username and not parsed.password and not parsed.port
            and not parsed.fragment and len(url) <= 500)


def load_sources(path: str | Path) -> list[dict[str, Any]]:
    file = Path(path)
    if file.stat().st_size > MAX_EVIDENCE_BYTES:
        raise ValueError("evidence file too large")
    payload = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) > MAX_SOURCES:
        raise ValueError("expected list of <=25 references")
    return payload


class ResearchBot:
    """Review supplied references; does NOT browse or validate their claims."""

    def run(self, task: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
        if not isinstance(task, str) or not task.strip() or len(task) > 2000:
            raise ValueError("task must contain 1-2000 characters")
        if not isinstance(sources, list) or len(sources) > MAX_SOURCES:
            raise ValueError("invalid source list")
        tokens = {s.casefold() for s in re.findall(r"[\w가-힣]{2,}", task)}
        accepted: list[dict[str, Any]] = []
        seen: set[str] = set()
        for source in sources:
            if not isinstance(source, dict):
                continue
            title, url, tags = source.get("title"), source.get("url"), source.get("tags")
            if not isinstance(title, str) or not 1 <= len(title) <= 150:
                continue
            if not _safe_url(url) or url in seen:
                continue
            if not isinstance(tags, list) or not all(isinstance(t, str) and 1 <= len(t) <= 40 for t in tags):
                continue
            seen.add(url)
            matched = sorted(tokens & {t.casefold() for t in tags})
            accepted.append({"title": title, "url": url, "matched_tags": matched})
        accepted.sort(key=lambda x: (-len(x["matched_tags"]), x["url"]))
        return {"status": "reviewed_supplied_metadata_only", "sources": accepted,
                "claims_independently_verified": False}


class BuilderBot:
    """Produce an inspectable plan, never code execution or a live mutation."""

    def run(self, task: str, research: dict[str, Any]) -> dict[str, Any]:
        return {"task": task, "target": "isolated_sandbox_only",
                "actions": list(ALLOWED_ACTIONS),
                "reference_urls": [x["url"] for x in research["sources"]],
                "real_changes_applied": False, "provider_calls": 0}


class VerifierBot:
    """Check structural policy, provenance and the no-side-effects contract."""

    def run(self, research: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
        urls = [x["url"] for x in research.get("sources", [])]
        checks = {
            "safe_reference_urls": bool(urls) and all(_safe_url(u) for u in urls),
            "source_lineage": proposal.get("reference_urls") == urls,
            "approved_actions_only": proposal.get("actions") == list(ALLOWED_ACTIONS),
            "sandbox_only": proposal.get("target") == "isolated_sandbox_only",
            "no_external_provider_calls": proposal.get("provider_calls") == 0,
            "no_live_mutation": proposal.get("real_changes_applied") is False,
            "source_claims_not_promoted": research.get("claims_independently_verified") is False,
        }
        return {"status": "PASS" if all(checks.values()) else "BLOCKED",
                "checks": checks, "scope": "offline_policy_checks_only"}


def collaborate(task: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    research = ResearchBot().run(task, sources)
    proposal = BuilderBot().run(task, research)
    verification = VerifierBot().run(research, proposal)
    report = {"execution_mode": "offline_deterministic_demo",
              "live_llm_agents": 0, "provider_api_calls": 0,
              "production_changes": 0, "research": research,
              "builder": proposal, "verifier": verification}
    report["audit_sha256"] = _json_hash(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Three-role safe offline bot collaboration")
    parser.add_argument("--task", required=True)
    parser.add_argument("--sources", required=True, help="Local JSON references; no network")
    args = parser.parse_args()
    try:
        result = collaborate(args.task, load_sources(args.sources))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verifier"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
