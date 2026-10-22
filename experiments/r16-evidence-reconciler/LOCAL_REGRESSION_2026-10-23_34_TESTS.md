# AI R16 — 증거 검사기 16건 상한 결함 수정 및 회귀 결과 (2026-10-23, 수동 채팅)

## 재현과 수정
- 발견: `audit_v2.py`에서 `len(tool_calls)>16`이면 모든 공식 도구 호출이 올바르게 기록되어도 무조건 `미검증`으로 판정하는 false-negative. 전체 scheduler raw tool-call ledger는 16건보다 클 수 있음.
- 격리 브랜치에서 1,024건까지 허용하고 초과분에 대해 보수적으로 `미검증` 처리하도록 최소 변경. 1,024는 합리적인 유한 방어 상한이지 ChatGPT 공식 한도라는 뜻은 아님.
- 감사 원칙 불변: `official_success_verified=false`, 공급자가 제공한 공식 native run ID / 도구 호출 원본이 없으면 무인 성공은 미검증. CLI 단순 형식 통과는 예약 성공의 증거가 아님.

## GitHub 원본
- 브랜치: `ai/r16-evidence-reconciler-2026-10-22` (GitHub main 변경 없음).
- 코드 수정 커밋: `f46d4a7b0c2de3b28f033f241f26039cea2698a5`, 원격 Blob: `21a716f3093bed229b5d0f366709d08d55ab8abe`.
- 테스트 수정 커밋: `1c74f2321cf1c3d2f663760af9e23869aa5188b0`, 원격 Blob: `4c5834ee0e872bb9758a438a63ce689d5691677d`.
- unchanged tool alias tests blob: `6e1623d0797473a34cdd21b0292095c40d45cb09`.
- 위 3개 소스가 로컬 `git hash-object` 값과 각자 동일함을 확인.

## 실제 무료 로컬 실행
```text
$ cd /mnt/data/r16_test
$ python3 -m unittest discover -s tests -v
Ran 34 tests in 0.003s

OK
```
- 34/34 통과. 이전 32건 외 **17개·1,024개 공식 호출 형식은 PASS** (단 진위 미검증), **1,025개는 보수적으로 거부** 회귀 포함.
- Python test는 **수동 격리 테스트**이며 예약의 실제 무인 실행 근거가 아님.
- 새 테스트 커밋에 대한 GitHub PR-triggered workflow runs 조회 `[]`와 combined statuses `[]`: 원격 CI 성공/실패 모두 미검증.
- Gemini/Claude/유료 API 호출 없음; main·예약·Activepieces 운영 플로우·알림 변경 없음.

## 07시대 예약 일시정지 이력 및 현재 증거
- 기존 인계 문서에 10/23 07:11 KST 단일 R16 예약의 일시정지 발견, 07:12 활성 복구가 원본 예약 상태 대조로 기록됨. 이번 수동 검사에서는 `automations.peek`에서 `is_enabled=true`, `paused_count=0` 재확인.
- 공식 OpenAI 문서는 승인 대기, 비활성 상태, 원본 채팅 보관/삭제가 일시정지의 가능한 이유로 설명하나, **이번 원인은 공식 개별 회차 상세 및 승인/감사 로그가 없어 확정 불가**.
- Activepieces `AI Scheduled Run Evidence (AUDIT ONLY)` 테이블의 `2026-10-23` 슬롯은 재조회 시 0건. 반드시 무인 성공 미검증.
- 다음 목표: 사용자 Scheduled → 기존 R16 → Previous runs/승인 대기에서 실제 플랫폼 실행 레코드가 있는지 확인. 예약 ID, last_run_time, GitHub SHA, Slack 메시지, Activepieces TESTING ID를 공식 개별 회차 ID로 대체하지 않음.
