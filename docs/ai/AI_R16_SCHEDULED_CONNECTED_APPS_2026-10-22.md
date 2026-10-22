# AI 정규 예약 R16: 개인 플러그인 v0.5.0의 연결된 앱 기반 역할 자동선택 적용
작성일: 2026-10-22 (Asia/Seoul)

## 실제 작업 및 재조회
- 사용자 직접 요청 "예약 ai 적용. 진행"에 따라 **기존 단일 예약** `6acb017062a08191a4136238b78b313a`의 prompt만 **R15 → R16** 수정. 별도 예약 생성 금지.
- `automations.update` SUCCESS, 이어서 `automations.peek` 독립 재조회. 제목 `AI`, `is_enabled=true`, schedule `BEGIN:VEVENT / DTSTART:20261013T110000 / RRULE:FREQ=HOURLY;BYMINUTE=0;BYSECOND=0 / END:VEVENT`, `default_timezone=Asia/Seoul`, `timing_mode=exact_schedule`, `notifications_enabled=false`, `email_enabled=false` 유지. 기존 일시정지/중지/삭제/중복 없음.
- 저장된 prompt 첫 문구 `[AI R16 — 예약 AI: 실제 연결 앱 기반 필요 봇 자동 실행·검증 / 2026-10-22]` 실제 재조회.
- 이전 R15 및 R14의 주요 보호 조건·매시간 목표·최신 GitHub/Slack 기억 복원·공식 예약 run ID 미제공/자가체크포인트 구분·독립 검증 원칙을 R16에도 모두 명시. 플러그인 성공률 수치나 공식 스케줄러 회차 ID는 추정하지 않음.
- 이전 예약 메타데이터 `last_run_time=2026-10-22T12:01:45.281530Z`는 플랫폼 제공 마지막 실행 시간 필드로만 관찰되며, **R16 실행의 증거나 특정 정규 회차 공식 run ID가 아님**.

## 실제 플러그인·연결 앱 확인
- 개인 플러그인 `ai-chat-bot-team`, ID `plugins_6ad9d7b745448191bb087af817f02f68`, v0.5.0, release `pluginrel_6ad9fb1fa79c8191bb00ea0658123982`; `get_plugin_files`로 `plugin.json`, `.app.json`, `ai-connected-tools/agents/openai.yaml` 실제 재조회.
- 스킬 `ai-connected-tools`의 `allow_implicit_invocation=true`, `products: CHAT` 설정 확인. GitHub `connector_1p_1a69035c238881919c4190932b2df699`, Slack `asdk_app_69a1d78e929881919bba0dbda1f6436d`의 검증된 앱 바인딩 확인.
- 실제 수동 ChatGPT 프로젝트 대화에서는 `mcp__GitHub__fetch_file`과 `mcp__Slack__slack_read_thread` 호출이 성공했음. 관련 memory record: `docs/ai/AI_CONNECTED_APPS_PLUGIN_V050_2026-10-22.md` Blob SHA `35b946878ed99a03d910b1e8dfc840b54d82f05b`; 지정 Slack thread `C0C9649RQAZ / 1792416391.631669` 읽기 성공.
- R16 프롬프트는 **예약 실행 환경에서 실제 도구가 제공되는 경우에만** 앱 호출을 수행하고, 그렇지 않으면 BLOCKED/UNVERIFIED로 보고하도록 설정. 모두 가능한 것은 아님.

## R16 실제 실행 요구사항
1. 정규 회차에서 최신 GitHub 인계·v0.5.0 적용 기록을 최소 read-only로 읽고 SHA 확인, Slack thread 관련 기록 읽어 ts 확인(실제 앱 접근 가능한 경우).
2. 미완료 가장 중요한 목표에 맞춰 TOP10 전문 스킬/3역할 총괄 중 필요한 것만 자동 선택; 원본 CI·SHA 재검증, 최소 합법 격리 수정, 중복 테스트/중복 기록 회피.
3. 직접 독립 모델 Gemini/Claude 호출 없이 무료 우선, Activepieces 운영 및 GitHub main 변경 금지, 차단된 Render 생성 경로 재시도·우회 금지, 비밀·결제·비검증 무료 quota 사용 금지.
4. 현재 최우선 **정규 무인 기억 복원의 공식 run ID 및 실제 예약 회차의 GitHub·Slack 호출 원시 로그** 대조. `automations.peek`의 마지막 시간/예약 ID·GitHub Actions run은 공식 회차 ID 아님. 서버가 제공하지 않으면 officialRunId='미제공', 독립 성공='미검증'.
5. 매회 간결한 상태 그래프/표와 다음 목표 보고. 실제 앱 호출 없이 스킬 파일만 로딩했거나 예약 프롬프트만 저장된 경우 실제 자동 봇 실행 성공이라고 단정 금지.

## 현시점 판정
- **완료**: R16 지침 저장, 동일 ID/활성/스케줄/알림 유지 직접 재조회, 플러그인 v0.5.0 및 앱 바인딩 확인.
- **미검증**: R16 새 정규 회차에서 실제 앱/전문 스킬 자동 호출, 정규 무인 기억 복원 성공, 플랫폼 공식 개별 회차 run ID.
- **불변**: 실운영 GitHub main, Activepieces 운영 플로우/연결, 유료 API 호출·결제, 기존 예약 외 추가 생성 없음.

