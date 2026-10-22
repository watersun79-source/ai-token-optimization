# AI 현재 인계 — 현행 예약 R16 / 이전 R15·R13 이력 (2026-10-22)

## 최신 후속 — R16 첫 회차 도래 후 검증기 결함 수정 (2026-10-22 23시 이후, 수동 채팅)
- **예약 원본 직접 재조회**: 예약 ID `6acb017062a08191a4136238b78b313a` / `is_enabled=true` / `Asia/Seoul` 매시간 정각 / 프롬프트 첫 줄 `[AI R16 ...]` / `last_run_time=2026-10-22T14:00:27.196513Z` (= **23:00:27 KST**). 이 값은 실행 시각 메타데이터이지 예약 실행 성공·공식 회차 ID·앱 호출 성공 근거가 아니다.
- **실제 신규 코드 버그 해결**: 기존 격리 감사 검증기는 매시 정각의 `last_run_time`이 갱신된 후에 **과거 회차 22:00의 원본 실행 증거를 뒤늦게 대조하면 부당하게 미검증 처리**하는 false-negative 가능성이 있었다. `ai/r16-evidence-reconciler-2026-10-22` 브랜치 `experiments/r16-evidence-reconciler/audit_v2.py`에서 최신 `last_run_time`을 공식 개별 실행 증거의 필수조건이 아닌 진단값으로 분리했다. 스케줄러 원본 `native_run` 및 같은 회차 호출 증거가 실제 제공될 때 과거 회차도 대조 가능. 단, 원본이 없으면 계속 `미검증`.
- **직접 회귀 테스트 23/23 통과**(수동 Python, 무료, 실제 예약 실행 증명 아님). 원격 소스 GitHub blob SHA `86d90166b8c8ed18162fd097583c5d506e23cd09`, 테스트 SHA `8b8cb06194125737eb827bcc731c5192dca6dc74` 독립 재조회 확인. [격리 브랜치 README](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/README_KO.md).
- **엄격한 운영 판정**: 22:00 및 23:00 공식 개별 회차 ID/앱 원시 도구 호출 로그는 현재 노출 도구에서 미제공. Activepieces 자체 기록·GitHub CI·수동 앱 읽기/쓰기 기록을 ChatGPT 공식 예약 무인 증거로 대체할 수 없다. 예약 성공의 **완료 판정은 여전히 미검증**.
- **보호**: 기존 예약·프롬프트·시각·알림·운영 Activepieces·GitHub `main`은 변경하지 않았다. 변경은 격리 실험 브랜치 코드와 이 읽기 전용 운영 인계 문서 갱신뿐이다. 이전 21:17 R16 섹션은 당시의 역사적 사실이며 최신 상태는 이 단락을 우선한다.

---


## 최상위 현재 상태 — 예약 R16 실제 재조회 (2026-10-22 21:17 KST)

- **사용자 최신 직접 지시**: "예약 ai 적용. 진행"에 따라 기존 예약 `6acb017062a08191a4136238b78b313a`의 **실행 지침만 R15→R16** 갱신. 이번 후속 "진행"에서 `automations.peek`로 R16 문구, `is_enabled=true`, 제목 `AI`, `Asia/Seoul`, `RRULE:FREQ=HOURLY;BYMINUTE=0;BYSECOND=0`, `timing_mode=exact_schedule`, 알림·메일 모두 기존 false 직접 확인. ID·일정·활성·운영 플로우·main에 변경 없음. 새 예약 생성/중지 없음.
- **최신 R16 적용 문서 원본**: `docs/ai/AI_R16_SCHEDULED_CONNECTED_APPS_2026-10-22.md` (이 업데이트 직전 GitHub blob SHA `f316d547d9914f48eed71da4f1ed879ad20c4fef`) 및 지정 Slack 부모 스레드 `C0C9649RQAZ / 1792416391.631669`의 R16 적용 메시지 `ts=1792671311.625679` 읽기 전용 대조 완료.
- **작업 내용**: 개인 플러그인 `ai-chat-bot-team` **v0.5.0**의 `ai-connected-tools` 스킬을 통해 예약 실행 환경에서 *실제로 제공되는 경우에만* GitHub/Slack 연결 앱 도구를 필요에 따라 선택하고 GitHub SHA·Slack ts를 원본 재조회한다. 필요 TOP10 역할만 사용하고 중복 검사·유료 제공자 생성·운영 변경·비밀 출력은 금지. 일반 수동 채팅에서 도구를 사용한 성공은 R16 무인 실행의 증거가 아님.
- **실행 증거 경계**: `last_run_time=2026-10-22T12:01:45.281530Z` (=21:01:45 KST)은 **R16 지침 갱신(12:13~12:14Z) 전**의 마지막 실행 시간 *메타데이터*다. 현재 조회 시각은 21:17 KST로 **R16 갱신 이후 첫 매시 정각 예정 회차는 22:00 KST**. 새 R16 무인 호출과 동일 회차 GitHub·Slack 원본 로그, 플랫폼 공식 `runId` **미제공·미검증**. 앞으로도 정확한 원본 없이 성공이라고 단정하지 말 것.
- **다음 최우선 목표**: 첫 R16 정규 회차가 실제로 도래한 뒤 예약 메타데이터와 플랫폼이 제공하는 공식 회차 식별·GitHub/Slack 원본 앱 호출 기록을 *동일 회차 증거*로 독립 대조. 제공되지 않은 회차 ID는 만들어내지 않는다. Activepieces 운영 플로우·증거 테이블의 과거 자체 체크포인트를 수정하거나 정규 실행으로 간주하지 않는다.
- **최신성 순서**: 사용자의 최신 명령 > 본 R16 상단 > R16 별도 적용 문서 > 아래 과거 R15/R13 섹션 > 오래된 색인. 아래 R15 당시 '최상위 현재'와 R13 항목은 **역사 스냅샷**일 뿐 현재 지침이 아니다.

---



## 과거 R15 당시 상태 (현행 아님) — 당시 직접 조회 기록
- **최신 사용자 지시 및 실제 예약 읽기**: 기존 예약 `6acb017062a08191a4136238b78b313a`의 `automations.peek` 응답에서 `is_enabled=true`, `default_timezone=Asia/Seoul`, `RRULE:FREQ=HOURLY;BYMINUTE=0;BYSECOND=0` 확인. 프롬프트는 **R15** TOP10 필요 역할 자동 선택 지침이며, 알림/이메일 활성값 모두 false인 기존 설정을 유지했다. `last_run_time=2026-10-22T10:05:21.611939Z`는 실행 시각 **메타데이터만** 의미한다. **공식 개별 회차 ID=미제공**, 동일 회차 원본 GitHub/Slack 도구 호출 로그 미제공 → **정규 무인 독립 성공 미검증**.
- **역할·검증 구분**: 사용자 요청에 따라 조사·개발·검증 3역할 및 TOP10 전문 스킬 중 필요한 것만 선택한다. 실제 연결된 스킬 내용 확인과 Python 오프라인 샘플 검증은 독립 LLM 10개 또는 ChatGPT 전체 채팅의 자동 실행을 입증하지 않는다. 과거 TOP10 오프라인 43/43·PR #5/#6/#7 CI 성공은 **코드 검증만** 의미하며 변경 없으면 반복하지 않는다. 참조: `AI_TOP10_SKILLS_PLUGIN_2026-10-22.md` 및 현재 플러그인 `ai-chat-collaboration` 스킬.
- **최신 원본 우선순위**: 사용자 최신 직접 지시 > 이 문서의 이 절 > `PROJECT_MEMORY_INDEX.md`의 현재 항목 > 아래 **R13 당시 기록(역사 자료)**. 이번 직접 읽기에서 색인 blob SHA `5c1235de2c3a68295a5eb58dee7de207b0835cbc` 확인. 아래 07:30 R13·7건 표기는 작성 당시 스냅샷이며 현재 예약/누적 건수로 사용하지 않는다.
- **감사 증거**: 직접 인증한 Activepieces `ap_list_tables` 결과 `AI Scheduled Run Evidence (AUDIT ONLY)` 테이블 `bYxKH9XvAf27ODJ6GrC1U`, rowCount **19** (확인 당시), 본 대화는 수동 요청이므로 정규 체크포인트 **신규 삽입 0**. 00시 -98.967초·07시 출처 없는 UUID 문제의 원본 보존. 공식 예약 회차 귀속 실패를 기록 수나 `last_run_time`으로 대체하지 않는다.
- **보호·작업 방향**: 원래 정각 예약/운영 Activepieces 플로우·연결/타 예약/유료 API·키/과거 거절 쓰기는 변경하지 않는다. 새 문제만 비용·보안·테스트 확인 후 비운영 최소 적용하고 SHA/실행 로그 재조회. 보고는 짧은 **상태 그래프 → 실제 변경·검증 → 다음 목표** 순서.

---

## 아래는 2026-10-22 07:30 R13 원본 이력 (당시 상태, 현행 아님)

# AI 현재 인계 — 예약 R13·검증 증거 (2026-10-22 07:30 KST)

> **이 파일은 예약/새 대화가 가장 먼저 읽을 현재 상태 진입점이다.** R13이 우선 참조하는 원본이며, 파일 SHA는 현재 GitHub에서 실제 다시 읽은 값으로 검증한다. 오래된 `PROJECT_MEMORY_INDEX.md`의 첫머리 R7 스냅샷은 당시 사실을 기록한 역사 자료이며 현재 R13을 대체하지 않는다. 이 인계는 ChatGPT 플랫폼 자체 메모리 요약 UI가 아니다. 사용자의 **가장 최신 직접 지시**가 외부 기록보다 우선한다.

### AI-R13-SLOT-PROVENANCE-2026-10-22 — 07시 새 감사 체크포인트·공식 실행 ID 오인 방지

- 원래 예약 `6acb017062a08191a4136238b78b313a`: 2026-10-22 07:30 KST에 **R13 지침 저장**; 응답에서 `is_enabled=true`, `Asia/Seoul`, `RRULE:FREQ=HOURLY;BYMINUTE=0;BYSECOND=0` 유지 확인. `automations.peek.last_run_time=2026-10-21T22:02:47.006262Z` (= **07:02:47 KST**)로 **새 실행 메타데이터** 확인. 이 값은 정규 실행 ID나 도구 호출 원시 로그가 아니다.
- Activepieces `AI Scheduled Run Evidence (AUDIT ONLY)` 원본 테이블 2026-10-22 **07시 자체 체크포인트 1건 추가**, 총 **7건**. 07시 `observedAtUtc=2026-10-21T22:02:22.239Z` (= **07:02:22 KST**), `automationId`는 원래 예약과 일치, 당시 GitHub 현재 인계 blob SHA `aa8a45ba11ea9ac7006e47e647b7cd90763b3dce` 및 기억 색인 `fcec353735530ed1f57e4fcfc9db05567b24dc87`, 프로토콜 `a7ff81101a72e8ca4d0c40b6756e8bb95e52636a`, 직전 보고서 `db48b83dca9c9a07864031ec202cf8a64042a425`의 독립 읽기 값과 일치. **이 SHA는 당시 버전의 지문**이며 본 문서 갱신 뒤 SHA가 바뀌는 건 정상이다.
- 새 07시 레코드의 `notes`에는 `officialRunId copied from automations.peek last_run.id`라는 **출처 설명**이 있지만, 현재 실제 `automations.peek` 도구 응답에는 `last_run.id`가 없고 예약 자체의 `id` 및 `last_run_time`만 있다. **07시의 공식 scheduled run ID는 독립 검증되지 않았다.** 해당 UUID를 플랫폼이 제공한 원본 ID로 인정하거나 기존 레코드를 정정하지 않는다.
- 00~05시 여섯 건은 그대로 보존(00시 슬롯 선행 **98.967초**, 01~05시 5건 시간 일치, 전체 officialRunId 독립 증명 없음). 06시 체크포인트 없음. **07시 실행 메타데이터 + 자체 체크포인트는 정황 증거이나 공식 호출 로그의 독립 인증이 아니며**, R12·R13 정규 무인 기억 복원 완전 성공을 단정하지 않는다.
- R13은 앞으로 예약 도구 `automations.peek`에서 제공되지 않는 `last_run.id`를 인용하거나 UUID를 만들어 `officialRunId`로 저장하는 것을 명시적으로 금지. 실제 플랫폼 공식 회차 ID·원본 호출 로그가 제공되지 않으면 `officialRunId=미제공`, `evidenceLevel=SELF_REPORTED_UNATTENDED_NOT_INDEPENDENTLY_PROVEN`, 읽기 성공은 `SELF_REPORTED_SOURCE_READ`처럼 제한해 표기. 기존 7건 원본 및 운영 Activepieces 플로우·연결·예약 상태 보존, 유료 API 호출 금지.

## 1. 보호 대상과 운영 결정
- **원래 예약**: `6acb017062a08191a4136238b78b313a` / AI / `Asia/Seoul` / `FREQ=HOURLY;BYMINUTE=0;BYSECOND=0` / `is_enabled=true` / **R13**. R12부터 이 현재 인계 문서를 옛 R7 색인보다 먼저 읽도록 지침을 갱신·재조회했고 기존 활성·정각 예약은 유지했다. 최신 도구 `automations.peek`에서 확인. 중지·일시정지·삭제·중복 예약 생성 금지.
- 사용자는 AI 프로젝트의 필수적인 GitHub `main`·Activepieces 최소 수정은 허가했다. 단 운영 플로우·연결·타 예약을 충분한 근거와 영향/테스트 없이 변경하지 않으며 개별 정책 거절을 우회하지 않는다. 유료 AI API·결제·키 노출 금지, 무료 우선·불필요한 Work와 토큰 소비 방지.
- 모든 대화/예약의 작업 순서: **원본 복원→문제 분석·우선순위→공식 문서/검증된 무료 오픈소스 조사→안전한 최소 적용→로컬/원격 테스트→파일 SHA와 실제 로그 독립 재조회→허용된 GitHub·Slack·Activepieces 저장·재조회→다음 목표**. 바뀌지 않은 성공 검사는 반복하지 않는다.
- 항상 **직관적 단계 그래프**와 `완료/부분/차단/미검증`으로 간결히 보고한다. 근거 없는 완료율·성공 판정 금지.

## 2. 현재 검증된 외부 기록
- GitHub `main` PR #1은 2026-10-19 **병합됨**; 옛 Issue #3 본문의 'open' 문구는 과거 자료다. PR #2, #4 역시 기존 병합된 작업을 되돌리지 않는다.
- 기억 브리지 PR #5는 `main` 병합 `5e1b3a63df651970fbaa068917b113244af259f6`, 원격 GitHub Actions run `39611501507`의 37/37 통과.
- 감사 시간검사 PR #6은 `main` 병합 `e997a6c119c58f3388bec3471d5c6c840c8847f0`, run `39676112095`의 49/49 통과.
- 자체 보고 `officialRunId` 출처 불명 검사 PR #7은 `main` 병합 `e8600906eb31da2735108842752a93887791f0c5`, [원격 Actions run 39680389613](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39680389613) 원본 로그 **53/53** 통과. `tools/ai_checkpoint_audit.py`는 자체 자료의 미인증 공식 실행 ID를 `unverified_official_run_id_claim`으로 검출한다. 코드는 증거 출처 검사를 하는 것이지 실제 플랫폼 실행을 입증하는 것은 아니다.
- 인증된 Activepieces 연결에서 프로젝트 범위 `ap_list_flows` 11개(활성 Slack 웹훅 1개, 나머지 10개 비활성)를 직접 확인. 활성 Slack 플로우 2단계 구성 검사 성공, 해당 플로우 production 실행 목록은 0건. 과거 비활성 하위 플로우 `bMKzPS0kb73NtEDQbq9D5`의 기존 실행 `CjomQ66DbymQqqXBIkbkX`는 읽기 도구로 성공 단계 확인했으나 **정규 ChatGPT 예약의 실행이 아님**. 프로젝트가 사용자가 의도한 UI 프로젝트와 동일한지는 시각적 독립 확인 미완료.
- GitHub [Issue #3 현재 검증 댓글](https://github.com/watersun79-source/ai-token-optimization/issues/3#issuecomment-6326954035) 작성 후 재조회 확인, 여전히 `OPEN` / **부분 해결**.

## 3. 현재 예약의 실제 증거 수준 — 반드시 구분
- Activepieces `AI Scheduled Run Evidence (AUDIT ONLY)` 실제 테이블 ID `bYxKH9XvAf27ODJ6GrC1U`에서 2026-10-22 **00~05시 자체 체크포인트 6건** 확인. 2026-10-22 **06:44 KST 시점에도 06시 이후 기록이 추가되지 않음**.
- 00시 기록은 표기 슬롯 00시보다 실제 `observedAtUtc`가 **98.967초 빠름**. 01~05시 다섯 건은 시간 정합성 검사를 통과하지만, **6건 모두** `officialRunId`에 미인증 UUID를 기입해 실제 ChatGPT 플랫폼 실행에 독립 귀속되지 않았다.
- `automations.peek.last_run_time=2026-10-21T20:58:01.840372Z`는 2026-10-22 05:58:01.840 KST에 해당하며, 공식 플랫폼 회차 ID/그 회차의 GitHub·Slack 도구 호출 원본 로그가 아니다.
- **최종 판정: 정규 무인 기억 복원 독립 검증 미완료.** 코드 CI와 직접 채팅 조회, 체크포인트 자체 기록은 이 결론을 바꾸지 않는다. 현재 연결에서 ChatGPT 정규 예약 원본 도구 로그를 읽는 지원 경로가 없다. 지원되지 않는 도구/URL/ID를 임의 생성하거나 플랫폼 거절을 우회하지 않는다.
- Activepieces 기억 검색 인덱스 `AI Memory Index (SEARCH INDEX ONLY)`는 실제 4개 레코드, 원본 기록을 대체하지 않는 보조 자료. 기존 감사 체크포인트 6건 보존, 원본 수정·삭제 금지.

## 4. 독립 조회 우선순위와 후속 목표
1. **이 인계 문서**를 GitHub에서 fetch 후 내용 SHA 확인. 다른 기본 원본: [실행 표준](AI_EXECUTION_STANDARD_2026-10-21.md), [프로젝트 기억 색인](PROJECT_MEMORY_INDEX.md), [기억 프로토콜](AI-memory-protocol.md), [최신 출처 보고서](AI_CHECKPOINT_RUNID_PROVENANCE_2026-10-22.md). 색인의 처음 R7 메타데이터를 현재로 해석하지 않는다.
2. Slack 부모 스레드 `C0C9649RQAZ / 1792416391.631669`를 직접 조회해 최신 사실 대조. 접근 실패 시에만 인증된 Activepieces 기억 검색 인덱스를 보조 조회. 회차별 체크포인트를 작성할 때 **공식 슬롯(제공 시)과 실제 관찰 시각을 구분**, 미래 슬롯 조기 성공 주장 금지, 슬롯당 최대 1건, 새 도구 호출 원본에 있는 SHA·ts만 기록.
3. **최우선 남은 목표:** 정규 예약 작업의 실제 플랫폼 회차 ID와 같은 회차의 GitHub·Slack 원시 읽기 호출 로그를 공식 도구 또는 접근 허용된 제품 화면에서 식별·독립 대조. 현재 연결이 제공하지 않으면 그대로 미검증 보고. GitHub Issue #3의 의도한 Activepieces UI 프로젝트 확인, provider 무료 할당량/청구 위험 독립 확인은 후순위이며 유료 생성 호출하지 않는다.
4. 기억 색인 `PROJECT_MEMORY_INDEX.md`의 새 요약 직접 수정은 이전 개별 안전 검사에서 거절된 이력이 있으므로 근거 변화 없이는 동일 쓰기 재시도/우회하지 않는다. **이 파일은 새로운 인계 원본으로 만들었고 기존 색인/예약/운영 흐름은 보존했다.**

근거: [GitHub Issue #3](https://github.com/watersun79-source/ai-token-optimization/issues/3), [PR #7](https://github.com/watersun79-source/ai-token-optimization/pull/7), [원격 CI](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39680389613), [Slack 원본 스레드](https://chatgpt-mor9047.slack.com/archives/C0C9649RQAZ/p1792618877689749?thread_ts=1792416391.631669).

## 5. 2026-10-22 07:51 KST 재검증 — 알림 설정 및 7건 감사
- 실제 `automations.peek` 원본 재조회: 기존 동일 예약 ID, `is_enabled=true`, `Asia/Seoul`, `RRULE:FREQ=HOURLY;BYMINUTE=0;BYSECOND=0`, 현재 R13. `last_run_time=2026-10-21T22:02:47.006262Z` (= 07:02:47.006 KST)는 **플랫폼 실행 시각 메타데이터만** 의미하며 GitHub·Slack 읽기 원시 로그나 공식 개별 회차 ID가 아니다.
- 새로 확인된 설정: `notifications_enabled=false` 및 `email_enabled=false`. **예약 중지 상태가 아니라 알림 비활성 상태**다. 현 대화의 예약 도구는 알림 on/off를 변경하는 매개변수를 지원하지 않는다. 사용자는 ChatGPT **설정 → 알림 → Push 또는 Email**에서 직접 선택할 수 있다. 이 변경이 정규 회차의 원본 도구 로그 접근 권한을 만드는 것은 아니다. 공식 자료: https://help.openai.com/en/articles/10291617-scheduled-tasks-in-chatgpt
- 실제 Activepieces 감사 원본 7건(00~05시 6건 + 07시 1건)을 **읽기 전용 재조회**하고 선언 슬롯 대비 관찰 시간 계산: 6건이 선언 시간대 안, **00시 1건은 98.967초 선행**. 모든 7건에 출처 독립 미검증인 `officialRunId` UUID가 있음. 본인의 데이터에 `SELF_REPORTED_UNATTENDED_NOT_INDEPENDENTLY_PROVEN`이라고 적힌 사실과 일치한다. `07시` 항목은 GitHub 색인/프로토콜/당시 검증 보고서 SHA 필드가 현재 동일 파일의 SHA와 일치했으나, **같은 예약 회차의 플랫폼 원본 호출 로그를 인증한 것은 아니다**.
- `main/tools/ai_checkpoint_audit.py`의 이전 테스트 통과한 `unverified_official_run_id_claim` 규칙이 인증 GitHub 원본 읽기에도 존재함을 재확인. 코드/기존 감사 7건/운영 플로우/원래 정각 예약의 상태는 이번 점검에서 **변경하지 않았다**. 기검증 CI는 재실행하지 않았다. 08시 예약은 예정 시각 이후 실제 확인해야 하며 **미래 성공을 미리 기록하지 않는다**.
- 결론: **현재 예약 활성/실행 시각 메타데이터 존재**, 외부 자체 체크포인트 기록 존재. **정규 R13 회차 공식 run ID와 동일 회차 GitHub·Slack 원시 호출의 독립 증명은 여전히 미검증**. 원본에 접근하는 합법적 도구가 새로 제공되기 전에는 반복적인 프롬프트 수정으로 성공을 조작하지 않는다. 모든 사용자 보고에 단계별 직관적 그래프와 완료/미검증 구분 유지.

## 6. 2026-10-22 09:13 KST — R13 08시·09시 출처 규칙 개선 검증
- 인증된 Activepieces `AI Scheduled Run Evidence (AUDIT ONLY)` 원본 테이블에서 전체 **9건** 직접 조회. 00~05시 6건, 07시 1건, **08시/09시 신규 2건**. 공식 플랫폼 회차 ID·동일 회차 원시 도구 로그는 여전히 직접 제공되지 않았다. 체크포인트는 증명 수준 `SELF_REPORTED_UNATTENDED_NOT_INDEPENDENTLY_PROVEN`인 보조 자료.
- 신규 08시 `hKWxQiW0rjMhAD9lMo1PK`: `observedAtUtc=2026-10-21T23:05:20.884Z` → 08:05:20.884 KST, 선언 슬롯 후 **320.884초**. 09시 `9rCJhS8dgJOxmX71zo9cQ`: `observedAtUtc=2026-10-22T00:01:00.974Z` → 09:01:00.974 KST, 선언 슬롯 후 **60.974초**. 두 기록 모두 시간 정합성은 일치, 이전 R13에 반영한 안전 규칙대로 `officialRunId=미제공`, `readResult=SELF_REPORTED_SOURCE_READ: ...`, 출처 미검증 `evidenceLevel` 유지.
- 두 신규 기록의 세 원본 SHA가 GitHub 실제 읽기 결과와 일치: 인덱스 `fcec353735530ed1f57e4fcfc9db05567b24dc87`, 프로토콜 `a7ff81101a72e8ca4d0c40b6756e8bb95e52636a`, 보고서 `db48b83dca9c9a07864031ec202cf8a64042a425`. 각 체크포인트가 명시한 **당시 인계 문서** SHA `075cfe9f52426c9307b0ed2d8fceb0d79fbca9c6`는 본 메모 작성 전 실제 GitHub blob과 일치했다. 이후 새 문서 수정에 따른 SHA 변화는 과거 기록의 잘못이 아니다.
- 두 기록이 참고한 Slack 스레드 ts `1792623344.411069`는 인증 Slack 스레드 원본 읽기에서 확인. **Slack 메시지 존재와 SHA의 일치는 그 시간대 예약 실행 도중 실제 도구를 호출했다는 플랫폼 원시 로그 증명과는 별개.** 현재 `automations.peek.last_run_time=2026-10-22T00:01:29.741042Z` (=09:01:29.741 KST), 원래 예약은 활성/한국시간 매시간 정각 유지.
- 전체 9건 중 **선언 슬롯 시간대 일치 8건**, 00시 **-98.967초 이상 1건**. 기존 7건은 `officialRunId`의 근거가 독립 미검증이고, 최근 2건은 ‘미제공’으로 정확히 기록했다. 이번 분석은 기존 9건/운영 플로우/main/예약을 수정하지 않고 원본을 **읽기 전용**으로 검증했다. 후속 최우선 목표는 지원되는 플랫폼의 정규 회차 원본 호출 로그 확보이며, 불가능하면 계속 미검증으로 표시한다. 불변 PR #5/#6/#7 CI 재실행 금지.
