# AI 실행 기록 — 2026-10-19 MCP 새로고침 UI 조사

- 상태: UI 접근 차단; 공식 경로 조사 완료
- 이어받은 기록: [현재 읽기 전용 재점검](https://github.com/watersun79-source/ai-token-optimization/blob/ai/continuation-readonly-audit-2026-10-18/docs/ai/ai-execution-2026-10-19-current-readonly-recheck.md)

## 실제 시도
- CUA에서 연결된 브라우저 목록을 조회함. Chrome/Edge 확장 브라우저는 탭이 없었고 request-header policy를 불러오지 못하는 오류로 탭 재조회도 실패함.
- 별도 Codex in-app browser에서 chatgpt.com을 열어 읽기 전용 상태를 확인함. 로그인 화면이 표시되어 연결 관리 설정에 접근할 수 없었음. 계정 로그인이나 인증값 입력은 시도하지 않음.
- 현재 세션의 도구 목록에는 Activepieces 도구가 있지만, MCP 연결 관리 UI나 도구 목록 새로고침용 도구는 노출되어 있지 않음. `ap_set_project_context`를 찾거나 호출하지 않음.

## OpenAI 공식 안내
- [Connecting custom MCP servers in ChatGPT](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt)는 Business 및 Enterprise/Edu에서 기존 custom MCP 도구 목록을 Workspace settings의 Apps 설정으로부터 새로고침할 수 있다고 안내함.
- 새로고침에는 앱 관리 권한과 유효한 연결이 필요함. Enterprise/Edu에서는 Workspace settings → Apps의 Action control 메뉴에서 Refresh를 사용할 수 있다고 설명함.
- 현재 계정/워크스페이스 유형, 사용자의 앱 관리 권한, Activepieces 연결의 유효성은 이 세션에서 확인되지 않음.

## 비용 및 변경
- Activepieces 프로젝트 범위 호출, 플로우 실행/테스트/변경: 0.
- 공급자 API/유료 API 호출, 구매/업그레이드: 0.
- 새 연결 생성, 로그인, 자격 증명 입력, 기존 연결 설정 변경: 0.
- 코드 테스트/ID 없음.

## 다음 목표
- 사용자가 이미 로그인된 ChatGPT 웹 워크스페이스의 Settings → Apps(또는 Workspace settings → Apps)에서 기존 Activepieces 연결이 보이는지, 해당 앱에 Refresh/Scan Tools 작업이 있는지 확인한다. 앱 관리 권한과 연결 상태가 충족될 때에만 기존 연결의 도구 목록을 새로고침한다.
- 새로고침이 완료되어 실제 도구 카탈로그에 변경이 보인 뒤 도구 목록을 다시 확인한다. 그 전까지 Activepieces 프로젝트 범위 작업은 중단 상태로 둔다.
