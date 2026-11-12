# OSS TOP 10 — 안전한 도입 판정 게이트 (2026-11-12 KST)

이 브랜치는 10개 공식 GitHub 프로젝트의 **검토 기록과 오프라인 fail-closed 게이트**를 적용한 거야.
**실제 10개 도구의 설치·연동·AI 호출·배포는 실행하지 않았다.**

공식 main 기준 SHA: `923c281f82023cc6b49f3844bad17f508f1ab203`.
기존 GitHub main/PR, ChatGPT 예약(6ae8db67fef081919af59fecbf162552), Activepieces 운영, D1 NO_WRITE, Site, 비밀키 보호.

| Upstream | License | Status |
|---|---|---|
| langchain-ai/langgraph | MIT | 설계 후보 |
| activepieces/activepieces | MIT core / commercial EE | 기존 참조만 |
| OpenHands/OpenHands | MIT community | 격리 후보 |
| mem0ai/mem0 | Apache-2.0 | 설계 후보 |
| langfuse/langfuse | MIT core / EE separate | 설계 후보 |
| microsoft/agent-framework | MIT | 대체 후보 |
| crewAIInc/crewAI | MIT | 대체 후보 |
| letta-ai/letta | Apache-2.0 | 대체 후보 |
| openai/openai-agents-python | MIT | 대체 후보 |
| FlowiseAI/Flowise | Apache-2.0 core / commercial EE | Archived/EOL 차단 |

검토 결과: primary 3 + 기존 참조 1 + sandbox 1 + 대체 4 + EOL 차단 1.
프레임워크 중복(오케스트레이터·기억 저장소), 유료 제공자·상용 EE, 운영 쓰기·설치와 아카이브 도입을 차단해.

실행:
```sh
python3 experiments/oss-top10-safe-adoption/safe_adoption.py
python3 -m unittest discover -s tests -p test_oss_top10_adoption.py -v
```

근거: https://www.activepieces.com/docs/about/license
 · https://github.com/langfuse/langfuse/blob/main/LICENSE
 · https://flowiseai.com/sunset
 · https://microsoft.github.io/autogen/dev/

실제 통합은 개별 후보의 격리 테스트, 계정별 무료 한도·권한·라이선스 재확인 후 별도 승인 필요.
