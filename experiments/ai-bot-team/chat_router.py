"""Deterministic opt-in chat routing demo. Does not read ChatGPT messages or run in background."""
from __future__ import annotations

import argparse
import json
import re

from bot_team import collaborate, load_sources

PROJECT_TRIGGERS = (
    "ai 프로젝트", "ai project", "3봇", "세 봇", "협업 봇", "봇 협업", "bot team",
    "github 검증", "github 수정", "github 테스트", "activepieces 분석",
    "activepieces 검증", "자동화 구축", "코드 테스트", "코드 수정", "오류 수정",
    "기억 복원", "원격 테스트", "무료 ai 연결", "ai 봇", "ai bot",
)


def route_task(task: str) -> dict[str, object]:
    if not isinstance(task, str) or not task.strip() or len(task) > 2000:
        raise ValueError("task must contain 1-2000 characters")
    normalized = re.sub(r"\s+", " ", task.casefold().strip())
    matches = [trigger for trigger in PROJECT_TRIGGERS if trigger in normalized]
    return {
        "route": "THREE_ROLE_WORKFLOW" if matches else "DIRECT_CHAT",
        "reason": "explicit AI project/task keyword" if matches else "no explicit project trigger",
        "matched_triggers": matches,
        "automatic_in_any_chat": False,
        "requires_chat_plugin_or_manual_invoke": True,
    }


def demo(task: str, sources: list[dict]) -> dict:
    routing = route_task(task)
    result: dict = {"routing": routing, "source": "manual_python_cli_not_chat_hook"}
    if routing["route"] == "THREE_ROLE_WORKFLOW":
        result["team_demo"] = collaborate(task, sources)
    else:
        result["team_demo"] = None
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Chat routing demo (not automatically installed into ChatGPT)")
    parser.add_argument("--task", required=True)
    parser.add_argument("--sources", required=True)
    args = parser.parse_args()
    try:
        result = demo(args.task, load_sources(args.sources))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["team_demo"] and result["team_demo"]["verifier"]["status"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
