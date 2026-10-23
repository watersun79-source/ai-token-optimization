# R16 무인 예약 실행 증거 대조기 — 격리 개발 브랜치

## 2026-10-23 후속 — 최신 GitHub 원본 4/4 SHA 독립 대조 및 전체 회귀 43/43 PASS
- 사용자 **수동 '실행' 명령**으로 원본 GitHub 브랜치 `ai/r16-evidence-reconciler-2026-10-22`에서 Python 소스와 테스트 3개를 실제 읽어 로컬 `/mnt/data/r16_test/`에 복원. 직접 `git hash-object` 해시를 각각 계산해 다음 GitHub blob SHA와 **4/4 완전 일치** 확인:
  - `audit_v2.py`: `05fcfd2eac1b76d2e2f351e749a90647347a88aa`
  - `tests/test_audit_v2.py`: `a1d68fbfad6c39218211f19a869c0f6f933726b6`
  - `tests/test_cli_exit_codes.py`: `e417f706e9b8f760987d17de72708ad4863047f0`
  - `tests/test_connected_tool_names.py`: `6e1623d0797473a34cdd21b0292095c40d45cb09`
- **실제 무료 로컬 실행**: Python `3.13.5`, `python3 -m unittest discover -s tests -v` → `Ran 43 tests in 10.953s`, `OK`, 실패/오류 **0**. 이전에 미실행이었던 변경 후 전체 회귀를 **이번에 직접 완료**. 네이티브 예약 검사나 원격 CI 통과라는 뜻이 아님.
- GitHub 테스트 commit `5c92a3f73d252871dcb51274a1f95f4242cbdd00`에 대한 `fetch_commit_workflow_runs` 결과 `workflow_runs=[]` 및 `get_commit_combined_status` 결과 `statuses=[]`: **원격 CI 성공·실패 모두 미검증**.
- ChatGPT 공식 `automations.peek`: 단일 기존 예약 `6acb017062a08191a4136238b78b313a` 활성, 매시간 정각(Asia/Seoul), `last_run_time=2026-10-23T01:00:54.365515Z` (=10:00:54 KST), `paused_count=0`. 이는 실행 시각 메타이지 공식 per-run ID·종료 결과·동일 회차 GitHub/Slack 원시 호출이 아님. **정규 무인 성공 계속 미검증**.
- 운영 보호: 예약·알림·주기·기존 Activepieces 운영·GitHub main 무변경, 모델 유료 API 호출 없음. 다음 목표: 지원되는 공식 Scheduled/Previous runs에서 개별 회차 원본이 제공되는 경우에만 같은 회차 독립 검증. 원본이 없으면 미검증을 유지하고 수동 테스트를 정규 실행으로 취급하지 않는다.


## 2026-10-23 추가 보강 — Python 공식 실행/호출 나노초 순서 검사
- **재현**: Python `datetime.fromisoformat`이 소수점 이하 **7~9자리**의 나머지를 잘라서, `completed_at=22:02:30.000000100` 종료보다 `observed_at=22:02:30.000000900` 호출이 늦어도 이전 코드에서 같은 시각으로 오인. 역전된 시작·종료 시각도 잘못 비교할 수 있었음.
- **범위**: 정규 예약과 무관한 수동 연구·격리 코딩. 기존 `target_slot` / `native_run.scheduled_for` 정각 문자 규칙 `EXACT_HOUR` 보존.
- **최소 수정**: `AUDIT_TIME` 1~9자리 ISO 시각 검증과 `parsed_time_ns` (UTC datetime, 0~999 나노초 잔여분) 튜플 비교. `started_at`, `completed_at`, `tool_calls[].observed_at` 정확도 유지. 유료 모델/외부 앱 자동 호출 없음.
- **실제 GitHub 격리 코드 커밋** `7b157aaaa2e8c5812181cd957a9bc2e5b3530b0c` / blob `05fcfd2eac1b76d2e2f351e749a90647347a88aa`.
- **신규 회귀 테스트 커밋** `5c92a3f73d252871dcb51274a1f95f4242cbdd00` / blob `a1d68fbfad6c39218211f19a869c0f6f933726b6`. 새 테스트 4개: 800ns 종료 후 호출 거부, 나노초 시작·종료 역전 거부, 종료 전 정상 50ns 형식 허용, 9자리 초과 소수초 거부.
- **검증 수준**: 위 판정 알고리즘을 로컬 Python에서 별도로 확인해 **표적 4/4 통과**, GitHub 원본 코드·테스트 blob 각각 재조회 일치. **수정 후 최신 전체 43개 단위 테스트/원격 CI는 이 채팅에서 실행하지 않았으므로 미검증**. 이전 39/39는 패치 *전* 수동 테스트 이력이며 최신 전체 성공으로 잘못 표기하지 않음.
- 모든 경우 `official_success_verified=false` 원칙 유지. 형식 일치만으로 ChatGPT Scheduled 정규 무인 실행 성공을 주장하지 않음. 현재 도구는 공식 native per-run ID와 원본 GitHub·Slack tool-call ledger 미제공.
- 기존 R16 매시간 정각 활성 예약/프롬프트/알림, 운영 Activepieces, GitHub main 및 유료 API 변경 없음. 다음 목표: **최신 소스 전체 회귀 실행·검증 → 공식 플랫폼 개별 실행 원본 접근 시 동일 회차 증거 비교**.



## 문제와 해결

2026-10-22 22:00 KST ChatGPT 정규 예약의 last_run_time=2026-10-22T13:01:47.915363Z는 실행 시각 메타데이터다. 성공 판정, 공식 개별 실행 ID 및 원본 앱 호출 로그가 아니다. Activepieces 자체 체크포인트에 기록한 UUID나 GitHub Actions run ID는 ChatGPT 예약의 공식 실행 ID가 아니다.

오류를 방지하기 위해 audit_v2.py를 추가했다. 공식 native_run 출처, run_id, 자동화 ID, 정각 슬롯, 시작/종료 시각, 성공 상태를 확인한 뒤 **같은 회차**의 GitHub 3개·Slack 1개 원본 호출을 도구명/대상/호출 ID/시간/버전으로 대조한다. 독립적인 원본 인증이 없으면 성공이라고 표시하지 않는다.

## 공개 구현 참조

- GitHub Actions 공식 변수 (run_id / run_attempt): https://docs.github.com/en/actions/reference/workflows-and-actions/variables
- OpenTelemetry GenAI tool spans (tool call ID와 trace): https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md
- LangGraph 체크포인트/복구: https://langchain-ai.github.io/langgraph/concepts/durable_execution/
- Activepieces 운영 실행 로그·보관 제한: https://www.activepieces.com/docs/install/reference/limits
- OpenAI 공식 ChatGPT 예약: https://help.openai.com/en/articles/10291617-scheduled-tasks-in-chatgpt

LangGraph는 MIT 라이선스, Activepieces 핵심 오픈소스도 MIT(엔터프라이즈는 상용). 코드는 직접 구현했으며 오픈소스 코드 복제·외부 모델 호출 없음.

## 재현 방법 (Python 표준 라이브러리)

1. python3 -m unittest discover -s tests -v
2. python3 audit_v2.py --input observed_2026-10-22T22.json

로컬 회귀 검사 21/21 통과. 본문 예시의 샘플 실행 ID는 실제 ID가 아니라서 절대 정규 실행의 증거로 사용하면 안 된다.

실측 22:00 입력은 공식 native_run=null, tool_calls=[]여서 정상적으로 "미검증: 공식 개별 회차 원본 로그 미제공" 판정한다. CLI 종료 코드는 **미검증 2 / 형식만 통과·진위 미검증 3**이다. 종료 코드 **0은 진위가 인증된 성공 전용으로 예약**했으며 이 오프라인 검증기는 0을 반환하지 않는다.

## 완료 조건과 보호 범위

ChatGPT Scheduled → AI → Previous runs에서 정확한 22:00 회차를 열어 실결과를 확인하고, 플랫폼이 실제 제공하는 개별 run ID·원본 tool call ID와 GitHub SHA·Slack ts를 같은 회차로 대조한다. 개별 run ID 또는 호출 로그가 공개되지 않으면 미검증이다.

기존 활성 예약·프롬프트·일정·알림·Activepieces 운영 플로우·GitHub main·Slack 운영 데이터를 전혀 변경하지 않는다. 이 브랜치는 적용 전 mock-only 개발용이며 자동 배포/실행되지 않는다.

## 2026-10-22 23시 이후 확인한 결함 수정
- 결함: 이전 검증기는 `automations.peek.last_run_time`이 목표 슬롯 +1시간 이내인지 **필수 조건**으로 사용. `23:00` 슬롯이 지난 후 `22:00` 원본 `native_run`을 나중에 검증하면 잘못 반려하는 과거회차 버그가 있었음.
- 수정: 마지막 실행 시각은 **진단용 최신 메타데이터**로만 사용하며, 공식 원본 실행 ID·회차별 시작/종료·호출 로그를 검증하는 독립 경로는 유지. 과거 회차의 `native_run`이 진짜 원본일 때 최신 예약 실행 시각 때문에 거절하지 않음. 증거가 없는 과거 회차는 계속 `미검증`이며 가짜 실행 ID는 인정하지 않음.
- 직접 로컬 회귀 테스트 **23/23 통과**. 실측 `23:00:27`을 최신 예약 시각으로 반영해 `22:00` 회차를 재검사하면 `미검증: 공식 개별 회차 원본 로그 미제공; 최신 예약 시각은 과거 회차 원본 증거가 아님`으로 판정. 공식 실행 증거를 새로 얻었다는 뜻은 아님.
- 원격 격리 브랜치 코드 blob SHA `86d90166b8c8ed18162fd097583c5d506e23cd09`, 테스트 blob SHA `8b8cb06194125737eb827bcc731c5192dca6dc74`; GitHub `fetch_file` 직접 재조회로 확인. 운영 예약/시간대/프롬프트와 Activepieces, `main` 변경 없음.


## 최신 수정 — R16 인계 문서와 검증 대상 정합성 (2026-10-22)
- **실제 발견 오류**: 1차 검사기의 `REQUIRED`가 과거 R13의 `PROJECT_MEMORY_INDEX.md`, `AI-memory-protocol.md`, `ai-unattended-success-audit-2026-10-21-0624.md` 및 Slack으로 고정돼 있었음. 현행 R16 지침은 `AI_CURRENT_HANDOFF_2026-10-22.md`를 최상위 기억 인계로 우선 읽기 때문에 R16 정상 실행도 오판할 수 있었음.
- **수정**: R16 실무 최초 조사 증거를 `current_handoff` (현행 인계 문서 SHA) + `slack_thread` (지정 스레드 ts)로 조정. 이전 R13 출처는 R16을 대신할 수 없으며, 기타 R16 문서는 필요시 선택 호출로 별도 처리. 이 두 출처가 모두 존재해도 `형식 통과 · 진위 미검증`으로 남기고 실제 목표 수행/원본 진위는 별도 판정.
- **재현·검증**: `python3 -m unittest discover -s tests -q` **27/27 통과**. 로컬 파일 git blob SHA와 원격 재조회 값 정확히 일치: `audit_v2.py` `eb3387b724e32e352b7eef8655e8997a3b843eaa`, `tests/test_audit_v2.py` `0139caeb04e8e0a0b51532d447467a8ca12b611e`. 실제 22:00 회차 입력은 계속 **미검증**: 공식 per-run ID/원시 tool call ledger 미제공.
- 이 브랜치의 변경은 **검증기 코드/테스트**에만 적용. 현행 ChatGPT 매시간 정각 예약, 예약 프롬프트·알림, GitHub `main`, Activepieces 운영 플로우는 변경하지 않음.


## 2026-10-23 00시 — 실제 연결 앱 도구명 호환 수정
- 이번 정규 회차에서 실제 노출된 도구명은 `mcp__codex_apps__github_fetch_file` 및 `mcp__codex_apps__slack_slack_read_thread`였다. 기존 검증기는 별칭이 없는 과거 canonical 이름만 허용해, 향후 공식 원시 호출 로그가 제공돼도 정상 호출을 누락할 수 있었다.
- TDD 재현: 새 테스트가 패치 전 실패함을 확인한 뒤 최소 별칭 목록을 추가했다. 기존 이름과 현재 연결 앱 이름만 허용하며 임의 도구명은 계속 거부한다.
- 로컬 검증: 신규 회귀 1/1, 기존 회귀 27/27 통과. 이는 검증기 코드의 수동 테스트이며 정규 예약의 무인 성공 증거가 아니다.
- 원격 read-back: `audit_v2.py` blob `0a362a8f66c16d066c4dd35cb2258fd87e53ee6c`, 신규 테스트 blob `6e1623d0797473a34cdd21b0292095c40d45cb09`.
- 현재 00시 예약의 `run_details.last_run.id`는 제공됐지만 상태가 조회 시 `in_progress`였고, 같은 회차의 플랫폼 원시 tool-call ledger는 미제공이므로 정규 무인 성공은 계속 미검증이다.


## 2026-10-23 오전 — 종료 코드 0의 오인 위험 수정 · fail-closed
- 실제 재현: 공식 회차 ID와 원본 호출처럼 꾸민 **모의 자료**를 입력하면 이전 Python CLI가 `형식 통과 · 진위 미검증`이라 쓰면서 `exit 0`을 반환. 다른 자동화가 이를 **정규 예약 성공**으로 오해할 수 있었음.
- 수정: 출력 JSON 전체에 `official_success_verified=false`를 명시. **진위 불명인 형식 통과는 exit 3**, 아예 증거가 없는/부적합한 회차는 **exit 2**. 실제 플랫폼 인증이 없는 현재 검증기에서 **exit 0 사용 금지**. 이는 CLI를 호출하는 상위 자동화의 성공 판정 기준을 더 엄격히 만드는 하위 호환성 변경이므로 운영 파이프라인에는 자동 배포하지 않는다.
- 새 `tests/test_cli_exit_codes.py` 테스트 3개를 먼저 만들어 기존 코드에서 **3개 실패/오류를 확인**한 뒤 수정. 최신 원격 소스 및 기존 테스트를 완전한 Git blob SHA로 대조해 **로컬 회귀 테스트 35/35 통과**. 테스트는 수동 Python 오프라인이며 **ChatGPT Scheduled 정규 실행의 인증이 아니다**.
- 확인한 현재 원격 SHA: `audit_v2.py` **`07433beddad31fd72b5a8c66eae3e5f0e58d053f`**, `tests/test_audit_v2.py` `f174eea913c1484884aaba8124a02d80311d0dff`, `tests/test_connected_tool_names.py` `6e1623d0797473a34cdd21b0292095c40d45cb09`, `tests/test_cli_exit_codes.py` **`e417f706e9b8f760987d17de72708ad4863047f0`**. 네 파일 모두 실제 로컬 git blob hash 와 GitHub 원격 read-back 정확히 일치.
- **동시 변경 보존**: 이 작업 중 다른 개발 이력에서 발견된 `0eefa7e7434f046350b2ee8de5367aed4e7f352d` (날짜 소수부/잘못된 tool-call 타입/과다 로그 차단)와 관련 테스트 `5195114d4ca408cef8c43e617f8dede5ed670b12`를 확인·보존하고 통합 테스트에 포함했다.
- 유료 API·운영 Activepieces·기존 R16 예약 ID/일정/활성/프롬프트·GitHub main 변경 없음. R16 00:00 및 최신 회차 공식 개별 실행 ID와 플랫폼 원본 호출 로그는 여전히 현재 도구에서 미제공. **무인 성공 미검증**.


## 2026-10-23 10:56 KST — 최신 원격 43/43 전체 Python 회귀 독립 완료
- **이 검증은 사용자가 일반 채팅에서 '실행'을 지시해 수동으로 수행한 Python 오프라인 검사**이며, ChatGPT 기존 매시간 정각 예약이 무인으로 GitHub/Slack 업무를 수행했다는 증거가 아니다.
- 10:26 KST 무렵 격리 브랜치에 수정된 나노초 처리 코드를 실제 GitHub에서 조회: `audit_v2.py` blob `05fcfd2eac1b76d2e2f351e749a90647347a88aa` (commit `7b157aaaa2e8c5812181cd957a9bc2e5b3530b0c`), 신규 4개 나노초 순서 테스트를 포함한 `tests/test_audit_v2.py` blob `a1d68fbfad6c39218211f19a869c0f6f933726b6` (commit `5c92a3f73d252871dcb51274a1f95f4242cbdd00`).
- 기존 로컬 확인본(`audit_v2.py` SHA `70683e029c525462a55f013701be1e806e6b1e2d`)에 **위 두 실제 GitHub 커밋의 원본 patch만 적용**. 나머지 두 테스트 파일 `tests/test_cli_exit_codes.py` SHA `e417f706e9b8f760987d17de72708ad4863047f0`와 `tests/test_connected_tool_names.py` SHA `6e1623d0797473a34cdd21b0292095c40d45cb09` 그대로 유지.
- 최신 GitHub 원격 read-back SHA와 로컬 `git hash-object` 방식 SHA1 blob 해시 **네 파일 모두 4/4 정확히 일치**(파일명/내용이 다르면 전체 실행을 중단하도록 사전 검사).
- `python -m unittest discover -s tests -v`를 격리 로컬 Python으로 직접 실행: **Ran 43 tests / OK / exit 0 / failures 0**, 전체 실행 로그 보존. 나노초 역전·종료 후 호출·10자리 소수부 거부 테스트 4개 포함.
- **통과 의미 구분**: 이 `exit 0`은 `unittest` 코드 품질 검사 성공이지, `audit_v2.py --input`로 판단하는 *공식 ChatGPT 예약 무인 성공*이 아니다. 후자는 별도 공식 per-run ID/원본 호출 없이 항상 `official_success_verified=false`.
- 기존 ChatGPT R16 예약 ID `6acb017062a08191a4136238b78b313a`, 한국시간 매시간 정각, 활성화/알림/프롬프트 및 GitHub main·Activepieces 운영 플로우·유료 API 변경 없음.
