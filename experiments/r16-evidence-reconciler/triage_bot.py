"""R16 provider-free audit BOT: deterministic Research -> Verify -> Next Goal.

Uses the existing fail-closed audit_v2 checker and never claims to authenticate
ChatGPT native task runs. Inspired by public agent workflow/checkpoint patterns,
not by copying a third-party agent runtime. No SDKs, network, credentials,
background tasks, or changes to reservations, GitHub, or Slack.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_v2 import AUTOMATION_ID, REQUIRED, check

MAX_INPUT_BYTES = 262144
ROLES = ("ResearchBot", "VerifierBot", "NextGoalBot")


def triage(payload: object) -> dict:
    """Return a safe action plan, not a success credential.

    Any origin or run ID in payload can be forged. Only platform-authenticated
    original run data (which this offline process cannot access) could prove
    actual unattended work.
    """
    source = payload if isinstance(payload, dict) else {}
    task = source.get("schedule")
    task = task if isinstance(task, dict) else {}
    native = source.get("native_run")
    native_present = isinstance(native, dict) and bool(native)
    verdict = check(payload)
    valid_task = task.get("id") == AUTOMATION_ID
    active = task.get("is_enabled") is True if valid_task else False
    missing = [key for key in REQUIRED if key in verdict.get("missing", [])]
    format_pass = verdict.get("status", "").startswith("형식 통과")
    if not valid_task:
        next_goal = "보호된 기존 예약 ID를 공식 예약 목록과 읽기 전용으로 대조"
    elif not active:
        next_goal = "기존 예약 활성 상태를 플랫폼 원본에서 점검; 임의 변경 금지"
    elif not native_present:
        next_goal = "ChatGPT 예약 Previous runs에서 개별 run ID·종료 상태 원본 확보"
    elif missing:
        next_goal = "동일 공식 회차의 GitHub·Slack 원본 tool-call 기록을 대조"
    else:
        next_goal = "원본 제공자·플랫폼에서 개별 회차와 도구 호출의 진위를 독립 인증"
    return {
        "automation_id": AUTOMATION_ID,
        "bot_mode": "OFFLINE_RULE_BASED_NO_LLM",
        "read_only": True,
        "external_calls": 0,
        "authenticated_unattended_success": False,
        "outcome": "미검증",
        "format_check": "PASS_NOT_AUTHENTICATED" if format_pass else "INCOMPLETE",
        "required_targets": list(REQUIRED),
        "missing_targets": missing,
        "roles": [
            {"name": ROLES[0], "result": "예약 메타·입력 존재 확인" if valid_task else "예약 ID 미확인"},
            {"name": ROLES[1], "result": "형식 일치·진위 미확인" if format_pass else "원본 증거 미충족"},
            {"name": ROLES[2], "result": "안전한 다음 목표 지정"},
        ],
        "next_goal": next_goal,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="R16 offline fail-closed agent triage")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        # Do not load unlimited untrusted inputs, never echo secrets/errors.
        with args.input.open("rb") as fh:
            buf = fh.read(MAX_INPUT_BYTES + 1)
        if len(buf) > MAX_INPUT_BYTES:
            raise ValueError("Too large")
        payload = json.loads(buf.decode("utf-8"))
        result = triage(payload)
    except (OSError, UnicodeError, ValueError, RecursionError):
        result = triage(None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 3 if result["format_check"] == "PASS_NOT_AUTHENTICATED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
