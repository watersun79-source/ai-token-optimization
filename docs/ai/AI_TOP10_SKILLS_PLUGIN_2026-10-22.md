# AI TOP10 전문 스킬 실제 설치·샘플 실행 기록 (2026-10-22 KST)

## 결론 및 범위
사용자의 "모두다 설치 실행" 지시로 **기존 개인 플러그인을 중복 생성하지 않고** `ai-chat-bot-team` 릴리스 `0.1.0 → 0.2.0` 갱신. 원래 총괄 3역할 스킬 1개를 유지하고 **TOP10 전문 스킬 10개**를 같은 플러그인에 실제 업로드·저장·파일 목록 독립 재조회 완료. TOP10은 ChatGPT 대화 작업을 위한 **스킬/역할**이며 독립된 AI 모델 10개나 상시 실행 10개 프로세스는 아님.

## 계정 설치 증거
- 플러그인: https://chatgpt.com/plugins/plugins_6ad9d7b745448191bb087af817f02f68
- 정확한 백엔드 ID `plugins_6ad9d7b745448191bb087af817f02f68`
- 새 개인 릴리스 `pluginrel_6ad9dbfa566481919a519546cbefa921`, `version=0.2.0`, `PRIVATE`, 사용자 기존 plugin ID 그대로
- 새 릴리스의 `get_plugin_files` 읽기 결과 총 32개 파일, `skills/*/SKILL.md` 11개(기존 총괄 1개 + 아래 전문 10개), 기존 `bot_team.py`·`chat_router.py` 모두 유지 확인, 전문 스킬 파일 일부 원본 내용과 패키지 메타데이터 재조회 완료.
- TOP10 스킬: `ai-memory-recovery`, `ai-scheduled-audit`, `ai-auto-debug`, `ai-code-verification`, `ai-open-source-research`, `ai-automation-design`, `ai-cost-security`, `ai-github-management`, `ai-cross-model-review`, `ai-optimization`.
- 패키지 SHA-256 `79de281da9261a160226797bb14fd26634a805373fe746e200c9aa24434c7b21`. 변경 패치 ZIP 26개 파일로 버전 업데이트 후 read-back.
- 중요한 **미검증**: 현재 이미 열린 채팅에서 `skills__list`는 기존 총괄 스킬 1개만 노출했으며 새 전문 스킬을 직접 `skills__read`로 호출 시 resource not found. 계정 저장 성공과 별도로 새 채팅 자동 디스패치 및 10개 스킬의 ChatGPT 런타임 호출 검증은 미완료. 새 대화/설치 UI 및 실제 호출 증거를 확인해야 함.

## 실제 무비용 실행 및 원격 CI
- 플러그인 동봉 코드 `skills/ai-chat-collaboration/runtime/specialist_team.py`는 데이터 제공형 **오프라인 검사** 10역할을 `--role all`로 동시 최대 4작업 수행. 각 검사는 구체적인 단위 변환(입력 SHA, JSON 정책, AST 구문, 단계 의존성, 비밀 패턴, 중복 분석 등)만 수행하고 외부 모델·GitHub·Slack·Activepieces 호출 없음.
- 기존 코드와 신규 코드 포함 로컬 `python -m unittest discover -s runtime/tests -v` **43/43 통과**, 10개 역할 일괄 실행 종료 코드 0.
- 격리 브랜치 [ai/top10-role-sandbox-2026-10-22](https://github.com/watersun79-source/ai-token-optimization/tree/ai/top10-role-sandbox-2026-10-22/experiments/ai-bot-team)에 `specialist_team.py`와 `tests/test_specialist_team.py` 저장.
- Git blob 독립 재조회: 코드 `7115925e1e3f5cfe25fbb411a9b2db3d622ce2fa`, 신규 테스트 `0c1740d53e83ae4236c75288908d7f2cc5ef1a12`. 계정 플러그인 `get_plugin_files` 원본 본문과 GitHub 원본 **문자열 전체 일치**.
- 새로운 비운영 GitHub Actions: [run 39758491085](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39758491085) `completed/success`, job `119756455084`, 실제 원본 로그 `Ran 43 tests in 0.209s`, 10역할 실행 단계 success. 이 원격 CI는 코드 검사 성공이며 ChatGPT 정규 예약/실제 독립 LLM 모델 실행 성공이 아님.

## 기존 시스템 보호
- 원래 AI 예약 ID `6acb017062a08191a4136238b78b313a` R14 지침, `Asia/Seoul` 매시간 정각, 활성화, 알림 설정 유지. **예약 update/create/disable/delete 이번 작업 0건**. 기존 R14는 동일 개인 플러그인 ID 참조를 유지하므로 향후 플러그인이 런타임에서 제공되면 새로운 전문 역할을 선택할 수 있으나 무인 호출 **미검증**.
- 기존 Activepieces 운영 플로우·연결·인증/비밀키 및 GitHub `main` 변경·게시·재활성화 0건. 생성 API/유료 API/결제/자동충전/키 출력 0.
- 일반 채팅/정규 회차의 플러그인 자동 선택과 계정 UI 설치 전파는 이번 도구에서 독립 입증되지 않았음. 플러그인 스킬은 지속 실행 자동화가 아니며 매 시간 10개 병렬 실행을 약속하지 않음.

## 다음 목표
- 새 ChatGPT 대화에서 플러그인 새 릴리스 v0.2의 실제 표시/개별 스킬 자동·명시 호출을 확인.
- 요구사항/도구 허용 범위 안에서 연결된 GitHub·Slack의 실제 증거를 해당 전문 스킬에 연결하고, 검증된 공급자 무료 quota 없이는 외부 Gemini·Claude 생성 API를 호출하지 않음.
- 정규 R14 회차의 플랫폼 공식 run ID+같은 회차의 원본 GitHub/Slack 로그가 확보되기 전까지 **무인 성공 미검증** 유지.
