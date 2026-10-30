# AI BOT v8.3.3 · SQLite 일회 실행기 + Activepieces 격리 합류

## 실제 구현 (2026-10-30)
- `tools/isolated_worker_v833.py`: SQLite 파일에서 `BEGIN IMMEDIATE` 원자적 임대 선점, 제한된 동시 작업자(1~4), 일회 실행(1~16건), 결과 완료/DEAD를 영속 저장. `tools/durable_queue_v831.py`의 임대 만료 회복 및 이전 토큰 펜싱 재사용.
- 실행 예: `python -m tools.isolated_worker_v833 --db /path/to/persistent/jobs.sqlite3 --limit 4 --concurrency 2`.
- **작업자 제한**: 오직 `synthetic-v83-*` ID의 `offline_check`만 CPU 로컬 모의 검증; 네트워크·유료 AI·Slack·실제 데이터 변경 없음. 허용되지 않은 작업은 거부하고 DEAD 기록.
- `tests/test_isolated_worker_v833.py`의 9개 테스트: 별도 프로세스에서 기록 선점·완료·재조회, 동시 실행 2개 실제 겹침, 만료 임대 회복, 비인가 종류 거부, 오류 문자열 격리, 중복 실행 방지.
- 데이터베이스 경로는 외부에서 영속적으로 보존해야 함. 앱 메모리의 일시 대기열이 아니다.

## Activepieces 실제 테스트 (운영 환경 아님)
- 실험 폴더 `TEST ONLY · AI BOT v8.3 Durable Queue`, 기존 테이블 `TEST ONLY · v8.3 Durable Job Ledger` ID `YnUiKeFYWV2ZURDw6CVsS`.
- **새 실험 플로우** `SgLOc6Y5Mts2VLgsU9rJI` 는 `DISABLED` / `published=false`인 채 TESTING에서 실제 합성 작업 처리 결과를 Table Update Record로 저장함.
- 성공 테스트 run `PvkuaQx7RXmgDoluq6O0i` (상태 SUCCEEDED), 테스트 기록 `synthetic-v83-20261030-e2e1` ID `xPpH0AZMl6HksXUJQaZ4Q`가 QUEUED → TEST_VERIFIED / SYNTHETIC_JOIN_OK로 바뀌었고 재조회됨.
- 거부 테스트 run `0zwSTREd6L8XmKw7DcICS`: 쓰기 요청 종류는 CODE 단계에서 실패했고 기록은 TEST_VERIFIED 상태로 보존됨. 이것은 **예상된 보안 거부**이지 운영 장애 아님.
- 합류 단계는 mock `Promise.all` 2개이고 Gemini/Claude/외부 작업이 실행되지 않았다.

## 남은 통합·운영 블로커
1. Activepieces Table과 SQLite 저장소는 **서로 다른 저장소**이며 자동으로 동기화되지 않는다. 완료된 이 두 개의 격리 검증을 하나의 실제 프로덕션 처리로 주장하면 안 됨.
2. Activepieces Tables MCP 읽기/쓰기에는 원자적 CAS/lease 연산이 없으며, 테스트 플로우를 게시/활성화하면 중복 작업 실행 위험이 있다. 해당 플로우는 계속 비활성.
3. Render 무료 웹 서버 `srv-dbhr5267bikc73fbaqk0`은 `tools.isolated_probe_v832`만 실행, 작업자가 배포되지 않음. Render Free의 절전 및 임시 로컬 저장소는 SQLite 영속 작업 큐의 보장 근거가 아님.
4. 실제 24시간 작업 복구를 위해 **영속 DB의 원자적 claim API**, 인증된 이벤트 진입, 실행기 상시 가동·재시작 정책, 비용/크레딧·재시도 제한, 플랫폼 원본 실행 증거가 필요.
5. 이미 연결된 D1 공용 기억의 `task_claim`은 AI 역할 인계 도구이지 임의 작업 큐 SQLite의 일반-purpose claim API로 대체할 수 없음.

## 보호
- 기존 ChatGPT 정각 예약, Render 읽기 전용 격리 서버, GitHub main, pinned :15 감사, 기존 Activepieces 운영 플로우 변경 없음.
- `v8.3.3`은 **격리 코드 및 TESTING 검증 후보**로만 사용하고 실제 운영 버전은 v8.1 유지.
