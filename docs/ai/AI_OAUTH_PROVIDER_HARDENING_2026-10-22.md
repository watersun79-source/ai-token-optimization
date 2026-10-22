# AI OAuth 실제 봇 연결 준비: 사용자 제한·제공자 검사 (2026-10-22)

## 이번 작업 완료
- 사용자 요청 '진행'에 따라 새 격리 GitHub branch ai/oauth-provider-readiness-2026-10-22 생성. 기존 ai/oauth-mcp-test-2026-10-22를 기반으로, **실제 외부 OAuth 제공자/ChatGPT 앱에 연결했다고 주장하지 않음**.
- oauth_mcp.py: AI_OAUTH_ALLOWED_SUBJECTS (실제 인증 제공자에서 부여한 변경되지 않는 opaque sub 목록, 1-12개, 별표 불가)을 필수화; 인증되더라도 sub가 등록되지 않은 타인 토큰은 MCP 호출 금지. JWKS URL이 발급자 issuer와 동일 HTTPS origin인지 확인, 비정상 JWT 길이 상한 8192, 누락 설정 차단.
- verify_oauth_mcp.py: 기존 만료·서명 위조·권한 부족 등 6가지 무효 토큰에 **실제 서명돼 있지만 허용되지 않은 타인 sub** 테스트를 추가해 총 7종 차단 확인. 정상 토큰으로 실제 localhost MCP initialize/list_tools/call_tool(delegate_message), Python worker DONE 확인.
- oauth_provider_preflight.py: OpenAI 플러그인의 정확한 issuer / HTTPS authorization+token endpoints / S256 PKCE / CIMD-DCR-등록된 client 방식과 scope 광고 등을 **제공자 discovery JSON만으로 정적 검토**. 정상 결과도 METADATA_COMPATIBLE_ONLY로 표기하고 실제 로그인·ChatGPT 연결·resource-to-audience 성공을 결코 보장하지 않음.
- tests/test_oauth_config.py 및 tests/test_oauth_provider_preflight.py 신규·강화 사례. 설정 URL loop 검사에서 한 차례 회귀 실패한 오류를 URL 필드만 확인하도록 최소 수정 후 재시험 성공.
- README-AUTH0-OAUTH-PROVIDER.md: 인증 제공자 선택/정확한 audience 일치·ChatGPT가 표시한 CIMD URL/redirect URI·개인 sub 허용목록·실호스팅 확인 절차 문서화.

## 원격 CI 직접 증거
- 최종 https://github.com/watersun79-source/ai-token-optimization/actions/runs/39773996781 ; completed/success, head 7b36e3b25c62a01a39f06fb03c3395cd57b0c0d4, job 119808243945.
- job 원본: oauth_mcp_resource_server PASS, rfc9728 PASS, invalid_token_cases 7, real_worker DONE, Ran 109 tests, OK, OWNER_FAIL_CLOSED PASS.
- 초기 새 테스트 run 39773483192는 FAIL (URL 아닌 AI_OAUTH_ALLOWED_SUBJECTS 설정을 URL용 검사에 넣었던 회귀 테스트 코드 오류); 수정 후 성공한 run 39773647693, 39773796735, 최종 문서 반영 후 run 39773996781까지 PASS.
- 원본 GitHub blob SHA 직접 재조회: oauth_mcp.py 3de9515f78e8653440bc43c8458c5117ba5a5ff2; verify_oauth_mcp.py 97bb39ffa4b377d0970a11caf4704dcde730baa6; oauth_provider_preflight.py 2ffe3d86d5e4d2eccc7fab0dcf8abc23f89ac710; tests/test_oauth_provider_preflight.py 942a86b94466258000eab1875f5b23e739bc7428.

## 공식 근거, 외부 공급자 준비
- https://developers.openai.com/plugins/build/auth (OAuth PKCE S256, ChatGPT CIMD/DCR/client, resource parameter 정확한 audience 보증, callback URL 관리).
- https://github.com/openai/openai-mcpkit/tree/main/python-authenticated-mcp-server-scaffold (Auth0 CIMD import/config 공식 예제).
- https://support.auth0.com/center/s/article/mcp-audience-error-with-auth0 (Auth0 Resource Parameter Compatibility Profile 설정 필요 시 실패).
- https://auth0.com/pricing (무료 플랜 예시; 실제 무료 한도·특수 기능/승인 여부 계정에서 독립 확인 전 과금 금지).
- ChatGPT 전체 메시지 외부 도구 무조건 실행 후킹은 지원이 보장되지 않음. 실제 외부 IdP가 발급한 토큰/승인, HTTPS 서버 배포, ChatGPT 사용 계정의 플러그인 MCP 도구 연결 및 실제 원본 호출은 아직 미검증.
- Plugin Management에서 Auth0 앱 검색 시 이 시점 제공되는 연결 앱 결과 없음. Auth0 계정·테넌트/사용자 승인 확보되지 않아 외부 환경변수를 추정하거나 등록하지 않음.

## 변경 금지 유지
- 기존 개인 ChatGPT skill-only 플러그인 v0.4.1 그대로. 별도 운영 Activepieces 플로우·GitHub main·기존 매시간 한국시간 정각 예약 AI R15 ID 6acb017062a08191a4136238b78b313a 미변경, 정지·중복 생성 없음.
- Render create_web_service는 직전 안전 검사에서 차단됐으므로 이번 회차 다시 호출/다른 경로 우회하지 않음. 무료/유료 실제 외부 서버 배포 없음. 외부 독립 Gemini/Claude 유료 생성 호출 0, 결제 0, 비밀 키 노출 없음.

## 다음 실제 장애물
인증된 외부 OAuth 제공자 개발 테넌트와 승인된 HTTPS 서버 호스팅 확보가 필요. 실제 issuer/JWKS/aud/PCKE 및 허용 sub 연결, ChatGPT MCP 도구 목록과 실제 call 로그 재조회 전에는 최종 자동 실행 성공이라고 판정 금지.