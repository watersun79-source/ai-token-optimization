"""Offline deterministic chat intent triage. NOT a ChatGPT callback or API bot launcher."""
from __future__ import annotations

import argparse
import json
import re
from typing import Any

# The LLM-facing skill uses natural-language intent and context; this offline
# module provides testable examples, not a semantic replacement for the LLM.
ROLE_TRIGGERS: dict[str, tuple[str, ...]] = {
    "ai-memory-recovery": ("기억 복원", "이전 ai 작업", "지난 ai 작업", "인계 문서", "기억 유지", "memory index"),
    "ai-scheduled-audit": ("예약 ai", "예약 실행", "무인 실행", "예약 로그", "공식 회차", "예약 감사", "scheduled run"),
    "ai-auto-debug": ("오류 수정", "오류 고쳐", "에러 고쳐", "버그 수정", "실패 원인", "debug", "traceback", "예외 발생"),
    "ai-code-verification": ("ci 확인", "ci 검증", "테스트 결과", "sha 검증", "회귀 테스트", "코드 검증", "workflow run"),
    "ai-open-source-research": ("오픈소스", "공식 문서", "github에서 찾아", "논문 조사", "무료 대안", "open source"),
    "ai-automation-design": ("자동화 구축", "자동화 설계", "워크플로", "activepieces", "웹훅", "봇 자동 선택", "자동 협업", "자동으로 알아서", "webhook"),
    "ai-cost-security": ("api 키", "비밀키", "무료 한도", "과금", "비용 보안", "유료 api", "결제 방지", "credit limit"),
    "ai-github-management": ("브랜치", "풀 리퀘스트", "pull request", "pr 생성", "깃허브 이슈", "github issue"),
    "ai-cross-model-review": ("gemini claude", "gemini와 claude", "교차 검토", "모델끼리 비교", "독립 검토"),
    "ai-optimization": ("압축 실행", "중복 제거", "문장 압축", "최적화 실행", "토큰 최적화", "성능 최적화", "속도 개선", "프롬프트 최적화", "반복 줄여", "품질 개선", "latency"),
}
DIRECT_CHAT_PREFIXES = ("안녕", "고마워", "오늘 날씨", "내일 날씨", "번역해", "음식 추천", "생일 축하")
PROJECT_CONTEXT = ("ai 프로젝트", "ai project", "3봇", "ai bot", "ai 봇", "bot team")
SENSITIVE_ACTIONS = ("삭제", "결제", "유료", "main 병합", "운영 변경", "프로덕션", "api 키")


def dispatch(message: str, max_roles: int = 3) -> dict[str, Any]:
    if not isinstance(message, str) or not message.strip() or len(message) > 4000:
        raise ValueError("message must have 1-4000 characters")
    if not isinstance(max_roles, int) or isinstance(max_roles, bool) or not 1 <= max_roles <= 10:
        raise ValueError("max_roles must be an integer in 1..10")
    normalized = re.sub(r"\s+", " ", message.casefold()).strip()
    direct = normalized.startswith(DIRECT_CHAT_PREFIXES)
    matches = {role: [term for term in terms if term in normalized] for role, terms in ROLE_TRIGGERS.items()}
    candidates = sorted((role for role, hits in matches.items() if hits and not direct),
                        key=lambda role: (-len(matches[role]), list(ROLE_TRIGGERS).index(role)))
    generic_project = any(x in normalized for x in PROJECT_CONTEXT)
    route = "SPECIALISTS" if candidates else "THREE_ROLE_WORKFLOW" if generic_project and not direct else "DIRECT_CHAT"
    return {
        "route": route,
        "roles": candidates[:max_roles],
        "matched_terms": {role: matches[role] for role in candidates[:max_roles]},
        "requires_action_permission_review": any(term in normalized for term in SENSITIVE_ACTIONS),
        "external_provider_api_calls": 0,
        "production_changes": 0,
        "chatgpt_global_auto_hook_installed": False,
        "chatgpt_skill_auto_invocation_verified": False,
        "provenance": "offline_keyword_heuristic_no_live_chat_integration",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline bot-selection example; no real ChatGPT hook")
    parser.add_argument("--message", required=True)
    parser.add_argument("--max-roles", type=int, default=3)
    args = parser.parse_args()
    try:
        out = dispatch(args.message, args.max_roles)
    except ValueError as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
