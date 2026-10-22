# AI 예약 R15·채팅 자동 역할 선택 선호 — 2026-10-22 (KST)

## 사용자 최신 지시
- **기존 매시간 AI 예약**에 개인 플러그인 `ai-chat-bot-team v0.2.0`의 조사·개발·검증 총괄과 전문 역할 **TOP10**을 필요한 작업별로 자동 배정한다.
- **일반 ChatGPT 채팅**에서도 AI 프로젝트 개발·기억 복원·예약 감사·오류 수정·코드 검증·오픈소스 조사·자동화·보안/비용·GitHub·교차 검토·최적화 요청에 자동으로 적합한 스킬만 선택하는 방식을 선호한다. 사용자에게 매번 봇 이름이나 `@` 지정 요구 금지. 단순 인사/일반 질문에서는 불필요한 분업 금지.
- 결과는 **한국어 반말·결론 우선·간결한 직관적 그래프/상태표**. 확인된 성공/부분/차단/미검증 정확히 구별, 근거 없는 진행률 금지. **무료 우선·유료 생성 API 금지·보호된 시스템 보존**.
- 이 내용은 ChatGPT 제품 계정의 메모리 요약을 직접 편집한 결과가 아니라 **인증 GitHub 프로젝트의 외부 지속 기억**이다. 계정 메모리 자체는 제품에서 비동기 갱신되며 실제 표시·새 채팅 자동 주입 여부 별도 확인.

## 실제 예약 적용·독립 재조회
- 기존 예약 ID `6acb017062a08191a4136238b78b313a`, 제목 `AI`; 2026-10-22 **R14 → R15 지침 업데이트 성공**.
- 같은 ChatGPT 자동화 `automations.peek` 독립 조회: `is_enabled=true`, `Asia/Seoul`, `RRULE:FREQ=HOURLY;BYMINUTE=0;BYSECOND=0`, 기존 ID 동일. 일정·활성·시간대·알림 설정 변경 없음. 새 예약 생성·중지·삭제 없음.
- R15에는 기존 인계 우선 GitHub 읽기, Slack 스레드, 정규 회차 공식 ID 출처 규칙, 안전·무료·운영 보호, 기록 중복 방지, 샘플 CI를 무인 성공으로 오인하지 않는 규칙 유지.
- 기존 우선순위 **①기억 복원 원본 검증 ②무인 저장 원본 증거 ③AI 전문 협업** 유지. 무인 동일 회차 성공은 공식 플랫폼 ID와 해당 원시 GitHub/Slack 호출 로그 없이 `미검증`.

## 자동 선택 가능한 10개 전문 역할
1. `ai-memory-recovery` 기억 복원
2. `ai-scheduled-audit` 예약 감사
3. `ai-auto-debug` 자동 디버깅
4. `ai-code-verification` 코드·CI 검증
5. `ai-open-source-research` 공식·오픈소스 조사
6. `ai-automation-design` Activepieces 설계
7. `ai-cost-security` 비용·보안
8. `ai-github-management` GitHub 관리
9. `ai-cross-model-review` 교차 검토(실제 연결/무료 quota 검증 시에만 모델 생성 호출)
10. `ai-optimization` 토큰·품질 최적화

- 개인 플러그인 URL: https://chatgpt.com/plugins/plugins_6ad9d7b745448191bb087af817f02f68
- 실제 현재 릴리스 `pluginrel_6ad9dbfa566481919a519546cbefa921`, version `0.2.0`. 파일 목록의 총괄 1 + 전문 10 스킬 확인. 여러 스킬의 `agents/openai.yaml`에서 `allow_implicit_invocation: true`, `products: [CHAT]` 직접 읽음.
- GitHub 10역할 오프라인 CI [run 39758491085](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39758491085) 43/43 통과는 **샘플 코드 검증**이고 실제 독립 LLM 10개의 협업 실행이나 일반 채팅의 자동 호출 증거는 아님.

## 검증 경계와 다음 검증
- R15 프롬프트에 전문 역할을 자동 분담하도록 지시한 **설정 적용 완료**. 새 일반 채팅에서 해당 스킬의 실시간 자동 로딩/실제 실행은 현재 환경에서 **미검증**; 기술적 지원·권한·모델 라우팅에 따라 달라진다. 호출되지 않으면 동일 절차를 지침으로 수행하고 플러그인 실행이라고 주장 금지.
- 기존 Activepieces 운영 플로우/연결 및 `main` 변경 없음. 이번 작업에서 유료 외부 생성 API/결제/업그레이드 없음.
- 다음 R15 정규 실행에서 도구가 제공하는 동일 회차의 **실제 호출·실행 원본** 확인. `last_run_time`만으로 무인 10봇 성공을 주장하지 않는다. 계정 메모리 요약이 자동 갱신되었는지도 별도 확인해야 한다.
