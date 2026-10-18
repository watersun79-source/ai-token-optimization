# AI 실행 기록 — 2026-10-18 후속 점검

- 시각: 2026-10-18 KST
- 상태: 부분 완료
- 기준: `ai/continuation-readonly-audit-2026-10-18`

## 확인
- GitHub의 운영 프로토콜, 인덱스, 진행 기록, 직전 실행 보고서를 다시 읽음.
- Slack 채널 `C0C9649RQAZ`의 최근 메시지를 다시 읽음.
- 직전 보고서와 인덱스가 현재 브랜치에서 조회됨.
- 브라우저 탭 조회는 originating browser context 오류로 실패함. Gemini/Claude 웹앱의 실제 응답은 확보하지 못함.
- Activepieces 프로젝트 컨텍스트 도구 `ap_set_project_context`가 현재 도구 목록에 없어, 추가 프로젝트 작업은 보류함.

## 비용 및 변경
- 생성 API 호출: 0회
- 유료 API 호출: 0회
- 구매/업그레이드: 0건
- 운영 플로우/예약/main/비밀값 변경: 0건

## 다음 목표
1. 연결된 브라우저 컨텍스트를 복구한 뒤 Gemini와 Claude 무료 웹앱 응답을 실제 확인한다.
2. Activepieces 프로젝트 컨텍스트 도구가 사용 가능해지면 읽기 전용으로 이전 Flow ID 불일치를 조사한다.
3. GitHub와 Slack에 기록한 뒤 양쪽에서 재조회 검증한다.

## 추가 진단 — 2026-10-18
- 프로토콜, 인덱스, 정본 맞춤 지침(1053자), 실행 보고서 `ai-execution-2026-10-18-0624.md`를 별도 작업 브랜치에서 다시 읽음.
- GitHub 프로필은 저장소 소유자 `watersun79-source`와 일치하고 저장소 메타데이터는 `admin=true`, `push=true`를 표시함. 다만 이 메타데이터만으로 연결 도구의 모든 쓰기 경로가 작동한다고 보장할 수 없음.
- 저장소 rulesets 조회 결과는 빈 배열. `main` branch protection 조회는 HTTP 403 `Resource not accessible by integration`; 따라서 branch protection 설정 유무는 미확인.
- 새 보고서 생성 시도는 HTTP 422 `"sha" wasn't supplied`로 실패. 후속 조회에서 대상 파일이 이미 작업 브랜치에 존재함을 확인함. 이 경로는 새 파일 생성이 아니라 기존 파일 갱신으로 처리해야 함.
- ChatGPT 맞춤 지침 설정 자체는 이 연결에서 직접 확인할 수 없음. GitHub에 파일이 있다는 사실은 ChatGPT 설정에 적용됐다는 뜻이 아님.
- Slack 추가 분석 보고서를 게시한 뒤 최근 메시지를 다시 읽어 게시를 확인함: https://chatgpt-mor9047.slack.com/archives/C0C9649RQAZ/p1792273385609079
- 이번 추가 점검에서 Gemini/Claude 생성 API 0회, 유료 API 0회. 운영 플로우, 기존 정각 예약, `main` 변경 0건. 비밀값을 읽거나 기록하지 않음.

## 저장 검증 결과 및 다음 목표
- 기존 파일을 정상 갱신함. GitHub 응답 커밋 SHA: `33ceb40efe387f79d302ad44f2a442c2db8b5581`.
- 같은 작업 브랜치에서 파일을 다시 읽어 추가 진단 내용과 HTTP 422/403 기록을 확인함. 조회된 blob SHA: `84ccde154073406643e053d1b6ca7a50b8ecb083`.
- 새 파일 생성 API는 대상 파일이 이미 존재해 `sha` 누락 422를 반환했으며, 기존 파일 갱신 API와 현재 blob SHA를 사용해 정상 경로로 해결함. 안전 검사 우회는 하지 않음.

1. 다음 회차에서 GitHub 쓰기/재조회 검증이 계속 정상인지 확인한다.
2. 연결 브라우저 컨텍스트가 복구될 때 Gemini와 Claude 무료 웹앱 응답을 실제 확인한다.
3. Activepieces 프로젝트 컨텍스트 도구가 제공되면 읽기 전용으로 과거 플로우 ID 불일치를 조사한다.


## 실행 기록 — 2026-10-18 추가 실행
- 작업 브랜치에서 프로젝트 인덱스와 직전 실행 보고서를 다시 읽음.
- Slack `#일반` 최근 메시지를 읽어 직전 보고가 남아 있음을 확인함.
- Activepieces 읽기 전용 목록 응답에는 총 7개 플로우가 표시됨: 3개 ENABLED/published, 4개 DISABLED/draft. 과거 기록의 5개와 차이가 계속되므로 원인 미해결. 이 실행에서는 플로우를 변경하거나 테스트 실행하지 않음.
- Gemini/Claude 소비자 웹앱의 실제 응답은 확보하지 못함. 브라우저 연결 컨텍스트가 필요함.
- 생성 API 호출 0회, 유료 API 호출 0회, 구매/업그레이드 0건.
- `main`, 운영 플로우, 기존 정각 예약, 연결·비밀값 변경 0건.
- Activepieces 프로젝트 컨텍스트 도구 `ap_set_project_context`가 현재 사용 가능한 도구 목록에서 확인되지 않아, 추가 프로젝트 변경은 보류함.
- 다음 목표: (1) Activepieces 프로젝트 컨텍스트를 올바르게 선택할 수 있는 도구를 복구/확인한 뒤 읽기 전용으로 플로우 ID 차이를 조사, (2) 연결 브라우저 컨텍스트에서 Gemini·Claude 무료 웹앱 응답을 실제 확인, (3) 매번 GitHub 저장 후 재조회와 Slack 게시 후 재조회를 계속 검증.


## 실행 기록 — 2026-10-18 기억 유지 후속 조사
- 작업 시작 시 프로토콜, 프로젝트 인덱스, 최신 실행 보고서, Slack 최근 메시지를 직접 재조회함.
- Activepieces 읽기 전용 실행 이력 조사:
  - Production 최근 10개 실행은 전부 SUCCEEDED였으나, 모두 flow ID `drNhxMhmCo3A0rKV0OhIZ`에 해당하며 최신 기록 시각은 2026-10-15 UTC. 이는 해당 플로우의 과거 실행 성공을 보여줄 뿐, 현재 Gemini/Claude 모델 응답이나 오늘의 자동화 실행 성공을 입증하지 않음.
  - `AI 3AI 협업`(`kt2N9yCVA3dLkFiNPSMsH`) 및 `Slack`(`vtRwEYmcwDTunBZut265G`)에 대해 조회한 Production 실행 기록은 0건.
  - Testing 최근 10개 기록은 조회됐고 모두 SUCCEEDED. 이는 별도 테스트 플로우의 테스트 실행이며 운영 실행과 구분함.
- GitHub 저장소 코드 검색에서 과거 기록의 Flow ID `hgPVOZQYdFTezhoZ6wj5j`, `yRqt1nbG4ZqiIkDX72vhN`, `1MAbLTS7HS9LjDRqq9l4b`는 검색 결과 0건. 검색은 현재 기본 브랜치 범위이므로 모든 브랜치/삭제 기록에 존재하지 않는다고 단정할 수 없음.
- Activepieces 프로젝트 컨텍스트 선택 도구는 현재 도구 목록에서 확인되지 않음. 플로우 수정·활성화·비활성화·실행은 하지 않음.
- Gemini/Claude 무료 웹앱의 실제 응답은 브라우저 연결 컨텍스트가 없어 이번에도 확보하지 못함.
- 비용: 생성 API 0회, 유료 API 0회, 구매/업그레이드 0건.
- 보호 상태: `main`, 기존 운영 플로우, 매시간 정각 자동화, 연결 및 비밀값 변경 0건.
- 다음 목표: Activepieces 프로젝트 컨텍스트 접근 경로를 확인한 후 현재 프로젝트와 과거 Flow ID 기록을 읽기 전용으로 대조한다. 이어서 브라우저 컨텍스트가 사용 가능해지면 Gemini와 Claude 소비자용 무료 웹앱의 실제 독립 응답을 확인한다.


## 실행 기록 — 2026-10-18 운영 플로우 읽기 전용 점검
- 맞춤형 지침의 최신 미완료 목표를 이어서 Activepieces 현재 프로젝트의 플로우·연결·테이블·구조·유효성 검사를 읽기 전용으로 수행함.
- 현재 목록: 7개 플로우(3 ENABLED/published, 4 DISABLED/draft). 3개 활성 플로우의 구조 및 유효성 검사:
  - `AI 3AI 협업` (`kt2N9yCVA3dLkFiNPSMsH`): 7/7 단계 유효. 현재 구조는 ChatGPT 초안 → Gemini 검토 → Claude 검토 → 최종 통합의 순차 체인으로, 병렬 실행이 아님. 이 구조가 실제 병렬 실행을 보장한다고 주장하지 않음.
  - `Slack` (`vtRwEYmcwDTunBZut265G`): 2/2 단계 유효.
  - `Gemini + Claude 협업 비서 (비용 확인 필요)` (`drNhxMhmCo3A0rKV0OhIZ`): 5단계 중 4개 유효, OpenAI 초안 단계 1개는 의도적으로 skipped 상태. 이 검사만으로 실제 무료 사용이나 현재 모델 응답은 입증되지 않음.
- 연결 목록에는 OpenAI, Google Gemini 2개 연결, Slack, Anthropic Claude가 ACTIVE로 표시됨. ACTIVE 상태는 인증이 현재 유효하거나 호출이 무료임을 증명하지 않음.
- Activepieces Tables의 검색 인덱스와 임시 레지스트리 테이블은 0행, MOCK ONLY 병렬 결과 테이블은 14행. 임시 테이블은 변경하지 않음.
- Production 실행 기록은 최근에 확인된 10건이 2026-10-15의 Gemini+Claude 협업 플로우 실행이며 SUCCEEDED. AI 3AI 협업과 Slack 플로우는 조회 범위에서 실행 기록 0건. 오늘 정상 실행 여부는 미확인.
- 과거 Flow ID 차이의 근본 원인은 아직 미해결. 현재 프로젝트 컨텍스트 전환 도구는 제공되지 않아 다른 프로젝트/브랜치에 접근했다고 주장하지 않음.
- 운영 플로우 실행·수정·게시·비활성화 0건. 기존 매시간 정각 자동화, main, 연결 및 설정 변경 0건. Gemini/Claude 생성 호출 0회, 유료 API 호출 0회, 구매/업그레이드 0건.
- 다음 목표: 별도 비운영 초안에서만 순차/병렬 동작을 mock 데이터로 검증할 계획을 세우고, 프로젝트 컨텍스트 접근 경로가 확인되면 과거 ID 불일치를 읽기 전용으로 대조한다. Gemini/Claude 실제 무료 웹앱 응답은 브라우저 연결 복구 후 별도 확인한다.


## 실행 기록 — 2026-10-18 비운영 모의 병렬/합류 테스트
- 작업 시작 시 운영 프로토콜, 프로젝트 인덱스, 최신 실행 보고서, Slack 최근 메시지를 재조회함.
- 읽기 전용으로 비활성 초안 2개를 구조 및 유효성 검사함: `MOCK ONLY · Promise.all 병렬 합류 검증기` (2/2 valid), `MOCK ONLY · Result Merge Harness` (2/2 valid). 둘 다 비활성/미게시 상태 유지.
- `Promise.all` 모의 테스트는 Activepieces TESTING 환경에서 제공된 합성 트리거 데이터로 실행됨. Run ID `FLDVVVr82EVgZEPVOCO2S`, SUCCEEDED. 분기 시작 이벤트가 0ms에서 함께 기록되고 양쪽 완료 이벤트가 약 1201ms에 기록되어 코드 내부 겹침 검사가 통과함. 합류 상태 시나리오 10/10, 결과 계약 검사 8/8 통과. 반환값은 SYNTHETIC_MOCK_ONLY, 외부 AI 호출 0, 외부 네트워크 호출 0.
- 모의 결과 합류 테스트는 합성 Gemini/Claude 계약 데이터를 사용함. Run ID `vVP3Qjubr94kVYf42rJ6V`, SUCCEEDED. 두 결과 모두 `MOCK_MERGE_OK`로 합쳐졌고 계약 시나리오 8/8 통과. 외부 AI 호출 0, 외부 네트워크 호출 0.
- 한계: 첫 테스트는 CODE 단계 안의 JavaScript `Promise.all` 동시성만 검증함. Activepieces 엔진 수준의 두 AI 액션 병렬 실행, 실제 Gemini/Claude 응답, 무료 사용 가능성, 운영 트리거에서의 동작은 증명하지 않음. 두 테스트 모두 합성 데이터만 사용했으며 운영 플로우를 실행하거나 게시하지 않음.
- 비용/변경: 생성 API 0회, 유료 API 0회, 구매/업그레이드 0건. `main`, 운영 플로우, 기존 정각 자동화, 연결 및 비밀값 변경 0건.
- 다음 목표: mock 초안의 테스트 입력/출력 계약을 계속 확인하고, Activepieces의 실제 분기 실행 기능이 운영을 건드리지 않는 별도 비운영 구조로 검증 가능한지 조사한다. Gemini/Claude 실제 무료 웹앱 응답과 과거 Flow ID 불일치는 여전히 미해결.


## 공식 문서 조사 — 병렬 분기 구현 방식
- Activepieces 공식 AI Router 문서(https://www.activepieces.com/docs/flows/ai-router)는 기본 설정에서 정확히 한 경로만 실행하고, `Match = Every route that applies`일 때만 여러 적용 경로를 실행한다고 설명함. 다만 이는 AI Router이며 라우팅 모델 동작/요금 검증이 필요하므로 무료-first 조건 아래 테스트하지 않음.
- Activepieces MCP 문서(https://www.activepieces.com/docs/mcp/tools)는 일반 ROUTER 단계 추가/브랜치 구성 기능을 설명하지만, 이 문서만으로 일반 Router가 병렬 fan-out을 수행한다고 증명되지는 않음. 따라서 기존 AI 3AI 플로우에 일반 Router를 끼워 넣어 병렬 실행을 보장한다고 주장하지 않음.
- Sub Flows 도구 메타데이터는 Call Flow 대상이 게시·활성화되어야 하고 Wait for Response를 켜면 호출 결과를 기다린다고 명시함. 비운영 테스트에서도 이를 사용하려면 하위 플로우 게시/활성화가 필요할 수 있어, 현재의 “운영 플로우 보호/초안 비활성 유지” 조건과 충돌할 가능성이 있으므로 진행하지 않음.
- 결론: 모의 CODE 단계의 Promise.all은 검증됐지만, Activepieces 엔진 수준의 무료·안전한 병렬 fan-out 및 join 방식은 아직 미검증. 다음 조사 대상은 공식 BARRIER/Waitpoints 지원과 Cloud에서 사용할 수 있는 안전한 구성 경로다. 기존 플로우·자동화는 그대로 유지함.


## 추가 재확인 — 브라우저 및 BARRIER 경로
- 연결 브라우저 탭을 다시 조회했으나 `Browser access requires the originating browser context` 오류가 재현됨. 이 세션에서 Gemini/Claude 소비자 웹앱의 실제 응답을 확인할 수 없음. 두 모델을 사용했다고 주장하지 않음.
- 기존 공식 BARRIER 감사 결과를 재확인함: 엔진 waitpoint API로는 BARRIER가 문서화되어 있지만 일반 비주얼 액션으로 확인되지 않았고, Cloud에서 사용자 정의 piece를 설치할 수 있는지 미검증. 사용자 정의 piece 관리에는 플랫폼 유료 기능 제한이 명시되어 있어, 무료 사용 가능성을 확인하기 전에는 이 경로를 진행하지 않음.
- 따라서 현재 완료 범위는 mock-level 병렬 타이밍 및 merge 계약 테스트뿐임. 엔진 수준 병렬 호출, Gemini/Claude 실제 응답, 무료 요금 상태, 과거 Flow ID 불일치는 미완료로 유지.
- 사용자 승인 없이 운영 흐름/자동화/연결/main을 변경하거나 유료 호출을 하지 않았음. 다음 작업은 브라우저 연결 컨텍스트가 복구되거나, 무료 플랜에서 사용 가능한 문서화된 엔진 수준 fan-out/join 경로가 확인될 때 이어서 진행함.


## 실행 기록 — 2026-10-18 후속 상태 확인 및 맞춤 지침 최적화
- 작업 시작 시 GitHub 프로토콜, 프로젝트 인덱스, 최신 실행 보고서, Slack 채널 C0C9649RQAZ 최근 기록을 다시 읽음.
- Activepieces 읽기 전용 재조회: 총 7개 플로우, ENABLED/published 3개(`AI 3AI 협업`, `Slack`, `Gemini + Claude 협업 비서 (비용 확인 필요)`), DISABLED/unpublished 초안 4개. 운영 플로우 상태는 변경하지 않음.
- `AI 3AI 협업` 구조 확인: ChatGPT 초안 → Gemini 검토 → Claude 검토 → 통합 → HTTP 응답 → Slack 알림 순차 체인(7/7 단계 구성됨). 실제 엔진 수준 병렬 실행은 확인되지 않음.
- 공식 문서 조사: AI Router는 기본적으로 한 경로를 선택하고 `Every route that applies`에서 적용되는 경로를 복수 실행할 수 있지만, 라우팅 모델 요청과 비용이 관련되어 비용 확인 전 테스트하지 않음(https://www.activepieces.com/docs/flows/ai-router). Waitpoints 문서는 구형 V0 waitpoint 조회가 실행당 여러 pending waitpoint를 처리하지 못할 수 있고 병렬 분기 시 수정이 필요하다고 명시함(https://www.activepieces.com/docs/install/architecture/waitpoints). 따라서 무료·안전한 엔진 병렬 fan-out/join은 여전히 미검증.
- 맞춤형 지침을 1,173자로 최적화함. GitHub의 canonical `AI-custom-instructions-ko-1500.md` 및 표시용 `CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md`를 브랜치 `ai/continuation-readonly-audit-2026-10-18`에서 갱신. Canonical commit `c9559a867f933a62314c65ca5bd9f2c994230cc1`; 표시본 commit `cda4becf8b253ec09e4935fac294d6d5fee5b7ce`. Canonical 파일 재조회에서 SHA `9481319cf792a6f2e85031b73bb45405c15eb300`, 실제 본문 길이 1,173자 및 선언 길이 일치 확인. 두 파일 본문 일치 여부는 후속 재조회 검증 대상으로 남김.
- 사용자 설정 읽기 결과: personality는 `친근함`으로 확인됨. Custom Instructions의 실제 UI 내용/활성화/저장 상태는 이 도구로 읽을 수 없어 미확인. OpenAI 공식 안내는 iOS Settings → Customize ChatGPT, Enable customization 켬, 지침 입력을 안내하며 Free/Go 한도는 1,500자(https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions).
- Gemini/Claude 소비자 웹앱 접근 시도 결과: Browser connector가 `originating browser context` 오류를 반환. 실제 웹앱 응답 0, 생성 API 호출 0, 유료 API 호출 0. 연결 상태 ACTIVE는 무료 한도/청구 또는 실제 응답을 입증하지 않음.
- 비용/안전: 구매·업그레이드 0, 운영 플로우 수정/실행/게시/비활성화 0, 매시간 정각 자동화 변경 0, main 변경 0. Activepieces 구조 응답에는 웹훅 인증 값이 포함될 수 있으므로 비밀값을 기록하거나 재출력하지 않음.
- 다음 목표: 두 지침 파일을 재조회해 본문 일치를 검증하고 이 보고서를 GitHub에 저장 후 다시 읽기, Slack에 상태 요약을 게시 후 재조회. 병렬 실행은 공식 문서상 무료·안전한 구성과 엔진 동작이 명확해질 때까지 운영 변경 없이 조사 지속.

## 실행 기록 — 2026-10-18 병렬 실행 방식 추가 공식 문서 검토

- 최신 실행 기록과 프로젝트 인덱스, 프로토콜을 작업 시작 시 다시 읽음. Slack 채널 `C0C9649RQAZ`에서도 최근 병렬/합류 기록을 재조회함.
- Activepieces 공식 Waitpoints 문서(https://www.activepieces.com/docs/install/architecture/waitpoints)를 다시 확인함. BARRIER는 여러 작업의 신호가 모두 도착할 때까지 기다리는 엔진 waitpoint로 설명되어 있으나, 문서에 명시된 알려진 제한은 deprecated V0 resume lookup이 한 실행의 임의 pending waitpoint를 반환한다는 점이며, 한 실행에 pending V0 waitpoint가 여러 개 있는 상황(병렬 분기 등)은 이 조회 문제가 해결되기 전 지원이 안전하다고 입증되지 않음.
- 공식 Flow Control 문서(https://www.activepieces.com/docs/build-pieces/piece-reference/flow-control)는 waitpoint API를 piece 내부에서 사용하는 방법을 설명함. 현재 Cloud 프로젝트에서 사용자가 직접 만든 custom/private piece를 안전하게 설치·사용할 수 있는지, 해당 기능이 무료인지, BARRIER를 일반 플로우 단계로 호출할 수 있는지는 확인되지 않음.
- Sub Flows piece 메타데이터 재조회: `Call Flow` 및 `Stream CSV to Subflows`는 대상 Callable Flow를 publish/enable해야 함. CSV action은 배치별 bounded concurrency를 명시하지만, CSV 대량 처리 전용이며 이 프로젝트의 비활성·미게시 테스트 조건과 충돌하므로 사용하지 않음.
- 공식 AI Router 문서(https://www.activepieces.com/docs/flows/ai-router)는 기본적으로 한 경로만 실행하고 `Match = Every route that applies` 설정에서 일치하는 여러 경로를 실행한다고 설명함. 다만 AI 평가 모델 사용 비용/무료 여부가 확인되지 않아 테스트하지 않았고, 일반 Router만으로 병렬 실행을 보장한다고 간주하지 않음.
- Activepieces 현재 플로우 목록 재조회 결과 7개: ENABLED/published 3개, DISABLED/draft 4개. 운영 플로우/예약/연결 설정 변경 0건. 기존 mock 테스트는 JavaScript `Promise.all` 코드 단계의 합성 테스트이며 엔진 수준 Gemini·Claude 병렬 실행 증거가 아님.
- Gemini/Claude 소비자 웹앱 응답은 현재 연결된 브라우저 컨텍스트 오류 때문에 이번에도 확보하지 못함. 실제 응답 0건. 생성 API 호출 0회, 유료 API 호출 0회, 구매/업그레이드 0건.
- 결론: 현재 안전 조건(무료 확인, 비활성 초안 유지, 운영 변경 금지)을 모두 지키면서 Activepieces Cloud 엔진 수준의 AI fan-out/join을 실제 검증할 수 있는 방법은 아직 입증되지 않음. 다음 목표는 사용자가 설치·실행할 수 있는 별도 무료 self-hosted test project/environment의 최소 요건과 안전한 검증 절차를 공식 문서로 정리하는 것. 설치나 운영 변경은 실행하지 않음.

## 다음 목표 조사 — 무료 별도 self-hosted 테스트 환경

- Activepieces 공식 설치 문서(https://www.activepieces.com/docs/install/options/docker-compose)를 확인함. 권장 self-host 구성은 Docker Compose v2, 최소 2 vCPU/4 GB RAM이며 Windows에서는 WSL2가 필요함. PostgreSQL, Redis, app, worker로 구성됨.
- 더 가벼운 개인 테스트 옵션(https://www.activepieces.com/docs/install/options/docker)은 Docker 하나로 단일 머신에서 실행되지만, PGLite와 메모리 큐를 사용하며 확장성이 제한됨. 개인용 mock/flow-control 테스트에는 후보가 될 수 있으나 BARRIER/custom-piece를 지원하는지는 별도 검증이 필요함.
- 공식 라이선스 안내(https://www.activepieces.com/docs/about/license)는 핵심 기능이 MIT 오픈소스이고 Enterprise/Cloud 기능은 상용 라이선스라고 구분함. 이 사실만으로 BARRIER custom piece가 Cloud 무료 플랜에서 설치 가능하다고 해석하지 않음.
- 현재 실행 환경에 Docker/WSL2 또는 사용자 PC 제어 권한이 확인되지 않아 설치 명령을 실행하지 않았고, 로컬 환경을 변경하지 않음. 다음 안전 단계는 사용자가 별도 테스트 머신에서 Docker가 있는지 확인한 뒤, isolated hobbyist container로 먼저 mock-only 테스트를 수행하는 것. 운영 Cloud 프로젝트, 운영 플로우, 예약에는 연결하지 않음.
- 이번 조사 비용: 생성 API 0회, 유료 API 0회, 구매/업그레이드 0건. 실제 Gemini/Claude 웹앱 응답은 브라우저 연결 컨텍스트 오류로 0건.

## 중요 정정 — Activepieces Router는 다중 일치 경로를 순차 실행 (2026-10-18)

- Activepieces 공식 엔진 소스 `packages/engine/src/lib/handler/router-executor.ts`를 직접 읽음: https://github.com/activepieces/activepieces/blob/3d0b6ef9/packages/engine/src/lib/handler/router-executor.ts
- `EXECUTE_ALL_MATCH`는 조건이 맞는 여러 경로를 처리하지만, 실제 실행 루프는 `for` 안에서 각 `flowExecutor.execute(...)`를 `await`한 다음 다음 경로로 이동함. 따라서 “Every route that applies”는 여러 경로를 실행한다는 뜻이지, 엔진 수준 병렬 실행을 뜻하지 않음.
- 이 소스 근거에 따라 AI Router를 병렬 fan-out 솔루션 후보로 간주하던 해석을 정정함. AI Router 평가 모델의 비용 이슈와 무관하게, 현재 확인한 엔진 구현은 Router 분기 자체가 순차 실행임.
- BARRIER waitpoint API는 fan-in primitive지만 일반 플로우 action으로 직접 쓸 수 있는지, Cloud에서 custom piece를 설치할 수 있는지, 무료인지 확인되지 않음. Sub Flows는 target Callable Flow publish/enable이 필요하므로 현재의 비활성 초안만 유지하는 정책 아래에서는 아직 채택하지 않음.
- 현재 프로젝트 플로우 7개(활성 3, 비활성 초안 4). 운영 플로우, 기존 정각 자동화, main, 연결 및 비밀값 변경 0건. Gemini/Claude 생성 응답 0, API 생성 호출 0, 유료 API 0.
- 결론: 기존 AI 3AI 협업 플로우는 순차 실행이며, Router만 바꾸어 병렬화할 수 있다고 안내하면 안 됨. 실제 병렬화의 다음 후보는 (a) 별도 self-hosted test instance에서 독립 실행을 오케스트레이션하고 fan-in을 검증하거나, (b) 하나의 Code step에서 실제 provider 호출을 Promise.all로 실행하는 방식이다. (b)는 유료/불확실 API 호출 및 credential exposure 위험 때문에 무료 조건이 확인되기 전 실행하지 않음.

## 비용 안전성 추가 확인 — Activepieces AI credits (2026-10-18)

- Activepieces 공식 pricing page(https://www.activepieces.com/pricing)는 Free plan을 $0/no card로 표시하고 월 1,000 credits를 제공한다고 설명함. 같은 페이지는 AI step에 모델 종류별 2/10/20 credits가 들고, Agentic action은 1 credit라고 안내함. Free quota 소진 시 실행은 credit refresh까지 대기하며 Plus/Team에서는 초과분이 과금될 수 있음.
- 공식 AI Providers 안내(https://www.activepieces.com/docs/admin-guide/guides/setup-ai-providers)는 provider credentials를 직접 연결하는 BYOK 방식을 설명함. BYOK이면 AI step은 1 credit이지만 provider 토큰 비용은 사용자 provider 계정에 청구됨.
- 현재 프로젝트 도구에서 확인 가능한 정보는 5개 연결이 ACTIVE이고 21개 Activepieces AI 모델이 표시된다는 사실뿐임. 실제 Free/Plus/Team 요금제, 잔여 credit balance, OpenAI/Gemini/Claude API 키의 무료 한도/청구 상태를 읽을 수 있는 도구는 확인되지 않음. 따라서 모델 목록이나 ACTIVE 상태를 무료라고 해석하지 않음.
- 비용 확인을 위해 AI step, provider generation API, 기존 운영 플로우를 실행하지 않음. Gemini/Claude 실제 응답 0, 생성 API 0, 유료 API 0, 구매/업그레이드 0.
- 다음 결정: 실제 provider 호출은 잔여 Activepieces credits와 외부 provider billing/quota를 읽기 전용으로 확인할 수 있을 때까지 보류. 그 전에는 synthetic mock만 사용.

## Read-only billing/credits UI path found (2026-10-18)

- Official Activepieces Usage guide: https://www.activepieces.com/docs/admin-guide/guides/usage. It states Platform Admin → Usage displays credits used and plan credit limit; project breakdown separates AI Usage, Runs Usage, and Total. Billing and Subscription provides the associated plan/billing breakdown.
- This is the documented read-only route for checking remaining credits without executing any AI step. Current connected Activepieces tools do not expose the platform usage/billing endpoints, and Browser connector has no originating browser context, so the account's current plan/credit balance cannot be read from this session.
- To proceed safely with actual provider tests, the only missing account-specific evidence is the current Usage page values (plan, credits used/limit or remaining, AI usage) plus provider-side billing/quota status for OpenAI, Gemini, and Claude. No API or AI step has been executed while these values remain unknown.
- Next goal: obtain these read-only usage/billing values from the account UI or restore the connected browser context; then choose a test whose maximum cost is bounded by verified free quota. Production flows and the hourly schedule remain unchanged.

## 격리된 엔진 병렬 실행 테스트 경로 설계 (2026-10-18)

- 공식 `@activepieces/piece-subflows/streamCsvToSubflows` action schema를 읽기 전용으로 확인함: CSV를 배치 단위로 스트리밍하고, 각 배치마다 `Callable Flow` 자식 실행을 bounded concurrency로 dispatch함. 행 배치 크기 1–10,000, 연결 필요 없음. 대상 Callable Flow는 published 상태여야 함.
- 따라서 현재 Cloud 프로젝트에서 비활성 초안 유지 정책을 깨지 않고 테스트하려면, 별도 로컬 self-hosted Activepieces 인스턴스에서 synthetic child flows만 publish하는 것이 가장 안전한 후보임. 테스트는 2개의 mock CSV 행, 각각 2초 대기, 자식 run의 시작/종료 타임스탬프 겹침 및 부모의 fan-in 완료 여부를 세 차례 확인하도록 설계함.
- 테스트 계획 문서 생성 후 재조회 검증: `docs/ai/isolated-fanout-join-test-plan-2026-10-18.md`, commit `aa6965bf2f087a65f3b7a6e7d1c8dacb6c561847`, blob SHA `ed0c882febde5fdd84e26c0e3f4d9751a3d8f6f2`. 재조회에서 synthetic-only 조건, concurrency pass 기준, Docker/Podman 차단 사유가 확인됨.
- 공식 self-host 문서: https://www.activepieces.com/docs/install/options/docker-compose. 요구사항: Docker Compose v2, 최소 2 vCPU/4 GB RAM, Windows는 WSL2. 현재 이 실행 환경에는 Docker/Podman이 설치되어 있지 않아 로컬 엔진 실행은 아직 불가. 이 문서는 계획만 저장한 것이며 실제 engine-level test 성공으로 보고하지 않음.
- 기존 Cloud 플로우 7개(활성 3, 초안 4)와 매시간 정각 예약은 변경하지 않음. Gemini/Claude 실제 응답 0, AI 생성 API 0, 유료 API 0, 구매/업그레이드 0.
- 다음 목표: Docker Compose v2가 있는 별도 로컬 머신에서 계획서의 synthetic-only 테스트를 실행하고, 세 번의 run ID/child timestamps를 수집. 그와 별개로 Platform Admin → Usage/Billing 및 외부 provider quota가 확인되기 전 실제 AI 생성 호출은 금지.


## 실행 기록 — 2026-10-18 Activepieces MCP 도구 복구 재시도
- 시작 시 작업 브랜치의 `docs/ai/AI-memory-protocol.md`, `docs/ai/PROJECT_MEMORY_INDEX.md`, 최신 실행 보고서, Slack 채널 `C0C9649RQAZ`의 최신 기록을 실제로 다시 읽음.
- 브랜치/경로 확인: `ai/continuation-readonly-audit-2026-10-18`. `docs/ai/AI-memory-protocol.md` blob SHA `6fe591ec8850c3877f2757f65a16843047a4bbaa`; 인덱스 blob SHA `3f11f0897344deb096eaf36587d8bf378b0d3cb3`; 직전 보고서 blob SHA `018947c50804a778d98a6a74d09dd6c6afa2ace0`.
- 공식 Activepieces MCP 도구 참조를 확인함: `ap_set_project_context`는 전체 도구 카탈로그에 존재하며 프로젝트 범위 작업 전에 필요함. 그러나 현재 연결에서 노출된 Activepieces MCP 도구 목록에는 해당 도구가 없음. 이 세션에서 도구 카탈로그 refresh/reconnect 액션도 발견하지 못함.
- 독립 읽기 전용 진단: 브라우저 탭 조회는 originating browser context 오류로 실패. Gemini/Claude 소비자 웹앱 응답을 확보하지 못함. GitHub 기본 브랜치에서 요청 파일 조회가 404였으나, 전용 작업 브랜치에서 세 파일을 정상적으로 읽음; 이는 기본 브랜치/작업 브랜치 차이와 일치함.
- Slack 최신 검색은 `C0C9649RQAZ`의 최근 AI/Activepieces 기록을 확인했고, 이전 도구 목록 재열거 및 브라우저 컨텍스트 실패가 이미 기록되어 있음을 확인함.
- 안전 경계: `ap_list_flows`, `ap_list_runs`, `ap_get_run`, 연결 조회 등 프로젝트 범위 도구는 호출하지 않음. 컨텍스트 가드 우회, 프로젝트 ID 추측, 플로우 테스트/실행/수정/게시, 예약 변경은 하지 않음.
- 비용/변경: 공급자 생성 API 0회, 유료 API 0회, 구매/업그레이드 0건, 운영 변경 0건, 기존 매시간 정각 Asia/Seoul 자동화 변경 0건, `main` 변경 0건. 테스트 ID 없음(실행 테스트를 하지 않음).
- 차단 및 사용자 조치: ChatGPT의 연결된 앱/MCP 관리 환경에서 Activepieces 연결의 도구 목록 갱신 또는 공식 재연결 기능을 찾아 실행한 뒤, `ap_set_project_context`가 실제 노출되는지 확인해야 함. 현재 세션은 그 설정 UI/연결 런타임을 제어할 수 없어 직접 갱신은 미완료.
- 다음 목표: 도구가 노출되면 의도한 프로젝트 ID를 읽기 전용으로 확인하고, 그 후에만 과거 Flow ID와 parent/trigger 출처를 조사함. 계정별 무료 한도·결제 위험은 별도의 신뢰 가능한 읽기 전용 증거가 확보되기 전까지 미확인으로 유지.


## 실행 기록 — 2026-10-18 공식 MCP 관리 경로 재검토

- 최신 공식 OpenAI 도움말을 다시 확인함: https://help.openai.com/en/articles/12584461-creating-custom-mcp-apps-in-chatgpt 및 https://help.openai.com/en/articles/12584461. 문서에 따르면 사용자 지정 MCP 앱의 도구 목록 Refresh는 Business/Enterprise/Edu 작업공간의 관리자/소유자 권한과 유효한 연결을 전제로 하며, MCP 앱 관리 기능은 ChatGPT 웹에서 제공됨. 현재 사용자 환경이 Go 플랜의 iOS 앱이므로 일반 앱 설정만으로 해당 관리 기능을 직접 사용할 수 있다고 가정하지 않음.
- Activepieces 공식 도구 참조를 다시 확인함: https://www.activepieces.com/docs/mcp/tools. `ap_set_project_context`는 프로젝트 선택에 필요한 도구이며 모든 프로젝트 범위 도구는 프로젝트 컨텍스트를 요구함.
- ChatGPT 플러그인 디렉터리에서 Activepieces 검색 결과가 비어 있었음. 따라서 현재 연결의 도구 manifest를 이 세션에서 재생성/갱신할 수 있는 공식 관리 도구가 발견되지 않음.
- 브라우저 connector는 여전히 originating browser context 오류로 실패. Gemini/Claude 소비자 웹앱 응답은 확보하지 못함.
- GitHub 이슈 #3에 이 관리 경로의 제약과 다음 단계 기록을 추가하고 read-back 확인함: https://github.com/watersun79-source/ai-token-optimization/issues/3#issuecomment-6247974106. Slack 후속 스레드에도 기록함: https://chatgpt-mor9047.slack.com/archives/C0C9649RQAZ/p1792314005086499?thread_ts=1792313602.528959&cid=C0C9649RQAZ.
- 다음 실행 가능한 조치: 이 MCP 연결/도구 manifest를 소유한 통합 런타임 관리자에게 `ap_set_project_context` 누락 및 tool-list refresh를 요청하거나, 동일한 공식 setter가 포함된 정상 MCP 연결을 제공받는다. 일반 Go/iOS 설정에 존재한다고 확인되지 않은 메뉴를 계속 안내하지 않는다.
- 비용 및 보호 상태: 공급자 생성 API 0회, 유료 API 0회, 구매/업그레이드 0건, 프로젝트 범위 Activepieces 호출 0회, 운영 플로우/연결/정각 예약/`main` 변경 0건.


## 추가 재시도 — 연결 안내 도구와 통합 검색 (2026-10-18)

- 현재 세션의 Activepieces 도구 목록을 다시 열거함. 공식 문서에는 `ap_set_project_context`가 있으나 현재 노출 목록에는 없음. 다른 프로젝트 범위 도구를 호출하지 않아 컨텍스트 가드를 우회하지 않음.
- `ap_setup_guide(topic="connection")`을 안전하게 조회함. 반환된 내용은 Activepieces 대시보드의 Settings → Connections에서 연결을 설정하는 일반 안내뿐이며, MCP tool manifest refresh/reconnect 기능은 제공하지 않음.
- ChatGPT 플러그인 디렉터리에서 Activepieces/MCP 연결 관리 관련 검색을 다시 실행했으나, 이 누락 도구를 복구하거나 기존 Activepieces 연결의 도구 목록을 새로고침하는 적합한 플러그인을 확인하지 못함. 새 플러그인을 설치하거나 연결을 변경하지 않음.
- 최신 공식 문서 확인: OpenAI custom MCP tool-list refresh는 관리 권한과 유효한 연결을 요구하며, MCP apps는 모바일에서 사용할 수 없다고 명시됨: https://help.openai.com/en/articles/12584461-creating-custom-mcp-apps-in-chatgpt. Activepieces tool catalog documents `ap_set_project_context`: https://www.activepieces.com/docs/mcp/tools.
- 결론: 현재 세션에서 추가로 수행할 수 있는 안전한 복구 액션은 확인되지 않음. 다음 필수 단계는 연결/런타임 관리자가 공식 MCP 연결의 tool manifest를 갱신하고 `ap_set_project_context`를 실제 노출하는 것. 그 전에는 project ID 추측이나 project-scoped tool 호출 금지.
- 안전 상태: 생성/유료 API 0회, Activepieces project-scoped call 0회, 구매/업그레이드 0건, 운영 플로우/연결/시간별 자동화/`main` 변경 0건.


## 핵심 원인 범위 좁힘 — Discovery 도구 누락 (2026-10-18)

- Activepieces 공식 MCP 개요를 추가 확인함: Discovery 도구는 항상 사용 가능하고, 나머지 도구 카테고리는 프로젝트별 MCP Server 설정에서 켜고 끌 수 있음. 공식 문서: https://www.activepieces.com/docs/mcp/overview.
- 공식 도구 참조에서 `ap_set_project_context`는 프로젝트 ID를 선택하거나 생략해 프로젝트 목록을 반환하는 Discovery 도구로 정의됨: https://www.activepieces.com/docs/mcp/tools.
- 현재 세션에 노출된 Activepieces 도구 45개를 다시 열거했으며 `ap_set_project_context`는 없음. 따라서 단순히 프로젝트별 Flow Management/Testing 카테고리가 꺼진 문제라기보다, 항상 사용 가능해야 하는 Discovery 도구가 연결/도구 목록에 누락된 상태라는 진단이 더 정확함. 단, 실제 서버 설정/런타임 로그는 접근 불가하므로 원인을 확정하지 않음.
- 실행 가능한 복구 경로는 Activepieces MCP 연결 소유자가 ChatGPT 앱 관리 화면에서 도구 목록을 새로고침하거나, 연결이 정상적인지 확인한 뒤 다시 연결하고, `ap_set_project_context`가 노출되는지 검증하는 것. OpenAI 공식 안내상 custom MCP tool-list refresh에는 관리 권한과 유효한 연결이 필요하며, 해당 MCP 앱 관리는 웹 환경 대상임: https://help.openai.com/en/articles/12584461-creating-custom-mcp-apps-in-chatgpt.
- 프로젝트 ID를 추측하거나 다른 프로젝트 도구로 우회하지 않음. 안전 상태 유지: 프로젝트 범위 Activepieces 호출 0회, 공급자 생성/유료 API 0회, 구매/업그레이드 0건, 운영 플로우/연결/정각 자동화/`main` 변경 0건.


## 관리자 전달용 복구 요청 — 바로 복사 가능 (2026-10-18)

> Activepieces MCP 연결에서 공식 Discovery 도구 `ap_set_project_context`가 ChatGPT에 노출된 도구 목록에서 누락되어 프로젝트 선택과 read-only 실행 이력 감사를 진행할 수 없습니다. Activepieces 공식 문서상 Discovery 도구는 항상 사용 가능해야 합니다 (https://www.activepieces.com/docs/mcp/overview, https://www.activepieces.com/docs/mcp/tools). 연결/통합 관리자가 공식 웹 앱 관리 경로에서 기존 MCP 연결의 유효성을 확인하고 tool list를 refresh/reconnect한 뒤, `ap_set_project_context`가 노출되는지 확인해 주세요. 새 연결 생성이나 운영 플로우 변경은 우선 하지 말고, refresh 이후에도 누락되면 MCP 서버/커넥터 버전과 도구 manifest를 확인해 주세요. 변경 결과와 실제 노출된 도구 목록만 알려주시면 프로젝트 컨텍스트 선택 후 read-only 감사를 재개하겠습니다. API 키, OAuth 토큰, 비밀값은 공유하지 마세요.

- 이 요청은 계정 소유자/연결 관리자 권한이 필요한 외부 조치임. 이 세션에서 해당 관리 권한이나 서버 로그는 사용할 수 없음.
- 완료 확인 기준: (1) setter가 도구 목록에 실제 노출됨, (2) setter로 프로젝트 목록을 확인, (3) 의도한 프로젝트 선택 후 프로젝트 ID 재확인, (4) 실행 이력/부모 트리거 read-only 검사, (5) 결과를 GitHub/Slack에 기록하고 read-back 검증.


## 실행 기록 — 2026-10-19 자동화 수동 실행
- 요청: 기존 AI 매시간 자동화를 지금 실행해 진행.
- GitHub: 프로토콜, PROJECT_MEMORY_INDEX, 최신 실행 보고서를 작업 브랜치에서 실제 재조회함. 저장소 기본 브랜치는 main이며 작업 브랜치는 ai/continuation-readonly-audit-2026-10-18.
- Activepieces: 현재 런타임 도구 인벤토리에서 45개 도구 확인, ap_set_project_context 없음. 사용자 규칙에 따라 프로젝트 범위 도구(ap_list_flows 등)는 호출하지 않음. 공식 Activepieces MCP 문서 검색으로 도구 존재 여부를 확인하는 작업은 이번 실행에서 별도로 하지 않음.
- Slack: 채널 C0C9649RQAZ 최근 메시지를 읽고 기존 관리자 전달용 복구 요청과 이전 진단을 확인함.
- 브라우저: 연결된 브라우저 컨텍스트를 읽으려 했으나 originating browser context 오류로 실패. Gemini/Claude 소비자 웹앱 응답 0건.
- 비용/변경: 공급자 API 호출 0회, 유료 API 호출 0회, 구매/업그레이드 0건. 운영 플로우·연결·테이블·main·기존 매시간 예약 변경 0건.
- 미완료: Activepieces 도구 목록에서 프로젝트 컨텍스트 선택 도구를 확인할 수 없어 프로젝트 범위 점검은 보류. 브라우저 컨텍스트가 없어 Gemini/Claude 무료 웹앱 사용은 미확인.
- 다음 목표: MCP 연결/런타임 관리 화면에서 도구 manifest를 갱신할 수 있는 관리자 경로를 확인하고, 실제 도구 노출이 달라지기 전에는 프로젝트 범위 호출을 하지 않는다.


## 실행 기록 — 2026-10-19 대체 경로 조사
- 사용자가 확인한 바와 같이, 현재 연결에서 `ap_set_project_context`를 호출할 수 없음. 다만 Activepieces 공식 MCP 도구 참조는 이 도구를 명시적으로 정의하고, 프로젝트 ID를 선택하거나 생략 시 프로젝트 목록을 반환한다고 설명함: https://www.activepieces.com/docs/mcp/tools. 공식 개요는 프로젝트 범위라고 명시하며 Discovery 도구는 항상 사용 가능하다고 설명함: https://www.activepieces.com/docs/mcp/overview.
- 런타임 인벤토리를 재검사했으나 Activepieces 도구 목록에 `ap_set_project_context` 또는 `ap_list_projects`는 없음. 그러므로 공식 문서와 실제 연결의 tool manifest 사이 불일치로 분류함. 문서가 현재 배포된 커넥터 버전과 동일하다고 단정하거나 서버 측 원인을 추측하지 않음.
- 대체 경로 검토: 공식 Activepieces Platform MCP는 별도 통합으로 `List Projects` 및 `Custom API Call` 도구를 제공한다고 소개됨: https://www.activepieces.com/mcp/activepieces. 하지만 현재 ChatGPT 세션의 연결 도구 목록에는 이 Platform MCP 도구가 없으며, 새 인증이나 임의 API 키를 사용하지 않고서는 여기서 호출할 수 없음. 공식 API는 projectId를 요구하므로 프로젝트 ID를 추측한 API 호출은 안전한 대안이 아님.
- 따라서 지금 가능한 대체 실행은 (1) GitHub/Slack에서 지속 작업과 감사 로그를 계속 관리, (2) 실제로 연결된 Activepieces 도구 목록을 확인, (3) 프로젝트 컨텍스트가 확인될 때까지 프로젝트 데이터 호출을 보류하는 것. 운영 플로우나 연결 변경, API 호출은 하지 않음.
- 현재 상태: Activepieces 프로젝트 데이터 읽기 0회, 공급자 API 호출 0회, 유료 호출 0회, 구매/업그레이드 0건, 운영 플로우/연결/테이블/`main`/기존 정각 자동화 변경 0건.
- 다음 진행 기준: Activepieces 연결 관리자에서 공식 MCP 도구 목록 갱신/재연결을 수행하거나, Activepieces Platform MCP를 별도로 연결한 경우 실제 노출된 `List Projects` 도구를 통해 프로젝트를 확인한다. 연결되지 않은 도구를 사용했다고 주장하지 않는다.


## 실행 기록 — 2026-10-19 연결 대안 검증
- 공식 웹 검색으로 Activepieces Platform MCP 페이지를 재확인함. 공식 페이지는 이 통합이 `List Projects`, `Custom API Call` 등 4개 도구를 제공하며, Activepieces의 Settings → MCP Server에서 서버를 활성화하고 MCP 클라이언트에 연결하는 방식이라고 설명함: https://www.activepieces.com/mcp/activepieces 및 https://www.activepieces.com/docs/mcp/overview.
- ChatGPT 플러그인/커넥터 카탈로그도 조회했으나, 이번 검색 결과에서 사용 가능한 Activepieces 전용 ChatGPT 앱/커넥터는 찾지 못함. 따라서 현재 대화에서 연결을 대신 생성하거나 Platform MCP의 List Projects를 직접 호출할 수 없음. 연결을 만들었다고 주장하지 않음.
- 문서상 경로와 달리 사용자의 현재 연결에는 필요한 프로젝트 Discovery 도구가 없으므로, 이 세션 안에서 다른 Activepieces 프로젝트 도구를 호출해 우회하지 않음. 실제로 필요한 다음 조치는 사용자가 Activepieces Platform MCP를 별도 MCP 클라이언트/연결 설정에서 연결하는 것. 연결 완료 후 실제 도구가 노출되면 읽기 전용 프로젝트 목록 확인부터 재개할 수 있음.
- 현재 실행에서 수행한 것: 공식 문서 재검증, ChatGPT 연결 카탈로그 검색, GitHub 보고서 갱신 및 재조회, Slack 기록 게시 및 재조회. API 호출/프로젝트 데이터 접근/운영 변경/유료 호출은 0건.


## 실행 기록 — 2026-10-19 현재 선택 프로젝트 읽기 전용 점검
- 사용자가 Activepieces에서 확인한 현재 선택 프로젝트: `Personal Project`, ID `Fr9OAsxi4FbVSVLZkexYi`. Activepieces 답변은 이 프로젝트가 자동 선택된다고 명시했으므로, 해당 컨텍스트에서 읽기 전용 조회를 시작함. `ap_set_project_context`와 별도 `List Projects` 도구는 여전히 이 세션 도구 목록에 없음.
- `ap_list_flows(limit=100)` 결과: 흐름 10개. ENABLED + published 3개(`AI 3AI 협업`, `Slack`, `Gemini + Claude 협업 비서 (비용 확인 필요)`); 나머지 7개는 DISABLED. 기존 상태는 변경하지 않음.
- 활성 3개 흐름의 구조를 읽기 전용으로 검사함. 각 단계는 설정 완료로 표시됨. 첫 번째 흐름은 ChatGPT → Gemini → Claude → 최종 통합 → HTTP 응답 → Slack 구조. 두 번째는 webhook → Slack 메시지 구조. 세 번째는 OpenAI 단계가 skip 설정이며 Gemini → Claude → webhook 응답 구조. 이 구조는 공급자 호출 시 비용이 발생할 가능성을 배제하지 못하므로 흐름 실행/테스트는 하지 않음.
- 활성 3개 흐름 각각에 대해 최근 PRODUCTION 실행 5건 조회: `AI 3AI 협업` 0건, `Slack` 0건, `Gemini + Claude 협업 비서 (비용 확인 필요)` 최근 5건 모두 SUCCEEDED (2026-10-15 UTC). 각 흐름의 FAILED 10건 조회 결과 0건, QUOTA_EXCEEDED 조회 결과 0건. 이 결과는 조회한 필터/범위에 한정되며 전체 기간의 모든 실행을 의미하지 않음.
- 안전 조치: 어떤 흐름도 실행/테스트/수정/게시/비활성화하지 않음. 연결·테이블·예약·`main`은 변경하지 않음. 공급자 API 호출 및 유료 호출 0회. 웹훅 비밀값은 로그/Slack 보고서에 복사하지 않음.
- 다음 목표: Gemini/Claude 협업 흐름의 실제 비용·무료 한도를 확인하기 전에는 실행하지 않고, 읽기 전용으로 해당 흐름의 설정/연결 메타데이터를 추가 점검한 뒤 근거 있는 개선안만 기록함.


### 추가 읽기 전용 연결 메타데이터 확인 — 2026-10-19
- 현재 선택 프로젝트의 연결 목록에서 OpenAI, Google Gemini, Google Gemini api, Slack, Anthropic Claude 총 5개가 모두 ACTIVE로 표시됨.
- ACTIVE는 연결 상태만 뜻하며 무료 한도, 청구 상태, API 크레딧 잔액을 증명하지 않음. 따라서 Gemini/Claude/OpenAI를 호출하거나 흐름을 테스트하지 않았고 비용 관련 미확인 상태를 유지함.
- 연결/인증 설정 변경은 0건. 연결 ID 외에 비밀값은 보고서에 기록하지 않음.


## 실행 기록 — 2026-10-19 무료 사용·비용 확인 경로 조사

- Activepieces에서 비용 위험을 만들지 않는 읽기 전용 메타데이터 확인을 이어감. `ap_list_ai_models` 결과에는 `activepieces` 제공자 아래 21개 모델이 표시됨(Gemini, Claude, OpenAI 계열 포함). 이는 모델 목록/설정 메타데이터일 뿐, 계정의 남은 크레딧·무료 사용량·청구 상태·각 모델의 실제 호출 비용을 확인한 결과가 아님.
- 연결 설정 안내를 조회함. Gemini 연결은 Google AI Studio API 키 경로를, Claude 연결은 Anthropic Console API 키 경로를 안내함. 안내 내용은 연결 설정 방법만 제공하며, 계정별 결제 상태나 무료 할당량을 조회하지 않음. 실제 공급자 호출이나 테스트는 하지 않음.
- 도구 인벤토리에서 Activepieces의 billing/credit/quota 조회 도구를 찾지 못함. 따라서 현재 연결의 ACTIVE 상태나 모델 목록만으로 무료 사용을 확인할 수 없음. 유료 호출을 막기 위해 AI 플로우 실행/테스트는 보류함.
- 공식 설치 문서 조사: Activepieces Community Edition은 self-hosted 환경에서 무료로 시작할 수 있고, 개인용 단일 컨테이너 설치에는 Docker가 필요함. 공식 문서의 Docker Compose 설치는 Docker Compose v2 및 최소 2 vCPU/4 GB RAM을 요구함. 이 사실은 외부 AI 제공자 API 자체가 무료라는 뜻은 아니며, 사용자의 장비 적합성도 이 실행에서 확인하지 않음. 설치·배포·시스템 변경은 수행하지 않음.
  - https://www.activepieces.com/docs/install/options/docker
  - https://www.activepieces.com/docs/install/options/docker-compose
  - https://www.activepieces.com/solutions/open-source-developers
- 다음으로 필요한 신뢰 가능한 확인은 Google AI Studio / Anthropic Console / OpenAI Platform의 계정별 usage·billing 화면에서 잔액·무료 할당량·결제/자동충전 설정을 직접 확인하는 것. 이 세션에는 해당 계정 화면을 읽는 도구가 없으므로, 확인된 것처럼 보고하지 않음.
- 변경/비용 보호: 공급자 생성 API 0회, 유료 API 0회, 구매·업그레이드 0건, 운영 플로우 실행·테스트·수정·게시·비활성화 0건, 연결·테이블·기존 정각 자동화·`main` 변경 0건. 비밀값은 읽거나 기록하지 않음.
- 상태: 읽기 전용 비용 경로 조사 완료 / 실제 무료 할당량·청구 상태 미확인 / 운영 호출은 계속 보류.


## 예약 실행 기록 — 2026-10-19
- 기존 AI 예약 상태는 활성화됨, 매시간 정각 Asia/Seoul로 확인됨. 새 예약 생성이나 일정 변경은 하지 않음.
- 공식 문서에서 개인용 단일 머신 Docker 설치와 Docker Compose 설치 조건을 확인함. 단일 컨테이너 방식은 Docker만 필요하지만 단일 인스턴스 한계가 있고, Compose 방식은 Compose v2 및 최소 2 vCPU/4 GB RAM과 PostgreSQL·Redis 구성이 필요함.
- Activepieces Community Edition 자체의 무료 사용과 외부 Gemini/Claude/OpenAI API 비용은 별개임. 현재 계정별 무료 한도·청구 확인 도구가 없어 공급자 API 호출 및 AI 흐름 테스트는 계속 보류.
- 이 회차는 문서 조사 및 예약 상태 확인만 수행. 로컬 설치·컨테이너·네트워크 변경 0, 공급자 API 호출 0, 구매 0, 운영 플로우·연결·main·기존 예약 변경 0.
- 공식 자료: https://www.activepieces.com/docs/install/options/docker ; https://www.activepieces.com/docs/install/options/docker-compose ; https://www.activepieces.com/solutions/open-source-developers
- 다음 단계: 별도 테스트 환경을 준비하려면 실제 사용할 장비/OS와 Docker 설치 여부를 확인해야 함. 현재 세션에서는 장비 상태를 확인하거나 설치를 수행하지 않음.


## 실행 기록 — 2026-10-19 해결 지속 점검 (현재 회차)

- 시작 시 `docs/ai/AI-memory-protocol.md`, `docs/ai/PROJECT_MEMORY_INDEX.md`, 최신 후속 보고서, Slack 채널 `C0C9649RQAZ` 의 최근 메시지를 다시 읽음.
- 공식 Activepieces 도구 참조를 웹에서 재확인함: https://www.activepieces.com/docs/mcp/tools 에는 `ap_set_project_context` 가 프로젝트 컨텍스트 선택용 Discovery 도구로 명시되어 있음. 그러나 현재 세션의 Activepieces 도구 인벤토리에는 이 도구가 없음. 프로젝트 범위 도구를 호출해 가드를 우회하지 않음.
- OpenAI 공식 안내도 재확인함: https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt. 도구 목록 새로고침은 해당 연결을 관리할 권한과 유효한 연결이 있는 Business/Enterprise/Edu 웹 작업공간의 관리 경로에 한정됨. 현재 사용자는 Go/iOS 환경이며, 이 세션에서 연결 관리 권한이나 tool-manifest 새로고침 도구를 사용할 수 없음.
- 연결 브라우저를 읽기 위해 `list_tabs` 를 호출했지만 “originating browser context” 오류로 실패. 따라서 Gemini/Claude 소비자 웹앱 실제 응답은 이번 회차에도 확보하지 못함.
- ChatGPT 플러그인 검색에서도 Activepieces 프로젝트 목록/컨텍스트 복구를 직접 수행할 수 있는 설치 가능한 연결은 확인되지 않음. 새 플러그인 설치나 인증 변경은 하지 않음.
- 남은 복구 단계는 MCP 연결 소유자/관리자가 공식 웹 관리 경로에서 연결 유효성을 확인하고 도구 목록을 새로고침/재연결한 뒤 `ap_set_project_context` 를 실제로 노출시키는 것. 도구가 노출되면 프로젝트 ID 확인 → 실행 기록/parent trigger read-only 감사 → 결과를 재검증하는 순서로 진행.
- 안전 상태: 공급자 생성 API 0회, 유료 API 0회, 구매/업그레이드 0건, Activepieces 프로젝트 범위 호출 0회, 운영 플로우/연결/테이블/기존 정각 자동화/`main` 변경 0건. 해결 완료로 표시하지 않음.


## 정정 및 실제 Activepieces 읽기 전용 감사 — 2026-10-19

- 이전 보고서의 `ap_set_project_context` 관련 설명은 잘못된 전제였다. 현재 공식 Activepieces MCP 도구 참조(https://www.activepieces.com/docs/mcp/tools)는 해당 도구를 Discovery 목록에 포함하지 않는다. 이를 “Activepieces에 있는 기능이지만 연결에서 누락됐다”고 단정하지 않는다.
- 현재 실제로 노출된 Activepieces MCP 도구 목록에는 `ap_set_project_context`가 없지만 `ap_list_flows`, `ap_flow_structure`, `ap_list_runs`, `ap_list_connections`가 존재하며, 이 읽기 전용 호출은 현재 선택된 프로젝트에서 정상 응답했다. 따라서 프로젝트 선택 setter 복구를 계속 요구하는 대신 실제 제공 도구로 감사한다.
- 현재 프로젝트 조회 결과: 총 10개 흐름, ENABLED/published 3개(`AI 3AI 협업`, `Slack`, `Gemini + Claude 협업 비서 (비용 확인 필요)`), 나머지 7개 DISABLED. 상태는 변경하지 않았다.
- 현재 연결 조회 결과 5개(OpenAI, Google Gemini, Google Gemini api, Slack, Anthropic Claude)가 모두 ACTIVE로 표시된다. ACTIVE는 인증/연결 상태만 나타내며 무료 할당량 또는 과금 여부를 입증하지 않는다.
- 세 운영 흐름의 구조를 읽기 전용으로 확인했다. `AI 3AI 협업`은 OpenAI → Gemini → Claude → OpenAI → webhook response → Slack의 순차 구조다. `Slack`은 webhook trigger → Slack 메시지 전송 구조다. `Gemini + Claude 협업 비서`는 OpenAI 초안 단계가 SKIPPED이고 Gemini → Claude → webhook response 순서다.
- 최근 PRODUCTION 실행 조회(각 흐름 최대 5건): `AI 3AI 협업` 0건, `Slack` 0건, `Gemini + Claude 협업 비서`는 2026-10-15 UTC의 최근 5건이 모두 SUCCEEDED. 이 조회만으로 현재 시각의 정상 실행이나 무료 사용을 주장하지 않는다.
- 구조 응답에 webhook 인증 값이 포함되어 있었으나 보고서/Slack에는 복사하지 않았다. 운영 흐름·연결·테이블·예약·main은 수정하지 않았다.
- 다음 목표: 최근 실행이 없는 두 흐름은 실행을 유발하지 않고 trigger source, run history 및 upstream caller를 확인할 수 있는 읽기 전용 근거를 조사한다. 실제 테스트는 무료/비용 안전성이 확인되기 전까지 보류한다.
- 비용/변경: 생성 API 0회, 유료 API 0회, 구매/업그레이드 0건, 운영 설정 변경 0건.
