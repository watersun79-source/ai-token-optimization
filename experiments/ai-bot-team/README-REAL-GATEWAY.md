# 실행 가능한 자동 봇 게이트웨이 (로컬)

LangGraph [라우터 패턴](https://docs.langchain.com/oss/python/langchain/multi-agent/router) 참고: 메시지 입력 -> 최대 3개 역할 선택 -> 실제 독립 Python 워커 함수 실행 -> 결과 통합. 소스는 표준 라이브러리만 사용하며 모델 추론을 호출하지 않는다.

## 실행

`python real_gateway.py --message "에러 고쳐" --code "print("`

`python real_gateway.py --serve --port 8765`

브라우저에서 `http://127.0.0.1:8765` 열고 메시지를 보내면 `/api/chat` 호출에서 **실제 파이썬 워커**가 실행된다. 이 브라우저는 ChatGPT 앱이 아니야. `--allow-github-read`는 외부로 GitHub 공개 REST GET만 허용하는 옵션이며 실패 시 BLOCKED다. 토큰이나 비밀키를 보내지 않는다. 서버는 로컬 루프백에만 바인딩.

## MCP

`pip install -r requirements-mcp.txt && python mcp_server.py`

이 명령은 실제 `delegate_message` MCP 도구를 로컬 스트리머블 HTTP로 제공한다. Python MCP SDK v1 버전을 고정했다. ChatGPT가 자동으로 모든 메시지에 이 툴을 붙이지 않는다. iOS/web 일반 채팅에서 도구를 사용하려면 **실제 HTTPS 호스팅 또는 공식 터널 + 앱 연결 + 권한**이 추가로 필요하다. 이 단계는 무료 호스팅·인증·제품별 지원 검증 전 미진행.

## 역할 능력

- 실기능: Python AST 구문검사(실행 금지), 비용·비밀 탐지, 중복 측정, 단계 초안, 승인된 읽기 전용 GitHub 메타데이터(옵션).
- 미연결: ChatGPT 공식 예약 회차 ID, 독립 Gemini·Claude 모델 생성, GitHub 쓰기, 외부 Activepieces 플로우 실행.
- 보고에서 BLOCKED/UNVERIFIED를 완료로 표현하지 말 것.
