"""R16 offline bot-role runner: real deterministic checks, not three LLM calls.

Design: Microsoft Agent Framework's sequential/handoff roles; CrewAI role separation.
Calls only the existing local audit_v2.check; does not access networks, secrets,
production Activepieces, the ChatGPT scheduler, or remote model APIs.
Source input is not independently authenticated. Fails closed by construction.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from audit_v2 import AUTOMATION_ID, check

MAX_INPUT_BYTES = 65536
ALLOWED_NEXT = {
    "READ_OFFICIAL_SCHEDULED_RUN",
    "READ_SAME_RUN_APP_CALLS",
    "COMPARE_INDEPENDENT_GITHUB_SLACK_READBACK",
}


class ResearchBot:
    """Summarize *supplied* source metadata; cannot authenticate an external source."""

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        refs = payload.get("references", [])
        if not isinstance(refs, list) or len(refs) > 20:
            raise ValueError("references must be a list of up to 20 entries")
        accepted = []
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            name = ref.get("name")
            url = ref.get("url")
            if (isinstance(name, str) and 1 <= len(name) <= 100
                    and isinstance(url, str) and len(url) <= 500
                    and url.startswith("https://github.com/")
                    and not any(c in url for c in ("@", "#", "?", "\n", "\r"))):
                accepted.append({"name": name, "url": url})
        return {"role": "ResearchBot", "references_reviewed": accepted,
                "source_authenticity": "NOT_VERIFIED_BY_OFFLINE_BOT"}


class BuilderBot:
    """Select one read-only next action, never mutate a real system."""

    def run(self, audit: dict[str, Any]) -> dict[str, Any]:
        reason = str(audit.get("reason", ""))
        if "공식 개별 회차" in reason or not audit.get("native_run_id"):
            action = "READ_OFFICIAL_SCHEDULED_RUN"
        elif audit.get("missing"):
            action = "READ_SAME_RUN_APP_CALLS"
        else:
            action = "COMPARE_INDEPENDENT_GITHUB_SLACK_READBACK"
        return {"role": "BuilderBot", "next_action": action,
                "mutations_performed": 0, "provider_calls": 0,
                "scope": "READ_ONLY_PROPOSAL"}


class VerifierBot:
    """Guard against laundering synthetic/manual CI data into unattended success."""

    def run(self, research: dict[str, Any], builder: dict[str, Any],
            audit: dict[str, Any]) -> dict[str, Any]:
        safe = (
            research.get("source_authenticity") == "NOT_VERIFIED_BY_OFFLINE_BOT"
            and builder.get("next_action") in ALLOWED_NEXT
            and builder.get("mutations_performed") == 0
            and builder.get("provider_calls") == 0
            and audit.get("official_success_verified") is False
        )
        return {"role": "VerifierBot", "policy_checks": "PASS" if safe else "BLOCK",
                "native_run_authenticated": False,
                "official_success_verified": False,
                "scope": "OFFLINE_FORMAT_AND_POLICY_ONLY"}


def collaborate(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("input must be a JSON object")
    task = payload.get("task")
    if not isinstance(task, str) or not task.strip() or len(task) > 2000:
        raise ValueError("task must contain 1-2000 characters")
    research = ResearchBot().run(payload)
    # Explicitly pass only expected fields; injected success flags are ignored.
    evidence = payload.get("evidence", {})
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a JSON object")
    audit = check({
        "schedule": evidence.get("schedule"),
        "target_slot": evidence.get("target_slot"),
        "native_run": evidence.get("native_run"),
        "tool_calls": evidence.get("tool_calls"),
    })
    builder = BuilderBot().run(audit)
    verifier = VerifierBot().run(research, builder, audit)
    return {
        "task": task, "pipeline": ["ResearchBot", "BuilderBot", "VerifierBot"],
        "mode": "OFFLINE_DETERMINISTIC", "live_llm_bots": 0,
        "existing_automation_id": AUTOMATION_ID,
        "production_mutations": 0, "provider_calls": 0,
        "official_success_verified": False,
        "research": research, "audit": audit,
        "builder": builder, "verifier": verifier,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline R16 research/build/verify role gate")
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("input file too large")
        result = collaborate(json.loads(args.input.read_text(encoding="utf-8")))
    except (OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Never emit success exit 0 for an unauthenticated scheduled run.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
