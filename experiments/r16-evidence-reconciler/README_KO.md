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
