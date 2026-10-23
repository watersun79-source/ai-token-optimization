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


## 후속 보안/안정성 패치 — 2026-10-23 06시 KST
- **이전 버전에서 실제 오류 재현**: JSON 도구 호출 `target: "constructor"` 가 JS 일반 객체의 상속된 속성으로 잘못 통과하여 `cfg.pattern.test` 접근에서 `TypeError: Cannot read properties of undefined (reading 'test')` 발생. Activepieces TESTING 실패 run ID `H1cS2Vs7dTLwk8FRAf0Ek`. 운영 플로우가 아니라 기존 비활성·미게시 격리 플로우에서 재현.
- **실제 패치**: `Object.prototype.hasOwnProperty.call(checks,c.target)` 검사로 `constructor`, `toString`, `__proto__` 등 상속 키를 거부. 입력 도구 호출 목록은 최대 16건으로 제한하고, 배열·비문자 target도 검증 전 거부. `external_calls=0`, `official_success_verified=false`의 fail-closed 정책 유지.
- **변경된 코드 원본**: [activepieces_mock_guard_2026-10-23.js](activepieces_mock_guard_2026-10-23.js), GitHub blob SHA `b1e35d29f0b9ce623d5696495d4ff76f9abf2a10`; 원격 재조회 후 Activepieces `ap_read_step_code`와 내용 일치.
- **수정 후 TESTING 직접 실행 + 단계 출력 재조회 5/5 통과**:
  - 이전 오류 `constructor` 케이스: `rmGy0IulUCq6L9QFcdoS4`, `UNVERIFIED` (더 이상 단계 실패 없음)
  - 원본 회차 ID 누락: `DLB6ZzWh0pCrCDAruf6mH`, `UNVERIFIED`
  - 형식만 맞춘 가짜 원본 증거: `bUXxCDXFbQL8iborBMliH`, `format_check=PASS`이나 `official_success_verified=false`, `authenticity=UNVERIFIED`
  - 예약 ID 불일치: `OFJsfrVjxMwP33eoGMoWS`, `UNVERIFIED`
  - 17건 과다 호출 입력: `gwoWTJ27DoZQo72oGuYFS`, `UNVERIFIED`
- **밤사이 상태**: 2026-10-23 06:00:49 KST `automations.peek.last_run_time` 확인, 예약 활성 유지. Activepieces 감사 테이블의 `scheduledSlotKst`에 `2026-10-23` 기록 0건. Slack 지정 스레드·채널의 자정 이후 새 증거 0건. ChatGPT의 공식 per-run ID·원시 앱 호출 로그가 없으므로 **정규 무인 성공 미검증**.
- 기존 Activepieces 운영 플로우 및 격리 플로우의 `DISABLED/published=false` 상태, ChatGPT 예약 일정, GitHub `main`, 유료 API 모두 변경 없음. 위 테스트는 수동 모의 TESTING 실행이며 생산 자동화가 아니다.


## 2026-10-23 06시 이후 — 유효하지 않은 날짜 정규화 버그 수정
- **수동 Activepieces TESTING에서 발견한 실제 결함**: JavaScript `Date.parse("2026-02-30T22:00:00+09:00")`가 존재하지 않는 2월 30일을 3월 2일로 정규화. 모의 원본을 꾸미면 검증기에서 잘못 `format_check=PASS` 처리될 수 있었음. 실패 재현 테스트 run ID `tn2GQJrDnnqswEyKjSzNb`의 실제 출력 `FORMAT_MATCH_ONLY`.
- **격리 코드 수정**: 정규 ISO-8601 입력 및 윤년·월별 실제 날짜·시분초·시간대 오프셋을 먼저 검사한 뒤 UTC 시각 계산. 비정상 날짜는 `UNVERIFIED: Invalid timezone-aware scheduled slot`으로 차단. `Date.parse`의 부정확한 날짜 자동 정규화 경로 제거.
- **모의 회귀 6/6 직접 실행·각 run step_1 원본 재조회**:
  - `sY1Jel7pTGI8wPxxLGDRe` 불가능한 2월 30일 → 미검증/날짜 오류
  - `B3qxXihKkzKYIFk0WlIxa` 평년 2월 29일 → 미검증/날짜 오류
  - `ZD7052otvIep1o0slJX3O` 실제 윤년 2028-02-29 → 형식 통과·원본 미인증
  - `AfE951KFQrFmIzgOMHAL8` 정상 2026-10-22 샘플 → 형식 통과·원본 미인증
  - `f5qnUmJcGo3uShJqMM70P` 공식 실행 ID 누락 → 미검증
  - `vulqtYLylYdDnAgNnUp2F` +25:00 시간대 → 미검증/날짜 오류
- 모든 회차 Activepieces 자체 테스트 `SUCCEEDED`, 출력 `official_success_verified=false`, `external_calls=0`; ChatGPT 실제 무인 실행 성공이 아니라 mock 검증기 자체 품질 검증임.
- 격리 JavaScript 코드와 GitHub 원격 read-back 일치. [소스](activepieces_mock_guard_2026-10-23.js) blob SHA `262d0e25ec84a6d29be59d22f6bbadbc939c433d`.
- 기존 정규 R16 예약(매시간 정각/활성), GitHub `main`, 운영 Activepieces, Slack 운영 설정은 변경 없음. 격리 플로우는 비활성·미게시 유지.


## 후속 조사 — 2026-10-23 06:29 이후, 00시 회차 연관 가능 커밋 발견
- 기존 `main` 및 기억 브랜치에서 자정 이후 커밋 0건이라고만 말하면 **불완전**하다. 격리 개발 브랜치 `ai/r16-evidence-reconciler-2026-10-22`에서 **00:07:21 KST** `f5986dbc7f9f1f6ca04f94d1823709ab7c7875c6` (도구명 추가 테스트), **00:07:44** `a5d54e757887d16b51868c8177334e0992b65a32` (Python 검사기 별칭 허용), **00:08:10** `f7a2cfbb30288feffee122ca0528281a048a6892` (문서) 3건을 GitHub 커밋 원본으로 확인했다. 실제 GitHub 사용자 계정에 귀속되어 있으나 `commit.verification.verified=false` (unsigned). **스케줄러 공식 개별 회차 ID와 해당 커밋을 연결하는 독립 원본 로그가 없으므로 무인 실행 성공 확정은 아님.**
- 00:08 문서에는 예약 세션에서 `mcp__codex_apps__github_fetch_file`, `mcp__codex_apps__slack_slack_read_thread` 이름으로 연결 앱을 봤고 `run_details.last_run.id` 메타데이터가 있었다는 당사 서술이 존재한다. **문서 자기 보고이지 플랫폼 공식 실행 기록을 현재 채팅에서 재조회한 것이 아님**.
- 새로 발견한 **실제 코드 정합성 오류**: Python `audit_v2.py`는 00:07부터 이 별칭을 허용하지만 Activepieces `MOCK ONLY` 검사기 코드는 옛 도구명만 인정. 테스트 `o4UG1IpKOrd4AMX7hS1Mv`에서 새 이름 GitHub·Slack 2개를 모두 `missing`으로 잘못 판정.
- **격리 Activepieces 안전 패치**: 허용 목록을 옛 이름과 새 이름 각각 정확히 두 개씩으로 좁혀서 추가하고, `cfg.tools.includes(c.tool)` 검사로 교체. 등록되지 않은 도구명은 여전히 거부. 기존 상속 키/윤년·날짜/오프셋 입력 방어 그대로 유지. **절대 ChatGPT 공식 실행이 확인됐다는 의미는 아님**.
- 직접 `TESTING` 환경의 모의 실행 5/5 및 각 `ap_get_run` 원본 출력 독립 조회:
  - 새 별칭 `uEZfY1i2YFloKW6kcD9h2` → `FORMAT_MATCH_ONLY`/진위 `UNVERIFIED`.
  - 기존 canonical `dZgpLvoOPG4rAYf0N6w3n` → `FORMAT_MATCH_ONLY`/진위 `UNVERIFIED`.
  - 임의 이름 거부 `XKys8C8mL5QlGazMCfT1w` → `UNVERIFIED`, `current_handoff` 누락.
  - 불가능 날짜 거부 `O58jdABHljnTMtBN2Axq6` → `UNVERIFIED`.
  - 공식 개별 회차 ID 누락 `shobjWOHf76utpKgtkB9W` → `UNVERIFIED`.
- 5개 모두 `official_success_verified=false`, `external_calls=0`; 새로운 외부 모델 호출이나 운영 연결 없음. 소스 [activepieces_mock_guard_2026-10-23.js](activepieces_mock_guard_2026-10-23.js)와 Activepieces step_1 실제 소스 독립 대조/원격 GitHub blob SHA `ffd1b3f351808f22bcab4feec5f42762e0f6ebea`.
- ChatGPT 기존 정규 AI R16 활성/Asia/Seoul 매시 정각/원래 일정 유지. 격리 플로우는 `DISABLED`, `published=false`; 기존 운영 Slack flow, GitHub `main` 보호.


## 2026-10-23 오전 — JS/Python 호출 로그 한도·정각 정밀도 동기화
- **수동 ChatGPT 채팅에서 수행한 격리 검증**, 정규 예약 무인 회차의 실행 결과가 아니다.
- 직접 재현한 2개 버그:
  1. Python `audit_v2.py`는 기본 2건 + 15건 보조 로그, 즉 17건을 유효 범위로 처리(최대 1024건). 반면 격리 Activepieces JS는 **16건 초과 전부 거부**. 패치 전 Activepieces MOCK TESTING run `Cu3LhqTJjKWmUW6Hmgs3h` → `Too many tool calls`.
  2. Python 검증기는 예약 시각의 microsecond가 0이 아니면 거부하지만 JS 정각 정규식은 `09:00:00.500`도 형식 통과. 패치 전 MOCK run `mZWYX0E1gvuqK7pM9eMgv` → `FORMAT_MATCH_ONLY`로 오판.
- **최소 수정**: 격리 JS CODE만 `calls.length > 1024`로 상한 일치, 예약 정각은 초 `00` + 선택적 소수부 **0만** 허용(`(?:\\.0+)?`), 기존 달력/윤년·정확한 도구명 허용·상속 키 방어·미인증 결과 유지.
- 수정 후 `ap_test_flow` + `ap_get_run` step 원본 6건 모두 Activepieces `SUCCEEDED`. 결과는 항상 `status=UNVERIFIED`, `official_success_verified=false`, `external_calls=0`:
  - 17건 정상 `J2cMxmAaLIYqkM1tFdfRJ` → `FORMAT_MATCH_ONLY`
  - 1024건 상한 `XNUj1IsY83WL6DaiOYnwf` → `FORMAT_MATCH_ONLY`
  - 1025건 초과 `Zi52El9M1DOD7scgWgHu9` → 안전 거부
  - 잘못된 `.500` 예약 시각 `W2YiqvZo4l6PwCXdCy2DH` → 안전 거부
  - 올바른 `.000` 예약 시각 `HWxoQTpM0POf9N0ExuQSI` → `FORMAT_MATCH_ONLY`
  - 공식 per-run 원본 없음 `Cw5hFyK8rtNUXlHcX7wsu` → 미검증
- 격리 JS Live CODE와 GitHub 원격 소스 exact read-back 일치; [동기화 소스](activepieces_mock_guard_2026-10-23.js) Git blob **`f75bd4ccc4934032cc5ab62b8ea52ed26545be49`**, commit **`cc04dcd0019857014359135a67722ec32b7425cb`**.
- 기존 단일 ChatGPT AI 예약 R16 `6acb017062a08191a4136238b78b313a`는 `is_enabled=true`, Asia/Seoul 매시 정각 유지. Activepieces 격리 flow `zgSopq6Txh68wxsDc5K5Z`는 **DISABLED·unpublished**; 운영 Slack 플로우 `vtRwEYmcwDTunBZut265G` 그대로 ENABLED. GitHub `main`, Activepieces 운영 플로우/연결, 예약 설정/알림, 과금/API 변경 없음.
- `FORM MATCH`는 원본 진위 인증이 아니다. 공식 ChatGPT 개별 예약 run ID 및 동일 회차 tool-call 원본이 없어 **무인 GitHub/Slack 업무 성공은 미검증**.



## 2026-10-23 오전 10시대 — 소수초 정밀도 손실 결함 수정 (격리 MOCK ONLY)
- **사전 재현**: JS `time()`이 ISO-8601 1~9자리 소수초를 `Date.UTC`의 밀리초(3자리)로 자르면서, 완료 시각 `10:00:02.000100+09:00` 이후 `10:00:02.000900+09:00`의 원시 호출을 같은 `10:00:02.000`으로 오인. 사용자 수동 ChatGPT 대화에서 비활성·미게시 격리 플로우에 가상 payload를 넣어 재현: Activepieces `TESTING` run `MSkp2Ej3BfBzI9wMW1KrK`, 실제 `format_check=PASS` (오판).
- **실제 최소 수정**: 입력된 1~9자리 소수초를 **정수 BigInt 나노초**로 변환해 UTC 시각을 비교하고, JSON 출력에는 BigInt를 포함하지 않도록 유지. 유효하지 않은 시각은 `null`로 차단. 슬롯/시작·종료/동일 회차 호출 시각을 모두 새 정밀도 비교에 적용. JS 판정 `status=UNVERIFIED`, `official_success_verified=false`, `external_calls=0` 불변.
- 수정 커밋 `dd756f0c03482b73e8a718663acc79303ee7f1b9`, GitHub JS blob SHA `d98d9842191e4e17753c56620800c7eca541e0b9`. Activepieces `ap_update_step`로 **같은 격리 CODE step_1만** 적용하고 `ap_read_step_code`/GitHub `fetch_file` **문자열 완전 일치** 확인. `ap_validate_flow valid=true` (2/2), `ap_list_flows status=DISABLED`, `published=false`.
- **수정 후 Activepieces TESTING + 각 `ap_get_run` 단계 출력 독립 재조회 3/3 통과**:
  - `4ftbYULAS5atOy2aCL4hx`: 종료 후 **800μs** 호출 → `Same-run tool-call evidence missing`, `missing=[slack_thread]`, 형식 PASS 오판 제거.
  - `ICTmdi4XnSLFlFFgk7AAG`: 종료 전 **50μs** 호출 → `FORMAT_MATCH_ONLY`, `format_check=PASS`, 하지만 `authenticity=UNVERIFIED`.
  - `Op8TOl8FmtqVusbJAV6GS`: 종료 후 **800ns** 호출 → `Same-run tool-call evidence missing`, `missing=[slack_thread]`.
  - 세 회차의 **Activepieces 실행 환경은 TESTING**, 샘플 payload의 `run_id=SYNTHETIC-NOT-A-REAL-CHATGPT-RUN`. 모든 출력 `official_success_verified=false`, `external_calls=0`. 이는 ChatGPT 정규 예약 실제 무인 실행이 아니라 **모의 검증기 회귀 결과**다.
- ChatGPT 기존 AI 예약 ID `6acb017062a08191a4136238b78b313a` 읽기 전용 `automations.peek`: `is_enabled=true`, `paused_count=0`, `last_run_time=2026-10-23T01:00:54.365515Z` (=10:00:54 KST), Asia/Seoul 정각 유지. 예약 종료 성공 또는 네이티브 개별 회차/앱 호출 증거가 아님. 별도 Activepieces AUDIT 10/23 기록 `count=0`.
- 예약 ID·프롬프트·주기·알림/기존 운영 Activepieces flow/연결·GitHub main·비밀/유료 모델 API 변경 없음. **정규 ChatGPT 무인 GitHub/Slack 성공: 미검증**.
- **다음 목표**: 공식 ChatGPT `Scheduled → AI → Previous runs`의 개별 회차 원본 및 같은 회차 앱 호출 감사 로그를 실제 제공 가능한 권한 있는 도구로 확보할 수 있을 때만 검증. 기존 예약/운영 플로우 쓰기·권한 우회 금지.
