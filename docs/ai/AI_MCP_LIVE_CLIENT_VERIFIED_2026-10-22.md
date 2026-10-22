# AI 봇 MCP 실제 프로토콜 시험 및 플러그인 v0.4.1 (2026-10-22)

## 목표와 실행 증거
사용자가 요청한 '평소 ChatGPT 채팅에서 필요 봇을 알아서 **실행**'하기 위한 기반으로, 기존 v0.4.0의 Python MCP 서버 `mcp_server.py`에 공식 MCP Python SDK v1 클라이언트를 실제 접속시킨 통신 시험을 신규 구현했다. 독립 ChatGPT 모바일 메시지 전역 후킹은 구현하지 않았으며, 테스트하는 동안 모의 ChatGPT 앱 호출/성공을 주장하지 않는다.

### 원격 CI 실제 통신 성공
- 격리 브랜치 `ai/mcp-live-handshake-2026-10-22`, main/운영 시스템 변경 없음.
- 실제 GitHub Actions **run [39767511489](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39767511489)** completed/success, head `70e96a7d71bd138e2bed68d759c76680c54cadb8`, job `119786518687`.
- GitHub Actions 원본에서 공식 `mcp>=1.28,<2` 패키지를 설치한 뒤 실제 HTTP `http://127.0.0.1:8000/mcp` 서버 기동, 공식 ClientSession을 통해 `initialize`→`tools/list`→`tools/call(delegate_message)` 수행 성공:
  `{"mcp_live_transport":"PASS","server":"AI Real Bot Gateway","tool":"delegate_message","worker":"ai-auto-debug","worker_status":"DONE","python_syntax_valid":false,"external_llm_calls":0,"production_writes":0,"connected_to_chatgpt":false}`
- 새 검증 스크립트 `experiments/ai-bot-team/verify_live_mcp.py`, Git blob SHA `4f6e895ebbaf7a082b38276b52603986ea8bcb18`.
- 같은 GitHub CI에서 변경 영향 회귀 테스트 **92/92 OK**. 이전 CI `39767173879`에서도 비슷한 스크립트 초안 MCP 연결 PASS 및 92/92; **현재 소스 최종 증거는 39767511489**.

### 기존 플러그인 소스에 재적용
- 개인 플러그인 URL https://chatgpt.com/plugins/plugins_6ad9d7b745448191bb087af817f02f68 .
- ID `plugins_6ad9d7b745448191bb087af817f02f68`, 기존 스킬-only 플러그인의 v0.4.0 → **v0.4.1** 제자리 갱신, release `pluginrel_6ad9ece809608191a2fcbe6f852e0d3c`.
- 읽기 재조회: 총 **41개 파일**, 기존 총괄 1+전문 10 = 스킬 **11개**, 기존 `real_gateway.py` `mcp_server.py` 유지, 실제 검사 스크립트 `runtime/verify_live_mcp.py` 추가. 원격 브랜치 원본 `verify_live_mcp.py`과 플러그인 파일 **완전히 동일**한지 양쪽 fetch/read로 독립 확인.
- README에 실제 실행/제약 명시. ZIP patch `/mnt/data/ai-bot-mcp-live-v0.4.1-patch.zip` SHA256 `95b07ee8d8d78783d47abf68cfae23e5b0e61cae2166d8be0d6d489d7add0f7c`.
- 기존 프로젝트 실행기 `/mnt/data/ai-real-bot-gateway.zip`는 이전 릴리스 v0.4 개발 ZIP으로 별도 보존. 새로운 v0.4.1 테스트 스크립트는 GitHub와 플러그인에 있음.

## 실제 ChatGPT 연결 한계 및 안전 기준
- [OpenAI 플러그인 도움말](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt): 설치된 관련 플러그인의 자동 선택은 *가능*하나 매 사용자 메시지에서 강제 실행/전역 전달을 보장하지 않는다. 단순 SKILL에 Python 코드를 포함해도 iPhone ChatGPT에서 프로세스가 자동 시작되지는 않는다.
- [OpenAI Sites 호스팅](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt): Sites 기반 MCP App 플러그인 가능하나 이 세션에는 Sites용 MCP 서버 도구/스킬이 제공되지 않음. 개인 플러그인 v0.4.1은 **앱/도구 없는 skill-only**로 남아 있고 Python MCP 서버는 지금 CI에서만 localhost 실제 통신 시험이 완료됐다.
- ChatGPT 커스텀 MCP 엔드포인트 직접 추가 UI는 계정·기기·플랜 제한이 있다. 공식 개별 [연결 안내](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt)는 웹+원격 HTTPS/tunnel 조건을 설명. iOS에서 일반적으로 로컬 MCP 프로세스 직결할 수 없다.
- 인터넷에 익명 서버를 열거나, 검증되지 않은 유료 호스팅/생성 API 호출을 하지 않았다. Replit에 편집 가능한 기존 `SmallPureApplet` 앱은 발견됐으나 사용자의 AI 봇 프로젝트가 아니므로 변경하지 않음. 별도 Site나 새 앱 게시·배포는 미실행.
- 원래 R15 예약 ID `6acb017062a08191a4136238b78b313a`: `automations.peek` 실제 조회 `is_enabled=true`, `FREQ=HOURLY;BYMINUTE=0;BYSECOND=0`, `Asia/Seoul` 유지. 이번 단계 예약 프롬프트·Activepieces 플로우·GitHub main·연결 등 실운영 변경 0.
- **남은 필수 작업**: 무료로 사용 가능한 인증된 Sites/MCP 배포 기능을 사용자의 계정에 연결하여 실제 HTTPS MCP URL을 배포하고, 새 ChatGPT 대화에서 도구 목록 및 `delegate_message` 실제 호출을 독립 확인. 플랫폼의 임의 모든 채팅 무조건 호출 보장 여부는 불가능한 경우 불가능하다고 명시.

## 판정
실제 MCP 서버↔클라이언트 도구 호출 **완료**. ChatGPT iOS 평소 채팅 자동 호출 **미연결**. 별도 독립 Gemini/Claude 유료 모델 호출 **0**, ChatGPT 예약 무인 성공 정규 로그 **미검증**.
