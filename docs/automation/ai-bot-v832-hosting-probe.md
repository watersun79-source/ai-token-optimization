# AI BOT v8.3.2 · Render 무료 호스팅 격리 점검

## 구성
- 진단용 서버: `tools/isolated_probe_v832.py` (Python 표준 라이브러리), 실행: `python -m tools.isolated_probe_v832`
- 읽기 전용 `GET /`, `GET /healthz`, `GET /readyz`, `HEAD`만 지원. 그 외 경로 404, 쓰기 메서드 405.
- 상태값: `probe_version`, `lease_code_version`, `boot_id`, `uptime_seconds`, `jobs_enabled:false`, `persistent_database_connected:false`, `automatic_restart_verified:false`.
- `boot_id`는 실제 프로세스마다 달라지므로 배포·리부팅·재시작의 간접 지표다. **두 시점의 응답이 달라야 실제 새 프로세스라고 할 수 있다.**
- 공개 endpoint에 비밀키/사용자 채팅/실제 작업 ID·작업 결과·데이터베이스 내용 포함 금지. 로그에 요청 데이터 출력 금지.
- 외부 업무 실행·Activepieces 웹훅·Github Actions dispatch·Slack 메시지·모델 API 호출 없음.

## 검증과 한계
- `tests/test_isolated_probe_v832.py`: 실제 localhost 자식 서버 실행→정상 응답, POST 차단, 없는 경로 404, HEAD, 수동 프로세스 종료/재실행 뒤 새 boot_id 검증.
- 이 테스트의 자동 재시작은 **시험 프로세스의 수동 재기동**이다. Render 플랫폼이 다운된 프로세스를 자동 재시작했음을 증명하지 않는다.
- Render Free 웹 서비스는 15분 무요청 시 절전하고, 요청이 오면 재기동한다. 즉 **항시 가동 24시간 보장 불가**.
- Render Free의 로컬 파일은 인스턴스 재시작/배포/절전 시 사라진다. 기존 `tools/durable_queue_v831.py`의 SQLite를 Free 디스크에 넣어 영속 복구된다고 주장하지 않는다.
- Render 무료도 대역폭/빌드 사용량 초과 시 계정 조건에 따라 유료 추가 비용이 발생할 수 있으므로 자동 트래픽 발생·유료 전환 금지. 이 검증 서버는 요청에 의해 기동되도록 유지한다.
- 배포시 설정: Python 서비스, `buildCommand: python -m unittest discover -s tests -v` 또는 `true`, `startCommand: python -m tools.isolated_probe_v832`, `plan:free`, `autoDeploy:no`, 민감한 환경변수 없음.
- 실제 유료 배포, 자동 재시작용 강제 크래시 endpoint, 지속 핑, 인터넷 공개 작업 실행 엔드포인트는 구현/활성화하지 않는다.

## 보호
- 기존 ChatGPT 정각 자동화 2개, Activepieces 운영 플로우, 기존 private Site, GitHub main과 시간별 워크플로 pinned SHA 변경 없음.
- 이 branch는 `ai/v831-durable-recovery-20261030`의 후속 **개발 버전 v8.3.2**. 운영판은 v8.1 유지.
