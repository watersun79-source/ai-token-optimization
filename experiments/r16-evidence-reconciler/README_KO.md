# R16 무인 예약 실행 증거 대조기 — 격리 개발 브랜치


## 2026-10-23 15시대 후속 — 동시 기여 변경·URL 바이디 검사 재조회, Python 72/72 최종 성공
- **신규 변경 충돌 감지·직접 대조**: 첫 OWASP URL 검증 변경은 코드 blob `de90d1460fc60c9e86d1852e8483802ed544f2b5`, 테스트 5건 blob `ac4571e96b9f30c70423987fbd84c6c50640624e`, GitHub run `39909757804`에서 Python 68/68 성공. 이후 **별도 기여의 변경**으로 최신 `bot_team_r16.py` blob `b3bc27702347029f8c28352b72917d5524baa977`에 `unicodedata.category(c).startswith('C')`를 이용한 bidi/숨은 제어문자 제목 차단이 추가됨. 같은 격리 브랜치에 `tests/test_bot_untrusted_references.py` 4건 추가, blob `2137942c4d282c685f0f38e258270a38a4663005`. 앞선 코드 SHA는 **패치 이력**이지 현행 최종 SHA가 아니므로 구분.
- **최신 원격 CI 원본 재조회**: [Actions run `39910021477`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39910021477), head SHA `97893289a61eb2c6e12fbe204ab1e834f5ceba2b`, 공식 Check/job `120270605065`, `completed/success`. 직접 조회한 원시 job log: Python 전체 **72/72 OK** (68 + 추가 4), Python 별도 다국어 2/2 OK, JavaScript 20/20 PASS, Java 공통 20/20 PASS, 추가 Java oracle 12/12 PASS, 경고 0. 직전 중간 커밋 run `39909896111`은 `failure`였으나 최종 성공으로 수정된 상태를 구분.
- **실제 수행 범위**: 사용자 일반 ChatGPT 지시에 따른 GitHub 격리 코드·표준 CI 검증. Microsoft Agent Framework Go (MIT, 미성숙 public preview), Pydantic AI (MIT), OWASP의 URL parser 방어 지침을 참고했으나 새 유료 API/모델 실행, 외부 에이전트 프로세스·패키지 설치 없음. 본 R16 ResearchBot은 제공된 Github URL *메타데이터* 검사만 하고 외부 원본 진위 확인은 계속 별도 필요함.
- **보호/미해결**: 기존 매시간 정각 예약 ID `6acb017062a08191a4136238b78b313a`, `is_enabled=true`, `paused_count=0`, 최근 `last_run_time=2026-10-23T06:07:08.222410Z` (=15:07:08 KST)는 트리거 메타. 예약 스케줄/알림·Activepieces 운영·GitHub main 불변. ChatGPT Scheduled **native per-run ID/같은 회차 GitHub·Slack 원본 호출이 제공되지 않아 무인 업무 성공 = 미검증**. 다음 목표는 공식 Previous runs 원본 접근을 확인하는 것뿐, 기실행 CI를 사용자 예약 성공으로 오인하지 않음.

---



## 2026-10-23 15시대 — OWASP 참고 AI Bot GitHub 출처 URL 검증 강화
- **새 외부 구현 조사**: [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)에서는 입력 URL을 그대로 신뢰하지 말고 허용 대상과 파서 차이를 엄격히 점검하라고 권고. [Python urllib.parse 공식 문서](https://docs.python.org/3/library/urllib.parse.html#url-parsing-security)는 `urlsplit`이 입력을 검증하지 않는다고 명시. [Pydantic AI](https://github.com/pydantic/pydantic-ai) MIT는 durable execution과 일반 영속 저장을 구분하고, [Microsoft Agent Framework Go](https://github.com/microsoft/agent-framework-go) MIT는 공개 프리뷰. 패키지 설치·LLM API 호출 없이 기존 Python·JS·Java 오프라인 CI를 이용해 검증.
- **실제 문제**: 기존 `bot_team_r16.py` ResearchBot이 사용자 제공 링크를 단지 `startswith('https://github.com/')`로 판정. URL의 host/username/query/fragment/경로 인코딩/역슬래시·제어문자 등을 정규화·재파싱하지 않고 참고 링크로 반영할 수 있는 *메타데이터 신뢰도 결함*. 이 코드는 네트워크 요청은 하지 않으므로 SSRF 실제 발생 증거는 아님.
- **실제 최소 수정**: Python 표준 `re`의 정확한 GitHub owner/repo ASCII URL 허용식 + `urllib.parse.urlsplit`의 host/scheme/username/path 확인, `..`/빈 경로·percent 인코딩·역슬래시·control/query/fragment/port/userinfo 거부. 참고 URL 중복 제거와 참고 제목의 줄바꿈/탭 등 control 문자 및 양끝 공백 차단. 자료의 **외부 진위는 여전히 검증하지 않았다고 명시** (`source_authenticity=NOT_VERIFIED_BY_OFFLINE_BOT`).
- **소스 증거**: 오직 격리 브랜치 `ai/r16-evidence-reconciler-2026-10-22`의 `experiments/r16-evidence-reconciler/bot_team_r16.py` 수정 커밋 **`521be931069d507d46db1ad13928dc054aeff7ab`**, GitHub blob **`de90d1460fc60c9e86d1852e8483802ed544f2b5`**. 추가 `tests/test_bot_source_url_policy.py` 5개 unittest 커밋 **`8a45be4e307eab0c5b0f6f20514a89b1023521bb`**, blob **`ac4571e96b9f30c70423987fbd84c6c50640624e`**. 테스트는 정상 GitHub/README 링크와 악성 host/항목 인코딩·path traversal·title injection·중복까지 다룸.
- **공식 GitHub 원격 증거**: [Actions run **`39909757804`**](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39909757804), head SHA **`8a45be4e307eab0c5b0f6f20514a89b1023521bb`**, Check/job **`120269756801`**, `push completed/success`. 독립 재조회한 실제 작업 로그: **Python 68/68 OK** (기존 63개 + 신규 5개), Python 추가 다국어 2/2, JS 20/20, Java 공통 20/20, 별도 Java oracle 12/12, runner warning 0. 이전에 변경 없는 성공 테스트를 수동 재실행하지 않았으며 새 코드/테스트 push 트리거에 따른 실행임.
- **명확한 경계**: 3봇은 무료 Python 결정론적 역할 검사로, 별도 외부 유료 LLM/Claude/Gemini 서버 및 일반 ChatGPT 대화 자동 감시가 아니다. CI 성공은 소스와 입력 검증기만 증명. **정규 ChatGPT 예약 무인 GitHub·Slack 기억 복원 성공은 공식 native per-run ID·같은 회차 앱 tool-call 원본이 미제공이므로 계속 미검증**.
- 기존 AI 매시간 정각 예약·알림/프롬프트·운영 Activepieces·GitHub main·비밀정보·결제는 변경하지 않음. 다음 목표: 권한 있는 공식 Scheduled → AI → Previous runs 기록이 제공되면 원시 회차 증거를 엄격히 교차 검증.



## 2026-10-23 14시대 — 외부 오픈소스 AI Bot 역할 연구 + 무료 3봇 실제 오프라인 연결
- **ResearchBot 조사**: Microsoft [Agent Framework](https://github.com/microsoft/agent-framework) (MIT, Python/.NET, sequential/concurrent/handoff orchestration) 및 [CrewAI](https://github.com/crewAIInc/crewAI) (MIT, Python agents/crews/flows)를 공식 upstream에서 참고. Microsoft [AutoGen](https://github.com/microsoft/autogen)은 **유지보수 모드**여서 새 기반으로 설치하지 않음. [Hypothesis](https://github.com/HypothesisWorks/hypothesis) (MPL-2.0), [fast-check](https://github.com/dubzzz/fast-check) (MIT)의 속성 기반 테스트 아이디어 검토했으나 무승인 dependency 설치·유료 모델/API 호출 없이 기존 `unittest`/Java/JS 표준 환경 유지.
- **BuilderBot 실제 수정**: 기존 `ai/bot-team-sandbox-2026-10-22`의 `experiments/ai-bot-team/bot_team.py` 및 `chat_router.py`를 읽고 본래 **오프라인 데모로써 실제 코딩·연결을 자동 수행하지 않는다는 한계** 확인. 현행 격리 R16에 `experiments/r16-evidence-reconciler/bot_team_r16.py`를 새로 작성. 세 역할 `ResearchBot`(제공된 참조 URL만 메타검사), `BuilderBot`(실제 audit 결과에 따른 읽기 전용 다음 행동 1개 선택), `VerifierBot`(실제 `audit_v2.check` 원본 형식·보호 정책 fail-closed). 64KB 입력 제한, 최대 참고 20개, 가짜 공식 성공 플래그 무시, 격리만 허용, CLI `exit 2`로 미검증을 성공 종료값으로 포장 금지. **외부 LLM 3개 또는 ChatGPT 전체 채팅의 실시간 자동 후킹이 아니고 무료 로컬 Python 코드**.
- **실제 소스/테스트 커밋**: bot `85ccb1aef39b11e0efb2085cdda22668f7fa8942` (blob `8e2fb8aecddda9997e3e0dae55e3905ac7a76af2`), `tests/test_bot_team_r16.py` 9개 회귀 `e9b64923695e0f1d6320b8d4a165a4962cfb7b2c` (blob `b6ff4d81e393d5535c98fd8cf88be76fca8f7cfe`), 격리 `.github/workflows/r16-evidence-verifier.yml`에 봇 코드 경로 트리거 추가 commit `06e382630928f3fcd583b8fedbec204e435fbb8a` (blob `2e58b16236999fc9beff33c876230a0a1dee2e3f`). GitHub 원격 독립 재조회에서 세 blob SHA 정확 일치.
- **VerifierBot 공식 원본 실행**: GitHub [Actions run `39905219028`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39905219028), head `06e382630928f3fcd583b8fedbec204e435fbb8a`, Check/job `120255511427`, `push completed/success`. 원본 job logs **Python 전체 63/63 PASS** (신규 봇 9개 포함), 다국어 Python 2/2, JS 공통 20/20, Java 공통 20/20, Java oracle 12/12, Actions warnings 0. GitHub 이전 cancel 회차 `39905165919`는 성공으로 세지 않음.
- **실제 능력의 한계**: 이 AI Bot 코드는 검증기 API를 호출하고 역할 간 상태 전달·정책 선택·독립 진위 부정 판정을 **실제로 실행**한다. 그러나 제공된 GitHub/Slack 문서·run 메타의 **외부 기원 인증**이나 ChatGPT 공식 Scheduled native per-run 실행 이력 접근 권한은 만들지 않는다. `official_success_verified=false` 항상 유지. 수동/CI 코드 통과와 **예약 AI 무인 GitHub·Slack 기억 복원 성공**은 별개로 **미검증**.
- **보호·다음 최우선**: 기존 매시간 정각 단일 ChatGPT 예약·프롬프트·알림, 운영 Activepieces, GitHub `main`, 비밀키·유료 호출 **변경 없음**. 공식 Scheduled → AI → Previous runs 원본이 인증된 읽기 권한으로 제공되면 그때 동일 실행 ID/원시 GitHub·Slack 호출을 독립 대조; 현재는 추정 ID·우회 API 사용 금지.



## 2026-10-23 — 다국어 UTC 오프셋 해석 불일치 수정 (JSON Schema Test Suite·Java 표준 라이브러리·SLSA 참고)
- **다른 사람 공개 구현 재검토**: [JSON Schema Test Suite](https://github.com/json-schema-org/JSON-Schema-Test-Suite) MIT의 여러 구현 공통 fixture 방식을 적용하고, Java `java.time.OffsetDateTime`이 `±18:00`을 초과하는 offset을 거부한다는 점을 독립 검사로 확인. [SLSA provenance](https://github.com/slsa-framework/slsa/blob/main/spec/build-provenance.md)의 실행 출처/빌더 정체성 분리 원칙도 검토. 타인 코드는 복사/설치하지 않았음.
- **원인 실제 재현**: Python `datetime.fromisoformat('2026-10-23T11:00:00+19:00')`은 +19시간을 파싱하지만 Java 21 `OffsetDateTime.parse`는 +19:00 및 +23:59를 거부. 기존 mock JS 구현은 offsetHour >23에서만 거부 → **같은 증거의 언어별 형식 판정 불일치**. RFC 3339가 금지한다고 주장하지 않으며, R16 내부 정책으로 `±18:00` 이하의 정합성 범위를 채택.
- **수정**: 격리 Python `audit_v2.py`의 `parsed_time()`에 `hour>18 || (hour==18 && minute>0)` 거부 추가(커밋 `d8ad3c4a66b8f2d05d9fdb76a41d266ecde4ba30`; blob `831de11d0a132392ea74476fa26288b29b5c020c`). 격리 JS `activepieces_mock_guard_2026-10-23.js`에도 같은 제한 추가(커밋 **`d3c8eb284656b789d7ab8695de08c2bba71d9d12`**, blob **`b0185fc20a939e468065e96ccea8ebf04247313b`**). Java 21은 기존 독립 표준 라이브러리 구현 유지.
- **실제 공통 fixture 확대**: `fixtures/time_cases.tsv` 기존 15건 → **20건** (`±19:00` 거부, `+18:01` 거부, `±18:00` 허용), blob `761dd2eda56980644703fe3a0dd4d2cfe4a789c6`. 기존 원본 Python·JS·Java 3개 구현에서 공통 판정 일치.
- **공식 GitHub CI 원본**: [run `39896738983`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39896738983), head SHA **`d3c8eb284656b789d7ab8695de08c2bba71d9d12`**, job `120228819827`, `completed/success`; 원시 runner log 직접 조회: Python 전체 **44/44 OK**, 추가 Python 다국어 **2/2 OK**, JavaScript 공통 **20/20 PASS**, Java 공통 **20/20 PASS**, 독립 Java oracle **12/12 PASS**, Actions warning **0**. 중간 두 커밋의 실패는 테스트/코드 동시 반영 이전의 예상 거부 불일치였으며 최종 커밋에서는 해결. 이미 통과한 같은 코드의 수동 중복 실행 불필요.
- **비활성 격리 Activepieces 적용·독립 재조회**: flow `zgSopq6Txh68wxsDc5K5Z`의 **MOCK ONLY `step_1`**에만 GitHub JS blob 본문 적용. `ap_read_step_code`와 GitHub 최신 소스 **문자열 정확히 일치**, `ap_validate_flow` **2/2 valid**, flow `DISABLED`, `published=false`. 실제 TESTING 모의 실행 `a6Wc8LQeKMK055sOX9Fqu` (+19:00→거부), `dl9wBmcdZt7ZnsSmJWRmr` (+18:00→형식 일치), **2/2 예상 결과 일치**; 양쪽 모두 `official_success_verified=false`, `external_calls=0`, 실예약이 아닌 가상 run ID.
- **변경 범위·미완료**: 기존 유일 ChatGPT 매시간 예약/일정/알림, 운영 Activepieces, GitHub `main`, 유료 모델 API **변경 없음**. CI가 검증한 것은 격리 코드/모의 입력 형식만이며 **ChatGPT 정규 예약의 공식 per-run ID와 같은 회차 GitHub·Slack 원본 호출 미제공 → 무인 성공 계속 미검증**. GitHub Actions 성공을 ChatGPT 예약 성공으로 전용하지 않음.
- **다음 최우선 목표**: 플랫폼이 인증된 예약 개별 실행 원본을 제공할 때만 동일 회차/원시 GitHub·Slack tool-call 교차 대조. SLSA의 빌더/출처 원칙처럼 스스로 만든 synthetic 로그를 진짜 예약 원본으로 간주하지 않는다.



## 2026-10-23 — 오픈소스 참조 Python·JS·Java 삼중 독립 검증 및 CI 실제 완료
- **외부 공개 구현 조사**: [Temporal Workflow ID vs Run ID](https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/workflow/workflow-execution/workflowid-runid.mdx) (공식 실행/회차 ID 구분, SDK Java Apache-2.0), [OpenTelemetry GenAI tool spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md) (호출 시각·도구 span, 핵심 Semantic Conventions Apache-2.0), [JSON Schema validators](https://json-schema.org/tools) (여러 언어의 공통 입력 검증, Python jsonschema MIT / JS Ajv MIT / Java networknt Apache-2.0), [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) (thread checkpoint와 long-term store 분리, MIT). **이 코드를 직접 복제하지 않고 설계·경계조건만 참고**. 현행 R16 검증에 LangGraph·Temporal 서버/클라이언트·서드파티 JSON Schema 패키지를 설치하지 않았으며 외부 유료 API/보안키 없음.
- **실제 최소 적용**: 기존 격리 `audit_v2.py` 및 `activepieces_mock_guard_2026-10-23.js`를 유지하면서, 같은 timestamp 조건 15개로 세 언어를 교차 검증. 파일 `fixtures/time_cases.tsv`, `tests/test_polyglot_fixtures.py`(Python 기존 `check()`를 직접 호출), `polyglot/check_js.mjs`(기존 GitHub mock CODE `code()`를 직접 호출), `polyglot/R16TimeOrderCheck.java`(JDK java.time의 독립 nanos 날짜·시간대 계산). 별도 병렬 추가된 `polyglot/R16TimeOracle.java` + `polyglot/time_vectors.tsv` 12건도 중복 파일 덮어쓰기 없이 **CI 두 번째 Java 기준 검사에 포함**.
- **검사 경계 15개**: 정상·9자리 ns·종료 전/후 ns·역전 시각·UTC/KST 동등·윤년/존재하지 않는 날짜·타임존 부재/불가능한 오프셋·정각 소수부·소수점 10자리·1시간 종료 경계. 모든 synthetic payload의 `official_success_verified=false`, JS `external_calls=0`; 형식 판정은 공식 ChatGPT 예약 성공 인증이 아님.
- **GitHub Actions 본문 실제 확대**: 기존 격리 `.github/workflows/r16-evidence-verifier.yml`의 기존 Python 테스트에 JS Node/Java JDK 표준 라이브러리 단계 추가. 특정 격리 브랜치 + 변경 경로에만 자동 트리거, `permissions:contents:read`, `persist-credentials:false`, 운영 main·기존 예약·Activepieces 운영 무수정.
- **최종 원본 GitHub Actions run** [`39894040301`](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39894040301), head commit **`446d2b277c8ee67a833b0b3fe7021ac33ed707e7`**, job **`120220187407`**, 공식 `completed/success`. job log 원본 독립 조회: Python **44/44 OK**, JS **15/15 PASS**, Java **15/15 PASS**, 두 번째 독립 Java oracle **12/12 PASS**, Actions 경고 0. 이는 별개의 동일 입력 **교차 검사**로, 44+15+15+12개 독립 기능이라는 의미는 아님.
- **경쟁 커밋 안전 대조**: 테스트 중 GitHub 브랜치에 별도 Java oracle/TSV 두 파일을 더한 변경이 나타났고, 기존 격리 워크플로 `cancel-in-progress:true`에 따라 한 회차 `39893876739`는 `cancelled`. 그 이후 공식 성공 회차 `39893926102`(Python 44/44 JS 15/15 Java 15/15) 및 최종 `39894040301`을 실제 원본으로 확인했음. 취소 회차를 성공으로 둔갑시키지 않음.
- **Activepieces 읽기 전용 대조**: 기존 격리 mock flow `zgSopq6Txh68wxsDc5K5Z`는 `DISABLED`/`published=false`. 현재 GitHub JS SHA `b378e7640a03b60ea86400e7d4c47602b27386fe`와 Activepieces `ap_read_step_code`는 **마지막 공백 줄바꿈 하나만 다른 동일 로직**, `trimEnd()` 비교 완전 일치. 격리 flow조차 무의미한 공백 수정을 피했고 운영에 변경 없음.
- **남은 최우선**: ChatGPT **정규 매시간 예약 자체의 공식 native per-run ID + 같은 회차 원본 GitHub·Slack tool calls**는 계속 미제공. `automations.peek.last_run_time=2026-10-23T03:04:51.184022Z` (=12:04:51 KST)은 시각 메타만 뜻함. **무인 예약 성공 미검증**. GitHub 원격 CI 성공과 절대 혼동하지 않는다.



## 2026-10-23 — R16 격리 브랜치 원격 CI 43/43 실제 성공 (ChatGPT 무인 예약과 분리)
- **원인 독립 대조**: `.github/workflows/validate.yml`은 `push: branches:[main]`, `pull_request: branches:[main]` 전용이고, 기존 `ai-memory-bridge.yml`은 기억 브랜치의 특정 파일 경로 변경에만 반응한다. R16 격리 브랜치에는 기존 CI 트리거가 없어 해당 코드 커밋의 Actions runs/check runs가 0이었던 것. 저장소 전체 Actions 실행 94건, main 브랜치 37건으로 저장소 GitHub Actions 기능은 작동 중. 기존 validate는 루트 `tests/`만 검사하므로 격리 `experiments/r16-evidence-reconciler/tests/`를 별도로 대상으로 삼아야 한다.
- **정확한 해결**: **격리 브랜치에만** 새 `.github/workflows/r16-evidence-verifier.yml` 파일 생성. `push` 이벤트의 branch는 정확히 `ai/r16-evidence-reconciler-2026-10-22`로 제한하고, 수정 경로도 워크플로 파일·`audit_v2.py`·격리 `tests/**`로만 제한. 루트 `main` 워크플로·운영 자동화·정규 ChatGPT 예약·Activepieces 운영은 수정하지 않았다. GitHub 토큰 `contents: read`만 허용, `ubuntu-latest`, Python 3.12 표준 라이브러리, 외부 AI API/웹훅/유료 모델 호출/아티팩트 저장 0.
- **공식 GitHub 출처 확인**: 저장소 `visibility=public`; [GitHub 표준 runner 공용 저장소 과금 규칙](https://docs.github.com/en/billing/concepts/product-billing/github-actions)은 무료, [브랜치·파일 경로 필터](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)는 AND 조건. 대형 runner 등 유료 리소스 없음.
- **첫 GitHub 실실행**: 신규 workflow commit `5a851d978aa229787bfbead88b3359df2f6f30aa`, workflow blob `ffaf8063a1bdf3cc51c472a8e41c4edfa7f5a1aa` → 공식 Actions run **`39891401115`**, Check/job **`120211760208`**, `push`, `completed/success`, 원본 runner 로그 **`Ran 43 tests in 0.122s`**, `OK`. [첫 실행](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39891401115). 기존 Node20 action 경고 발견.
- **경고 최소 수정/독립 재검증**: 같은 workflow의 `actions/checkout@v4`→`@v7`, `actions/setup-python@v5`→`@v7`, 인증자료 지속 저장 비활성 `persist-credentials: false` (오직 격리 workflow). 최신 소스 commit `9cdaffad73b083a00d577e8771e154a66f1af58e`, workflow blob **`dd9d1f192e65bc868552462d10384a114473e203`**. 새 공식 Actions run **`39891502065`**, job/check **`120212092643`**, `push`, `completed/success`, 공식 원본 GitHub job logs **`Ran 43 tests in 0.094s`**, `OK`, Node.js20 사용 중단 경고 **0건**. [최종 통과](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39891502065).
- **증거 구분**: 이것은 GitHub 격리 코드의 자동 CI 성공이 **실제 검증된 것**이며, GitHub 공식 run ID·head SHA·Check ID·job logs 원본이 존재한다. 하지만 ChatGPT 정규 예약 AI의 native per-run ID/동일 회차 GitHub·Slack 호출 원본은 여전히 도구에 미제공 → **정규 예약 무인 성공 미검증**. GitHub Actions ID를 ChatGPT 공식 예약 ID로 오인하지 않는다.
- **다음 목표**: 새 코드/테스트 변경 시에만 CI가 다시 도는 경로 유지. GitHub 기본 브랜치 및 운영·예약 보호, 이미 통과한 수동 테스트 재실행 금지. 공식 ChatGPT Scheduled → AI → Previous runs에서 개별 회차 로그가 접근 가능해질 때 동일 회차 원시 증거만 검증.


 
## 2026-10-23 — GitHub CI 빈 조회 결과의 범위 확인 (읽기 전용 원인 분석)
- **기존 반복된 오해 교정**: `mcp__GitHub__fetch_commit_workflow_runs` 커넥터는 **pull_request로 트리거된 첫 페이지의 실행만** 반환한다. `workflow_runs=[]`는 `push`, 수동 실행 등 다른 이벤트에 대해 확인한 결과가 아님.
- `mcp__GitHub__get_commit_combined_status`의 `statuses=[]`는 GitHub [Commit Statuses REST API](https://docs.github.com/en/rest/commits/statuses)의 커밋 상태 목록이다. GitHub Actions의 **Check runs/check suites**와 같은 API가 아니므로, 체크 미실행·실패·성공을 증명하지 못함.
- 실제 테스트 커밋 `5c92a3f73d252871dcb51274a1f95f4242cbdd00`에 대한 두 커넥터 조회는 모두 빈 목록. 기본 브랜치 Github 코드 검색에서도 `runs-on` 및 `workflow_dispatch`에 해당하는 파일 결과를 찾지 못했으나 검색 누락 가능성이 있어 **워크플로 자체가 없다고 단정하지 않음**.
- 정확한 결론: **로컬 Python 회귀 43/43 PASS는 증거로 완료**, **GitHub 원격 전체 CI(모든 이벤트 유형 및 Checks)는 조회 범위 미충족으로 미검증**. 사용자 결제/Actions 실행 요구 없이 임의의 원격 워크플로를 만들어 비용·운영에 영향을 주지 않음.
- **정규 ChatGPT 예약 11:00 회차**: `automations.peek`의 기존 단일 R16 예약 `is_enabled=true`, `paused_count=0`, `last_run_time=2026-10-23T02:06:18.531665Z` (=11:06:18 KST). 시각 메타만 확인; 공식 개별 per-run ID 및 동일 회차 도구 호출 원본은 미제공이므로 **무인 성공 미검증**. Activepieces 2026-10-23 감사 테이블 `count=0`이며 해당 테이블이 모든 실행을 포괄한다고 보장할 수 없음.
- 다음 작업은 실제 지원되는 GitHub **all-events workflow runs + Checks** 및 ChatGPT **Scheduled Previous runs** 접근이 생겼을 때 그 공식 ID로 재검증. 접근 권한 제한을 우회하지 않고, 기존 예약·main·운영 Activepieces·알림은 변경하지 않음.


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


## 2026-10-23 12:20 KST — 15건·12건 이중 교차검증 보존, Node 24 호환 수정 후 원격 CI 성공
- 사용자 `다른 사람이 만든 것 찾아서 파이썬, 자바 등등 동원` 요청에 따라 **공개 레퍼런스 구현의 설계만 참고**, 기존 소스 직접 복제나 외부 모델 API 호출 없이 **기존 R16 격리 브랜치 전용** CI에 Python 3.12, Node 24 `node:test`, OpenJDK 21 `java.time`을 사용한 독립 검사 추가. 참고: [OpenTelemetry execute_tool spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md), [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [actions/setup-node](https://github.com/actions/setup-node), [actions/setup-java](https://github.com/actions/setup-java). 모듈들은 모두 표준 기능, `npm install`, `pip install`, `mvn` 불필요.
- 본 작업이 시작되기 전부터 병렬로 생성된 **15개 공통 시각 사례** `fixtures/time_cases.tsv` + Python `tests/test_polyglot_fixtures.py` + JS `polyglot/check_js.mjs` + Java `polyglot/R16TimeOrderCheck.java`의 기존 검사 체계를 보존. 새로 작성한 **12개 타임존·윤년·나노초 경계 사례** `polyglot/time_vectors.tsv` + Python `polyglot/test_polyglot_vectors.py` + Node `polyglot/test_activepieces_guard.mjs` (실제 원본 JS `code()` import) + JDK `polyglot/R16TimeOracle.java`를 추가함. **15+12는 중복된 유형이 있을 수 있어 독립적으로 새로운 버그 27개를 의미하지 않음**.
- **통합 CI 첫 장애 직접 재현**: 기존 검증 체계의 `node --experimental-default-type=module` 옵션을 Node 24에 그대로 넘겨서 remote run **`39894369222` / `failed` / exit 9 `node: bad option`**. 격리 워크플로에서 **옵션만 삭제**하여 `node polyglot/check_js.mjs fixtures/time_cases.tsv`로 최소 수정. 새 버전은 파일 자체가 `.mjs`이며 Node 24가 정상 ESM 처리함. 운영/예약/기타 워크플로우 변경 없음.
- **실제 GitHub Actions 재검증 완료**: 격리 workflow commit **`aca1087776b154f5febdfe94a2df6a45689121ff`**, run **`39894432542`**, job/check **`120221459588`**, event `push`, `completed/success`와 exact head SHA·Checks 독립 확인. 직접 조회한 **job 원시 로그**: Python 기본 **44/44 OK** (기존 43 + 15-vector 테스트 1), Python 추가 **2/2 OK** (12-vector 1 + 테이블 완전성 1), 원본 JS `node:test` **12/12 PASS** + 기존 JS `check_js.mjs` **15/15 PASS**, Java `R16TimeOracle` **12/12 PASS** + 기존 `R16TimeOrderCheck` **15/15 PASS**. GitHub URL: https://github.com/watersun79-source/ai-token-optimization/actions/runs/39894432542.
- **보안·과금**: branch 정확히 R16 격리만, workflow token `contents: read`, `persist-credentials:false`, Ubuntu 공개 저장소 일반 runner. [GitHub 공식 문서](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) 기준 공개 저장소 표준 runner 사용 무료. 별도 SaaS·모델 API 호출, 비밀키/연결 사용, 예약 중단/중복 생성, 운영 플로우와 main 변경 없음.
- **검증 한계**: 위 Python 46건은 실제 함수 검사 수이고 12/15개는 Python의 `subTest` 등 하나의 테스트 메서드 안에서 평가함. JS/Java 각 12+15건은 **형식 판정/경계 회귀 성공**이다. GitHub Actions run ID는 ChatGPT Scheduled **공식 정규 회차 ID가 아님**. 현재 정규 무인 GitHub·Slack 실행 원시 호출 기록 미제공 → `official_success_verified=false` 정책 유지.
