# 실제 OAuth IdP 연결 준비 — Auth0 (아직 미연결)

목표: ChatGPT가 관련 MCP 도구를 선택한 경우 실제 Python worker를 실행. 외부 로그인·배포 성공 주장 금지.
공식 문서: https://developers.openai.com/plugins/build/auth
Auth0 예시: https://github.com/openai/openai-mcpkit/tree/main/python-authenticated-mcp-server-scaffold
Auth0 resource 파라미터 호환: https://support.auth0.com/center/s/article/mcp-audience-error-with-auth0
Auth0 가격/무료 범위(계정별 재확인): https://auth0.com/pricing

## 안전한 연결 순서
1. Render 생성 안전 차단 우회 금지. 먼저 승인된 HTTPS 서버 호스팅 확보. 운영 main 및 R15 예약 그대로 유지.
2. 기존 계정 대신 격리된 Auth0 개발 테넌트 사용. 기능·무료 한도·계정 권한은 사용자 로그인으로 확인.
3. Auth0에 API Identifier를 실제 HTTPS MCP resource URL (서비스의 /mcp 포함)과 정확히 일치하도록 설정하고 ai:analyze scope를 구성.
4. Auth0 Tenant Settings > Advanced에서 Resource Parameter Compatibility Profile을 확인. ChatGPT의 resource 파라미터가 발급된 JWT audience로 들어오는지 실토큰으로 확인.
5. Auth0 authorization server 또는 OIDC discovery JSON에서 issuer 정확 일치, S256 PKCE, authorization/token HTTPS endpoints, CIMD 등록이나 DCR 지원 확인.
6. oauth_provider_preflight.py로 발견 문서의 정적 요건을 확인. METADATA_COMPATIBLE_ONLY 는 실제 로그인 성공이 아님.
7. ChatGPT MCP 연결 관리 화면의 정확한 CIMD URL/redirect URI를 Auth0에 등록. 사용자별 클라이언트·허용 API·scope 정책 확인. URL 추정 금지.
8. 허용 사용자 immutable sub를 AI_OAUTH_ALLOWED_SUBJECTS 환경변수에 넣는다. 한 사람의 opaque ID만 허용, 별표 허용 금지. 이메일/토큰/비밀키는 GitHub·Slack에 저장 금지.
9. AI_MCP_RESOURCE, AI_OAUTH_ISSUER, AI_OAUTH_JWKS_URI는 정확한 값으로 HTTPS 서버 환경에 설정. JWKS는 issuer와 동일 origin. 누락 또는 잘못된 설정이면 서버 부팅 거절.
10. 실제 승인된 HTTPS MCP 서버에서 401 challenge, RFC9728 discovery, 로그인+PKCE S256, JWT iss/aud/sub/exp/scope, MCP tools/list 및 tools/call 원본을 독립 검증.
11. ChatGPT는 관련성에 따라 도구를 선택할 수 있지만, 모든 메시지 강제 외부 실행은 보장되지 않는다.

## 검증 경계
로컬 JWKS mock 및 GitHub CI는 신원/토큰 검증 코드의 기능 증거일 뿐, Auth0 사용자 동의·프로덕션 로그인·ChatGPT 자동 도구 호출의 증거가 아니다.
운영 변경, 유료 모델 생성 호출, Render 재시도/우회 금지.
