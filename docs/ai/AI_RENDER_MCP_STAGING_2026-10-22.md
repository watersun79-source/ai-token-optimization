# AI 자동 봇 Render Free MCP 배포 준비 및 인증 시험 — 2026-10-22

## 실제 완료
- 사용자의 연속 지시(“진행”)에 따라 기존 Python 로컬 실행기와 v0.4.1 MCP 테스트를 보존한 채 **원격 배포 준비 작업**을 격리 브랜치 `ai/render-free-mcp-staging-2026-10-22`에 적용.
- 공식 Render Docs 확인: Python Free 웹 서비스 제공, 15분 비활성 시 절전, 무료 대역폭·빌드/실행 한도 존재. Render `RENDER_EXTERNAL_HOSTNAME` 및 `PORT`를 공식 제공. 실제 사용자 계정의 무료 잔량/요금은 **미확인**. 공식: https://render.com/docs/free , https://render.com/docs/environment-variables , https://render.com/docs/infrastructure-as-code .
- 사용자 Render 계정은 현재 미연결이어서 Render 앱 플러그인을 설치 후보로 제시함. **실제 Render 서비스 생성/호스팅/배포는 시도하지 않음**. 유료 API 호출 0. 기존 Replit 앱과 Higgsfield 관련 자산은 건드리지 않음.

## 새 코드 및 보안
- `experiments/ai-bot-team/remote_mcp.py`: FastMCP v1, `/mcp` Streamable HTTP, Bearer 인증 비밀을 **환경변수에서만** 읽음. 비밀이 비었거나 32자 미만이면 서버 로드 실패(기본 fail-closed). 프로덕션 호스트는 Render가 제공하는 `RENDER_EXTERNAL_HOSTNAME` 또는 로컬 테스트용 `AI_MCP_ALLOWED_HOST`로 한정, MCP SDK Host/Origin 허용목록 사용. MCP 도구 `delegate_message`는 이전 `real_gateway.run_message(..., network=False)`를 직접 호출하며 기존 읽기 전용 분석 및 0 유료 LLM/0 운영 쓰기 원칙 유지.
- `experiments/ai-bot-team/verify_remote_mcp.py`: 실제 HTTP 클라이언트 검증: 비인증/오류 Bearer→401, 올바른 Bearer→ MCP initialize, tools/list, tools/call 성공; 사용자 입력 `에러 고쳐` + 구문 오류 `print(` → 실제 `ai-auto-debug` 워커 `DONE`, `syntax_valid=false`.
- 격리 브랜치 루트 `render.yaml`: `plan: free`, `autoDeployTrigger: "off"`, 별도 실험 브랜치만 참조, `rootDir=experiments/ai-bot-team`, `AI_MCP_BEARER_TOKEN`은 `sync:false`로 사용자 개인 콘솔에서 직접 설정해야 함. 비밀값은 GitHub·Slack·ChatGPT 메시지·아티팩트에 적지 않음.
- 상세 절차 `experiments/ai-bot-team/README-RENDER-DEPLOY.md`. 고정 Bearer 토큰 기반의 실험 서버이고 완전한 OAuth 로그인 공급자는 미구현. ChatGPT 개인 플러그인에서 API-key 인증 연결 가능 여부는 계정·제품별 추가 검증이 필요함. OpenAI 공식 문서 참고: https://developers.openai.com/plugins/build/plugins , https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt .

## 증거
- GitHub 원격 격리 CI **run [39768988127](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39768988127)** head `823618eb9a3c6528dd6a7ec441647826944ac829` job `119791462781` `completed/success`:
  `FAIL_CLOSED_WITHOUT_KEY PASS`, `mcp_real_authenticated_transport: PASS`, `unauthorized_http: 401`, `actual_worker: DONE`, `external_llm_calls: 0`, `production_writes: 0`, 기존 `Ran 92 tests`, `OK`, `RENDER_FREE_BLUEPRINT_STATIC_CHECK PASS`.
- CI는 GitHub 호스팅 러너의 **localhost 실제 HTTP 통신**. Render 퍼블릭 URL, ChatGPT 앱 실제 도구 자동 선택/실행, OAuth/고정 API키 ChatGPT 인증은 **미검증·미연결**.
- 실험 코드/로컬 배포 준비 ZIP `ai-bot-mcp-render-free-staging.zip`, SHA256 `21c27ed9396d348414ae1e7c10bffbaa25ec6f8d2f17fe7dcd5a544ad99138dc`, 20개 엔트리. 관련 소스는 이미 동일 기능으로 GitHub 격리 브랜치에 커밋됨.

## 기존 보호
- 한국시간 매시간 정각의 기존 예약 AI R15 `6acb017062a08191a4136238b78b313a` 및 운영 Activepieces 플로우·연결·GitHub main 변경 0. 기존 개인 ChatGPT 플러그인 `plugins_6ad9d7b745448191bb087af817f02f68` v0.4.1 변경 0 (아직 실행기 코드를 원격 MCP로 직접 연결하지 않았음).
- 사용자의 최종 요구 '평소 ChatGPT 채팅하면 필요한 실제 봇 자동 실행'은 완결되지 않았다. 다음 필수 단계는 Render Free 계정 연결, 보안 비밀 수동 설정, 실제 HTTPS `/mcp` URL 반환 후 ChatGPT 사용 가능한 표면에서 연결·실제 자동선택 검증. 사용자 메시지의 **무조건적 전역 도구 호출은 ChatGPT 제품에서 보장하지 않는다**. 정규 R15 예약의 플랫폼 공식 개별 실행 로그도 계속 미검증.


## 2026-10-22 후속 운영 상태: 계정 연결 확인 및 생성 요청 차단

- Render 플러그인이 **사용자 연결 완료** 상태로 제공되어 `mcp__Render__list_workspaces`를 읽기 전용 호출했고, 계정의 단일 워크스페이스를 확인. 사용자 Render 사용량/잔액이나 Free 플랜 자격은 도구로 독립 확인하지 못함.
- `mcp__Render__create_web_service`에 `plan="free"`, `autoDeploy="no"`, 싱가포르 리전, 위 격리 브랜치, 환경변수 비밀을 포함하는 실제 생성 요청을 1회 보냈으나 **OpenAI 안전 검사에서 해당 도구 호출 차단**. 서비스 생성 성공 응답을 받지 못했다. 차단된 요청을 반복하거나 우회하지 않는다. 이후 읽기 전용 `list_services` 응답은 `null`이며 **실제 서비스 생성/배포 상태 미확인**, URL 추정 금지.
- **중요한 인증 설계 변경:** OpenAI 공식 인증 안내 `https://developers.openai.com/plugins/build/auth`에 따르면 ChatGPT는 커스텀 API 키나 client-credentials를 전달하지 못한다. 앱을 인증하려면 OAuth 2.1의 인증/리소스 서버와 토큰 검증, refresh token 메타데이터 등이 필요. **현재 코드의 고정 Bearer 키 방식은 ChatGPT 커스텀 MCP 연결에 곧바로 호환된다고 단정할 수 없으며, 보안 검사 후 무조건 배포할 대상이 아니다.** 관련 도움말 `https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt` 참고.
- ChatGPT 커스텀 MCP 서버 설정은 지원 계정에서 **웹 UI 전용**이며 iPhone 앱에서 연결 설정이 되지 않는다(연결 후 앱 내 사용 가능 여부는 별도). ChatGPT 플러그인의 자동 선택 또한 *관련성 조건부*이지 모든 메시지 강제 외부 실행 보장 아님.
- 후속 안전 작업: 인증 설계를 공식 OAuth 2.1로 바꿀지 검증하거나, 완전히 공개해도 되는 무상태 읽기 전용 도구만 별도의 안전 심사 후 분리. 그전까지 본 staging 서비스는 **배포 차단 / 로컬 격리 인증·실행 CI PASS**로 표시. Render 계정 인증·결제/권한, 운영 플로우, 예약 R15는 변경하지 않음.
