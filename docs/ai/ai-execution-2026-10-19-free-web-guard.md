# AI 이어서 실행 — API 차단 검토본과 게시 버전 대조

최신 확인: 2026-10-19 22:28 KST. API 차단 검토본 구현·검증과 사용자가 승인한 기존 AI 두 플로우 비활성화를 완료했다. 실제 공급자 API 협업의 무료 운영을 입증한 것은 아니다.

## 실제 변경

- [초안 PR #4](https://github.com/watersun79-source/ai-token-optimization/pull/4): 순수 로컬 메타데이터 검증 코드·회귀 테스트·가이드·기존 CI의 추가 검사 단계. Head `c35dff3c2087756540694767f99f5424258fed3f`. main에서 분리한 브랜치이며 미병합 상태다.
- [Activepieces 검토 플로우](https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/3kRMmWICEPt0vIarX7kLR): `TEST ONLY · API 차단·웹 검토 메타데이터`, DISABLED·미게시. 웹훅 트리거 → CODE의 2단계만 있으며 공급자·외부 HTTP·Slack 실행 단계가 없다.
- 배포한 CODE를 다시 읽어 로컬 소스와 일치함을 확인했다. 재시도와 실패 후 계속 진행은 모두 false다. 입력은 `inputs.request`에 바인딩한다.

## 검증 결과

| 검증 | 결과 |
|---|---|
| 로컬 Node 테스트 | 72/72 통과. 최초 단순 전달 기준 구현은 금지된 API 요청을 허용해 RED 실패를 재현 |
| 독립 코드 검토 | API 허용 우회·정확한 필드 제한·URL·날짜·길이·출력 권한을 검토, 수정이 필요한 결함 없음 |
| GitHub CI | [39259453101](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39259453101) completed/success. 기존 Python·JavaScript fixture·새 guard 단계 모두 성공 |
| Activepieces 정적 검증 | 2/2 valid, invalid 0 |
| Activepieces 샘플 검증 | TESTING 실행 4개 모두 예상 결과와 일치 |
| 승인 후 운영 상태 | AI3·Gemini+Claude 두 플로우 DISABLED, Slack만 ENABLED. PR #1·main·예약 설정 변경 없음 |

| TESTING 샘플 | 결과 | 실행 ID |
|---|---|---|
| mock 메타데이터 | SUCCEEDED, synthetic, 실행 권한 false | `kh2VkNVnbtVtgFgwcBlQG` |
| API 모드 | FAILED, INVALID_REQUEST — 예상한 차단 | `mUz5qZRm4TPCnywCngKmn` |
| mock + allow_paid/free_quota | FAILED, INVALID_REQUEST — 예상한 우회 차단 | `y0fn2eB2XfxfpFT6AeVyL` |
| 수동 웹 검토 메타데이터 | SUCCEEDED, caller_supplied_unverified, 실행 권한 false | `h4U678BRdx808BflUiJUL` |

두 FAILED 실행은 동작 오류가 아니라 의도한 거부다. 업로드한 샘플 데이터의 시험이며 실제 운영 웹훅이나 공급자 실행을 검증한 결과가 아니다. 기존 웹 검토 링크를 메타데이터로 사용했으며 이번 테스트가 새 Gemini·Claude 응답을 생성한 것은 아니다.

## 게시 버전 대조로 바로잡은 내용

- Gemini+Claude 협업: 버전 이력의 최신 #21에 Published 표시를 직접 확인했다.
- AI3: 최신 초안 #3과 게시본 #2가 분리돼 있다. 기본 MCP 구조 조회는 최신 초안을 읽으므로 게시본 감사와 구분해야 한다.
- AI3 이력 메뉴에서 #2의 View를 선택하고 `Viewing version #2`를 확인했다. 해당 읽기 전용 게시본 Claude 설정도 `Max Web Search Uses=5`, `Retry on Failure=true`였다. 검색 상한 5는 저장소 정책 상한 3과 다르다.
- 기존 플로우의 필드 수정·테스트·Publish·Use as Draft·Discard changes는 실행하지 않았다. 현재 새 초안이 기존 운영 플로우의 API를 차단한다고 주장하지 않는다.

## 사용자 승인에 따른 운영 API 차단 — 22:28 KST

사용자는 운영 처리 범위에 대한 질문에 **“두 AI 플로우 비활성화까지 진행”**이라고 선택했다. 이 명시적 승인을 받고 두 상태를 변경한 뒤 별도의 조회로 재검증했다.

| 플로우 | 최종 상태 |
|---|---|
| AI 3AI 협업 · `kt2N9yCVA3dLkFiNPSMsH` | DISABLED · 기존 게시 구성 보존 |
| Gemini + Claude 협업 비서 · `drNhxMhmCo3A0rKV0OhIZ` | DISABLED · 기존 게시 구성 보존 |
| Slack · `vtRwEYmcwDTunBZut265G` | ENABLED · published 유지 |

두 AI 플로우 각각의 PRODUCTION RUNNING·QUEUED 조회는 모두 0건이었다. 현재 두 플로우의 새 트리거 실행을 막았으며, 기존 게시 설정을 삭제하거나 새 검토 코드를 운영에 게시한 것은 아니다. 다른 시스템의 API 사용까지 차단했다고 해석하지 않는다. 사용자의 명시적 요청 없이 이 두 플로우를 다시 활성화하지 않는다.

## 실행 경계와 남은 작업

새 코드는 `mock`과 `manual_web`의 제한된 메타데이터만 허용한다. 추가 키·API 모드·권한 우회 플래그는 거부하며, 모든 허용 출력도 `provider_execution_allowed=false`, `network_execution_allowed=false`다. 수동 메타데이터는 사실·출처 검증 성공으로 승격하지 않는다.

3,500 제한은 정제한 요청을 JSON.stringify한 UTF-16 코드 단위 수다. HTTP 원문 바이트나 최종 출력 전체 길이 제한이 아니다. 외부 URL을 열거나 네트워크·파일·환경·SDK를 사용하지 않는다.

이 초안에는 인증 없는 테스트 트리거가 있으므로 비활성·미게시 상태를 유지한다. 검토 코드의 운영 게시, 공급자 API 무료 잔량·청구 검증, PR 병합은 완료로 표시하지 않는다. 기존 두 AI 경로의 새 실행은 사용자 승인에 따라 플로우 상태를 비활성화해 차단했다. 실제 API 연쇄 실행 시험은 하지 않았다.

## 비용 근거와 보존

공급자 생성 API 0회, 기존 운영 실행 0회, 구매·업그레이드 0건. 새로 실행한 것은 공급자 없는 TESTING 샘플 4개다. 새 페이지 로드 뒤 Activepieces 크레딧 표시는 전후 모두 402였으나 계정 전체 청구 감사로 확대 해석하지 않는다.

공식 자료는 builder test run 무료를 명시한다. 현재 공개 구현에서도 MCP flow test는 TESTING 환경을 사용하며 일반 실행 크레딧은 PRODUCTION에만 기록한다. Cloud 배포 SHA 자체는 확인하지 않았다.

- [Workflow Builder 공식 설명](https://www.activepieces.com/product/workflow-builder)
- [MCP 테스트 구현](https://github.com/activepieces/activepieces/blob/a04936e40ee48e4e4112d1c5a3e5b1b506e45f29/packages/server/api/src/app/mcp/tools/flow-run-utils.ts)
- [실행 크레딧 기록 조건](https://github.com/activepieces/activepieces/blob/a04936e40ee48e4e4112d1c5a3e5b1b506e45f29/packages/server/api/src/app/flows/flow-run/flow-run-hooks.ts)
- [버전별 Get Flow 공식 API](https://www.activepieces.com/docs/endpoints/flows/get)

샘플과 테스트 로그는 검토 증거로 남겼다. 새 테이블·공급자 연결·자격 증명은 만들지 않았으며 비밀값·원본 요청 헤더·개인 위치는 기록하지 않았다.

