# 예약 실행 및 병렬 합류 후속 조사 — 2026-10-18

## 이번 회차 목표
이전 보고서의 미완료 목표를 이어서, Activepieces의 실제 실행 로그와 비운영 병렬 합류 테스트 증거를 읽기 전용으로 조사한다. 운영 플로우·연결·스케줄은 변경하지 않는다.

## 확인한 예약 작업
- 기존 ChatGPT 자동화 `AI`: enabled=true, schedule `FREQ=HOURLY;BYMINUTE=0;BYSECOND=0`, timezone Asia/Seoul. 기존 예약 ID `6acb017062a08191a4136238b78b313a`.
- 스케줄/알림 설정은 변경하지 않았고 중복 예약을 만들지 않았다.
- 기록된 last_run_time은 `2026-10-18T00:03:04.511990Z`. 이 값은 예약 관리자가 제공한 마지막 실행 시각일 뿐, 특정 실행 산출물의 성공을 입증하지 않는다.

## Activepieces 상태 및 실행 증거
- 현재 연결된 Activepieces 도구는 10개 플로우를 반환: ENABLED/published 3개, DISABLED 7개.
- 활성 운영 흐름 `AI 3AI 협업` (`kt2N9yCVA3dLkFiNPSMsH`)의 조회 가능한 PRODUCTION 실행은 0개. 따라서 실제 최근 운영 실행을 이 도구에서 입증하지 못했다.
- `Gemini + Claude 협업 비서`의 최신 5개 조회 결과는 2026-10-15 UTC이며 모두 SUCCEEDED. 이는 최근 시간별 실행의 증거가 아니다.
- 연결 목록에는 OpenAI, Google Gemini(두 개 라벨), Slack, Anthropic Claude가 ACTIVE로 표시된다. ACTIVE는 인증/연결 상태일 뿐 무료 한도 또는 결제 위험이 없다는 증거가 아니다.
- 현재 도구에는 프로젝트 ID를 독립적으로 확인하는 프로젝트 목록/컨텍스트 선택 기능이 노출되지 않는다. 저장된 프로젝트 URL은 참조로만 사용하며, 현재 연결 대상 프로젝트와 동일하다고 확정하지 않는다.

## 비운영 병렬 합류 검증
### TEST ONLY · Concurrent Join Parent
- Flow ID: `4BrtUZsKexpdxjIpWMtYR`, 현재 DISABLED/draft.
- 정적 검증: 6/6 단계 valid, issues 0.
- 테스트 실행 `KYDtzNjTMeO530TzxVwgk`: TESTING, SUCCEEDED, 19.5초.
- 최종 검증 단계에서 해당 testId의 매칭 이벤트 4개 확인.
- 이 플로우는 child flow 두 번을 비동기 디스패치한 뒤 bounded wait 및 테이블 기록을 확인한다. 이는 비운영 child-dispatch/event-record 패턴의 증거이며, 실서비스 AI 제공자 병렬 호출을 증명하지 않는다.

### MOCK ONLY · Promise.all 병렬 합류 검증기
- Flow ID: `jRWo1ktjzHHgoLcrPSyzx`, 현재 DISABLED/draft.
- 정적 검증: 2/2 단계 valid, issues 0.
- 최근 조회 가능한 TESTING run `w3beLx8xbT77tMR4amo1h`: SUCCEEDED. 이 테스트는 코드에 명시된 synthetic in-memory 작업이며 네트워크/AI provider 호출이 없는 mock이다.
- 이 결과는 Promise.all mock contract/timing 테스트의 실행 증거이지, Activepieces 엔진의 AI 호출 병렬성이나 실제 모델 비용/품질 증거가 아니다.

### TEST ONLY · Polling Join Parent
- Flow ID: `4a8OSFX1yERP6TZ9D0Hob`, 현재 DISABLED/draft.
- 테스트 실행 `yLtbcaYHamVYSxTHUeKk4`: TESTING, SUCCEEDED, 23.9초.
- 최종 단계는 동일 testId의 child event 2개를 확인했고, 마지막 검사에서 terminalA=true, terminalB=true, ready=true를 반환했다. 초기 polling 회차에서는 이벤트가 아직 없었으나 후속 회차에서 양쪽 완료를 확인했다.
- 이 테스트는 비운영 join/readiness 흐름의 증거다. 실서비스 AI provider 병렬 실행을 입증하지 않는다.

## 비용 및 안전
- 이번 조사 중 모델 제공자 API 호출: 0.
- 구매/업그레이드: 0.
- 플로우 수정, 게시/활성화, 연결 변경, 예약 변경, `main` 변경: 없음.
- 비밀값은 보고서/Slack에 복사하지 않는다.

## 상태 판정
- 완료: 기존 예약의 enabled/hourly schedule 읽기 확인; Activepieces 흐름/연결 읽기 확인; 세 종류의 비운영 테스트 실행 결과 확인; 두 join flow의 정적 검증.
- 미확인: 예약 관리자가 보고한 마지막 실행의 실제 산출물; 현재 도구의 대상 Activepieces 프로젝트 ID; 실서비스 ChatGPT/Gemini/Claude 병렬 호출; 런타임에서 유료 API 호출을 기술적으로 차단하는지 여부.
- 중요 차이: `SUCCEEDED` run status는 각 run이 오류 없이 끝났음을 뜻할 수 있지만, 비즈니스 acceptance assertion은 별도로 확인해야 한다. 이번에는 testId, terminal flags, matched-event counts를 확인했다.

## 다음 목표
1. 프로젝트 ID를 읽기 전용으로 식별할 수 있는 UI/connector 경로 확인. REST API 키 또는 유료 호출은 사용하지 않는다.
2. 예약 자동화의 실제 실행 산출물을 scheduler UI 또는 연결된 읽기 전용 로그 경로에서 확인한다.
3. 실제 AI-provider 병렬성은 비용이 검증된 무료 경로가 확인되기 전에는 호출하지 않는다. 비운영 mock/child-join 테스트는 비활성 상태로 유지한다.
