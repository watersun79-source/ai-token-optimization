# API 차단·웹 검토 메타데이터 테스트 가이드

`TEST ONLY · API 차단·웹 검토 메타데이터`는 **DISABLED·미게시** 상태의 검토용 초안입니다. 구성은 웹훅 트리거와 CODE 단계 2개이며, AI 제공자·HTTP·Slack 실행 단계와 연결된 자격 증명이 없습니다. 이 초안은 기존 운영 플로우를 보호하지 않습니다.

[Activepieces 테스트 플로우](https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/3kRMmWICEPt0vIarX7kLR) · [공식 Workflow Builder 소개](https://www.activepieces.com/product/workflow-builder)

## 허용 입력과 결과

CODE 단계는 `inputs.request`의 `mode`, `evidence`만 받습니다.

- `mock`: 합성 자료 0~4개. 각 항목은 `fixture_id` 1~80자, `summary` 1~500자입니다.
- `manual_web`: 사용자가 수동으로 확인한 자료의 메타데이터 1~4개. 각 항목은 `provider` (`gemini` 또는 `claude`), `stage` (`independent` 또는 `cross`), 승인된 대화 URL, 유효한 ISO 관찰 시각 `observed_at`, `summary` 1~500자로 구성됩니다.
- URL은 `https://gemini.google.com/app/` 뒤 소문자 16자리 16진수 또는 `https://claude.ai/chat/` 뒤 소문자 UUID 형식만 허용합니다. 사용자 정보·쿼리·해시는 허용하지 않습니다. CODE는 URL을 열지 않습니다.
- 요청 전체를 표준 `JSON.stringify`로 직렬화한 길이는 **3,500 UTF-16 코드 단위 이하**여야 합니다. 원문 공백을 포함한 HTTP 바이트 길이나 출력 길이 제한이 아닙니다.

추가 속성, 잘못된 형식, API 실행 모드, `allow_paid`·`free_quota` 등의 우회 플래그는 정적 오류 `INVALID_REQUEST`로 거부합니다. 허용된 결과도 `provider_execution_allowed=false`, `network_execution_allowed=false`로 고정됩니다.

`mock` 결과는 `synthetic`, 수동 웹 자료는 `caller_supplied_unverified`입니다. 자료 형식을 검사하는 기능이며, 자료의 진실성·출처 내용·AI 응답 품질을 검증하지 않습니다. 제공자/API를 실행하는 기능도 없습니다.

## 확인한 범위

로컬 `node --test`는 **72개 통과·실패 0개**였습니다. 최초 RED에서는 의도적으로 단순 전달만 하는 기준 구현이 금지된 API 요청을 허용하여 실패하는 것을 확인했습니다. 최종 소스와 테스트는 `tools/free-web-guard/guard.mjs`, `tools/free-web-guard/guard.test.mjs`에 있으며 CI에서도 같은 테스트를 실행합니다.

Activepieces에서는 아래 **TESTING 샘플 실행 4개**의 결과가 예상과 일치했습니다. 실패로 표시된 차단 시험 2개도 의도한 결과입니다. 업로드한 CODE 소스는 읽어 온 소스와 일치하는 것으로 확인했습니다.

| 샘플 | 실행 ID | 관찰 결과 |
|---|---|---|
| mock | `kh2VkNVnbtVtgFgwcBlQG` | SUCCEEDED · synthetic · 실행 권한 두 값 false |
| API 모드 | `mUz5qZRm4TPCnywCngKmn` | FAILED · INVALID_REQUEST · 예상한 차단 |
| mock + allow_paid/free_quota | `y0fn2eB2XfxfpFT6AeVyL` | FAILED · INVALID_REQUEST · 예상한 차단 |
| manual_web | `h4U678BRdx808BflUiJUL` | SUCCEEDED · caller_supplied_unverified · 실행 권한 두 값 false |

이 기록은 로컬 검사와 TESTING 샘플 검증 결과입니다. 운영 웹훅 성공, 운영 환경의 인증·접근 통제, 모든 입력에 대한 무결성을 보증하지 않습니다.

## 사용 상태 유지

미게시 테스트 트리거에는 인증이 없습니다. **이 상태로 게시하거나 활성화하지 마세요.** 현재 비활성·미게시 상태를 유지하는 검토용 자료입니다. CODE 단계에 실제 API 키·토큰·연결 자격 증명을 입력하거나 연결하지 마세요. 플랫폼은 CODE 검증 전에 입력을 기록할 수 있습니다.

API 차단은 이 제공자 없는 검토 플로우에 한정됩니다. 뒤에 AI·HTTP 실행 단계를 추가하거나 기존 운영 플로우 앞에 이 코드를 붙이는 것만으로 운영 API 실행이 차단된다고 해석하면 안 됩니다.

