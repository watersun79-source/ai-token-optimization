# AI BOT v8.3.4 — 격리 인증 이벤트 접수 → 원자적 선점 → 자동 합성 작업 실행

## 구성
- `tools/isolated_queue_api_v834.py`: Python 표준 라이브러리 HTTP API. 로컬 또는 격리 호스팅용이며 외부 모델/API 호출 없음.
- `POST /private/submit`: `X-Queue-Key` 환경변수 인증 확인 → 오직 `synthetic-v83-*` 형식의 `offline_check` 작업 접수 → 동일 SQLite 파일에서 `tools/isolated_worker_v833.py` 일회 배치 2개 동시 실행 → 완료 기록/상태 응답. 중복 ID는 동일 작업으로 취급.
- `POST /private/recover`: 인증된 요청 시 DB 만료 임대 복구·제한 배치 실행. 서버가 자동으로 무인 재시작을 예약하거나 지속 호출하는 기능은 없음.
- `GET /private/state`: 인증된 경우 상태 개수만 읽기. `GET /healthz`: 공개, 안전 메타데이터만 제공.
- `ISOLATED_JOB_KEY`가 없거나 길이가 32 미만이면 private endpoint는 **401 fail-closed**. `ISOLATED_DB_PATH`가 없으면 인증이 구성되어도 401. 접근 키·DB 파일 경로·헤더/요청 본문 로그 금지.
- 각 요청 작업 실행은 안전한 합성 입력만 허용, 배치 상한 2, 작업자 상한 2. 사용자 업무, Gemini/Claude, 외부 Slack/GitHub 변경 없음.

## 공식 검증
`tests/test_isolated_queue_api_v834.py` 테스트 7개: 실제 localhost 서버 별도 프로세스, 자격 없음 401, HTTP submit→SQLite persisted completion, 재전송 멱등, 실제 새 서버 프로세스의 boot_id 변화 + 동일 디스크 지속, 인증 회복 호출로 만료 임대 복구, 위험 타입 거부, 보호 경로 검증. 기존 v8.3.3 회귀 전체 유지.

## 중요: 실제 운영 불가 상태 분리
- 이 서버의 원자적 선점 보장은 **같은 SQLite 파일에 접근하는 워커**에게만 적용된다. 앞서 구성한 Activepieces Tables와 **동일 저장소가 아니다**. 비공개 인증 토큰 없는 외부 Activepieces-Render 브리지·D1 연동도 현재는 없다.
- Render Free 웹 서버의 로컬 SQLite 데이터는 **절전·배포·재시작하면 삭제**된다. Render Free Key Value도 재시작 시 사라진다. Render Free PostgreSQL은 30일 만료. 이 조건에서 24시간 영속 복구 PASS는 주장할 수 없다.
- 실서비스 승격은 승인된 영속 DB, 최소 권한 인증, 감사 원장, 단일 작업의 중복 부작용 차단, 실제 24시간/장애 회복 관측, 크레딧 한도 확인 후에만 가능. 인증 자격을 소스/테스트 로그/공용 기억에 저장하지 않는다.
- 이미 있는 Render 상태 전용 서버 `srv-dbhr5267bikc73fbaqk0`과 ChatGPT 3개 예약, 기존 Activepieces 운영 플로우, GitHub main 및 고정 SHA를 변경하지 않는다.

## 버전
격리 코드의 새 기능으로 **v8.3.4**. 운영 AI BOT은 여전히 기존 v8.1.
