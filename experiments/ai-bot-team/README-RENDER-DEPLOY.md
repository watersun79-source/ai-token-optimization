# 배포 대기: Render Free MCP 봇 서버

현재 상태: **원격 배포 준비 코드 / 인증된 클라이언트 통신 검증**, **ChatGPT 앱 실제 자동 호출 미연결**. 기존 예약 R15, Activepieces 운영 플로우, GitHub main은 수정하지 않는다.

## 소스

- `remote_mcp.py`: Python MCP SDK 1.x를 사용한 인증 필수 Streamable HTTP `/mcp` 서버. 요청마다 Bearer 토큰 비교 후 기존 `real_gateway.py`의 제한된 Python 워커 실행, GitHub 쓰기와 유료 API 없음.
- `verify_remote_mcp.py`: 인증 없을 때 401, 잘못된 인증 때 401, 정상 인증 때 MCP initialize → tools/list → tools/call 실제 호출 검증.
- 저장소의 **격리 브랜치 루트** `render.yaml`: Render Free 서비스 템플릿. 운영 배포와 무관하며 자동 배포 OFF.

## 배포 (Render 계정 연결 및 사용자 직접 인증 필요)

1. Render 앱/계정을 연결하고 Render의 해당 시점 Free 플랜 잔량·결제 설정을 실제 확인.
2. GitHub `watersun79-source/ai-token-optimization`의 `ai/render-free-mcp-staging-2026-10-22` 브랜치의 루트 `render.yaml`을 Render Blueprint로 선택. 생성 전에 `plan: free`를 확인.
3. `AI_MCP_BEARER_TOKEN`을 **Render 웹 콘솔의 환경변수로만**, 길이 32자 이상 난수로 등록. ChatGPT 메시지·GitHub·Slack·CI 로그·플러그인 ZIP 안에 토큰을 붙여넣거나 저장하지 않는다. 누락 시 서버는 부팅 자체가 실패하도록 설계됨.
4. 서비스 시작 후 Render가 제공한 실제 `https://<render-service>.onrender.com/mcp`를 MCP 클라이언트에서 테스트. Render Free는 15분 비활성 시 절전할 수 있고 무료 시간·네트워크 사용량 한도가 있음.
5. **ChatGPT 사용 연결은 별개**: 연결 가능한 계정/제품과 API-key 방식 지원 여부를 실제 검증해야 함. 고정 Bearer 토큰만 제공하는 이 프로토타입은 **OAuth 로그인 서버를 구현하지 않는다**. OpenAI 공개 플러그인 제출 포털은 API-key 입력을 지원하지 않을 수 있으므로 실제 연결 전에는 성공이라고 말하지 않는다.

**인증 없이 공개 배포 금지.** MCP에 제공하는 사용자 메시지는 외부 호스팅 업체 서버를 거치므로 개인정보·비밀을 전송하기 전에 범위를 확인하라.
