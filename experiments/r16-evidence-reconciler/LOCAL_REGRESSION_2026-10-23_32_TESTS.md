# AI R16 — 원격 SHA 일치 로컬 Python 회귀 검증 (2026-10-23, 수동 채팅)

## 범위
- 격리 브랜치: `ai/r16-evidence-reconciler-2026-10-22`. GitHub `main`, ChatGPT 정규 예약, Activepieces 운영 플로우는 변경하지 않음.
- 이번 회차 **수동 로컬 Python 검증**이며 정규 ChatGPT 예약의 무인 실행 또는 원본 앱 호출 증거는 아님.
- 무료 Python 3.13.5, 표준 라이브러리 unittest, 외부 모델 호출 없음.

## 원본 GitHub blob 검증
| 파일 | GitHub fetch_file 반환 SHA | 로컬 git hash-object | 대조 |
| --- | --- | --- | --- |
| `audit_v2.py` | `07433beddad31fd72b5a8c66eae3e5f0e58d053f` | 동일 | PASS |
| `tests/test_audit_v2.py` | `f174eea913c1484884aaba8124a02d80311d0dff` | 동일 | PASS |
| `tests/test_connected_tool_names.py` | `6e1623d0797473a34cdd21b0292095c40d45cb09` | 동일 | PASS |

원격 코드를 인증된 GitHub 연결에서 `fetch_file`로 읽은 후 로컬에서 정확히 재구성했고 3개 파일 모두 `git hash-object` 해시가 일치함. 브라우저/CLI로 GitHub 직접 다운로드는 불가능했으나 SHA로 동일 바이트 확인.

## 직접 실행 명령과 결과

```text
$ cd /mnt/data/r16_test
$ python3 -m unittest discover -s tests -v
Ran 32 tests in 0.003s

OK
```

32/32 PASS, 실패 0. 외부 생성형 모델·유료 API 호출 0. 테스트에는 분수 초 정각 차단, 유효하지 않은 tool/target 타입 방어, 16건 초과 입력 거부, 도구명 별칭, 동일 회차 증거 누락 방어가 포함됨.

## 원격 CI / 무인 성공
- 마지막 관련 테스트 커밋: `5195114d4ca408cef8c43e617f8dede5ed670b12`.
- GitHub `fetch_commit_workflow_runs` (PR 이벤트만 필터) → `workflow_runs: []`; `get_commit_combined_status` → `statuses: []`. **이는 CI 실패의 증거가 아니며 새 원격 CI 성공도 미검증.**
- 공식 ChatGPT 예약 per-run ID·동일 회차 GitHub/Slack native tool-call 원본 ledger 미제공 → **정규 무인 성공 미검증**.
- Activepieces 모의 TESTING 성공, GitHub 커밋, Slack 수동 기록과 원래 예약 실행을 혼동하지 않음.

## 다음 목표
공식 ChatGPT Scheduled `Previous runs`에서 해당 정규 회차가 제공하는 실제 ID·상태·원본 GitHub/Slack 도구 호출 감사 레코드를 공식 출처로 얻을 수 있으면 검증. 제공되지 않으면 `UNVERIFIED` 유지하고 보호 운영 환경은 변경하지 않음.
