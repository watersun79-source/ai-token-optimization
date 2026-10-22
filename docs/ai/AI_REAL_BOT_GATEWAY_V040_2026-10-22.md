# 실제 Python 봇 자동 실행 게이트웨이 v0.4 — 2026-10-22 KST

## 사용자 요구
"아니 나는 채팅 하면 자동으로 알아서 붓 실행을 말하는 거야. 다른 사람이 만든것 있으면 찾아서 적용해줘. 아니면 파이썬 등등 맞춰서 만들어."

기존 스킬-only `ai-chat-bot-team`은 단지 ChatGPT 내 역할 지침이었으므로, 메시지를 받으면 **실제 Python worker 함수가 실행되는 HTTP 및 MCP 도구 서버 소스**를 추가하였다. 사용자의 **공식 ChatGPT iOS/웹 입력창 전체 메시지 자동 후킹은 미구현**이며 플랫폼 자동 선택과 동일시하지 않는다.

## 참고한 검증된 외부 구현
- [LangGraph Router 공식 패턴](https://github.com/langchain-ai/docs/blob/main/src/oss/langchain/multi-agent/router.mdx) — classify → specialized workers parallel → synthesize, source/license 확인 후 외부 라이브러리 설치 없이 경량 규칙 기반 구조로 자체 구현.
- [CrewAI](https://github.com/crewAIInc/crewAI) — Python 역할별 task/flow 디자인 참고. 크루 대형 의존성 설치, 공급자 생성 API 호출 없음.
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) — 운영 멀티에이전트 후속 후보. 과거 AutoGen은 maintenance mode이므로 신규 채택 보류.
- [공식 MCP Python SDK v1](https://py.sdk.modelcontextprotocol.io/v1/) — FastMCP streamable-http 명세를 이용하는 소스 작성, `mcp>=1.28,<2` 명시.
- [OpenAI ChatGPT 플러그인 공식 도움말](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt) 및 [커스텀 MCP 연결](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt) — ChatGPT는 설치된 플러그인을 관련 요청에서 자동 선택할 수 있으나 전역 메시지 가로채기/항상 호출 보장 없음. 사용자 계정/플랫폼에 따라 원격 MCP 서버 실제 연결, 인증, 사용자 추가 조치 필요. iOS에서 임의 로컬 stdio MCP 자동 연결 불가.

## 실제 구현
기존 개인 플러그인 `plugins_6ad9d7b745448191bb087af817f02f68`을 **v0.4.0**으로 제자리 갱신.
- URL https://chatgpt.com/plugins/plugins_6ad9d7b745448191bb087af817f02f68
- 저장·재조회된 릴리스 `pluginrel_6ad9e7e818dc8191b105daa1d2ffab74`.
- 플러그인 구성 파일 40개, 기존 10개 전문 스킬과 총괄 스킬 및 모든 기존 샘플 유지.
- `skills/ai-chat-collaboration/runtime/real_gateway.py`: `run_message(message, code, network)`가 기존 `auto_dispatch.py` 분류 후 최대 세 전문 워커의 **진짜 Python 함수**를 `ThreadPoolExecutor`로 호출하고 결과/증거를 결합. 10개 역할 중 구현된 실제 한정 능력: 제출된 Python 코드 AST 파싱(사용자 코드 실행 금지), 비밀 패턴 검사(값 출력 금지), 중복 텍스트 측정, 플로우 계획 구성, 옵션 켰을 때만 허용된 GitHub GET의 기억 문서/CI/레포/검증된 OSS 프로젝트 메타데이터 읽기. 공식 예약 run ID와 실제 독립 Gemini/Claude 모델은 지원되지 않는다고 정확히 반환.
- `--serve` 실행하면 `127.0.0.1:8765` 브라우저 채팅 / `POST /api/chat` / `GET /health` 제공. **이 별도 브라우저의 메시지는 입력할 때마다 Python 워커 실제 실행**, 공식 ChatGPT 앱이 아님. localhost만 수신, 입력 한도·무캐시·읽기 전용 기본·공급자 생성 호출 0.
- `mcp_server.py`: FastMCP의 실제 `delegate_message` 도구 등록 코드. `requirements-mcp.txt`에는 `mcp>=1.28,<2` 버전 범위 명시. 이 환경은 pip DNS 연결 실패로 MCP SDK 설치·실제 Streamable HTTP 핸드셰이크 테스트 **차단**. 목(mock) FastMCP 어댑터 등록과 함수 호출만 테스트; 실제 외부 ChatGPT 앱에 MCP 도구 연결/자동 호출은 **미검증**.
- Python 코드/사용법/테스트 제공: GitHub 격리 브랜치 [ai/real-bot-gateway-2026-10-22](https://github.com/watersun79-source/ai-token-optimization/tree/ai/real-bot-gateway-2026-10-22/experiments/ai-bot-team), 테스트/배포용 파일 `real_gateway.py`, `mcp_server.py`, `requirements-mcp.txt`, `tests/test_real_gateway.py`, `tests/test_mcp_adapter.py`, `README-REAL-GATEWAY.md`.

## 검증 근거
- 로컬 `python -m unittest discover -s tests -v` **92/92 OK**, 코드 실행 샘플 `에러 고쳐` + 문법오류 입력 → AST 탐지 **DONE**, `예약 AI 로그 확인하고 오류 수정` → 예약은 UNVERIFIED/코드 AST는 DONE → 통합 PARTIAL.
- 독립 GitHub Actions [run 39764904322](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39764904322) **completed/success**, job `119777820918`, 실제 원본 job log `Ran 92 tests in 0.770s` / `OK`, 실 Python 워커 CLI 호출·예약 출처 미검증 검사 스텝 각각 success.
- 플러그인 `get_plugin_files`와 GitHub `fetch_file` 원본 전체 일치: `real_gateway.py` GitHub blob SHA `e398ec49b11ad5432a9248a817fca3142fde56fd`, `mcp_server.py` SHA `4a90bf3c4aee6e990859f1d09de19824efa3c142`, HTTP 테스트 SHA `8f1a22e312c25badedce191fdf76a63166747643`.
- 사용자에게 전달할 프로그램 ZIP SHA256 `4c751f76b8ad9be82c6d688d1691fdf3b5364e66fee20146ade98e5edca082a7` (대화 세션 /mnt/data/ai-real-bot-gateway.zip). 플러그인 patch ZIP SHA256 `394c7e2794bf727bec25bea88bde8b9d0b48e3cbf661f7064c5a383bd359854e`.
- GitHub main·운영 Activepieces 플로우/연결, 기존 한국시간 정각 R15 예약 ID `6acb017062a08191a4136238b78b313a` 수정 없음. 유료 API/모델 생성 호출 0, 외부 과금 0.

## 남은 문제: 사용자의 진짜 최종 목표
네가 **기본 ChatGPT 앱**에서 메시지를 보내면 자동으로 외부 Python 프로그램을 호출하도록 하려면 인증된 원격 HTTPS MCP 서비스(또는 지원되는 개인 Site/앱 호스팅)와 ChatGPT 연결이 필요. 앱 선택과 실제 도구 호출은 모델/제품/계정 권한에 달려, 매번 자동 실행이 보장되지 않는다. 이 요청에서는 무료 호스팅/사용자 인증이 확보되지 않았으므로 원격 서버를 게시하지 않고 **미구현**으로 남김. SDK 설치도 네트워크 DNS 연결 실패로 보류. 원본 GitHub 파일·작업 로그·로컬 실행기 실제 동작은 검증 완료.

최초 목적 및 우선순위: 일반 채팅은 직접 답변, 프로젝트 메시지는 실제 이용 가능한 봇/연결 도구부터 실행하고 검증된 것만 완료 표시. 마찬가지로 R15 예약의 무인 공식 회차 로그 증명은 미검증 유지.
