# v8.3.5 — Neon → Render 최소 권한 연결 안내 (사람이 관리 화면에서 설정)

**2026-10-30 상태:** Neon 실DB의 원자적 선점/임대 펜싱 PASS, v8.3.5 Render Free 서버 LIVE. **연결 미완료**: `aibot_v835_render_runtime` SQL 작성 역할은 DB 생성/역할 생성/RLS 우회가 불가능하고 오직 격리 큐 권한이 있으나, Neon 관리 API에서는 `authentication_method=no_login`이며 비밀번호가 없는 상태로 반환됨. 프로그램으로 한 번에 비밀값을 가져와 Render에 전달하는 요청은 플랫폼 안전 검사에 차단됐음. **우회 금지**. 기존 앱·예약·main은 그대로.

## 수동 보안 연결 (비밀은 ChatGPT/GitHub/공용 D1 메모리에 전송하지 않는다)

1. Neon Console https://console.neon.tech 에서 프로젝트 `ai-bot-v834-isolated-durable-queue` (`autumn-frog-53985417`), 기본 브랜치 `main`, DB `aibot_isolated` 선택.
2. `Postgres database → Roles` 에서 SQL로 생성된 전용 역할 `aibot_v835_render_runtime` 인증 상태를 확인. **기존 DB 소유자/관리자 역할의 접속 문자열을 Render에 넣지 않는다.**
3. 전용 역할에만 강력하고 유일한 비밀번호를 설정. 권장: 본인 컴퓨터의 `psql`에서 `\\password aibot_v835_render_runtime` 명령을 사용하여 명령 기록에 비밀번호가 남지 않도록 한다. Neon Console의 Roles에서 reset 지원 시 그 화면을 이용할 수도 있다. Neon API가 "cannot update password for role without password"를 반환했다면 UI 재설정도 지원되지 않을 수 있다. 그 경우 사용자가 직접 Neon SQL Editor에서 `ALTER ROLE aibot_v835_render_runtime WITH LOGIN PASSWORD '<private unique password>';` 설정할 수 있으나 SQL 입력/조회 이력에 비밀번호가 남을 수 있으므로 위험을 인지하고 권한 및 히스토리 관리에 주의한다. **여기 채팅에 비밀번호 입력 금지.**
**2026-11-01 읽기 전용 권한 확인:** DB 접속 역할 `aibot_isolated_owner`는 `CREATEROLE=true`이고, `pg_auth_members` 기준 대상 `aibot_v835_render_runtime`에 직접 `admin_option=true`를 가지고 있어. SQL 역할 자체는 `rolcanlogin=true`지만 Neon 관리 API에는 `authentication_method=no_login`으로 보이며, **실제 비밀번호 설정과 원격 로그인 성공은 아직 확인되지 않았어.** 이 권한 검사만으로 접속 성공으로 처리하지 마. 안전한 수동 비밀번호 설정은 사용자 소유 `psql` 세션에서만 수행하고, 어떤 비밀도 ChatGPT/CI/메모리/커밋에 남기지 않아야 해.

4. Render Dashboard [v8.3.5 격리 서비스](https://dashboard.render.com/web/srv-dbhsc1nlk1mc739rstng) → **Environment** → **Add Environment Variable**에 다음 두 변수 설정:
   - `NEON_QUEUE_DATABASE_URL`: 위의 최소권한 역할을 사용하는 Neon TLS 연결 문자열. 사용자·비밀번호·호스트·`aibot_isolated` DB를 정확히 설정하고 `sslmode=require` 유지. Neon Console의 Connect 정보에서 **소유자 비밀번호를 복사하지 않는다**.
   - `ISOLATED_JOB_KEY`: DB 비밀번호와 다른 독립적인 32+ 문자 랜덤 키. 절대 소스, GitHub, Activepieces 로그, ChatGPT에 저장하지 않는다.
5. Render에서 **Save and deploy** (최소권한의 격리 서비스만). 새 빌드/배포 시작 전에 Render Free 사용량/잠재 과금 여부를 직접 확인한다.
6. 배포 후 공개 `https://ai-bot-v835-neon-isolated-20261030.onrender.com/healthz`에서 `version=8.3.5`와 `configuration_present=true`를 확인. **최초 인증 조회 전에는 `intake_enabled=false`, `database_connection_verified=false`가 정상적인 안전 차단 상태**다. `configuration_present=true`는 URL/키의 형식 확인일 뿐 실제 DB 연결 성공 증거가 아니다. 처음부터 `intake_enabled=true`를 기대하면 잘못된 장애 판정이 된다.
7. 개인 소유의 API 클라이언트에서 키를 헤더 `X-Queue-Key`에 안전하게 실어 **한 번만** `GET /private/state` 호출해 HTTP 200 및 `state_counts`를 검사. 이 응답이 **호스팅 Render→Neon 실인증 연결의 최초 PASS 근거**다. 키를 채팅/로그에 붙여 넣지 않는다. 이후 **60초 안에** 공개 `/healthz`에서 `database_connection_verified=true`, `intake_enabled=true`를 재확인할 수 있다(60초 TTL 경과 시 다시 false가 되는 것이 정상). 그 다음 `POST /private/submit`에 `{"task_id":"synthetic-v83-manual-v835-01","kind":"offline_check"}` 한 건만 보내 Neon SQL readback `SUCCEEDED` 확인. 공개 Github CI는 키를 몰라 **401 차단**만 검증해야 한다.
8. 같은 작업을 반복 요청했을 때 새 작업으로 실행되지 않는지 확인. 이후에만 실제 서버 절전·재시작 이벤트와 `boot_id`, 복구 기록을 비교해 무인 복구를 별도로 검증한다. 강제 장애/과금/항상 켜두기 금지.

## 실제 연결 확인 판정과 장애 구분

| 관측값 | 판정 | 다음 행동 |
|---|---|---|
| 공개 `/healthz` HTTP 200, `configuration_present=false` | 환경 변수 미설정/형식 불충족 | Render Environment의 **두 변수 이름**과 값 형식을 개인 화면에서 확인 |
| `configuration_present=true`, `database_connection_verified=false` | 서버는 구성만 인지, 아직 인증 연결 미증명 | 인증 헤더를 붙인 `/private/state`를 개인 클라이언트로 1회 호출 |
| `/private/state` HTTP 401 | 키 누락 또는 불일치 | `ISOLATED_JOB_KEY`가 동일한지 개인 환경에서만 확인 |
| `/private/state` HTTP 503 | Neon 로그인·네트워크·DB 접근 문제 | Render 앱 로그(비밀값 제외)와 Neon 전용 역할/DB/TLS 설정 확인. 자동 재시도 금지 |
| `/private/state` HTTP 200, `state_counts` 존재 | **Render→Neon 읽기 연결 PASS** | 60초 이내 합성 `POST /private/submit` 1회 및 Neon DB 결과 재조회 |
| `/private/submit` HTTP 503 `DATABASE_NOT_VERIFIED` | 60초 DB 확인 유효 기간 경과 또는 최초 확인 안 됨 | `/private/state` 인증 조회를 다시 수행한 뒤 제한적으로 테스트 |
| `/private/submit` HTTP 202 `execution_status=UNVERIFIED` | 큐 접수는 되었을 수 있으나 실행 성공 미증명 | 같은 `task_id`의 DB 상태와 필요 시 별도 수동 복구 확인 |

연결 문자열과 API 키는 **오직 Neon/Render 관리 화면 및 사용자의 비공개 API 클라이언트**에서 취급한다. 서비스가 실제 DB 인증을 통과하기 전에는 합성 작업도 자동 활성화하지 않고, 기존 보안 차단·무료 제한·운영 보호를 유지한다. 이 문서 교정은 서버 배포나 데이터베이스 인증 완료가 아니다.

## 자동화가 검증하는 것과 하지 않는 것
- 신규 `tools/verify_v835_public_security.py`은 공식 GitHub CI에서 외부 HTTP GET **1회**와 미인증 POST **1회**만 수행한다. 상태 200, 익명 작업 401은 검증하지만 **실제 DB 연결·작업처리·사용자 비밀키는 접근하거나 증명하지 않는다**.
- Render Free는 절전할 수 있어 24시간 무중단을 보장하지 않는다. PostgreSQL Free는 영속 저장 가능해도 compute 제한이 있으며, 실제 작업 복구는 별도 원본 이벤트와 결과 저장이 필요한 사안.
- 기존 예약 3개, GitHub main, old Render 서비스 2개, Activepieces 운영 플로우에 변경 없음.

**출처:** [Render Environment Variables](https://render.com/docs/configure-environment-variables), [Neon Manage Roles](https://neon.com/docs/manage/roles).
