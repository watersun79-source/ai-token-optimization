# AI 채팅 자동 실제 도구 라우팅: 계정 개인 플러그인 v0.5.0 — 2026-10-22

## 실제 적용
- 사용자 목표: 별도 명령/@ 없이 평소 ChatGPT AI 프로젝트 대화에서 요청 의도를 보고 필요한 전문 역할을 선택한 뒤 **실제 연결 앱 도구**를 호출하게 하는 것.
- 기존 개인 플러그인 ai-chat-bot-team (ID plugins_6ad9d7b745448191bb087af817f02f68) **v0.4.1 -> v0.5.0** 업데이트 성공, release pluginrel_6ad9fb1fa79c8191bb00ea0658123982. 기존 10개 전문 역할 + 총괄 1개 유지.
- OpenAI 공식 문서 https://help.openai.com/en/articles/20001256-plugins-in-chatgpt : 앱과 스킬 결합 지원, 관련 요청 시 설치 플러그인 자동 사용 가능(보장 아님). 별도의 원격 MCP 서버 없이 이미 연결된 앱을 스킬에서 사용 가능.
- 계정 플러그인의 plugin.json 에 extensions.com.openai.apps = ./.app.json, 실제 앱 ID로 연결: GitHub connector_1p_1a69035c238881919c4190932b2df699; Slack asdk_app_69a1d78e929881919bba0dbda1f6436d. 둘 모두 Plugin Management 검색에서 installed=true. Activepieces는 앱 디렉터리에서 검증된 app ID가 없어 거짓으로 추가하지 않음.
- 새 ai-connected-tools/SKILL.md + agents/openai.yaml allow_implicit_invocation true, products CHAT. 요청 분석 → 관련 GitHub/Slack 실제 앱 호출 → 증거 SHA/ts read-back → 상태 보고. 일상/무관 질문 스킵. 운영 쓰기 금지·비밀키 노출 금지.
- Plugin Creator update_plugin 실제 성공, get_plugin_files 재조회 44 files, 10 전문 스킬 유지, 새 skill 문서 및 .app.json 원본 접근 확인. 버전 0.5.0. 패치 ZIP /mnt/data/ai-bot-connected-apps-v0.5.0-patch.zip SHA256 63964857698e40cc4ec379847b5c323788fb6b5923135b0b15abbec3a982d1aa.

## 실제 연결 앱 실행 검증과 미확인
- 이 대화에서 실제 mcp__GitHub__fetch_file 호출 성공: docs/ai/AI_OAUTH_PROVIDER_HARDENING_2026-10-22.md blob SHA 492ef0ccf8bdb9b929629d45f254926e5a484ae1, 실제 CI 번호 39773996781 포함.
- 실제 mcp__Slack__slack_read_thread 호출 성공: 채널 C0C9649RQAZ 부모 thread_ts 1792416391.631669, 이전 message 1792670137.613149 및 CI 39773996781 내용 읽음.
- 중요 구별: 현재 모델이 이 대화에서 실제 이미 연결된 앱을 직접 호출한 사실은 확인됐지만, v0.5.0 자동 스킬이 **새 ChatGPT 대화에서 자동 선택되고 해당 앱이 스킬 내부에서 사용되는지**는 아직 독립 검증되지 않음. tools.skills__list 현재 채팅 캐시에는 새 ai-connected-tools URI가 아직 표시되지 않음. 새로운 채팅에서 사용자 테스트 필요.
- mcp__Plugin_Management__get_plugin_dependencies는 공개 globally listed plugin만 다루므로 현재 개인 PRIVATE 플러그인 ID에는 plugin_not_found; 따라서 이 결과는 app binding 오류가 아님. Plugin Creator .app.json 실제 재조회는 통과. 계정·제품별 추가 연결/권한이 필요할 수 있음.
- 외부 Python Gateway와 OAuth 서버는 별도 소스·CI 검증 상태이며 이 플러그인에 실제 호스팅 서버 엔드포인트가 붙었다는 의미가 아님. 아직 기본 ChatGPT의 모든 채팅 메시지를 외부 Python 서버에 무조건 전달할 수 없음.

## 보호한 설정 및 다음 단계
- automations.peek 로 기존 AI R15 id 6acb017062a08191a4136238b78b313a is_enabled=true, FREQ=HOURLY;BYMINUTE=0;BYSECOND=0, Asia/Seoul, 알림 상태와 프롬프트 변경 없음. GitHub main / Activepieces 운영 플로우 / 연결/예약 변경 0.
- Render 서비스 생성 도구의 과거 안전 차단 재시도/우회 금지. 유료 생성 API 호출·결제 0. 허용되지 않은 외부 모델/비밀 사용 없음.
- 다음 우선순위: 새 채팅에서 개인 플러그인 v0.5.0/ai-connected-tools 자동 노출 여부 실제 확인, 채팅에서 '내 AI 프로젝트 최신 CI 대조해' 같은 관련 요청으로 GitHub 도구 원시 호출과 Slack 읽기 증거 확인. 성공해도 일반 모든 메시지 100% 자동 호출 보장 아님.
- 별도 안전한 HTTPS MCP OAuth 배포는 사용자 요구가 아직 충족되지 않는 다른 경로임. 이 새 app-backed 플러그인은 기존 앱으로 즉시 실제 작업을 수행하기 위해 서버 문제를 우회하는 것이 아니라 정상적인 제품 지원 경로를 새로 선택한 것.

## 2026-10-22 후속 연결 실행 관찰 (동일 대화 후속 '진행')
- **새 스킬 현재 채팅에서 실제 로딩 확인**: tools.skills__read('skills://plugins/ai-chat-bot-team/ai-connected-tools/skill.md') 성공. tools.skills__list에서 ai-chat-bot-team에 속한 스킬 **12개**, 이 중 ai-connected-tools 존재. 기존 기록의 '현재 채팅에 새 스킬 미표시'는 **과거 시점 사실**, 후속 관찰로 갱신됨.
- Plugin Creator get_plugin_files로 계정 개인 플러그인 **v0.5.0**, release pluginrel_6ad9fb1fa79c8191bb00ea0658123982, 44 files, .app.json의 검증된 GitHub/Slack ID, ai-connected-tools/agents/openai.yaml allow_implicit_invocation true 직접 재확인.
- **@ 멘션 없는 사용자 메시지 '진행'을 AI 프로젝트 문맥으로 해석하고 실제 연결 도구 호출**: mcp__GitHub__fetch_file로 이 문서 자체의 이전 버전 blob SHA 60e9e11d820a286de21245226971594b69bbfa21 읽음, Slack mcp__Slack__slack_read_thread로 기존 v0.5 CI/릴리스 기록 읽음. 이는 '현재 대화에서 의도 기반 도구 사용 성공'을 뜻하지만, 플랫폼이 별도 플러그인 내부 에이전트를 독립 자동 실행했다는 증거나 다른 새 채팅에서 항상 implicit 호출된다는 증거는 아님.
- 설치 권한 API 간 불일치 발견: Plugin Management search_plugins는 GitHub·Slack installed=true를 반환하는 한편 get_app_permissions(각 동일 exact id)는 status=not_installed를 반환. 그러나 현재 채팅에서 양쪽 실제 읽기 도구는 정상 동작. 진단 불일치로 표시하며 어느 값을 전역 설치/권한 보장이라고 단정하지 않음. 사용자 승인 없이 권한을 상향/변경하지 않음.
- 별도 원격 OAuth/Python MCP 호스팅 미연결, ChatGPT 일반 메시지를 외부 Python에 **항상 강제** 전달하는 기능은 불명/보장 불가. 기존 R15 예약은 automations.peek으로 is_enabled=true·Asia/Seoul 매시간 정각 확인; 스케줄/프롬프트 및 Activepieces 운영·GitHub main 변경 없음.
- 남은 목표: **새 채팅 표면에서** @ 멘션 없이 같은 사용자 프로젝트 요청을 넣고 해당 채팅의 실제 GitHub/Slack 도구 호출 원본으로 자동 선택 여부 확인. 이 현재 대화의 후속 턴만으로 새 채팅 implicit 동작을 재현했다고 주장하지 말 것.
