# Activepieces R16 무인 원본증거 안전 검사 — 격리 적용 (2026-10-22 23:54 KST)

## 실제 연결에서 확인한 현재 상태
- Activepieces 인증 연결 프로젝트에서 플로우 12개, 그중 운영 활성 플로우는 기존 `Slack` (`vtRwEYmcwDTunBZut265G`) 1개. 그 기존 플로우를 건드리지 않았다.
- 새 격리 플로우 `MOCK ONLY · AI R16 evidence verifier · isolated`
  - 플로우 ID: `zgSopq6Txh68wxsDc5K5Z`
  - [Activepieces 플로우 열기](https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/zgSopq6Txh68wxsDc5K5Z)
  - 상태 `DISABLED`, `published=false`, 단계 2/2 구성 정상. 기존 ChatGPT 정규 예약과 연결하지 않았다.
  - 구조: `catch_webhook` 트리거(`authType:none`; **테스트 초안으로 비활성**, 게시 금지) → `CODE` JavaScript 단일 로컬 확인 단계. 외부 서비스 호출·개인정보 저장·생성형 모델 호출 없음. 재시도 꺼짐. 운영 승격 전에 반드시 인증(HMAC 등)·요청 제한·비용·보안 별도 점검.
  - 입력: webhook mock `body` 객체. 검증용 봇 단계는 `{{trigger['output'].body}}`를 읽는다.
- 설정 검증: Activepieces `ap_flow_structure` 단계 2/2 valid, `ap_validate_flow` `valid=true`, 이슈 0.

## 실제 TESTING 환경 회귀 결과 (3/3)
| 케이스 | Activepieces flow run ID | Activepieces 실행 상태 | 코드 판정 |
|---|---|---|---|
| 공식 회차 원본 로그 누락 | `Q01QONuRJvVg3HZqJ5ZFA` | `SUCCEEDED` (`TESTING`) | `UNVERIFIED`, official_success_verified=false |
| 예약 ID 불일치 | `HU4w4PsGavmBmvV2MsZd9` | `SUCCEEDED` (`TESTING`) | `UNVERIFIED`, official_success_verified=false |
| 형식상 일치하는 가짜 회차+앱 호출 로그 | `kSuV3wqjJUYZQqu3oD0Vt` | `SUCCEEDED` (`TESTING`) | `UNVERIFIED`, `format_check=PASS`, `authenticity=UNVERIFIED` |

각 회차에서 `ap_get_run`으로 `step_1` 원본 출력까지 재확인했다. 3건 모두 `external_calls=0`; Activepieces 실행 성공은 **모의 검증 단계 성공**이지 ChatGPT Scheduled 공식 정규 AI 실행 성공이 아니다.

## 공개 구현 분석과 적용 이유
- Activepieces 공식 소스 [TriggerSource/TriggerEvent 구조](https://github.com/activepieces/activepieces/blob/main/brain/knowledge/flows-execution/triggers.md): Enabled WEBHOOK 등의 트리거 관리 및 테스트/운영 구분이 필요.
- Activepieces 이슈 [#14621](https://github.com/activepieces/activepieces/issues/14621): Wait for Response + Retry on Failure로 서브플로우 호출이 반복될 수 있었음. 이 플로우는 서브플로우·재시도 없음.
- Activepieces 이슈 [#14328](https://github.com/activepieces/activepieces/issues/14328): 트리거 OAuth 에러 등은 flow run이 생성되지 않을 수도 있어 `run_count=0`만으로 실패/성공 단정 불가.
- Activepieces 이슈 [#15626](https://github.com/activepieces/activepieces/issues/15626): 하위 작업 내부 오류·재시도와 부모 상태 불일치 사례. 따라서 프로덕션 예약/워크플로우는 수정하지 않고 격리 구조에서만 확인.

## 분명한 한계와 다음 목표
- 현재 Activepieces는 자기 플로우의 run ID와 실행 로그만 보여준다. ChatGPT Scheduler의 `official_task_run_details` 원본 run ID나 도구별 호출 로그를 대신 제공하지 못한다.
- 이 격리 플로우에는 **외부 앱 증거 자동 수집·매시간 트리거가 없다**. 독립 인증 원본이 제공되기 전에는 어느 입력도 ChatGPT 무인 성공으로 판정하지 않는다.
- 다음 실제 목표: ChatGPT Scheduled 원본 22:00/23:00 회차 결과가 공식적으로 조회 가능한 경로·권한을 확보한 뒤, 같은 회차의 GitHub SHA/Slack ts로 검증한다. 자료가 없으면 `미검증` 유지.

## 보호 준수
기존 R16 ChatGPT 예약 활성·정각·프롬프트·알림을 변경하지 않았다. 기존 Activepieces 11개 플로우의 설정을 바꾸거나 게시·중지·삭제하지 않았다. 새 격리 모의 플로우 1개만 추가해 **DISABLED/미게시**로 유지한다. GitHub `main` 수정, 유료 API 호출, 비밀키 변경 없음.
