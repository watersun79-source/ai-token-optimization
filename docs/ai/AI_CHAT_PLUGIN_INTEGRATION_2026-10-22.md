# AI ChatGPT 3봇 협업 플러그인 — 실제 적용 및 검증 (2026-10-22 KST)

## 사용자 요청
기존 3역할 오프라인 프로그램을 기반으로 ChatGPT의 일반 대화에서 필요시 협업하도록 무료 우선 연결. 기존 예약 AI 및 Activepieces 운영 플로우 변경 금지.

## 실제 수행
- 연결된 GitHub 원본과 실행 표준 읽기. Activepieces 원본 플로우 11개 상태를 읽기 전용 확인(활성 Slack 1, 기타 비활성 10). 운영 수정/테스트 호출 없음.
- OpenAI 도움말 공식 확인: 설치된 ChatGPT 플러그인은 관련 요청에 자동 선택될 수 있고, `@` 멘션으로 명시 선택 가능. 실제 자동 선택 여부/일반 채팅 전부 적용은 사용자 새 대화에서 별도 검증 필요.
- Private plugin **AI 3봇 협업** 새로 생성. ID `plugins_6ad9d7b745448191bb087af817f02f68`, release `pluginrel_6ad9d7b8e2608191ac8cf261434c5fa2`, URL https://chatgpt.com/plugins/plugins_6ad9d7b745448191bb087af817f02f68. 단일 skill `ai-chat-collaboration`, `policy.allow_implicit_invocation: true`, `policy.products: [CHAT]`; 도구/외부 MCP 없음. Plugin Creator `get_plugin_files`로 구성 파일 10개·릴리스 재조회.
- 플러그인은 자동 상시 실행 서비스가 아니라 **ChatGPT 내부 3역할 지침**(ResearchBot 조사 → BuilderBot 적용 → VerifierBot 증거 검증)이며, 기존 무료 파이썬 PoC 코드와 테스트 동봉. 이 답변 시점 새 채팅 자동 호출 원본은 미검증; 현재 세션 `skills__list`에서 newly created skill 미노출. 자동 호출 성공이라고 주장하지 않음.
- 격리 GitHub 브랜치 `ai/bot-team-sandbox-2026-10-22`: `experiments/ai-bot-team/chat_router.py`와 `tests/test_chat_router.py` 추가, README의 채팅 연동 범위 설명 갱신. 다른 `main`·예약·플로우·연결 설정 변경 없음.
- Git blob 직접 재조회: router `6233718b120d307263346af25c4539a5d2466838`, router tests `2dc30d7ee2993201beaf764a711f980da45e95d4`, README `c6a250697dabaea1ae7a5034e0b876f9858c3a06`.
- 로컬 `python -m unittest discover -s tests -v`: **23/23 OK**. 패키지 ZIP을 별도 디렉토리 압축 해제하고 테스트 **23/23 OK**, 샘플 라우팅 `THREE_ROLE_WORKFLOW` + VerifierBot `PASS`; 일반 채팅은 `DIRECT_CHAT`. ZIP SHA256 `31826c0411fde03cac775ebdb5560439526b0f9d8e0d8700ed2ae498ebe2a01a`.
- 독립 GitHub Actions 최종 [run 39756217258](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39756217258) `completed/success` head `4af4e29e78b5c33e91655a78d480267d887d1afa`; 코드 변경 이전 성공 run `39756148632` job `119748532504` 원본 로그 `Ran 23 tests in 0.136s`, `OK`.

## 중요한 구분
- 역할 3개 = ChatGPT 협업 **워크플로**, **독립 3개의 AI 모델/백그라운드 에이전트가 아님**. Python `chat_router.py`도 ChatGPT의 실제 채팅 훅이 아닌 로컬 분기 데모. 플러그인 선택과 연결 앱 사용은 제품/권한/설치 상황에 달림.
- 사용자 대화 예시: 일반 ChatGPT에 `AI 프로젝트 코드 오류 분석하고 수정해`; 정확한 플러그인 사용 시 `@AI 3봇 협업` 선택 후 요청. 개인 플러그인에서 설치가 필요하다고 나오면 사용자 설치 동작을 해야 함.
- 외부 Gemini/Claude/ChatGPT 모델 생성 API 호출 0, 청구/결제/업그레이드 0, 운영 변경 0. 계정별 무료 quota 미검증. 자동 실행/실제 외부 모델 협업/정규 ChatGPT 예약 성공은 **미검증 또는 미구현**.
- [OpenAI plugin 공식 문서](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt), [스킬 공식 문서](https://help.openai.com/en/articles/20001066-skills-in-chatgpt).

## 다음 조치
- 새 일반 ChatGPT 대화에서 (a) 설치/표시 여부, (b) 자동 선택 1회, (c) `@` 명시 선택, (d) Research/Builder/Verifier 결과와 실제 연결 도구 호출을 독립 확인. 제품 지원 범위를 벗어나면 성공이라고 추정하지 않음.
- 실제 독립 모델 자동화는 무료 가능성·청구 통제·원격 MCP 서버·권한 승인까지 별도 검증 후 격리 구축. 기존 Asia/Seoul 매시간 AI 예약 ID `6acb017062a08191a4136238b78b313a` 유지.
