# 일반 ChatGPT 채팅에서 필요 봇 자동 선택 — v0.3.0 (2026-10-22)

## 사용자 의도와 실제 완료
사용자 요청은 "평소처럼 채팅만 해도 ChatGPT가 의미를 분석하고 필요한 봇이 자동 선택"되는 것이다. 현 ChatGPT가 지원하는 범위에서 기존 개인용 플러그인 **AI 3봇 협업 / ai-chat-bot-team** 을 v0.2.0에서 **v0.3.0**으로 갱신했다. **일반 채팅 전체에 반드시 발동하는 플랫폼 전역 훅은 만들 수 없으며, 실제 자동 호출은 플랫폼의 관련성 판단에 따름.** 외부 Gemini·Claude 독립 모델 10개가 자동 호출되는 방식이 아니다.

## 계정 플러그인 적용 및 증거
- 개인 플러그인 URL https://chatgpt.com/plugins/plugins_6ad9d7b745448191bb087af817f02f68
- plugin_id `plugins_6ad9d7b745448191bb087af817f02f68`, 기존 플러그인을 제자리 업데이트
- version `0.3.0`, release `pluginrel_6ad9e14dcab88191867dd0c0229f9ffd`, 이전 TOP10 스킬 10개 + 총괄 1개 전부 보존
- `skills/ai-chat-collaboration/SKILL.md`의 자동 작업 분류와 불필요한 봇 호출 방지 규칙 강화. `runtime/auto_dispatch.py` / `runtime/tests/test_auto_dispatch.py` 추가. `references/USER_GUIDE_KO.md` 갱신. 기존 직접 호출 지침·오프라인 코드 그대로 보존.
- `get_plugin_files` 독립 재조회: 전체 파일 **34개**, 수정된 5개 코드·스킬 파일 접근 확인, 기존 전문 스킬 10개 유지. 플러그인 patch ZIP SHA-256 `476661b317c701c30b803f209a98fb31efde7b0cc6c680fbf100ee1e53ab83b2`.
- ChatGPT 공식 문서 https://help.openai.com/ko-kr/articles/20001256-plugins-in-chatgpt : 설치된 관련 플러그인은 자동 사용 가능, `@` 멘션으로 수동 선택 가능. 사용 가능 여부는 계정·제품·권한에 따라 다름.

## 구현·테스트 증거
- 10개 전문 역할로 라우팅하는 오프라인 **키워드 샘플**. `에러 고쳐` → `ai-auto-debug`, `예약 AI 정규 회차 검증` → `ai-scheduled-audit`, `CI 확인` → `ai-code-verification`, `토큰 최적화` → `ai-optimization`, `오늘 날씨` → 직접 응답.
- 복합 요청은 최대 3개 전문 역할만 선택. 유료/삭제/운영 영향 검토 필요 여부 표시. API 호출 0, 운영 변경 0. 실제 ChatGPT 대화 자동 후킹은 미구현, 외부 모델 호출·과금 0.
- 기존 TOP10 검증 + 신규 라우터 로컬 회귀 **64/64 PASS**, 변경분 저장 경로는 격리 브랜치 `ai/top10-role-sandbox-2026-10-22` 내 `experiments/ai-bot-team/auto_dispatch.py` 및 `tests/test_auto_dispatch.py`.
- GitHub 원격 Actions [run 39761352875](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39761352875): `completed/success`, job `119766031872`, 실제 테스트 로그 `Ran 64 tests in 0.194s\nOK`. 코드 blob `5b5df6898098efbdc190c6aa348267c2ffcb5489`, 테스트 blob `df989313ffea506129707b0380d810a61f6ab795`.
- 이러한 테스트는 샘플 코드의 분류/정책 검증이며 외부 플러그인 자동 호출이나 예약 회차 무인 협업 성공의 증거는 아니다.

## 보호 대상 및 다음 목표
- 기존 정규 예약 R15(`6acb017062a08191a4136238b78b313a`)의 프롬프트·시간·활성·알림 이번 변경 없음; R15에는 이미 TOP10 역할을 작업에 따라 자동 선택하는 지침이 들어 있었다.
- Activepieces 운영 플로우·연결, GitHub main, 비용·API·보안 설정 변경 없음. 외부 호출 0.
- **미검증:** 새로운 일반 ChatGPT 채팅에서 별도 `@` 멘션 없이 실제 `ai-chat-collaboration` 또는 전문 스킬 호출 여부, 기존 R15의 실제 정규 무인 원본 로그. 플랫폼에서는 성공한 호출에 대해 도구·스킬 선택을 관찰한 후에만 성공 판정한다.
- 새 채팅에서는 간단 질문을 바로 처리하고, 프로젝트 관련 복잡한 질문은 의도를 보고 필요한 역할만 선택. 플러그인이 자동 선택되지 않을 때는 `@AI 3봇 협업` 사용 가능.
