# Gemini REST 준비 모듈

**상태: 오프라인 준비 완료 / 라이브 인증·무료 프로젝트·현재 quota 미검증 / 기본 호출 차단.**

이 디렉터리는 재사용 REST 모듈과 오프라인 fixture 검사를 보관해. 호스팅 MCP의 `api_runtime.py`는 동일 소스를 프로젝트 루트의 `gemini_direct.py`로 복사해 사용하며, 전체 deadline과 SQLite 시도 예산은 그 host가 담당해. 실제 키 인증과 모델 응답은 별도 검증 대상이야. `import gemini_direct`와 `dry_request()`는 계정·네트워크·자격증명 I/O를 수행하지 않아. 자동 실행 진입점도 없어.

Google AI Studio의 새 auth key 공개 접두부 `AQ.`를 지원해. 접두부 뒤 ASCII 영숫자·밑줄·하이픈 16~253자만 허용하며 전체 256자 상한을 유지해. 기존 점 없는 16~256자 형식도 유지해. 추가 점·공백·개행은 거부하고, 새 형식은 모델 prompt·응답에서도 비밀 패턴으로 차단해. 이는 형식 호환이며 실제 인증·무료 조건의 증명이 아니야. 테스트에는 명확한 합성값만 사용해.

| 구성 | 동작 |
|---|---|
| 구현 | Python 3.11+ 표준 라이브러리만 사용 |
| 고정 모델 | `gemini-3.5-flash-lite` |
| 유일한 외부 요청 | `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent` |
| 인증 | caller 전용 `Config(api_key=...)` 또는 명시적으로 호출한 `Config.from_environment()`의 `GEMINI_DIRECT_API_KEY`만 사용 |
| 기본 상태 | `Config.enabled=False`, 증거 예제 `UNVERIFIED` |
| 크기 제한 | 직렬화된 요청 본문과 응답 본문 각각 최대 65,536 bytes |
| 생성 제한 | text 입력만, `tools: []`, 출력 `TEXT`, 후보 1개, 최대 출력 256 tokens |
| 시간 제한 | TLS hostname·certificate 검증, socket 작업 timeout 30초 |
| 재호출 | 자동 retry 0, redirect 0, fallback 0 |
| proxy | `http.client.HTTPSConnection`으로 고정 host에 직접 연결, 환경 proxy 탐색·tunnel 설정 없음 |
| 비밀값 | 키를 URL·repr·stdout·로그·파일에 쓰지 않음. HTTP debug 출력과 TLS key logging을 활성화하지 않음 |
| 출력 | text·고정 요청 모델·종료 사유·정수 token count whitelist만 반환 |

`timeout=30`은 표준 라이브러리의 socket 작업 timeout이야. DNS와 전체 프로세스 wall-clock 30초를 보장하지 않아. 향후 실행 host가 별도의 프로세스 deadline을 적용해야 해. 사용한 `SSLContext`는 OS 기본 신뢰 저장소를 사용하므로 그 저장소의 관리는 운영자 책임이야.

## 안전한 preview

이 명령은 키·인증 헤더·실제 prompt 없이 endpoint와 body shape만 출력해.

```bash
python -B -c 'import json; from gemini_direct import dry_request; print(json.dumps(dry_request(), ensure_ascii=False, indent=2))'
```

`dry_request()`는 prompt나 Config를 받지 않아. preview를 수정해도 다음 실요청의 고정 schema는 바뀌지 않아.

## Caller API

```python
from gemini_direct import Config, GeminiDirectClient, OperatorEvidence, dry_request

# owner_supplied_secret과 independent_operator_record는 이 모듈이 수집하지 않아.
config = Config(api_key=owner_supplied_secret, enabled=False)
client = GeminiDirectClient(config)
evidence = OperatorEvidence.from_mapping(independent_operator_record)
preview = dry_request()

# 향후 별도 승인·검증된 caller에서 사용하는 함수 서명:
# client.generate_once(prompt: str, *, evidence: OperatorEvidence) -> TextResult
```

키·endpoint·model·tools·임의 JSON body를 `generate_once` 인자로 받을 수 없어. 실제 키를 model tool arguments나 채팅 메시지로 전달하면 안 돼. `from_environment()`도 import 때 자동 실행되지 않아. 다른 API 키·ADC·Vertex·OAuth 캐시·설정 파일은 검색하지 않아.

반환된 `TextResult.complete`는 `finishReason == "STOP"`일 때만 참이야. `MAX_TOKENS`는 일부 text가 반환돼도 완료로 보지 않아. 도구 호출·비문자 출력·grounding·provider 오류 본문은 반환하지 않아. 응답에 키 원문이 포함되면 text 반환을 차단해. 이 모듈은 외부 tracing·debugger·프로세스 메모리 검사까지 통제하는 secret vault는 아니야.

## 독립 운영자 증거 gate

`evidence.example.json`은 값이 없는 차단용 예제야. 실제 검증을 대신하지 않아. 다음 사실을 **동일 API key / 동일 프로젝트 / 고정 모델**에 대해 독립 관측한 운영자 기록이 없으면 HTTP 객체를 만들기 전에 차단돼.

| 필드 | 통과 조건 |
|---|---|
| `schema_version` | 정수 `1` |
| `status` | `VERIFIED_BY_OPERATOR` |
| `evidence_id` | 새 canonical UUID, 한 번의 시도에만 사용 |
| `api_key_sha256` | caller 키의 SHA-256과 일치하는 소문자 hex 64자리 |
| `model` | `gemini-3.5-flash-lite`와 일치 |
| `observed_at` | timezone이 있는 관측시각, 현재보다 미래가 아니며 15분 이내 |
| `quota_day_pacific` | 현재 `America/Los_Angeles` 날짜와 일치 |
| `auth_verified` | 실제 인증의 독립 확인이 참 |
| `key_project_binding_verified` | 실제 key→project 대응의 독립 확인이 참 |
| `free_tier_verified` | 해당 프로젝트의 실제 Free tier 확인이 참 |
| `billing_account_linked` | billing account가 **연결되지 않음**을 확인한 `false` |
| `paid_billing_enabled` | 실제 과금 미활성 확인인 `false` |
| `quota_verified` | 당일·해당 모델 요청 잔량의 독립 확인이 참 |
| `remaining_requests` | 정수 `>= 1`; boolean·문자열·비율 추정치는 불가 |
| `evidence_refs` | `auth`, `project_binding`, `free_tier`, `billing`, `daily_quota` 각각의 비밀 없는 관측기록 식별자 |

`evidence_refs`는 1~256자의 식별자이며 허용 문자는 영숫자 및 `:._/-`야. key·token·raw header·query string을 넣으면 안 돼. 코드에는 기록을 다운로드하거나 서명을 검증하거나 Google 계정 상태를 확인하는 기능이 없어.

**수동 gate는 자기 입증이 아니야.** JSON에 참을 적는 것만으로 사실이 검증되지 않아. 문서의 무료 가격표, 모델 목록, 과거의 성공, 테스트 fixture를 현재 계정의 인증·과금·quota 증거로 사용할 수 없어. 독립 증거 확보·보관·검토와 실제 활성화는 caller/operator의 별도 책임이야. `free_tier_verified:true`를 입력해도 API의 실제 billing tier가 바뀌지는 않아.

관측 후 다른 caller가 quota를 소모하거나 계정 설정을 바꿀 수 있어. 이 gate는 quota 예약·실시간 청구 보증이 아니며 RPM·TPM 등 다른 제한으로 요청이 실패할 수 있어. 실패하거나 응답이 불명확한 네트워크 시도도 자동 재시도하지 않아.

한 client는 HTTP 시도를 최대 1회만 해. 같은 `evidence_id`의 재사용도 프로세스 안에서 차단해. 이 메모리 기록은 프로세스 재시작·다른 worker와 공유되지 않아. 향후 통합 caller는 프로세스 간 single-flight·증거 소비 기록·계정 설정 변경 시 증거 폐기를 별도로 구현해야 해. 키나 raw 응답을 그 기록에 쓰면 안 돼.

## API key만으로 metadata를 검증할 수 있는지

현재 구현과 조사에서 **key만으로 프로젝트·Free tier·billing 미연결·당일 정확 잔량을 한 번에 안전하게 검증하는 공개 지원 API는 UNVERIFIED**야. 없는 사실로 단정한 건 아니며 이 후보에는 그 조회 기능이 없어.

| 공식 수단 | 확인한 한계 |
|---|---|
| [API Keys `keys.lookupKey`](https://docs.cloud.google.com/api-keys/docs/reference/rest/v2/keys/lookupKey) | key→project 조회 API는 존재하지만 별도 OAuth scope와 `apikeys.keys.lookup` 권한이 필요해. `keyString` query parameter를 사용하므로 이번 키 URL 금지 조건에서도 제외했어 |
| [Cloud Billing `projects.getBillingInfo`](https://docs.cloud.google.com/billing/docs/reference/rest/v1/projects/getBillingInfo) | 프로젝트 billing 정보 API는 존재하지만 별도 OAuth·프로젝트 IAM 권한이 필요해. API key 단독 인증 경로가 아니야 |
| [AI Studio billing 문서](https://aistudio.google.com/docs/billing) | Projects의 Billing Tier와 billing 상태 확인을 안내해 |
| [AI Studio rate limits 문서](https://aistudio.google.com/docs/rate-limits) | 실제 제한은 프로젝트·모델·계정 상태에 따라 다르며 AI Studio에서 확인하라고 안내해 |

`generateContent`를 성공시켜 보거나 오류를 유발해서 billing·무료 여부를 추정하는 동작은 없어. 이 준비 작업에서는 어떤 metadata provider 요청도 실행하지 않았어.

## 오프라인 검증

```bash
python -B -m unittest discover -s tests -v
```

fixture 키는 provider credential이 아닌 합성 문자열이야. 테스트는 실제 socket 연결을 차단하고 외부 HTTPS 경계 또는 socket을 fixture로 대체해. 현재 환경의 API key나 proxy 값, OAuth cache를 읽지 않아.

테스트 범위는 기본 차단·잘못된 key/model/과금 사실·15분/날짜 경계·고정 요청 직렬화·TLS 검증 설정·proxy 미조회·키 전용 env 선택·preview 비밀 제거·요청/응답 64KiB 제한·redirect/retry 차단·upstream 예외 정제·키 echo 차단·도구 응답 거부·client/evidence 재사용 차단이야. 전역 HTTP debug가 켜진 상황도 실제 stdlib HTTP 직렬화를 fixture socket에 흘려 검증해.

## 공식 근거

- [모델 무료 입력·출력 가격](https://aistudio.google.com/docs/pricing#gemini-3.5-flash-lite)
- [REST generateContent API reference](https://aistudio.google.com/api-reference/generate-content)
- [공식 API key 인증](https://aistudio.google.com/docs/api-key)
- [프로젝트 billing 상태 검증](https://docs.cloud.google.com/billing/docs/how-to/verify-billing-enabled)

일반 [text-generation 문서](https://aistudio.google.com/docs/text-generation)의 첫 예제는 현재 Interactions API를 사용하지만, 위 API reference에는 `POST /v1beta/models/{model}:generateContent`가 별도로 남아 있어. 이 모듈은 요청된 고정 generateContent 경로만 사용해.
