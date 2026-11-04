> Current provider policy, verified 2026-11-04: Google ended Gemini CLI consumer Login with Google (individual/free, Google AI Pro and Ultra) on 2026-06-18. See https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals . An installed CLI and successful private MCP status response do not prove model-service access. The model gate remains closed. The official Gemini API route requires separate verified Free-tier project credentials; none are configured here. Antigravity consumer wrappers are not a supported substitute (https://antigravity.google/docs/faq/).

# 실제 Gemini CLI MCP 호출부 · v0.1.0

`gemini_review`는 공식 Gemini CLI를 별도 프로세스로 실행하는 실제 호출부야. 응답을 모의 텍스트로 대체하지 않아. 현재 인증·CLI 무료 할당량 검증 기록이 없으므로 모델 호출은 차단돼.

## 실제로 확인한 범위

- 공식 설치 CLI `--version`: **0.66.0**.
- 공식 CLI `--help`: `--prompt`, `--output-format`, `--policy`, `--approval-mode` 존재 확인.
- 실제 별도 MCP stdio 프로세스의 `initialize`, `tools/list`, `tools/call gemini_status`, `tools/call gemini_review` 차단 응답: **4건 왕복 확인**.
- 실제 외부 Gemini 모델 생성: **0건**.
- 공식 0.66.0 모듈을 인증·네트워크 없이 불러와 system 설정이 사용자 무제한 턴·자동 메모리 설정보다 우선하는지, 실제 PolicyEngine이 기본 도구 27개와 MCP 이름 1개를 모두 deny하는지 확인했어. 실행 중인 모델의 도구 요청을 관찰한 검사는 아니야. 근거는 `policy-control-evidence.json`이야.
- ChatGPT/iOS에서 도구가 직접 노출됐는지, 공급자 인증이 유효한지, 예약이 Gemini에게 위임하는지: **미검증**.

`smoke-evidence.json`은 실제 stdio·CLI 메타데이터 증거야. 테스트용 가짜 실행 파일로 수행한 단위 검사는 별도이고 실제 Gemini 인증·생성 증거가 아니야.

## 실행

Python 3.10 이상과 별도로 설치·검증한 공식 Gemini CLI **0.66.0**이 필요해. MCP SDK가 제공되지 않는 현재 환경에서는 표준 JSON-RPC stdio 최소 서버를 사용해. 네트워크 HTTP 서버는 열지 않아.

1. `GEMINI_CLI_PATH`에 승인된 실제 `gemini` 실행 파일의 절대 경로를 지정하거나 `PATH`에서 `gemini`를 찾을 수 있게 해.
2. 선택적으로 `GEMINI_MCP_STATE_DIR`을 어댑터 전용 비공개 상태 폴더로 지정해.
3. `GEMINI_CLI_HOME`으로 CLI가 직접 인증을 관리하는 전용 홈을 지정해. 생략하면 상태 폴더 아래 새 `cli-home`을 사용해. 기존 인증값을 복사하거나 읽지 않아.
4. `python3 server.py`를 stdio MCP 클라이언트에서 실행해.

검증은 `python3 -m unittest discover -s tests -v`, 실제 안전 smoke는 `python3 smoke.py`로 수행해. smoke는 새 임시 CLI 홈과 누락된 gate로 실행되어 실제 생성이 차단되는지도 확인해.

## 도구

| 도구 | 실제 동작 |
|---|---|
| `gemini_status` | 실제 CLI 버전과 외부 검증 gate의 상태를 확인해. 토큰 파일 내용을 읽거나 모델을 호출하지 않아. |
| `gemini_review` | `request_id`, `prompt`만 받고 검증 gate 통과 후 공식 CLI를 1회 실행해. gate가 없으면 실행 전에 차단해. |

CLI 경로나 추가 인자, 모델 선택, 환경 변수, 인증 코드는 도구 입력으로 받을 수 없어. 질문 본문은 프로세스 인자가 아닌 표준 입력으로 전달해.

## 인증·무료 할당량 gate

운영자가 실제 공식 CLI 인증과 CLI 공급자 무료 할당량을 독립 확인한 뒤 전용 gate JSON 경로를 `GEMINI_MCP_VERIFIED_GATE`에 지정해야 해. gate를 생성하거나 인증을 시작하는 MCP 도구는 제공하지 않아.

- `verified-gate.example.json`은 **미검증 예시**여서 그대로 사용하면 차단돼.
- 인증 성공은 `oauth-personal` 공식 CLI 실행 증거로, 무료 할당량은 `gemini-cli-provider-quota` 근거로 각각 확인해야 해.
- Gemini 웹 사용량 %, GitHub CI, 모의 토큰, 이 README나 상태판은 gate의 실제 인증·무료 증거가 아니야.
- gate는 최근 15분 이내 근거, 같은 CLI 경로·버전·전용 홈과 연결돼야 하고 소유자만 읽고 쓸 수 있어야 해.
- V2 gate의 `max_cli_invocations: 1`은 공식 CLI **프로세스 실행 1회**만 허용해. 타임아웃이나 실패 때도 예산을 재사용하지 않아. V1이나 예전 `max_model_calls` 필드는 허용하지 않아.
- CLI 내부의 라우팅·공급자 재시도 등은 별도 요청을 만들 수 있어. CLI 실행 1회가 공급자 요청 1회라는 뜻은 아니며 실제 `provider_request_count`는 **UNVERIFIED**야.
- gate는 외부에서 독립 확인한 근거를 적용하는 로컬 실행 조건이야. 공급자 서명 영수증이나 자동 인증 검증기로 확대 해석하면 안 돼.

전용 CLI 홈의 설정·훅·확장·MCP 연결을 사전에 검토해야 해. 설정이 임의 작업을 실행하지 않는다고 확인되지 않으면 gate를 발급하지 마. 어댑터는 인증 캐시 내용을 직접 읽거나 복사하지 않아.

## 보호·실패 동작

- API 키·Vertex 환경이 설정되면 차단하고, 실제 자식 프로세스에는 필요한 환경만 전달해.
- 모든 모델 도구를 deny하는 고정 정책과 `plan` 모드를 사용해. 중앙 관리 정책이 이 제한을 무효화할 가능성이 있으면 차단해.
- 이미지 빌드 때 `adapter.CLI_SYSTEM_SETTINGS`를 `/etc/gemini-cli/settings.json`에 설치해야 해. 파일은 root 소유 0644, 모든 상위 폴더는 root 소유이며 그룹·다른 사용자가 쓸 수 없어야 해. 실행 시 이 경로를 `GEMINI_CLI_SYSTEM_SETTINGS_PATH`로 고정해. 어댑터는 내용이나 권한이 다르면 생성을 차단해.
- 이 공식 system 설정은 `model.maxSessionTurns: 1`과 개인 OAuth를 강제하고 자동 메모리·훅·원격 측정을 꺼. 추가 MCP·확장·스킬이 없는 전용 홈인지 별도로 사전 검토해야 해. 로컬 `admin` 설정으로 이 항목들을 비활성화했다고 주장하지 않아. 도구 거부만으로 추가 추론을 막을 수 없으므로 세션 턴 제한을 별도로 적용해. 턴 제한도 공급자 재시도 횟수의 증거는 아니야.
- 최대 동시 실행 1개, 최대 60초, 출력 1MiB 상한, 모델 응답 16,000자 상한이야.
- POSIX는 별도 프로세스 그룹을 종료하고, Windows는 `taskkill /T /F`를 사용해. 현재 실제 프로세스 검사는 Linux에서만 수행했어.
- stdout JSON을 검증하고 stderr를 결과·로그에 포함하지 않아. 비밀값처럼 보이는 입력·출력은 거부해.
- SQLite에는 요청 본문 대신 SHA-256과 검증된 결과만 보관해. 결과는 같은 요청 ID의 중복 호출 방지에 사용돼. 상태 폴더는 비공개로 유지해.
- 같은 ID·다른 본문은 충돌로 거부해. 진행 중이거나 실행 여부가 불확실한 요청은 자동 재시도하지 않아. 프로세스가 강제로 종료되면 남은 요청을 사람이 근거와 함께 검토해야 해.

예약·GitHub main·운영 배포·연결·결제는 변경하지 않아. 이 패키지를 업로드하거나 stdio smoke가 통과했다고 ChatGPT 웹·iOS에 서버가 자동으로 연결되는 것은 아니야.

공식 참고: https://geminicli.com/docs/get-started/authentication/ · https://geminicli.com/docs/cli/headless/ · 설치된 0.66.0 번들 `docs/reference/policy-engine.md`.
