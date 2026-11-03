# AI BOT — D1 역사 증거 참조 복원 (격리·오프라인 전용)

**판정:** 기존 아카이브 회전 27/27 + 신규 참조 복원 41/41 = **68/68 PASS**. 전체 테스트 스위트 **30회 반복 PASS**. **운영 D1 변경 없음.**

## 실행

```bash
cd ai_bot_d1_reference_migration_isolated
python -m unittest -v test_guard test_migration
```

구성: `guard.py`(이전 27개 테스트의 격리 CAS 아카이브 로직), `test_guard.py`(원형 보존), `migration.py`(검증된 참조 복원), `test_migration.py`(41개 신규 테스트), `test-output.txt`, `evidence-summary.json`, `manifest.json`.

## 이번 세션에서 실제 조회한 D1 사실

- 연결된 D1 `project.ai-bot.unified-report`: **최종 읽기 전용 조회 r39**, **7,712자**, `source_runs` 5개·최신 요약·snapshot 이름/ID 연결 일치. `report_archives`, `history_archive`, `render_trace_evidence` 필드 없음.
- D1 `project.ai-bot.memory-capacity-policy`: **r6**, 경고 **9,300자**, 도구 쓰기 제한 **10,000자**. 계정 실측 디스크 한도/잔여량은 **미확인**.
- 공식 `memory_read(history=true)`의 원문과 별도 D1 아카이브의 원문을 직접 대조: **r27·r28·r29·r30·r31·r36 전부 exact match**, 각 아카이브 revision 1.
- 공식 r32·r33의 `report_archives`, `history_archive`, `render_trace_evidence`가 서로 일치. r31의 `source_content_sha`/`archive_content_sha`는 서로 다른 **서버 메타데이터 해시**다. 이는 동일 문자열의 SHA-256을 뜻하지 않으며, 원문 자체 비교로 무결성을 검증했다.
- r37~r39에 있는 r36 아카이브 참조의 서버 메타데이터와 r36 원본/아카이브를 일치 확인함.
- Render 추적 감사 `project.ai-bot.render-trace-path-20261103@1`은 **과거 Render native run**에 관한 기록이다. **현재 실행의 외부 서비스 인과관계 PASS 증거가 아님**.
- r39 원본 기준 독립 JS 읽기 전용 검증 **19/19 PASS**. 검증된 참조만 추가하는 후보 약 **8,606자**(JS 직렬화 예비값), 경고 9,300자 미만. 그러나 **실제 운영 CAS 쓰기 호출은 전혀 하지 않았다.**

## `migration.py` 동작 (별도 신뢰된 어댑터가 주어졌을 때만)

1. 활성 보고서의 revision/원문, 현재 `source_runs`·5개 snapshot·summary를 검증한다.
2. 진본 인증이 끝난 공식 이력 r27~r33·r36과 별도 아카이브 r27~r31·r36을 **원문 문자열로 비교**한다. 과거 r32·r33의 참조가 충돌하면 차단한다.
3. 과거 r30·r31의 Render run ID와 감사 키의 구 버전 기록을 대조한다. 과거 추적 참조를 현재 회차 성공 증거로 승격하지 않는다.
4. r27~r31을 과거 `report_archives`로 연결한다. **r36** 아카이브만 현행 `history_archive` 지점으로 사용한다. `render_trace_evidence`에는 검증된 과거 기록만 쓴다.
5. 활성 보고서 **기존 모든 필드의 값은 변경하지 않고** 검증된 참조 필드만 추가한다. 결과가 10,000자 초과 또는 9,300자 이상이면 차단한다.
6. 원본 revision/value/server-sha를 재확인하고 `expected_version` CAS 기록한다. CAS 응답 자체와 독립 readback을 검사한다. 충돌/응답 위조/누락에는 재시도 없이 실패한다.
7. 같은 마이그레이션의 재실행은 NO_UPDATE 처리한다.

**중요한 신뢰 조건:** 이 파일에는 운영 D1 네트워크 어댑터가 없다. 호출 측에서 공식 MCP 연결, source receipt와 `history_at(...)` 결과를 별도 검증해야 한다. 독립적인 원격 인증을 Python의 합성 레코드만으로 증명할 수 없다.

## 오프라인 회귀 검증

- 기존 CAS 보관 테스트 27개 변형 없이 PASS.
- 신규 41개: 정확한 아카이브 6개/원문, 과거 원장 run ID와 범위, 위조된 서버 메타데이터, 누락 및 변조된 기록, 이력 r32↔r33 충돌, 최신 실행 ID·요약 변경 금지, 쓰기 ACK/readback 검증, 재실행 멱등성, 현재 활성 보고서 revision 경합 등 PASS.
- 격리 동시 경쟁: 실제 8스레드 접근에서 **성공 1회**, 나머지는 NO_UPDATE/CONFLICT로 처리, 이중 쓰기 없음. 이 테스트는 로컬 FakeStore CAS를 검증하며 실제 D1 경합 증거가 아니다.
- `test_guard`와 `test_migration` 전체 **68개를 30회 반복 재실행**: 모두 PASS.

## 안전·운영 범위

이번 작업에서 **D1 `memory_write` 호출 0회**, 기존 예약 5개 수정 0건, GitHub main 수정 0건, Render 운영 변경 0건, 비밀키 접근 0건, 유료 외부 API 호출 0건. 원격 저장소 push/PR 생성·모든 예약 지시문 수정 없음.

다음 배포 전 단계: 검증된 읽기 어댑터 + 권한 검증 + 최신 CAS 경쟁을 실제 비운영 테스트 키에서 허가받아 검증하고, 롤백 및 보호 조건을 확인한 후 별도 승인을 받아야 한다. 자동 마이그레이션이나 백그라운드 스케줄은 **운영 중이지 않다**.
