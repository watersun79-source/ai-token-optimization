# R16 무인 예약 실행 증거 대조기 — 격리 개발 브랜치

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

실측 22:00 입력은 공식 native_run=null, tool_calls=[]여서 정상적으로 "미검증: 공식 개별 회차 원본 로그 미제공" 판정한다. CLI 미검증은 종료 코드 2, 형식만 통과 시 0이지만 원본 신뢰성 확인이 필요하다.

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
