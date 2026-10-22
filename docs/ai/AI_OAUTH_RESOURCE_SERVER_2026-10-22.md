# OAuth 기반 실제 Python 봇 연결 — 격리 검증 기록 (2026-10-22)

## 결론
기존 AI 봇 게이트웨이에 OAuth 2.1 보호 MCP 리소스 서버와 서명 토큰 검증 코드를 별도 격리 브랜치에서 구현·원격 테스트했다. 실제 공개 배포·외부 OAuth 로그인 승인·ChatGPT iPhone 일반 메시지 자동 외부 도구 호출은 미연결·미검증. 과거 Render 서비스 생성 요청 보안 차단은 재시도하지 않았다.

## 구현
- GitHub 원본 branch: ai/oauth-mcp-test-2026-10-22; source experiments/ai-bot-team/oauth_mcp.py (blob c4ffe7fcf8f38dce5c11e43b915b994293060467).
- MCP SDK v1 FastMCP Resource Server: 기존 delegate_message가 Python 실제 워커를 호출하되 Github 쓰기·외부 LLM API 없음.
- 운영 필수 환경: AI_MCP_RESOURCE (HTTPS /mcp), AI_OAUTH_ISSUER (공식 OAuth 발급자), AI_OAUTH_JWKS_URI (발급자의 서명 공개키). 셋 중 하나라도 누락되면 실행 금지. CI의 로컬 mock 모드는 localhost로만 제한.
- RSA RS256 서명, issuer, audience/resource, exp/nbf/iat, sub, client_id, scope ai:analyze 검증. 로그인/동의/PKCE 토큰 발행은 외부 Identity Provider 책임.
- MCP Python SDK 공식 RFC9728 resource metadata, WWW-Authenticate 401 응답 사용. 구성 원본 test_oauth_config.py, verify_oauth_mcp.py.

## 원격 시험 원본
- 첫 CI Actions run 39771178612 FAILED: 서버가 AS issuer 끝에 /를 붙이는 유효한 RFC9728 응답을 테스트에서 과잉 비교. 검사 문자열 비교만 수정, 운영 코드 변경 없음.
- 최종 Github CI https://github.com/watersun79-source/ai-token-optimization/actions/runs/39771301619 : completed/success, head bdc852fd9697f65dc2ec3396bbe8e7859dce1760, job 119799232398.
- job 로그: oauth_mcp_resource_server PASS; rfc9728 PASS; invalid_token_cases 6; real_worker DONE; 전체 테스트 98/98 PASS; OAUTH_FAIL_CLOSED_NO_PROVIDER PASS.
- 중요한 비검증: oauth_login_pkce NOT_TESTED, chatgpt_connected=false. 이는 mock JWKS·임시 RSA 키로 통신한 테스트이며 외부 사용자 인증/플러그인 채팅 자동 실행 증거가 아님.

## 공식 자료
- https://developers.openai.com/plugins/build/auth
- https://py.sdk.modelcontextprotocol.io/run/authorization/
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/authorization/index.mdx
- 참고: OpenAI 플러그인 선언 문서 https://developers.openai.com/plugins/build/plugins 에는 api_key 방법도 존재. 계정에서 실제 이용 가능한 방식과 고정 키가 자동 전달되는지 여부는 별도 검증 대상이므로 'API key 방식이 모두 불가능하다'는 이전 단정은 부정확함.

## 기존 시스템 보호 및 다음 단계
- 기존 ChatGPT AI 개인 플러그인 v0.4.1 유지; 새 OAuth 서버 코드는 아직 호스팅·연결되지 않은 격리 실험. 기존 R15 예약 ID 6acb017062a08191a4136238b78b313a, 매시간 정각, Activepieces 운영 플로우·연결, GitHub main 미변경.
- 외부 유료 생성 API, 결제, 배포, 사용자 인증키 기록 없음. 독립 Gemini/Claude 모델 실제 협력 미구현.
- 다음 단계는 실제 외부 OAuth 2.1 제공자 (issuer·JWKS·PKCE·CIMD/DCR) 연결, audience를 실제 HTTPS /mcp와 일치시킨 토큰 발급, 안전하게 승인된 호스팅 및 ChatGPT 도구 호출 로그로 검증. 안전 차단된 Render 생성 요청의 우회 재시도 금지.