# AI R14 — 기존 매시간 예약에 3역할 협업 적용 + 개인화 봇 TOP10 (2026-10-22 KST)

## 승인·대상
사용자 최신 요청: "기존 예약 ai 에 적용 시키고. 나에게 맞는 맞춤형 추천 붓 알려줘 top 10개?"
기존 ChatGPT 예약 `6acb017062a08191a4136238b78b313a`의 **지침만 R13→R14 수정**, 신규 예약 없음. `automations.update` 성공 응답 및 `automations.peek` 독립 재조회: `is_enabled=true`, `Asia/Seoul`, `RRULE:FREQ=HOURLY;BYMINUTE=0;BYSECOND=0`, `timing_mode=exact_schedule`, 제목 AI 유지. `notifications_enabled=false`, `email_enabled=false` 값 변경 없음. 직전 `last_run_time=2026-10-22T09:01:17.429101Z` (18:01:17 KST)은 **R14 수정 전** 실행 시각 메타데이터로 R14 정규 실행 성공 증거가 아님.

## R14 새 지침
- 최고 우선: `docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md` → 관련 GitHub/Slack 원본 및 SHA → 실제 플랫폼 정규 회차 ID·원시 호출 로그가 없으면 무인 복원 미검증. 수동 조회/코드 CI/Activepieces 자체 체크포인트를 공식 예약 성공과 혼동 금지.
- 신규 AI 프로젝트 개선 과제가 있는 경우에만 `ResearchBot(공식자료·OSS·무료/라이선스 조사)` → `BuilderBot(안전한 최소 수정)` → `VerifierBot(원본·회귀 테스트·SHA·비용 검증)` 조건부 적용. 단순 질문은 직접 답하고 중복 실행은 건너뜀.
- 기존 ChatGPT 개인 플러그인 `AI 3봇 협업 v0.1.0`(ID `plugins_6ad9d7b745448191bb087af817f02f68`) 및 GitHub 샌드박스 코드 참조. **실제 모델 세 개가 자동 호출된다는 뜻은 아님**. 플러그인 호출/원격 LLM 호출은 접근·승인·원본 도구 로그 없으면 미검증.
- 유료 API·결제·키 노출·안전 검사 우회 금지. 원래 Activepieces 운영 플로우·다른 예약·GitHub main에 이번 작업으로 직접 변경 없음. 정규 R14 다음 실행/무인 저장 성공은 아직 미확인.

## 사용자 맞춤 추천 TOP10 (주관적 운영 우선순위, 벤치마크 순위 아님)
| 순위 | 추천 봇 | 이유 | 당장 활용 방식 |
|---|---|---|---|
| 1 | 기억 복원 봇 | 새 채팅·예약 간 작업 맥락 복원 | GitHub 최신 인계+Slack 읽기 |
| 2 | 예약 증거 감사 봇 | 정규 무인 성공 오판 방지, 최우선 미검증 해결 | 공식 회차/원시 로그 출처 대조 |
| 3 | 오류 진단·수정 봇 | 원인 분석 후 최소 자동 수정 | 격리 GitHub 브랜치+로컬 테스트 |
| 4 | 코드 검증·회귀 봇 | 변경으로 인한 품질 저하 차단 | Python unittest/pytest·GitHub Actions |
| 5 | 공식 자료·오픈소스 조사 봇 | 타인 구현 재사용, 근거·라이선스 확인 | GitHub·공식 문서·웹 |
| 6 | 자동화 설계 봇 | Activepieces 흐름 실험과 배포 전 위험 분석 | 비운영 mock/draft 검증 |
| 7 | 비용·비밀정보 보안 봇 | 유료 호출 차단·무료 한도 확인 | 정적 가드·권한 확인 |
| 8 | GitHub 변경·PR 관리 봇 | 안전한 저장·CI·SHA/리뷰 절차 | 브랜치·PR·읽기 재조회 |
| 9 | AI 모델 교차 검토 봇 | ChatGPT/Gemini/Claude 실제 접근 시 품질 교차 검토 | 무료 사용 근거 확인 전 API 사용 0 |
| 10 | 품질·토큰 최적화 봇 | 최소 호출·효율·오류 감지와 결과 시각화 | 실제 측정 기반 회귀·보고 |
네트워크 외부 모델 10개를 생성하거나 추가 예약을 만드는 추천은 아님. 한 ChatGPT 운영 워크플로의 조건부 전문 역할을 뜻함. 1→4 우선, 5→10은 필요할 때만 호출.

## 공식 검증·라이선스 참고
- ChatGPT 예약작업: https://help.openai.com/en/articles/10291617-scheduled-tasks-in-chatgpt
- ChatGPT 플러그인 사용: https://help.openai.com/en/articles/20001256-plugins-in-chatgpt (자동 선택 가능하나 매회 보장 아님)
- LangGraph MIT: https://github.com/langchain-ai/langgraph/blob/main/LICENSE
- CrewAI MIT: https://github.com/crewaiinc/crewai
- pytest MIT: https://github.com/pytest-dev/pytest
- Activepieces Community Edition MIT; 클라우드/기업 기능 일부 상용: https://github.com/activepieces/activepieces/blob/main/docs/about/license.mdx
- Aider Apache-2.0; 실제 모델 연결 비용은 별도: https://github.com/Aider-AI/aider
이들은 도입된 의존성이 아니라 공식·오픈소스 비교 후보. 추가 설치·API 호출 없음.

## 다음 독립 검증
R14 **다음 실제 정규 예약**에서 GitHub·Slack 원본·3역할 실제 수행 여부를 같은 공식 회차에 묶어 검증할 수 있을 때만 성공으로 기록. 이번 수동 지침 수정은 코드 CI/공식 정규 회차/무인 저장의 성공 근거가 아님.
