# AI 현재 인계 — 현행 예약 R16 / 이전 R15·R13 이력 (2026-10-22)

## 2026-10-24 03:06 KST — R16 OTLP AnyValue 타입 혼동·비정상 입력 예외 수정
- **새 실제 결함**: _attrs가 값 타입을 확인하지 않아 stringValue 배열/객체가 ai.evidence.target에 들어오면 TypeError, boolValue/intValue 문자열이 current_handoff 등 증거 대상 문자열로 통과. 여러 AnyValue variant를 동시에 넣어도 첫 문자열을 채택함. 실제 침해/공식 예약 인증 성공 사례 아님.
- **공식 upstream 대조**: Apache-2.0 OpenTelemetry common.proto AnyValue oneof(string/bool/int64 등), 공식 common 규약과 대조. upstream common.proto blob d659c26a66da0c1234e951694924b12eb96bd0e0. https://github.com/open-telemetry/opentelemetry-proto/blob/main/opentelemetry/proto/common/v1/common.proto
- **TDD·최소 변경**: adapter 회귀 3개 추가, 수정 전 19건 실행 결과 4 failures/2 errors 재현. string/bool 타입 및 int64 범위 확인·intValue decimal 문자열을 실제 정수로 변환·알려진 oneof variant 중복 거부. unsupported variant는 증거로 사용하지 않음. 신규 테스트는 malformed 값, 중복 variant, 정상 bool/int64 속성과 기존 호출 보존을 검증.
- **격리 원격 SHA**: 테스트 commit 872146e12d83f6c20ebdb69ae0896ef2bfc9cf80 / blob 8d7296906d28bf4d9cb8ca71c2e256865a638a77. 수정 commit fc0c10b1ee753ef4e52b93b07bc51698029c2474 / adapter blob 459d62f64677f5e924b287a63af1641f6a217975. 두 파일 원격 재조회 SHA가 로컬 Git blob과 일치.
- **실제 검증**: 로컬 adapter 19/19 및 갱신된 전체 Python 95/95 통과. GitHub Actions https://github.com/watersun79-source/ai-token-optimization/actions/runs/40000509030 completed/success, head fc0c10b1ee753ef4e52b93b07bc51698029c2474, job 120575052734 모든 단계 success. 원시 로그 Python 95/95+2/2, JavaScript 12/12+20/20, Java 12/12+20/20 통과. 별도 리뷰 에이전트 읽기 검토에서 차단급 회귀 없음; 테스트/원격 SHA 재실행 없이 root의 원격 조회와 분리.
- **다른 기여 보존**: 직전 task bidi/구분자 방어 변경 head 3dc0adb015ad682767dd02f12b15764a991406da / CI 40000185589 success 직접 확인. 해당 bot 코드/테스트를 덮어쓰지 않고 현재 전체 회귀에 포함.
- **공식 예약 결과 귀속**: 읽기 전용 peek에서 03:00 KST 공식 회차 dbd09b73-6fd8-832f-b086-e0d5bf0217b6 completed, latest_result 동일 ID. 본문이 참조한 이전 CI 39999901160의 진행 중 상태는 당시 스냅샷; 현재는 failure이며 후속 40000185589 success와 구별. 공식 결과 제공은 확인됐지만 같은 회차 원시 GitHub/Slack tool-call ledger 미제공 → 무인 앱 호출 성공 미검증.
- **교차/보호**: 지정 Slack 기존 기록 재조회, 인증 Activepieces 기억 인덱스 4건 읽기 완료. 현재 수동 점검의 정규 체크포인트 삽입 없음. main·예약 프롬프트/상태/일정/알림·운영 Activepieces·비밀/결제/유료 API 변경 없음.
- **다음 목표**: 공식 동일 회차 원시 GitHub/Slack 호출 ledger가 지원 도구에 제공될 때만 검증. 이미 통과한 변경 없는 CI 반복 금지.

---

## 2026-10-24 02:54 KST — R16 OTLP fixed64 timestamp 예외·범위 결함 수정
- **공식 조사**: OpenTelemetry OTLP/JSON 규약의 fixed64 timestamp decimal-string/JSON integer 처리와 upstream opentelemetry-proto(실제 LICENSE Apache-2.0, blob 261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64)를 확인. 새 SDK 설치나 외부 LLM 호출 없음. https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding
- **실제 재현**: 기존 _time_ns는 superscript ² 및 5000자리 숫자 문자열에서 ValueError, uint64 초과값 허용, 정상 JSON 정수 시간값 거부. 기존 12개 adapter 검사에 회귀 4개 추가 후 로컬 RED(2 failures, 2 errors) 확인.
- **격리 최소 수정**: 시간값 변환 전에 ASCII/길이/타입 검사, 양수 uint64 범위 제한, bool/float 거부, JSON int 허용. 코드 commit b2520b80564075b408bbff80dd8d789be3ef90c2 / blob d092a581755e25d9d86575893486d521156e806e. 테스트 commit bc29c56f6f0bb3509ef13dd77ac226e0192a399c / blob 4bf511f134d40b185e4b2be5c9ef77e5f228c303. 두 파일 원격 재조회·로컬 Git blob 일치.
- **검증**: 로컬 Python 90/90 + 2/2, JavaScript 12/12 + 20/20 통과. 로컬 javac 미설치로 Java는 실행 불가; 원격 로그로 검증. Actions https://github.com/watersun79-source/ai-token-optimization/actions/runs/39998755200 의 첫 attempt는 최종 cancelled였으므로 성공으로 간주하지 않고 취소된 job만 1회 rerun. attempt 2 / job 120569514148 / 같은 head / completed/success 독립 조회; 원시 로그 Python 90/90 + 2/2, JS 12/12 + 20/20, Java 12/12 + 20/20.
- **실제 봇 실행 경계**: bot_team_r16.collaborate의 ResearchBot→BuilderBot→VerifierBot Python 결정론적 오프라인 파이프라인 실제 실행. live_llm_bots=0, provider_calls=0, official_success_verified=false 유지. 외부 Gemini/Claude 모델 실행 아님.
- **독립 리뷰**: 별도 코드 리뷰 에이전트가 변경 함수/회귀 4개를 읽고 차단급 결함 없음 판정. 리뷰어는 테스트/원격 SHA를 재실행하지 않았으며 원격 SHA·CI는 root가 앱 재조회로 검증.
- **예약 읽기 전용**: 기존 ID 6acb017062a08191a4136238b78b313a 활성. 최근 공식 last_run.id bb3a6feb-ee2c-8324-8ca0-a93800c50bf4 / 2026-10-24 02:00 KST / no_update. latest_result는 이전 19시 회차 자료이며 최신 회차와 혼합하지 않음. 원시 per-run 앱 호출 ledger 미제공 → 무인 성공 미검증 유지.
- **교차 기록**: 인증 Activepieces 기억 인덱스 4건 직접 읽음(일부 R13/R15 역사 메타는 현행 R16보다 오래됨); 감사 테이블 rowCount 21, 자체 기록 개수는 성공 증명 아님. 본 수동 점검에서 정규 체크포인트 삽입 없음.
- **보호/다음 목표**: GitHub main·예약 설정/주기/알림/프롬프트·Activepieces 운영 및 원본 감사 기록 변경 없음. 유료 API/비밀/결제 변경 없음. 다음은 같은 공식 정규 회차 GitHub/Slack 원시 호출 ledger가 실제 제공되는 경우에만 독립 검증.

---

## 2026-10-24 02시대 KST — R16 OTLP 중간 조상 cross-trace 연결 결함 수정 · 3언어 CI 성공
- **조사/재현**: OpenTelemetry Trace API의 "child TraceId MUST match parent" 공식 규약과 격리 `otel_evidence_adapter.py`를 대조. `_descends_from`이 루트 연결·순환만 검사하고 **중간 부모 span의 traceId**는 검사하지 않아, 서로 다른 trace에 속한 중간 부모를 통과시키는 결함을 로컬 Python 재현함. 실제 운영 침해 또는 공식 예약 호출 진위 인증은 아님.
- **격리 TDD 회귀**: `tests/test_otel_evidence_adapter.py`에 cross-trace 중간 부모 거부 및 동일 trace 중간 부모 허용 2건 추가. test commit `6a6835c90feacc726e70aca0779a8a388cb67ee0`, blob `519c5eacfa4f8e1a3eced6668c621f046fdf092c`.
- **최소 수정**: `_descends_from` 중간 부모마다 `traceId == root_trace` 확인, 기존 acyclic/unbroken ancestry 보존. fix commit `2e6def913297946be3a9e2652b7e8f4a2cf297d7`, adapter blob `bed826fd68b65309330652c1757603e2972b0b39`. 두 파일 GitHub 원격 read-back SHA 일치.
- **원격 CI 독립 재확인**: [GitHub Actions run 39997746299](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39997746299), job `120565577978`; `push / head=2e6def913297946be3a9e2652b7e8f4a2cf297d7 / completed/success` 직접 조회. 원시 job 로그 Python **86/86+2/2**, Node JS **12/12+20/20**, Java **12/12+20/20** 통과.
- **예약 읽기 전용**: 인증된 `automations.peek`에서 기존 단일 예약 ID `6acb017062a08191a4136238b78b313a`, `is_enabled=true`, `paused_count=0`, 최근 `last_run_time=2026-10-23T17:02:15.322242Z` 조회. 이 응답은 원본 per-run GitHub·Slack tool-call ledger를 제공하지 않음. 기존 정규 무인 앱 호출 성공 **미검증** 유지. 이전 handoff의 특정 정규 회차 결과 귀속 '부분 검증'과 혼동하지 않음.
- **보호**: 기존 예약/주기/알림/프롬프트, GitHub main, 운영 Activepieces 플로우/연결, 비밀정보/결제/유료 생성 API 변경 없음. 외부 Gemini/Claude 독립 모델 호출 없었음.
- **다음 목표**: 동일 정규 실행 회차의 공식 결과·원시 앱 호출 ledger가 제공될 때만 독립 검증; 없으면 성공 승격 금지.

---

## 2026-10-23 19:03 KST — 직전 공식 회차 결과 귀속 부분 검증
- 인증된 `automations.peek.run_details.latest_result`가 직전 회차 `run_id=3381bc18-d844-832e-b64a-61c29bb8598a`, scheduled 18:00 KST, completed와 전체 결과 본문을 실제 제공했다. 직전 관찰에서 `in_progress`였던 동일 ID가 완료 결과로 전환된 것을 확인.
- 결과 본문의 격리 commit `493ea72de030f2e402d3db34959fea6462bb8fa7`, Actions `39928466966`, 인계 blob `97aa7b91e5602aba40aced694a3de70742063413`, Slack ts `1792745941.496949`는 이번 GitHub·Slack 원본 재조회와 일치했다. **공식 회차 ↔ 저장된 결과 본문 ↔ 외부 원본**의 결과 귀속은 부분 검증됨.
- 한계: 플랫폼 응답은 여전히 회차별 GitHub·Slack 원시 tool-call ledger를 제공하지 않는다. 따라서 결과 본문과 원본의 일치는 확인했지만, 해당 회차가 실제로 앱을 호출한 사실 자체는 독립 인증되지 않아 **정규 무인 앱 호출 성공 미검증** 유지.
- 새 현재 회차는 `last_run.id=144a1464-05fc-8327-8d7d-1b5d7b6f1d37`, scheduled 19:00 KST, 조회 당시 `in_progress`; 완료로 승격하지 않음.
- Slack 부모 스레드 기록 ts `1792749854.464169`. 새 코드 변경·CI 재실행 없음. GitHub main·예약 설정·운영 Activepieces·유료 API 변경 없음.

---


## 2026-10-23 18:00 KST — 공식 회차 ID 필드 제공 확인 + OTLP 중복키 회귀 보완
- **공식 회차 식별자 경계 개선**: 인증된 `automations.peek`가 이제 `run_details`를 실제 반환한다. 직전 완료 결과는 `latest_result.run_id=fb16cf89-ccf0-832c-8937-e9060a59d434`(scheduled 16:00 KST, completed), 이번 관찰 시점의 현재 회차는 `last_run.id=3381bc18-d844-832e-b64a-61c29bb8598a`(scheduled 18:00 KST, 조회 당시 `in_progress`). 이 값은 예약 ID·`last_run_time`·GitHub Actions ID와 다른 **플랫폼 회차별 필드**이므로 향후 공식 run ID 출처로 사용할 수 있다. 단, 현재 회차는 완료로 승격하지 않는다.
- **독립 증거 한계 유지**: 동일 응답은 회차별 GitHub·Slack 원시 tool-call ledger를 제공하지 않는다. 직전 완료 결과 본문의 GitHub SHA/Actions와 Slack ts는 외부 원본과 일치하지만, 그 회차가 실제로 앱을 호출했다는 독립 원시 장부는 미제공 → **정규 무인 앱 호출 성공 미검증**.
- **새 코드 결함**: 격리 브랜치의 선행 commit `17041863b05c6ed9d8c57deae1afd81d31710c9e`는 OTLP 중복 속성 키를 거부했지만, 첫 값이 미지원 value 형식이면 키를 기록하지 않아 같은 키의 두 번째 값을 받아들일 수 있었고 회귀 테스트도 없었다.
- **격리 최소 수정**: 모든 관찰 키를 value 디코딩 전에 추적하고, 미지원 첫 값 뒤의 중복도 실패 폐쇄. commit `493ea72de030f2e402d3db34959fea6462bb8fa7`; adapter blob `a23cb538ffe7e4aab6771302c7c9c67e3506c057`; regression test blob `d2cdb34a802ee5bbec58ba49f3eaba938b1f6f02`.
- **원격 검증**: GitHub Actions [run 39928466966](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39928466966), job `120330570234`, matching head, `completed/success`; Python·JS·Java 모든 단계 success. 현재 GitHub 연결은 원시 logs download endpoint를 허용하지 않아 정확한 test count는 **미확인**으로 유지.
- **Slack 기록**: 지정 부모 스레드에 ts `1792745941.496949` 기록 성공. 검색 인덱스/스레드 reply read-back은 즉시 반영되지 않아 독립 재조회는 다음 회차로 이월. GitHub main·예약 설정·운영 Activepieces·유료 API 변경 없음.

---


## 2026-10-23 16:09 KST — R16 OpenTelemetry OTLP 호출 증거 연결 실제 구현
- **새 결함 확인**: 격리 `audit_v2.py`는 OpenTelemetry tool span을 설계 근거로만 언급했고 실제 OTLP→검증기 `tool_calls` 어댑터가 없었다. 기존 CI path filter도 `triage_bot.py` 및 새 adapter 경로를 누락해 source-only 변경이 CI를 건너뛸 수 있었다.
- **공식 규약 대조**: OpenTelemetry GenAI agent/tool span 규약(Development)의 `invoke_agent`, `execute_tool`, `gen_ai.operation.name`, `gen_ai.tool.name` 및 OTel trace/span ID·status 규칙을 사용. trace ID/span ID/`gen_ai.tool.call.id`를 ChatGPT 공식 scheduled run ID로 승격하지 않으며, arguments/result 원문은 민감 가능해 수집하지 않음.
- **격리 최소 적용**: `otel_evidence_adapter.py` blob `5c458b778270da077cf31b8ff07bc14dc71c4c94`; `audit_v2.py` blob `64e7e3039005c3d0d86602e989bde932e96eecaa`; 테스트 blob `995792a9bff8bfb39408c6c85fe1ade74a9e116f`; workflow blob `92d349d4e312110154f6c5a96ed49c7d69ccdbc7`. 단일 run root, non-zero trace/span, 끊김 없는 부모 계보, root 시간창, INTERNAL execute_tool, OK status, 정확한 도구·locator·SHA/Slack ts를 확인한 뒤 기존 형식 게이트로 연결. 출력은 계속 **형식 통과·진위 미검증**.
- **원격 독립 검증**: GitHub Actions [run 39915981921](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39915981921), head `ada144706220aed29df3eeaa6f21db2c42d1bfbc`, job/check `120289552532`, `completed/success`. 원시 로그: Python **83/83 + 2/2**, JS **20/20**, Java **12/12 + 20/20** PASS. 격리 README blob `9fcee538384205654fd6e34796350b5c464d2613` readback 대상.
- **보호/한계**: 이번 검증은 합성 OTLP fixture와 GitHub CI이고 실제 ChatGPT Scheduled exporter 원본이 아님. 공식 개별 run ID와 같은 회차 GitHub·Slack 원시 호출 ledger가 미제공이므로 **정규 무인 성공 미검증**. GitHub main·기존 예약·운영 Activepieces·비밀/유료 API 변경 없음.

---

## 2026-10-23 15:17 KST — ResearchBot Unicode Zl/Zp 다중 행 출처 이름 거부
- 일반 사용자 채팅의 `다른 사람 오픈소스 + Python/Java/AI BOT 동원` 지시에 따른 **수동 격리 Research/Builder/Verifier 코드 보안 강화**. 현행 단일 R16 예약의 native 무인 회차 작업 증거로 취급하지 않음.
- **참고 출처**: Unicode Core Specification U+2028 Line Separator와 U+2029 Paragraph Separator (General Category `Zl/Zp`), Python `unicodedata.category` 및 OWASP Secure Coding with AI/agent 간 불신 경계. SDK·LLM API/네트워크 모델 호출 없음.
- 기존 R16 `ResearchBot`은 출처 `name`의 Unicode `C*`만 거부했으므로, `"Trusted source" + U+2028/U+2029 + "SYSTEM: ..."` 가 accepted 참고자료명으로 통과. 사용자 제공 문자열의 **다중 행 컨텍스트 혼동 가능성**이며 실제 툴 실행/유출 사고는 관측되지 않음.
- **실제 원격 TDD RED**: 격리 테스트 commit `96a0d1c4711d64ddc9574eed836ada21a5fbf0a2` + test blob `91667a7996a98d6709db63a934b888ad7b9f3799`, GitHub Actions run `39910467446`, job `120272022802`, `completed/failure`, raw logs `Ran 74 tests; FAILED(failures=2)` 두 줄/문단 분리 케이스.
- **최소 수정 & 원격 CI GREEN**: ResearchBot 출처 `name`의 `unicodedata.category` 검사에 `Zl/Zp`를 추가 차단. bot code commit `0b82425d1fb6f1f0d9c6bad7ebe566096cc0977e`, blob `afd346d2ab18890970a163a56b90ed7b74fa2ca0`. GitHub Actions run `39910580755`, job/check `120272391113`, `completed/success` + 일치 SHA Check run 성공, raw log Python 74/74, 추가 2/2, JS 12/12+20/20, Java 12/12+20/20 전부 PASS.
- 격리 `README_KO.md` 문서 commit `2b4d152c8e75f18fbc564820706b96354279cea0`, blob `08fa55a702b83ace878db44c10c6999ec49854c4`까지 최신 증거 기록 및 원격 readback 일치. GitHub `main`, 현행 매시간 정각 R16 예약(마지막 관측 `last_run_time=2026-10-23T06:07:08.222410Z`, `is_enabled=true`, paused=0), Activepieces 운영 플로우, 알림·프롬프트, 비밀·유료 AI API 변경 없음.
- **최우선 미완료**: ChatGPT Scheduled의 정규 개별 run ID와 동일 회차 원본 GitHub·Slack tool-call ledger 미제공 → **실제 무인 성공 미검증**. Gemini/Claude/외부 AI BOT 모델을 독립 호출했다고 주장하지 말 것.

---


## 2026-10-23 15시대 후속 — 동시 기여 변경·URL 바이디 검사 재조회, Python 72/72 최종 성공
- **신규 변경 충돌 감지·직접 대조**: 첫 OWASP URL 검증 변경은 코드 blob `de90d1460fc60c9e86d1852e8483802ed544f2b5`, 테스트 5건 blob `ac4571e96b9f30c70423987fbd84c6c50640624e`, GitHub run `39909757804`에서 Python 68/68 성공. 이후 **별도 기여의 변경**으로 최신 `bot_team_r16.py` blob `b3bc27702347029f8c28352b72917d5524baa977`에 `unicodedata.category(c).startswith('C')`를 이용한 bidi/숨은 제어문자 제목 차단이 추가됨. 같은 격리 브랜치에 `tests/test_bot_untrusted_references.py` 4건 추가, blob `2137942c4d282c685f0f38e258270a38a4663005`. 앞선 코드 SHA는 **패치 이력**이지 현행 최종 SHA가 아니므로 구분.
- **최신 원격 CI 원본 재조회**: [Actions run `39910021477`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39910021477), head SHA `97893289a61eb2c6e12fbe204ab1e834f5ceba2b`, 공식 Check/job `120270605065`, `completed/success`. 직접 조회한 원시 job log: Python 전체 **72/72 OK** (68 + 추가 4), Python 별도 다국어 2/2 OK, JavaScript 20/20 PASS, Java 공통 20/20 PASS, 추가 Java oracle 12/12 PASS, 경고 0. 직전 중간 커밋 run `39909896111`은 `failure`였으나 최종 성공으로 수정된 상태를 구분.
- **실제 수행 범위**: 사용자 일반 ChatGPT 지시에 따른 GitHub 격리 코드·표준 CI 검증. Microsoft Agent Framework Go (MIT, 미성숙 public preview), Pydantic AI (MIT), OWASP의 URL parser 방어 지침을 참고했으나 새 유료 API/모델 실행, 외부 에이전트 프로세스·패키지 설치 없음. 본 R16 ResearchBot은 제공된 Github URL *메타데이터* 검사만 하고 외부 원본 진위 확인은 계속 별도 필요함.
- **보호/미해결**: 기존 매시간 정각 예약 ID `6acb017062a08191a4136238b78b313a`, `is_enabled=true`, `paused_count=0`, 최근 `last_run_time=2026-10-23T06:07:08.222410Z` (=15:07:08 KST)는 트리거 메타. 예약 스케줄/알림·Activepieces 운영·GitHub main 불변. ChatGPT Scheduled **native per-run ID/같은 회차 GitHub·Slack 원본 호출이 제공되지 않아 무인 업무 성공 = 미검증**. 다음 목표는 공식 Previous runs 원본 접근을 확인하는 것뿐, 기실행 CI를 사용자 예약 성공으로 오인하지 않음.

---


## 2026-10-23 15시대 — R16 ResearchBot 비가시 유니코드 이름 방어 회귀 TDD
- **사용자의 일반 ChatGPT 채팅에서 지시한 수동 ResearchBot·BuilderBot·VerifierBot 오프라인 보안 강화 작업**, ChatGPT 예약 AI가 자체 실행한 작업이라고 오인하면 안 됨.
- **추가로 조사한 공식 구현**: Microsoft Agent Framework [Sequential/Handoff/Approval](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/), OpenAI Agents SDK [guardrails](https://openai.github.io/openai-agents-python/guardrails/), OpenTelemetry의 [execute_tool span](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md). API 비용/승인 없이 직접 SDK 설치·모델 호출은 하지 않았고 데이터 입력 방어 패턴만 참고.
- 기존 격리 `bot_team_r16.py`의 `ResearchBot`는 직접 전달된 GitHub 참고자료 이름에서 `<CR/LF/TAB>` 등 ASCII control은 제외하지만 `U+202E`(양방향 방향전환)와 `U+200D`(제로폭 조인 문자)를 허용하는 약점 발견. 같은 격리 브랜치에서 이미 별도 개선된 GitHub URL allowlist는 **중복 덮어쓰기 없이 보존**.
- 신규 `tests/test_bot_untrusted_references.py`에 URL 혼동/비가시 문자·잘못된 출처 자료 및 고정 시드 200개 합성 입력의 실패 폐쇄 안전 불변식 테스트 추가. 새 테스트 commit `8b214bf274690cce56321c272998431839727312`, blob `2137942c4d282c685f0f38e258270a38a4663005`. **패치 전 원격 TDD RED**: GitHub run **`39909896111`**, job `120270200607`, Python 72건 중 U+202E·U+200D 각각 오류로 **2 failures**. 다른 URL 검사는 통과.
- **최소 수정**: 격리 Python BOT `ResearchBot` 이름 허용 조건의 ASCII 제어문자 검사만 `unicodedata.category(c).startswith('C')` 기반 전체 control/format 문자 거부로 교체. 나머지 안전 URL 검사/모의 provenance/기존 3봇 협력 정책 보존. 코드 commit `97893289a61eb2c6e12fbe204ab1e834f5ceba2b`, GitHub blob `b3bc27702347029f8c28352b72917d5524baa977`.
- **정규 격리 CI GREEN 실제 원본**: [Actions run 39910021477](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39910021477), head SHA `97893289a61eb2c6e12fbe204ab1e834f5ceba2b`, job/check ID `120270605065`, `completed/success`. GitHub 원시 job 로그 **Python 72/72**, 별도 Python 2/2, JavaScript 12/12+20/20, Java 12/12+20/20 모두 통과. 동일 head SHA의 GitHub Check run `completed/success` 독립 확인. 각 검사는 모의/로컬 정합성 검사이며 예약 플랫폼 실제 원시 실행 원본 인증과는 별개.
- **운영 영향 0**: 별도 R16 격리 브랜치 Python 봇/테스트만 변경, GitHub `main`, 기존 단일 ChatGPT 매시간 정각 예약, Activepieces 운영 플로우/연결, 과금/키/유료 모델 API 변경 없음. 정규 예약의 공식 native per-run ID와 동일 회차 GitHub·Slack 원시 tool-call ledger 미제공 → **무인 성공 미검증**.
- **다음 최우선 목표**: 공식 ChatGPT Scheduled/Previous runs에 대한 인증된 개별 실행·원시 호출 ledger 접근이 제공될 때만 교차 검증. 제공되지 않으면 허위 run ID 생성/추측/우회 금지.

---


## 2026-10-23 15시대 — AI BOT GitHub 소스 URL 보안 검증 68/68
- **오픈소스 공식 참조**: OWASP SSRF 방지 지침의 호스트 allowlist/파서 간 해석 불일치 주의 및 Python `urllib.parse` 공식 경고('URL split does not validate'). Pydantic AI(MIT)의 durable execution과 일반 memory 저장의 차이, Microsoft Agent Framework Go(MIT, preview)도 조사. 라이브러리/모델 추가 설치·유료 API 호출 없이 기존 격리 Python·JS·Java CI 그대로 재사용.
- **실제 새 버그**: 격리 `bot_team_r16.py` ResearchBot이 제시된 참조 URL을 `startswith("https://github.com/")`로 판정해서 인코딩·경로 정규화·역슬래시 및 중복/제어문자 문제를 충분히 점검하지 못함. 이 모듈에는 네트워크 호출이 없으므로 실제 SSRF 침해로 단정하지 않는다.
- **수정 및 GitHub SHA**: 격리 `ai/r16-evidence-reconciler-2026-10-22`에서 Python `re` fullmatch + `urllib.parse.urlsplit` 이중 확인으로 **정확한 github.com scheme/host·owner/repo 경로만** 참고 메타에 허용. 포트/userinfo, 퍼센트 인코딩, 경로 `..`/빈 segment, 쿼리/fragment, 탭·개행·역슬래시 거부. 중복 URL 제거·제목 제어문자 차단. bot 소스 commit `521be931069d507d46db1ad13928dc054aeff7ab` GitHub blob **`de90d1460fc60c9e86d1852e8483802ed544f2b5`**. 신규 `tests/test_bot_source_url_policy.py` 5건(commit `8a45be4e307eab0c5b0f6f20514a89b1023521bb`, blob **`ac4571e96b9f30c70423987fbd84c6c50640624e`**).
- **공식 원격 CI 증거**: [GitHub Actions **`39909757804`**](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39909757804) 및 공식 Check/job **`120269756801`**, head SHA **`8a45be4e307eab0c5b0f6f20514a89b1023521bb`**, `completed/success`; 실제 runner 로그에서 Python **68/68 OK** (이전 63 + 신규 5), Python 다국어 2/2, JS 공통 20/20, Java 공통 20/20, Java oracle 12/12, 경고 0 직접 재확인. 변경 없는 성공 테스트를 별도로 재실행하지 않았음.
- **격리 세부 기록**: [R16 README](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/README_KO.md) blob **`9dc454b0ef2439bb60c835c4e699105e5d3be5f2`**, commit `fdc0f113127fbb74f0ffb50a97a27f14e33e1da1`. 이 CI는 단순 GitHub 코드 테스트 성공; ResearchBot은 실제 참고 소스의 진위는 여전히 확인하지 않는다고 표시.
- **기존 예약 보호 상태 직접 조회**: ID `6acb017062a08191a4136238b78b313a` `is_enabled=true`, `paused_count=0`, Asia/Seoul 매시간 정각; `last_run_time=2026-10-23T06:07:08.222410Z` (=15:07:08 KST)은 예약 트리거 시각 메타뿐. 예약 알림·프롬프트·주기/상태, 기존 Activepieces 운영 flow, GitHub main, 비밀정보/결제 변경 없음.
- **유일한 최우선 미완료**: ChatGPT Scheduled 공식 개별 per-run ID 및 동일 회차 GitHub/Slack 원시 tool-call 로그는 해당 연결에서 제공되지 않음. **정규 예약 무인 기억 복원 성공 = 미검증**. 수동 챗에서 만든 GitHub Actions ID나 Slack 자체 메모를 정규 예약의 무인 성공으로 오인하지 않는다. 다음 목표는 **권한 있는 공식 Scheduled → AI → Previous runs 원본 접근 가능 여부 검증**.

---


## 2026-10-23 15시대 — R16 봇 증거 게이트 오독·공급망 고정 보완
- **독립 봇 감사에서 확인한 두 개선점**: (1) 미인증 입력도 안전 규칙만 통과하면 `policy_checks=PASS`로 보여 예약 진위 통과로 오독될 수 있음, (2) 격리 CI가 GitHub Actions 가변 메이저 태그를 사용해 실행 의존성 재현성이 약함.
- **격리 최소 수정**: `ai/r16-evidence-reconciler-2026-10-22`의 `bot_team_r16.py`를 `SAFE_UNVERIFIED`로 명확화(blob `6d1d48e39f72698d8364ebcaab13a24519ebb86f`), 관련 테스트 blob `3be872ddb166bd0d053ec208bbb451fd3aa256c4`. checkout/setup-python/setup-node/setup-java를 실행 로그에서 검증한 전체 commit SHA로 고정한 workflow blob `81dde1e4ebd769e16d35533dd8e3123dc23d95e3`. main·운영 Activepieces·기존 예약 무변경.
- **공식 원격 검증**: GitHub Actions [run `39909423239`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39909423239), job `120268698529`, head `d2309ceb6b1d9a22ad2ee3e6b1d4d74d05a43938`, `completed/success`. 원시 로그가 네 Action의 고정 SHA를 그대로 다운로드했고 Python 63/63, 추가 Python 2/2, JS 20/20, Java 12/12+20/20 통과.
- **오픈소스 판단**: Microsoft Agent Framework·CrewAI의 역할/순차/승인 패턴, Hypothesis·fast-check의 property-test 패턴만 참고. 외부 패키지·유료 모델·비밀키·운영 호출 0. 실제 병렬 조사 봇은 이번 수동 작업의 조사 보조이며 정규 예약의 상시 독립 AI가 아님.
- **판정/다음 목표**: 격리 코드·공급망 검증은 완료. 공식 예약 회차와 같은 실행의 GitHub·Slack 원시 tool-call 원장은 계속 미제공이므로 **정규 무인 기억 복원 성공 미검증**. 다음 목표는 공식 원장이 실제 제공될 때만 회차별 독립 대조.

---



## 2026-10-23 14시대 — R16 ResearchBot·BuilderBot·VerifierBot 오프라인 증거 게이트 추가
- **다른 사람 개발물 조사**: [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) MIT의 순차/병렬/handoff 패턴, [CrewAI](https://github.com/crewAIInc/crewAI) MIT의 역할 분리, [Hypothesis](https://github.com/HypothesisWorks/hypothesis) MPL-2.0와 [fast-check](https://github.com/dubzzz/fast-check) MIT의 property-test 패턴. AutoGen은 유지보수 모드이므로 새로운 종속성으로 채택하지 않았고, 모델 API/외부 에이전트 추가 비용·보안 승인 없이 호출하지 않음.
- **기존 3봇 자산 재활용**: GitHub `ai/bot-team-sandbox-2026-10-22`의 `experiments/ai-bot-team/bot_team.py` 및 `chat_router.py` 원본을 실제 읽고, 해당 도구는 수동 오프라인 계획 데모이며 자동 코딩/ChatGPT 전체 메시지 후킹이 아님을 확인.
- **실제 격리 새 기능**: `ai/r16-evidence-reconciler-2026-10-22` 브랜치 `experiments/r16-evidence-reconciler/bot_team_r16.py`에 ResearchBot(입력된 GitHub 참조 메타 판정), BuilderBot(`audit_v2.check` 결과로 READ_OFFICIAL_SCHEDULED_RUN / READ_SAME_RUN_APP_CALLS / COMPARE_INDEPENDENT_GITHUB_SLACK_READBACK 중 안전한 1개 선택), VerifierBot(원시 예약 진위 미확인 상태 강제 유지)을 순차 실행. **독립 모델 세 개가 동작하는 것은 아니며, 실제 실행 가능한 표준 Python 오프라인 다중 역할 프로그램**. 입력 64KB/참조 20건 상한, 링크 안전 검사, 예약·운영 쓰기/과금 0, 원본 없이 성공 표시 주입하면 거부. `--input` CLI 성공 허위 보고를 막도록 unauthenticated exit code 2.
- **CI 추가 실제 검증**: 새 bot 코드 commit `85ccb1aef39b11e0efb2085cdda22668f7fa8942`, blob **`8e2fb8aecddda9997e3e0dae55e3905ac7a76af2`**; 신규 9개 bot 테스트 commit `e9b64923695e0f1d6320b8d4a165a4962cfb7b2c`, blob **`b6ff4d81e393d5535c98fd8cf88be76fca8f7cfe`**; 격리 CI 코드 경로 추가 commit `06e382630928f3fcd583b8fedbec204e435fbb8a`, workflow blob **`2e58b16236999fc9beff33c876230a0a1dee2e3f`**. 실제 원격 GitHub [Actions **`39905219028`**](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39905219028) head SHA `06e382630928f3fcd583b8fedbec204e435fbb8a`, job/Check **`120255511427`**, `completed/success`. 원시 job 로그 **Python 전체 `Ran 63 tests in 0.218s OK`**, 봇 9개 포함, 다국어 Python 2/2·JavaScript 20/20·Java 20/20·Java oracle 12/12, 경고 0. 이전 취소 run `39905165919` 성공 처리하지 않음.
- **기억 인계 상세**: [R16 격리 README](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/README_KO.md) commit `0cab00af341cec6ea9772a93a10cefb28b9eef1e`, GitHub blob **`f9f1f5fe6f9b61303eab8b49241db4ecf7740f83`**.
- **한계/최우선**: GitHub Actions는 R16 코드와 봇 역할 프로그램의 **CI 검증 성공**만 의미. ChatGPT 기존 매시간 정각 단일 예약 ID `6acb017062a08191a4136238b78b313a`의 `automations.peek is_enabled=true`, `paused_count=0`; 마지막 `last_run_time=2026-10-23T04:59:11.509561Z`은 회차 성공/완료 증거 아님. 공식 개별 `native per-run ID`와 같은 회차 GitHub·Slack 앱 호출 원본 계속 미제공: **무인 기억 복원 성공 미검증**. main·Activepieces 운영·예약 프롬프트/알림/주기/활성·유료 API 변경 없음.
- **다음 목표 1개**: 인증된 ChatGPT Scheduled → AI → Previous runs 공식 개별 회차와 원본 tool-call 장부가 제공되는 실제 공식 도구 경로를 확인하고, 없으면 미검증 유지. 원본 미제공을 임의 합성 run ID로 대신하지 않음.

---



## 2026-10-23 — R16 다국어 시간대 검증 차이 해소 20/20 + 공식 원격 CI 성공 (정규 무인 예약과 구별)
- **다른 사람 공개 구현 참조**: JSON-Schema-Test-Suite(MIT) 공통 다언어 fixture 구조, Java 21 OffsetDateTime의 `±18:00` 경계 검증, SLSA build provenance의 출처/실행 ID 분리. 외부 코드를 직접 복제·추가 설치하지 않고 R16 격리 코드의 위험한 오프셋 해석 불일치를 수정.
- **실제 재현**: Python `fromisoformat`은 `+19:00` 시간대를 수용하지만 Java는 거부; 기존 JS는 +23시까지만 검사. 격리 `fixtures/time_cases.tsv` 15→20건으로 확대하여 `±19:00`, `+18:01` 거부·`±18:00` 허용을 세 언어에서 동일하게 판정.
- **적용**: GitHub 격리 branch `ai/r16-evidence-reconciler-2026-10-22`의 Python `audit_v2.py` commit `d8ad3c4a66b8f2d05d9fdb76a41d266ecde4ba30`, JS `activepieces_mock_guard_2026-10-23.js` commit `d3c8eb284656b789d7ab8695de08c2bba71d9d12`, 원본 blob `831de11d0a132392ea74476fa26288b29b5c020c` / `b0185fc20a939e468065e96ccea8ebf04247313b`. Java 표준 구현은 변경하지 않고 독립 기준 유지.
- **검증(공식 GitHub 원본)**: Actions [`39896738983`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39896738983), job `120228819827`, head SHA `d3c8eb284656b789d7ab8695de08c2bba71d9d12`, `completed/success` 및 원본 로그: Python 기존 44/44 OK, polyglot Python 2/2, JS 20/20 PASS, Java 20/20 PASS, 추가 Java oracle 12/12 PASS, 경고 0.
- **비활성 격리 Activepieces**: flow `zgSopq6Txh68wxsDc5K5Z`의 mock CODE step만 수정. GitHub JS와 `ap_read_step_code` 본문 **완전 일치**, flow `DISABLED/unpublished`, `ap_validate_flow` 2/2 valid. 실제 TESTING 모의 run `a6Wc8LQeKMK055sOX9Fqu` (+19 거부), `dl9wBmcdZt7ZnsSmJWRmr` (+18 형식 통과), 2/2 예상 출력 일치·`official_success_verified=false`·`external_calls=0`.
- **인계 상세**: [격리 검증 README](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/README_KO.md) 원격 blob `3bc7ca961f010987176931d12239d0b91afb9e74`, commit `8295afc3c6424cf7f72c856977b997b18d244162`.
- **최우선 미검증**: GitHub Actions는 **격리 코드 CI**만 증명. ChatGPT 원래 정각 예약의 **공식 개별 per-run ID·실행 종료 상태·같은 회차 GitHub/Slack 도구 호출 원본은 미제공** → **정규 무인 기억 복원 성공 미검증**. 기존 예약·운영 플로우·main·알림·과금 설정은 변경하지 않음.
- **다음 목표**: 공식 Scheduled → AI → Previous runs에서 인증된 원본이 실제 제공될 경우에만 같은 회차 앱 호출을 독립 대조. 원본 없으면 미검증, 추정 실행 ID·비공식 API 우회 금지.

---


## 2026-10-23 12:20 KST — Python·JavaScript·Java 기존 15건 + 추가 12건 통합 CI 최신 성공
- **사용자 일반 채팅에서 수동으로 작업한 R16 교차 검증**. 기존 R16 정규 ChatGPT 예약의 무인 성공 증거는 아님.
- 공개 원본 조사: OpenTelemetry tool-call span과 Temporal workflow ID/run ID 구별, GitHub Actions의 branch/path 필터, Eclipse Temurin JDK+Python/Node 표준 검사 구조를 참고. 외부 오픈소스 프로그램 복제/추가 패키지 설치·유료 생성 API 호출 없이 격리 소스에서 최소 구현.
- R16 격리 브랜치에서 기존 15건 공통 자료(`fixtures/time_cases.tsv`, Python `test_polyglot_fixtures.py`, Node `check_js.mjs`, Java `R16TimeOrderCheck.java`) + 새 12건 자료(`polyglot/time_vectors.tsv`, Python `test_polyglot_vectors.py`, Node `test_activepieces_guard.mjs`, Java `R16TimeOracle.java`)를 **둘 다 보존**. 기존 JS 실제 `code()`를 import해 검사, Java는 `java.time`으로 독립 판단; 모든 합성 입력은 원본 진위 `UNVERIFIED`.
- **중간 통합 실패의 원인과 수정**: GitHub run `39894369222`는 Node 24가 더 이상 `--experimental-default-type=module`을 허용하지 않아 `node: bad option` / exit 9. 기존 자바스크립트 `.mjs` 파일의 Node 명령에서 **해당 옵션만 삭제**, 기존 테스트 포함 유지.
- **최신 공식 CI 성공**: 격리 워크플로 commit **`aca1087776b154f5febdfe94a2df6a45689121ff`**, GitHub Actions run **`39894432542`**, job/check **`120221459588`**, `push`, `completed/success`이며 Check run의 exact commit SHA 일치 독립 확인. 원시 job log: Python 기존 **44/44**, 추가 Python **2/2**, Node JS 실제 검증기 **12/12**, 기존 Node JS **15/15**, Java 새 oracle **12/12**, 기존 Java oracle **15/15** 모두 PASS. GitHub URL https://github.com/watersun79-source/ai-token-optimization/actions/runs/39894432542.
- 실제 사용한 원격 `.github/workflows/r16-evidence-verifier.yml` SHA **`d9b42318ed5fe4a8bc2139a2cd1a50edf17784a8`**, 최신 격리 README 원격 blob SHA **`fc7f918e15bbbc02a1a1a9d25f66d2920b429565`**. 마지막 README 업데이트는 docs만 변경하므로 동일 코드 SHA의 최신 CI 결과와 별도로 구분. 기존 `main`, 단일 매시간 정각 예약(활성 유지), Activepieces 운영, 알림, 비용·비밀 모두 변경 없음.
- **다음 최우선 목표**: 기존 ChatGPT Scheduled AI의 **공식 개별 per-run ID + 종료 결과 + 동일 회차 GitHub/Slack 원시 tool-call**이 실제 제공되는지 확인. `automations.peek.last_run_time`은 실행 메타일 뿐 원본 인증이 아니다. 원시 접근이 불가능하면 **정규 무인 성공 미검증** 유지.
---


## 2026-10-23 — 실제 오픈소스 참조 3언어 교차 CI 통과 (R16, 수동 채팅 작업)
- **ResearchBot 참고 결과**: 공식 Temporal의 Workflow ID ≠ Run ID, OpenTelemetry 도구 호출 span, JSON Schema의 언어별 공통 검증, LangGraph의 단기 checkpoint / 장기 store 구분 조사. Python jsonschema·JS Ajv·LangGraph MIT, Java networknt/Temporal SDK·OpenTelemetry Apache-2.0. 오픈소스 코드 직접 복제·라이브러리 설치 없이 검증기 설계와 경계 사례에만 반영. API 키·유료 모델·새 서버 사용 없음.
- **BuilderBot 적용 범위**: 격리 `ai/r16-evidence-reconciler-2026-10-22`에 `fixtures/time_cases.tsv` 15건, `tests/test_polyglot_fixtures.py`(Python 기존 검증기 호출), `polyglot/check_js.mjs`(기존 mock Activepieces JS 코드 직접 호출), `polyglot/R16TimeOrderCheck.java`(JDK java.time 나노초 독립 구현) 및 기존 별도 변경의 `R16TimeOracle.java`+ `time_vectors.tsv` 12건을 보존·통합. GitHub 격리 Actions의 실행 경로에 JS/Java 단계 추가. `main`, 예약 AI, Activepieces 운영 플로우 무변경.
- **VerifierBot 공식 독립 증거**: GitHub Actions **run `39894040301`**, head SHA **`446d2b277c8ee67a833b0b3fe7021ac33ed707e7`**, job/check **`120220187407`**, status **`completed/success`**. 실제 job log: Python **44/44 OK**, JS 공통 15/15, Java 공통 15/15, 별도 Java 경계 12/12, GitHub Actions 경고 0건. [공식 실행 링크](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39894040301). 앞선 중복 실행 `39893876739`의 `cancelled`와 구분. 신규 README 상세 기록: [격리 증거 문서](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/README_KO.md) blob **`2112a3dd16b2c8a5bfe9feac7fdd1525716c38f0`**.
- Activepieces 기존 MOCK ONLY 격리 flow `zgSopq6Txh68wxsDc5K5Z`는 계속 비활성·미게시, GitHub JS SHA `b378e7640a03b60ea86400e7d4c47602b27386fe`와 실제 CODE 내용은 **마지막 공백 줄 1개 차이 외 정확히 동일**. 새 Activepieces 게시/변경 없음. 예약 유일 ID `6acb017062a08191a4136238b78b313a`, `automations.peek is_enabled=true`, `paused_count=0`, 최근 메타 `2026-10-23T03:04:51.184022Z` (=12:04:51 KST), 매시간 정각/알림/프롬프트 변경 없음.
- **최종 구분**: GitHub 격리 코드의 **실제 자동 CI 성공 완료** vs ChatGPT 공식 예약의 **무인 GitHub·Slack 기억 복원 미검증**(native per-run ID·같은 회차 원시 호출 미제공). GitHub Actions ID를 ChatGPT 예약 run ID라고 주장하지 않는다.
- **다음 목표**: 공식 Scheduled → AI → Previous runs / 원시 tool-call ledger에 실제 접근이 제공되면 인증된 개별 회차에 대해서만 독립 대조. 그 전에는 기능 성공을 추정하지 않고 이미 성공한 코드 검사 반복 실행 금지.

---



## 2026-10-23 — R16 격리 원격 GitHub CI 실성공 43/43 × 2 (정규 ChatGPT 무인 성공과 별개)
- **기존 CI 0건 원인 규명**: main `.github/workflows/validate.yml`은 main 푸시/PR만, 격리 branch `ai-memory-bridge.yml`은 기억 branch 특정 파일 변경만 실행. R16 별도 CI 트리거 없었음. GitHub API 원본에서 저장소 Actions 전체 **94건**, main **37건**, R16 **0건**(격리 CI 생성 전), 격리 커밋 `5c92a3f73d252871dcb51274a1f95f4242cbdd00`의 전체 이벤트 Actions/Checks 0건 확인. GitHub Actions 기능 전반 고장 아님.
- **격리 브랜치 전용 CI 실제 생성**: `ai/r16-evidence-reconciler-2026-10-22` 의 `.github/workflows/r16-evidence-verifier.yml`. 정확히 해당 격리 branch push와 검증기 코드/테스트/워크플로 경로에만 트리거. `main` 무수정. 루트 테스트가 아닌 `experiments/r16-evidence-reconciler/tests` 기준으로 Python 3.12 표준 unittest 43건. 토큰 권한 `contents: read`, 무료 공개 저장소 + `ubuntu-latest` 표준 runner 사용, 외부 유료 API/비밀/AI 호출 0.
- **GitHub 원격 CI 첫 통과**: 생성 commit `5a851d978aa229787bfbead88b3359df2f6f30aa`; Actions 공식 run **`39891401115`**; Check/job ID `120211760208`; event push; status `completed/success`; 직접 재조회된 job logs `Ran 43 tests in 0.122s`, `OK`. 최초 Node.js20 deprecation 경고 확인.
- **최신 Action으로 경고 수정하고 다시 통과**: checkout/setup-python `@v7`, checkout `persist-credentials: false`; 소스 commit **`9cdaffad73b083a00d577e8771e154a66f1af58e`**, workflow blob **`dd9d1f192e65bc868552462d10384a114473e203`**. 공식 GitHub Actions run **`39891502065`**, Check/job **`120212092643`**, `completed/success`. 원시 로그 `Ran 43 tests in 0.094s`, `OK`, Node.js20 경고 **0건**. [실제 최종 CI 성공 링크](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39891502065). 이력과 원본 SHA: [격리 README](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/README_KO.md) blob `ca1173974fbff8609fcf1da586eb17e0919fec08`.
- **구분**: GitHub 공식 CI 성공 **완료·독립 검증**. ChatGPT Scheduled의 공식 per-run ID·같은 실행 네이티브 GitHub/Slack 호출 ledger는 현재 이 대화 API에서 제공되지 않아 **ChatGPT 정규 예약의 무인 복원·업무 성공은 여전히 미검증**. Actions run ID를 ChatGPT 예약 ID로 대체 금지.
- 보호: 기존 단일 예약 `6acb017062a08191a4136238b78b313a` 활성·정각·제목/프롬프트/알림 불변. 운영 Activepieces와 GitHub `main` 불변, 무료 우선 유지. 코드/테스트가 변경될 때만 자동 CI 재실행, 통과한 테스트를 무의미하게 수동 반복하지 않음.
- **다음 목표**: 공식 ChatGPT `Scheduled → AI → Previous runs`의 해당 회차 원시 로그/앱 사용 승인 상태 실제 제공 시 같은 회차 앱 호출을 검증, 제공 없으면 미검증 유지.

---


## 2026-10-23 11:43 KST — 모든 이벤트 GitHub Actions·Checks 실제 재대조
- **이 항목은 일반 ChatGPT 채팅 수동 읽기 전용 대조**. ChatGPT 기존 정규 예약이 자체 실행한 원본 증거가 아니다.
- 기존 R16 `6acb017062a08191a4136238b78b313a`: `automations.peek` 원본 `is_enabled=true`, `paused_count=0`, 매시간 정각(Asia/Seoul), `last_run_time=2026-10-23T02:06:18.531665Z` (= **11:06:18 KST**), schedule/title/prompt/alerts/email 설정 변경하지 않음. 이 값만으로 실제 run 완료 시각·도구 실행 결과를 주장할 수 없음.
- 이전 보고의 `fetch_commit_workflow_runs`는 PR 필터 + 첫 페이지이므로 `workflow_runs=[]`로 push 기반 CI의 부재를 확정할 수 없다는 문제를 **GitHub REST 전체 이벤트 조회**로 실제 해소: `GET /repos/watersun79-source/ai-token-optimization/actions/runs?per_page=100` → `total_count=94`, `main` 지정 → 37건, R16 기억 브랜치 → 5건, R16 격리 검사 브랜치 → 0건(이번 조회 시점, 저장소의 모든 워크플로우 실행을 뜻하는 단일 집계). 이전 Commit Status 0건과 GitHub Actions Checks는 별개.
- **현재 `main` HEAD 원본** `GET /branches/main` → SHA **`e8600906eb31da2735108842752a93887791f0c5`**. 정확히 동일 SHA의 `push` Actions run **`39680499361`**, `completed / success`, `2026-10-21T21:39:03Z` (= **2026-10-22 06:39:03 KST**), 원본 `jobs` 1건 `test` success, `Python regression`, `Compare JavaScript validator`, `provider-free review metadata guard` 각 step success. 동일 SHA의 `check-runs` 1건 `test` success. **현재 main HEAD와 검증된 CI가 정확히 일치**.
- **PR #1 병합 후**: Pull Request 원본 `merged=true`, merge SHA **`840e7142779d4a66938b334c71ca41f5a92e49b2`**, 2026-10-19T13:39:01Z. 같은 SHA `push` Actions run **`39261957043`**, `completed / success`, 실제 `test` job success, Python·JS 단계 success, `check-runs` 1건 success.
- **PR #4 병합 후**: Pull Request 원본 `merged=true`, merge SHA **`297d1d2d52e213e0b3c93c93d74e322fb11e744b`**, 2026-10-19T13:39:32Z. 같은 SHA `push` Actions run **`39262028914`**, `completed / success`, 실제 `test` job success, Python·JS·provider-free guard 단계 success, `check-runs` 1건 success.
- **현재 main에 두 병합 포함 독립 검증**: `compare/{PR#1 merge SHA}...main` → `status=ahead, ahead_by=6, behind_by=0, merge_base=PR#1 merge SHA`; `compare/{PR#4 merge SHA}...main` → `status=ahead, ahead_by=3, behind_by=0, merge_base=PR#4 merge SHA`. 두 병합 커밋 모두 현재 main의 조상임.
- **R16 격리 검사 현재 CI와 혼동 금지**: `ai/r16-evidence-reconciler-2026-10-22` 브랜치의 GitHub Actions 0건. 이 브랜치의 최신 `Python unittest 43/43`는 사용자가 채팅에서 실행한 **수동 로컬 검증**이고, GitHub CI 통과는 직접 검증되지 않았음. R16 기억 브랜치 과거 5개 push CI success는 2026-10-21 커밋이며 **현재 기억 브랜치 HEAD의 CI 성공을 뜻하지 않음**.
- **예약 무인 성공 별도 미검증**: ChatGPT 공식 개별 per-run ID/terminal status/동일 회차 GitHub·Slack 원본 도구 호출 ledger는 현재 연결 도구로 미제공. Activepieces 2026-10-23 감사 행 0, 11:00~11:45 지정 Slack 신규 기록은 채팅 수동 기록 외 독립 증거 확인 불가. 오프라인/CI 통과 ≠ 예약 무인 성공.
- 원본 링크: [main HEAD Actions](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39680499361), [PR #1 병합 Actions](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39261957043), [PR #4 병합 Actions](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39262028914). GitHub main·Activepieces 운영 및 연결·기존 예약 설정·비용/비밀정보 변경 없음.
---


## 2026-10-23 11:00 예약 메타 및 CI 조회 범위 정정 — 수동 읽기 전용 감사
- 기존 유일 R16 예약 `6acb017062a08191a4136238b78b313a`를 `automations.peek`로 다시 조회: `is_enabled=true`, `paused_count=0`, Asia/Seoul 정각, `last_run_time=2026-10-23T02:06:18.531665Z` (=11:06:18 KST), 주기·제목·프롬프트·알림 불변. **정규 회차 공식 run ID·완료 상태·동일 회차 원시 GitHub/Slack 호출 로그는 미제공 → 무인 성공 미검증**.
- Activepieces `AI Scheduled Run Evidence (AUDIT ONLY)` 테이블의 2026-10-23 검색 행 `0`; Slack 자정 이후 검색에는 사용자 채팅에 의한 수동 점검/수정 기록만 식별됨. 실제 정규 예약 성공·실패 어느 쪽도 증명하지 못함.
- **새로 발견한 CI 조회 한계**: 연결된 `mcp__GitHub__fetch_commit_workflow_runs`는 **PR 이벤트에서 발생한 첫 페이지**의 실행만 검색한다. 따라서 `workflow_runs=[]`는 push 등 모든 이벤트의 실행 부재 증거가 아니다. `get_commit_combined_status`의 `statuses=[]` 또한 **Commit Statuses**만 의미하고 GitHub Actions **Check runs/check suites**를 대체하지 않는다. GitHub 공식 [statuses 문서](https://docs.github.com/en/rest/commits/statuses)도 두 API를 구분. 전체 원격 CI는 **미검증**(실패 확정 아님).
- 기존 전체 Python 로컬 회귀 `43/43 PASS`, 원격 소스 SHA 4/4 검증은 그대로 유지하고 변경 없는 테스트 반복 금지. 격리 브랜치 상세 수정 기록: [README_KO.md](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/README_KO.md).
- 다음 공식 증거 확보: GitHub 모든 이벤트의 Actions run + Checks, ChatGPT Scheduled → AI → Previous runs의 인증된 개별 회차 ID/도구 호출. 현재 도구 미노출은 접근 불가로 정확히 보고하고 우회하지 않음. 기존 예약·Activepieces 운영·main·유료 API·비밀정보 변경 없음.

---


## 2026-10-23 후속 — 수동 Python 전체 43/43 통과 (정규 예약 성공 아님)
- **작업의 출처**: 사용자 직접 채팅의 `실행` 요청에 따른 수동 오프라인 검증. 정규 ChatGPT 예약이 Python을 호출했다는 증거로 오인 금지.
- 격리 GitHub `ai/r16-evidence-reconciler-2026-10-22`의 최신 Python 검사기 + 단위 테스트 3개 파일을 로컬에 복원하고 `git hash-object` SHA-1을 원격 GitHub blob과 **4/4 완전 일치** 확인. 코드 `05fcfd2eac1b76d2e2f351e749a90647347a88aa`, 테스트 `a1d68fbfad6c39218211f19a869c0f6f933726b6`, CLI 테스트 `e417f706e9b8f760987d17de72708ad4863047f0`, 연결 도구명 테스트 `6e1623d0797473a34cdd21b0292095c40d45cb09`.
- **실제 Python 3.13.5** `python3 -m unittest discover -s tests -v`: `Ran 43 tests in 10.953s`, `OK`, 실패 0건. 나노초 타임스탬프 회귀 4개를 포함한 **현재 코드 전체 43/43 PASS**. 과거 39/39와 구분하고, 동일 소스에서는 이 검사를 불필요하게 재실행하지 않는다.
- 격리 브랜치 [검증 결과 README](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/README_KO.md) GitHub 실제 commit `7d05698e89eb30dc1fe36efa7b0e9281987c28b2`, blob `7284e7e87b65f78703d2173f3ce0486e2b13f94b`, 별도 원격 읽기 일치.
- GitHub 해당 테스트 커밋 `5c92a3f73d252871dcb51274a1f95f4242cbdd00`의 Actions workflow_runs 및 statuses가 빈 목록이라 **원격 CI 성공은 미검증**. 기존 보호 예약 `6acb017062a08191a4136238b78b313a`는 `is_enabled=true`, `paused_count=0`, Asia/Seoul 매시간 정각, 마지막 시각 메타 `2026-10-23T01:00:54.365515Z` (=10:00:54 KST). 새 예약·일정·활성·알림 변경 없음.
- **가장 중요한 미완료**: ChatGPT 개별 예약 공식 per-run ID·종료 상태·같은 회차 GitHub/Slack 원시 호출 원본은 이 도구에서 제공되지 않음. 그래서 **무인 성공 미검증** 유지. 수동 GitHub 커밋/Slack 알림/Activepieces TESTING run과 공식 무인 성공을 혼동하지 않는다.
- 다음 최우선: 공식 Scheduled → AI → Previous runs 또는 지원되는 공식 연결 도구에서 실제 개별 회차 로그·승인 대기 여부가 확인될 경우에만 같은 회차 독립 교차 검증. 운영 Activepieces·main·예약 설정 보호 및 무료 우선.

---


## 2026-10-23 10:56 KST — 최신 R16 Python 원격 원본 43/43 전체 회귀 실측
- 사용자가 일반 채팅에서 `실행`을 요청한 **수동 오프라인 검사**. 정규 ChatGPT 매시 정각 회차의 무인 GitHub·Slack 성공을 뜻하지 않는다.
- `automations.peek` 원본: 기존 단일 R16 ID `6acb017062a08191a4136238b78b313a`, `is_enabled=true`, `paused_count=0`, Asia/Seoul 매시 정각, 최근 `last_run_time=2026-10-23T01:00:54.365515Z`(10:00:54 KST). 일정·활성·알림·프롬프트 변경 없음.
- 10:26경 격리 브랜치에 이미 반영된 새 Python 나노초 원본 검사 수정·회귀 테스트 4개를 GitHub read-only로 확인. 코드 blob `05fcfd2eac1b76d2e2f351e749a90647347a88aa`, 주요 테스트 blob `a1d68fbfad6c39218211f19a869c0f6f933726b6`, CLI 테스트 `e417f706e9b8f760987d17de72708ad4863047f0`, connected tools 테스트 `6e1623d0797473a34cdd21b0292095c40d45cb09`.
- 정확히 위 두 GitHub 커밋 원본 patch만 로컬 격리 복제에 적용하여 네 파일의 **Git blob SHA 4/4 완전 일치 검증**. `python -m unittest discover -s tests -v` 실제 로컬 실행 **43/43 PASS, exit 0**, 새 나노초 4테스트 포함. 기존 GitHub 노트의 '최신 43건 전체 미실행' 제한을 이번 수동 테스트로 해소. 그 외 GitHub CI/공식 예약 실행의 검증은 별개로 유지.
- 동일 내용을 격리 브랜치 `experiments/r16-evidence-reconciler/README_KO.md`에 기록하고 GitHub 원격 재조회: blob `d369e44e8f900fe1ae260b3bd3b50a4de6bae010`, commit `2e0a3fd40167df389a8ea826d53aabddd4f7f3a1`.
- 해당 슬롯 `ChatGPT 공식 개별 per-run ID`, `run_details` 원본 종료 상태·동일 회차 원시 GitHub/Slack 호출을 현재 도구로 조회할 수 없으므로 **무인 성공 미검증**. 기존 운영 Activepieces, GitHub main, GitHub CI, 과금/비밀정보 변경 없음.

---

## 2026-10-23 10:21 KST — 정규 회차 종료 경계의 검증기 불일치 수정
- 사용자의 `실행` 요청에 의한 **수동 ChatGPT 격리 작업**. 공식 예약 R16 `6acb017062a08191a4136238b78b313a`는 `is_enabled=true`, 매시 정각, 최근 `last_run_time=2026-10-23T01:00:54.365515Z`(10:00:54 KST). 개별 회차 원본 run ID/도구 호출 ledger는 미제공으로 **무인 성공 미검증**.
- GitHub Python 원본 SHA `70683e029c525462a55f013701be1e806e6b1e2d` + 일치하는 로컬 Git blob으로 **슬롯 10:00/완료 11:00** 모의 입력을 확인: `형식 통과 · 진위 미검증`. 격리 Activepieces JS 동일 입력은 `end < next-slot` 때문에 `Run timestamps inconsistent` → 수정 전 `TESTING` 원본 run `4VDnVPPKRaVvlpDhfQnWX`.
- 격리 MOCK ONLY Activepieces flow `zgSopq6Txh68wxsDc5K5Z` JS 종료 경계 `<= next-slot`로 최소 변경 (Python 정책과 동기화). 수정 후 실제 `ap_test_flow`+독립 `ap_get_run` **4/4**: `xmIcVTEjePms5okYRmYPM` 경계 정확히 포함, `XrUFMiKfToISQWUJHRNKr` 1ns 전 포함, `A8LyP62BssgPzvoK4CUMB` 1ns 후 거부, `Qza2RyENPtecV2kXX8ovo` 공식 로그 누락 거부. 전부 `official_success_verified=false` / `status=UNVERIFIED` / `external_calls=0` (TESTING `SUCCEEDED`는 테스트 스텝 실행 완료만 뜻함).
- 변경 JS GitHub 격리 blob `b378e7640a03b60ea86400e7d4c47602b27386fe`, `ap_read_step_code`와 remote read-back exact 일치. [상세 원본](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/ACTIVEPIECES_MOCK_SAFE_FLOW_2026-10-22.md) 문서 blob `c0f39bec1743dd639efc66983a7270c1d5bc05cf`.
- 사용자가 보호 지시한 단일 정규 예약(활성·일정·프롬프트·알림), GitHub main, Activepieces 운영 플로우/연결, 비용·비밀은 변경 없음. 다음 우선 목표는 공식 개별 예약 run ID와 GitHub·Slack 동일 회차 원본 호출 확보이며, 데이터가 없으면 미검증을 유지.

---

## 2026-10-23 10시대 — Python 나노초 정확도 오류 2개 수정, JS 독립 교차 검증
- **사용자의 일반 채팅 '실행' 요청에 따른 수동 격리 수정**, 기존 정규 예약의 무인 성공 증거가 아님.
- `automations.peek`: 단일 기존 R16 ID `6acb017062a08191a4136238b78b313a`, `is_enabled=true`, Asia/Seoul 매시간 정각, `last_run_time=2026-10-23T01:00:54.365515Z` (=10:00:54 KST). 일시정지 0, ID/일정/프롬프트/알림 수정 없음. 10:00 이후 기존 기억·격리 GitHub 커밋 조회(당시) 0, 지정 Slack 스레드 신규 0, Activepieces 오늘 AUDIT 기록 0; 수동/자동 원시 조회 부재로 무인 성공은 계속 미검증.
- **Python 독립 테스트 신규 오류 발견**: `datetime.fromisoformat`은 소수초가 6자리보다 길 때 나머지를 자를 수 있어, `2026-10-22T22:00:00.000000001+09:00` (실제로는 정각 +1나노초)을 정각으로 오판. `target_slot`과 `native_run.scheduled_for` 두 경로에서 실제 원격 버전의 모의 입력을 `형식 통과`로 잘못 판정함. 추가한 두 회귀 테스트가 패치 전 **2/2 실패**.
- **격리 Python 수정**: 문자열 단계의 엄격한 `EXACT_HOUR` (`(?:\\.0+)?`만 허용) 검사를 두 슬롯에 추가. 기존 테스트 포함 Python unittest **39/39 PASS**, 정상 정각의 `.000000000`은 유지하며 미인증 결과는 항상 `official_success_verified=false`. 최신 GitHub `audit_v2.py` blob **`70683e029c525462a55f013701be1e806e6b1e2d`** commit `c8aff856012d29c05cac490c41bff5873f9340aa`, `tests/test_audit_v2.py` blob **`0bf74ed8b5da2abb95f61ef619cc393b04ef583c`** commit `7259b10cade177bdd88a53288ecb0da5a10583fe`; GitHub 원격 fetch read-back exact 일치.
- **JS 동시 변경 보호 및 독립 교차 확인**: 별도 10:06 KST GitHub 커밋 `dd756f0c03482b73e8a718663acc79303ee7f1b9`가 격리 Activepieces JS의 시각 계산을 `BigInt` 나노초로 변경했음. 정규 예약과의 인과관계 증거 없음. 이미 반영된 코드를 **덮어쓰지 않고** Activepieces `ap_read_step_code`와 GitHub 코드 blob `d98d9842191e4e17753c56620800c7eca541e0b9`의 정확한 일치 확인. `ap_test_flow`+ `ap_get_run` 3건: 정상 정각 `CioiC4q4xgLiliQPZ4tw8` 형식만 통과, 나노초 오류 타깃 슬롯 `XgL5fenmcFYHEb4RoT4YP` 거부, 나노초 오류 공식 슬롯 `PNo2qepQawJwgrKDTnJAi` 거부. 모두 테스트 환경 `SUCCEEDED`이지만 **`status=UNVERIFIED`, `official_success_verified=false`, `external_calls=0`**.
- Activepieces 격리 MOCK flow `zgSopq6Txh68wxsDc5K5Z`는 여전히 DISABLED/unpublished, 기존 운영 Slack flow `vtRwEYmcwDTunBZut265G` 보호. GitHub `main`, 유료 API·결제, 원래 예약 프롬프트/주기/알림 쓰기 없음.
- **다음 유일한 무인 완료 목표**: ChatGPT 플랫폼 공식 per-run ID + 같은 회차의 실제 GitHub·Slack 원시 tool-call ledger 확보. 현재 도구에 없는 실행 원본의 출처를 문서/모의 자료로 만들어내지 말 것.

---

## 2026-10-23 오전 09시대 수동 R16 격리 검증기 JS/Python 불일치 2건 수정
- 실제 Activepieces 격리 flow `zgSopq6Txh68wxsDc5K5Z`의 CODE step과 GitHub Python `audit_v2.py` 형식 검사 기준을 직접 대조해 **두 가지 재현 가능한 결함** 발견: JS는 16개 초과 도구 호출 전체 거부(반면 Python 1024개 허용), 예약 정각의 `.500`초도 허용(반면 Python 거부).
- Activepieces `TESTING` 사전 재현 원본 run `Cu3LhqTJjKWmUW6Hmgs3h`(17건 오거부), `mZWYX0E1gvuqK7pM9eMgv`(`.500`초 오통과). 실제 기존 플로우가 아닌 **비활성·미게시·MOCK ONLY** 검증기에서만 수정.
- JS CODE를 최소 수정(`>1024` 제한, `(?:\\.0+)?` 정각 소수부 검사), 17건/1024건 허용, 1025건/.500초 거부, .000초 허용, 공식 run 누락 거부 **6/6 실제 Activepieces TESTING·ap_get_run 검증**. 각 결과 `official_success_verified=false`, `external_calls=0`, 원본 진위 `UNVERIFIED`.
- 변경된 격리 JS GitHub blob `f75bd4ccc4934032cc5ab62b8ea52ed26545be49` (actual CODE step read-back exact match). [상세 모의실행 ID·결과/문서](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/ACTIVEPIECES_MOCK_SAFE_FLOW_2026-10-22.md), 문서 blob `2864d5cb39e24d8ed6078ea9e4f5b1e8f2c84eb8`.
- 실제 활성 운영 flow: 기존 Slack `vtRwEYmcwDTunBZut265G` 1개. 격리 MOCK flow는 `DISABLED`, `published=false`, `ap_validate_flow valid=true`, 2/2 단계, issues 0. 정규 예약 R16 `6acb017062a08191a4136238b78b313a` 활성/한국시간 매시간 정각, 마지막 관측 `last_run_time=2026-10-23T00:00:35.077362Z`(09:00:35 KST), 일정/프롬프트/활성화/알림 변경 금지 및 이번 회차에서 설정 변경 없음.
- **핵심 구분:** 이 검증은 사용자의 요청으로 시작한 **수동 ChatGPT 채팅**과 Activepieces 모의 테스트의 품질 검사일 뿐 정규 무인 실행 성공 증거가 아니다. 공식 per-run ID·동일 회차 원본 GitHub/Slack 호출 로그는 미제공 → 무인 성공 **미검증**.

---

## 2026-10-23 09:00 KST — 수동 R16 최신 검증기 37/37 및 공식 실행 원본 부재
- **작업 출처**: 사용자의 `실행` 요청으로 **일반 ChatGPT 채팅에서 수동 실행**한 감사다. 09:00 예약 세션이 실행한 검사로 표기하지 않는다.
- **예약 공식 메타 원본**: 기존 단일 ID `6acb017062a08191a4136238b78b313a`, `is_enabled=true`, Asia/Seoul 매시간 정각, `last_run_time=2026-10-23T00:00:35.077362Z` (=09:00:35 KST), paused_count=0; 이는 정규 슬롯 시각 메타일 뿐 개별 작업 성공이 아니다.
- **GitHub 현재 인계**: 사용자 기억 브랜치 본 문서 blob SHA `5c1c74471346de1e29d62680a0f6798fc82ac20f`를 수정 *전에* 직접 읽음. 09:00~09:22 KST 사이 `main`, 기억, 격리 테스트 3개 브랜치 신규 커밋 0건. 같은 시간창 지정 Slack 부모 스레드/채널에서 새 응답·기록 0건. Activepieces 2026-10-23 감사 행 0, 기존 운영 Slack flow만 ENABLED, 별도 MOCK flow는 DISABLED/미게시.
- **실제 최신 파이썬 검증기 독립 실행**: GitHub 4개 파일 blob SHA `audit_v2.py=21a716f3093bed229b5d0f366709d08d55ab8abe`, `tests/test_audit_v2.py=4c5834ee0e872bb9758a438a63ce689d5691677d`, `test_connected_tool_names.py=6e1623d0797473a34cdd21b0292095c40d45cb09`, `test_cli_exit_codes.py=e417f706e9b8f760987d17de72708ad4863047f0`. ZIP 보관본을 격리에서 복원한 후 GitHub 실제 커밋 `f46d4a7b0c2de3b28f033f241f26039cea2698a5`과 `1c74f2321cf1c3d2f663760af9e23869aa5188b0`의 *정확한 수정 내용만 반영*. 네 파일 모두 로컬 SHA1 Git blob과 현재 GitHub 원격 SHA **4/4 일치 확인**, Python unittest **37/37 통과**(수동 테스트).
- **09:00 예약 입력 검사**: `native_run=null`, `tool_calls=[]` (실제 공식 플랫폼 원시 실행 상세/도구 호출 로그는 이 채팅에 노출되지 않았기 때문). `audit_v2.py --input` 실제 subprocess 종료 코드 `2`, 출력 `status=미검증`, `official_success_verified=false`, `reason=공식 개별 회차 원본 로그 미제공`. 외부 앱 도구의 수동 READ 및 변경 없는 무소식은 예약 본체의 무인 성공 증거가 아니다. **정규 예약 무인 성공: 미검증**.
- **다음 최우선**: 플랫폼에서 공식 개별 예약 회차 run ID·종료 결과·동일 회차 GitHub/Slack 원시 호출이 합법적으로 제공될 경우에만 대조. 허가·로그 접근 제한 우회 금지. 예약 일시정지·삭제·신설/일정 변경 금지. 운영 Activepieces·GitHub main·비밀/과금 불변.

---

## 2026-10-23 07:12 KST 긴급 상태 변화 — 일시정지 발견 후 활성 복구
- **첫 예약 상태 원본 조회 07:11~07:12 KST**: 기존 R16 정확한 예약 ID `6acb017062a08191a4136238b78b313a`가 `is_enabled=false`, `paused_count=1`로 변경된 것을 `automations.peek`에서 직접 확인. 당시 메타 `updated_at=2026-10-22T22:11:40.258672Z`(07:11:40 KST), `last_run_time=2026-10-22T22:01:12.762052Z`(07:01:12 KST).
- **사용자 기존 명시 지시 '예약 AI 일시정지 금지/활성 유지'에 따라 즉시 복구**: 공식 `automations.update(jawbone_id, is_enabled=true)` 1회 성공. 새 메타 `updated_at=2026-10-22T22:12:07.678750Z`, 기존 제목/프롬프트/일정/시간대/예약 ID/알림·이메일 설정 유지. 별도 `automations.peek` 재조회에서 `is_enabled=true`, `paused_count=0` 확인. 새 예약을 만들거나 기존 예약을 삭제하지 않았음.
- **왜 정지됐는지 실제 로그는 미제공, 원인 단정 금지**: OpenAI 공식 [Scheduled tasks 도움말](https://help.openai.com/en/articles/10291617-scheduled-tasks-in-chatgpt) 및 [앱 트러블슈팅](https://help.openai.com/en/articles/20001497-troubleshooting-plugins-and-apps-in-chatgpt)은 추가 승인 필요, 앱 접근 문제 및 자동 비활성화 가능성을 설명하나, **이 회차의 특정 원인은 플랫폼 개별 실행 기록/승인 대기 화면에서 확인해야 함**. 자동화 도구는 활성/프롬프트/last_run_time만 제공, 일시정지 작업자 및 이유 로그는 제공하지 않음. 필요한 사용자 승인·연결이 있으면 Scheduled의 해당 R16 → Previous runs/승인 대기 확인. 과거 권한 거부 우회/쓰기를 재시도하지 말 것.
- **복구 후 분리 확인**: GitHub `main`/격리 기억 브랜치 정규 07시 이후 새 커밋 0건, Activepieces 감사 테이블 2026-10-23 날짜 행 0건, Slack의 07:00 이후 글은 수동 채팅 기록만 확인. 읽기 호출의 부재를 증명하지는 않음. **정규 회차 GitHub/Slack 무인 성공은 아직 미검증**.
- **보호 범위**: GitHub `main` 및 운영 Activepieces 플로우/연결, 유료 API 건드리지 않았음. 복구 외에 R16의 주기/프롬프트/시간대/알림/제목 변경 없음. **다음 최우선: 정지 원인(승인 대기·계정/앱 권한·제품 자동 일시정지 여부) 공식 실행 화면에서 확인 및 활성 상태 재검증**, 추가 정지 금지.

---

## 2026-10-23 아침 후속 — 누락된 00:07 커밋 3개 + 도구명 별칭 격리 수정
- 현행 예약 ID `6acb017062a08191a4136238b78b313a`, `is_enabled=true`, Asia/Seoul 매시간 정각, 10/23 마지막 `last_run_time=2026-10-22T21:00:49.759834Z`(=06:00:49 KST). 예약 설정 수정·중지 없음. 이는 *예약 실행 시각 메타데이터*이며 실제 앱 작업 결과가 아님.
- **자정 이후 GitHub 원본 새 발견**: main/기억 브랜치는 신규 커밋 0건이지만 **격리 브랜치** `ai/r16-evidence-reconciler-2026-10-22`에 10/23 **00:07:21, 00:07:44, 00:08:10 KST** 커밋 3건이 실제 존재한다: `f5986dbc7f9f1f6ca04f94d1823709ab7c7875c6` 테스트, `a5d54e757887d16b51868c8177334e0992b65a32` 검사기 연결 앱 도구명 별칭, `f7a2cfbb30288feffee122ca0528281a048a6892` 설명. GitHub 작성자 watersun79-source, 전부 unsigned. 00시 정규 예약과 시각상 연관 가능하나 **공식 native per-run ID 및 tool-call ledger 독립 검증 없음 → 무인 성공 미검증**. 00:08 README 내 `run_details.last_run.id` 제공 주장은 **당시 문서의 자기 보고**이며 현 채팅 플랫폼 API readback 아님.
- 격리 Activepieces `MOCK ONLY · AI R16 evidence verifier · isolated` `zgSopq6Txh68wxsDc5K5Z`도 구 도구명만 수용하던 불일치를 테스트 `o4UG1IpKOrd4AMX7hS1Mv`로 재현·수정. ChatGPT Work alias `mcp__codex_apps__github_fetch_file`, `mcp__codex_apps__slack_slack_read_thread`를 원래 이름과 함께 정확히 허용. 형식만 통과해도 결과는 반드시 `UNVERIFIED`, `official_success_verified=false`.
- Activepieces 격리 `TESTING` 신규 회귀 **5/5 통과**, 원본 `ap_get_run` 확인. GitHub 격리 JS 소스 blob SHA `ffd1b3f351808f22bcab4feec5f42762e0f6ebea`, read-back 완료. [상세 검증 기록](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/ACTIVEPIECES_MOCK_SAFE_FLOW_2026-10-22.md).
- ChatGPT Scheduled의 직접 개별 회차 결과/원본 호출 조회는 현재 채팅 연결 도구에 미노출. 수동 TESTING 실행이나 자체 GitHub 커밋은 대체 불가. 새 예약/유료 API/운영 Activepieces/ GitHub main 변경 없음.

---

## 최신 예약 R16 다음 진행 목표 등록 — 2026-10-22 23:42 KST
- **사용자 새 지시**: "진행. 다음 진행 목표는 예약 ai 등록. 진행" → 기존 **단일 예약 ID** `6acb017062a08191a4136238b78b313a`의 **프롬프트만** 갱신해 다음 진행 목표를 직접 등록함. 새 예약/중지/일시정지/시간대 변경 없음. 제목 AI, Asia/Seoul 매시간 정각, `is_enabled=true`, 기존 `notifications_enabled=false`, `email_enabled=false` 재조회 유지. 실제 `automations.update` 성공 및 별도 `automations.peek` readback으로 저장 확인; `updated_at=2026-10-22T14:42:47.055881Z`.
- **새 최우선 목표**: 매 정규 회차에서 ChatGPT 예약의 공식 개별 실행 ID·종료 상태·원시 GitHub/Slack 앱 호출 로그 제공 여부를 확인하고, 같은 회차의 SHA/ts를 독립 대조. 없다면 반드시 `무인 성공 미검증`. 해당 실행 세션에 실제 연결 앱이 제공될 때 최신 GitHub 기억 인계·Slack을 먼저 복원하고, 가능한 안전한 범위 내에 분석→최소 수정→테스트→원격 readback→보고. 새로운 다음 목표 1개를 **회차 보고 내에서** 이어서 설정; 설정 때문에 예약을 추가하거나 임의 수정하지 않음.
- **R16 코드 현황**: 격리 `ai/r16-evidence-reconciler-2026-10-22`의 `experiments/r16-evidence-reconciler/` Python 감사 검증기, 마지막 로컬 27/27 테스트 통과. 공식 개별 예약 run ID와 원본 호출 로그는 이전 22:00/23:00에 대해 아직 제공되지 않아 무인 성공 **미검증**. 코드 자동 배포/실제 예약 세션 Python 가용성을 추정하지 않음.
- **보호**: GitHub `main`, 운영 Activepieces 플로우/연결/기록, 별도 예약, 비용·키, 이전 알림 상태는 변경 없음. 현재 문서 수정과 Slack 알림은 **사용자가 채팅에서 직접 승인한 등록 작업의 기록**이며 무인 예약 자체의 자동 앱 호출 증거가 아님.

---


## R16 검증 기준 최신 보완 — 2026-10-22 23시 이후
- **새로 발견·실제 수정**: 기존 격리 실행 증거 검사기가 과거 R13에서 사용했던 `PROJECT_MEMORY_INDEX.md`·`AI-memory-protocol.md`·오래된 unattended-report의 3개 GitHub 원본을 R16 필수로 요구하는 불일치. 실제 R16 프롬프트는 **`docs/ai/AI_CURRENT_HANDOFF_2026-10-22.md` 인계 읽기 우선**이므로 정상 회차여도 false-negative 가능.
- **수정 완료**: 격리 브랜치 `ai/r16-evidence-reconciler-2026-10-22`의 검사기 필수 호출 `current_handoff` + `slack_thread`으로 조정. R13 자료만 있으면 R16 검증 불충분 처리. R16 선택 문서는 optional 취급. 공식 원본 실행 ID·동일 회차 원시 호출 로그가 없을 때는 여전히 `미검증`을 엄격 유지.
- **재현·재검증**: Python 27/27 통과, *검사기* GitHub blob SHA `eb3387b724e32e352b7eef8655e8997a3b843eaa`, *테스트* SHA `0139caeb04e8e0a0b51532d447467a8ca12b611e`를 GitHub 재조회 및 로컬 `git hash-object`로 대조. [격리 브랜치 기록](https://github.com/watersun79-source/ai-token-optimization/blob/ai/r16-evidence-reconciler-2026-10-22/experiments/r16-evidence-reconciler/README_KO.md).
- **여전히 미완료인 목표**: R16 22:00/23:00 공식 개별 실행 ID 및 예약 무인 GitHub/Slack 앱 호출 원본 증거는 현재 도구에서 미제공. **수동 채팅에서 한 테스트·메시지 작성은 정규 무인 예약 성공의 근거가 아니다.**
- 기존 AI 예약 ID/프롬프트/활성/일정·알림/Activepieces·GitHub `main` **변경하지 않음**. 이 문서 갱신은 사용자의 수동 채팅 작업.

---

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
