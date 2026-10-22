# AI 봇 3개 협력 — 격리형 무료 PoC (2026-10-22 KST)

## 이번 사용자 직접 요청
'AI bot 만들어서 협력 가능?' → '그렇게 해봐.' 사용자 요청으로 기존 AI 프로젝트의 조사·개발·검증 **3개 역할 봇을 별도 테스트 브랜치에 구현**함.

## 실제 구현과 실행 증거
- 저장소: https://github.com/watersun79-source/ai-token-optimization
- 격리 브랜치: `ai/bot-team-sandbox-2026-10-22`; 본 작업에서 `main`, 기존 예약/운영 Activepieces 플로우 설정 변경 없음.
- 구현: `experiments/ai-bot-team/bot_team.py`, `tests/test_bot_team.py`, `examples/sources.json`, `README.md` (각각 디렉터리 앞에 `experiments/ai-bot-team/`).
- 파일별 Git blob SHA 독립 재조회: `bot_team.py` `94ba924c0bfc6b21b08474c1a58704ea6346a80a`; `tests/test_bot_team.py` `f6e26ced494ce5997853774f0f8391efd110b5d5`; `examples/sources.json` `8425be1b2578cda95c8f0d5db440e28f94d2dea2`; `README.md` `5461b83b4457bcdd381568df9ac1683d71d66d2a`. 모두 로컬 소스 Git blob SHA와 일치.
- 로컬 명령 `python3 -m unittest discover -s tests -v`: **15/15 OK**. 로컬 CLI 샘플 실행 시 `verifier.status=PASS`, 안전 정책 조건 **7/7** 통과.
- 독립 원격 CI: [GitHub Actions run 39754406104](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39754406104), job `119742664956`, `completed/success`. 원본 job 로그 `Ran 15 tests in 0.096s`; 무공급자 호출 샘플 단계 success.
- GitHub 워크플로 `.github/workflows/ai-bot-team-sandbox.yml`: 새 격리 브랜치 push / 수동 실행 전용, `contents: read`, 외부 공급자 API 무호출.

## 안전·비용·검증 경계
- 모든 봇은 **실제 실행되는 Python의 독립 3개 역할**이나, **현재 LLM 추론/외부 실시간 조사/코드 생성 에이전트는 아님**. 정확한 모드 `offline_deterministic_demo`, 공급자 생성 API 호출 **0**, 운영 변경 **0**, 로컬 외부 의존성 **0**.
- ResearchBot은 공급된 메타데이터만 읽고 실제 웹을 탐색하거나 주장의 사실성을 입증하지 않음. BuilderBot은 안전한 검토 계획만 작성하고 코드 수정/운영 배포 없음. VerifierBot은 구조·출처 연결·안전 정책만 검사. `PASS`는 **PoC 정책 회귀 합격**이고 실제 AI 품질, 무인 예약 복원, Activepieces 운영 성공이 아님.
- Activepieces 연결 5개(이름만) 및 기존 플로우 11개 읽기: 기존 `AI 3AI 협업`과 `Gemini + Claude 협업 비서` 모두 DISABLED 유지; 운영 활성 Slack webhook 1개 유지. 실제 무료/과금 한도 미확인으로 OpenAI/Gemini/Claude 생성 API 실행 0.
- 참고: [Python concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html), [LangGraph](https://github.com/langchain-ai/langgraph). 외부 패키지 설치/코드 복제 없음.

## 다음 목표
1. 운영 기록의 직접 연결과 별개로, **검증 가능한 무료 로컬 LLM 또는 검증된 무료 소비자/호출 경로**를 1개 확인해 별도 샌드박스의 역할 중 하나에 한정 연동.
2. 모델 생성 결과를 `VerifierBot`으로 반드시 사후 검증하고 부정합/차단 케이스 검증.
3. 유료 결제/자동충전/비밀키 공개 금지. 기존 ChatGPT AI 예약 `6acb017062a08191a4136238b78b313a` 활성/매시간 Asia/Seoul 보존; 정규 무인 성공은 공식 run ID와 원본 로그 없으므로 미검증.
