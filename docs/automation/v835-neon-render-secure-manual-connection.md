# v8.3.5 — Neon → Render 최소 권한 연결 안내 (사람이 관리 화면에서 설정)

**2026-10-30 상태:** Neon 실DB의 원자적 선점/임대 펜싱 PASS, v8.3.5 Render Free 서버 LIVE. **연결 미완료**: `aibot_v835_render_runtime` SQL 작성 역할은 DB 생성/역할 생성/RLS 우회가 불가능하고 오직 격리 큐 권한이 있으나, Neon 관리 API에서는 `authentication_method=no_login`이며 비밀번호가 없는 상태로 반환됨. 프로그램으로 한 번에 비밀값을 가져와 Render에 전달하는 요청은 플랫폼 안전 검사에 차단됐음. **우회 금지**. 기존 앱·예약·main은 그대로.

## 수동 보안 연결 (비밀은 ChatGPT/GitHub/공용 D1 메모리에 전송하지 않는다)

1. Neon Console https://console.neon.tech 에서 프로젝트 `ai-bot-v834-isolated-durable-queue` (`autumn-frog-53985417`), 기본 브랜치 `main`, DB `aibot_isolated` 선택.
2. `Postgres database → Roles` 에서 SQL로 생성된 전용 역할 `aibot_v835_render_runtime` 인증 상태를 확인. **기존 DB 소유자/관리자 역할의 접속 문자열을 Render에 넣지 않는다.**
3. 전용 역할에만 강력하고 유일한 비밀번호를 설정. 권장: 본인 컴퓨터의 `psql`에서 `\\password aibot_v835_render_runtime` 명령을 사용하여 명령 기록에 비밀번호가 남지 않도록 한다. Neon Console의 Roles에서 reset 지원 시 그 화면을 이용할 수도 있다. Neon API가 "cannot update password for role without password"를 반환했다면 UI 재설정도 지원되지 않을 수 있다. 그 경우 사용자가 직접 Neon SQL Editor에서 `ALTER ROLE aibot_v835_render_runtime WITH LOGIN PASSWORD '<private unique password>';` 설정할 수 있으나 SQL 입력/조회 이력에 비밀번호가 남을 수 있으므로 위험을 인지하고 권한 및 히스토리 관리에 주의한다. **여기 채팅에 비밀번호 입력 금지.**
4. Render Dashboard [v8.3.5 격리 서비스](https://dashboard.render.com/web/srv-dbhsc1nlk1mc739rstng) → **Environment** → **Add Environment Variable**에 다음 두 변수 설정:
   - `NEON_QUEUE_DATABASE_URL`: 위의 최소권한 역할을 사용하는 Neon TLS 연결 문자열. 사용자·비밀번호·호스트·`aibot_isolated` DB를 정확히 설정하고 `sslmode=require` 유지. Neon Console의 Connect 정보에서 **소유자 비밀번호를 복사하지 않는다**.
   - `ISOLATED_JOB_KEY`: DB 비밀번호와 다른 독립적인 32+ 문자 랜덤 키. 절대 소스, GitHub, Activepieces 로그, ChatGPT에 저장하지 않는다.
5. Render에서 **Save and deploy** (최소권한의 격리 서비스만). 새 빌드/배포 시작 전에 Render Free 사용량/잠재 과금 여부를 직접 확인한다.
6. 배포 후 공개 `https://ai-bot-v835-neon-isolated-20261030.onrender.com/healthz`에서 `version=8.3.5`와 `intake_enabled=true` 확인. 이 값은 **설정값 형태 검사만** 뜻하고 실제 DB 인증 성공 증거는 아니다.
7. 개인 소유의 API 클라이언트에서 키를 헤더 `X-Queue-Key`에 안전하게 실어 **한 번만** `GET /private/state` 호출해 HTTP 200 및 `state_counts`를 검사. 키를 채팅/로그에 붙여 넣지 않는다. 그 다음 `POST /private/submit`에 `{"task_id":"synthetic-v83-manual-v835-01","kind":"offline_check"}` 한 건만 보내 Neon SQL readback `SUCCEEDED` 확인. 공개 Github CI는 키를 몰라 **401 차단**만 검증해야 한다.
8. 같은 작업을 반복 요청했을 때 새 작업으로 실행되지 않는지 확인. 이후에만 실제 서버 절전·재시작 이벤트와 `boot_id`, 복구 기록을 비교해 무인 복구를 별도로 검증한다. 강제 장애/과금/항상 켜두기 금지.

## 자동화가 검증하는 것과 하지 않는 것
- 신규 `tools/verify_v835_public_security.py`은 공식 GitHub CI에서 외부 HTTP GET **1회**와 미인증 POST **1회**만 수행한다. 상태 200, 익명 작업 401은 검증하지만 **실제 DB 연결·작업처리·사용자 비밀키는 접근하거나 증명하지 않는다**.
- Render Free는 절전할 수 있어 24시간 무중단을 보장하지 않는다. PostgreSQL Free는 영속 저장 가능해도 compute 제한이 있으며, 실제 작업 복구는 별도 원본 이벤트와 결과 저장이 필요한 사안.
- 기존 예약 3개, GitHub main, old Render 서비스 2개, Activepieces 운영 플로우에 변경 없음.

**출처:** [Render Environment Variables](https://render.com/docs/configure-environment-variables), [Neon Manage Roles](https://neon.com/docs/manage/roles).
