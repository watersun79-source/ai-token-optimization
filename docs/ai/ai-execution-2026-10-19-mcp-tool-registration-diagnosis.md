# AI 실행 기록 — 2026-10-19 MCP 도구 등록 진단

- 상태: 부분 완료
- 작업 브랜치: `ai/continuation-readonly-audit-2026-10-18`
- 목표: `ap_set_project_context` 누락을 공식 소스 코드와 공개 문서로 진단
- 비용 정책: 공급자 API 0회, 유료 API 0회, 구매/업그레이드 0건

## 실제 확인한 증거

1. Activepieces 공식 도구 문서에 `ap_set_project_context`가 계속 문서화되어 있음:
   https://www.activepieces.com/docs/mcp/tools
2. 공식 GitHub 소스 `packages/server/api/src/app/mcp/tools/ap-set-project-context.ts`에서 `SET_PROJECT_CONTEXT_TOOL_NAME = 'ap_set_project_context'` 및 도구 구현을 확인함:
   https://github.com/activepieces/activepieces/blob/main/packages/server/api/src/app/mcp/tools/ap-set-project-context.ts
3. `packages/server/api/src/app/mcp/mcp-server-builder.ts`에서 조건부 등록 분기를 확인함:
   - `mcp.projectId`가 있으면 프로젝트 범위 flow/static 도구를 등록하는 분기로 들어감.
   - `mcp.projectId`가 없고 `platformId`, `userId`, `resolveProjectMcp`가 있으면 `registerPlatformTools`를 통해 `ap_set_project_context`를 등록함.
   - 그 외에는 placeholder 도구를 등록함.
   소스: https://github.com/activepieces/activepieces/blob/main/packages/server/api/src/app/mcp/mcp-server-builder.ts
4. 따라서 문서와 소스상 도구 자체가 제거됐다는 증거는 없음. 다만 서버의 실제 런타임 설정과 ChatGPT가 받은 `tools/list`를 직접 비교하지 않았으므로, 사용자의 연결이 어떤 분기로 구성됐는지는 미확인.
5. 공식 최신 릴리스 페이지에서 당시 표시된 최신 태그는 0.92.3이었음. 사용자의 서버 버전은 미확인:
   https://github.com/activepieces/activepieces/releases

## 이슈 제출 시도

- `activepieces/activepieces`에 GitHub 이슈 생성 시도.
- 결과: HTTP 403 `Resource not accessible by integration`.
- 이슈 URL/번호는 생성되지 않음. 성공했다고 주장하지 않음.
- 연결 브라우저 조회는 originating browser context 오류로 실패.
- 공식 저장소에 대한 쓰기 권한이 없으므로, 공개 이슈 대신 사용자의 개인 저장소에 잘못된 이슈를 만들지 않음.

## 안전 범위 및 비용

- 프로젝트 ID 추측: 없음.
- Activepieces 프로젝트 범위 도구 호출: 0회.
- 운영 플로우/연결/테이블/자격 증명/기존 정각 자동화/main 변경: 0건.
- 공급자 생성 API 및 유료 API 호출: 0회.
- 구매/업그레이드: 0건.
- 테스트/플로우 실행: 0회.

## 다음 목표

1. 연결이 platform-level MCP인지 project-scoped MCP인지 확인할 수 있는 비밀값 없는 구성 정보만 확보.
2. 서버가 제공한 도구 이름 목록과 ChatGPT에 노출된 도구 이름 목록을 비교. 인증 헤더/토큰은 공유하지 않음.
3. 기존 ChatGPT 연결의 도구 목록 새로고침을 지원하는 공식 UI가 해당 워크스페이스에 있는지 확인; 중복 연결 생성은 하지 않음.
4. 이슈 제출은 현재 GitHub integration의 403 권한 제한 때문에 미완료. 권한이 있는 공식 지원 채널을 통해 제출한 뒤 URL과 응답을 검증.
