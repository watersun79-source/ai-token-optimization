# AI — 현재 상태와 지속 기억

최종 지침 적용 확인: 2026-10-19 22:55 KST. 저장소 main 검증은 22:41, 운영 상태는 22:28~22:29 관찰
작업 브랜치: `ai/continuation-readonly-audit-2026-10-18`
판정: 사용자 승인으로 PR #1·#4 main 병합과 최종 main 로컬 127/127·push CI 성공 확인. 기존 두 AI 플로우 비활성화 유지. 무료 공급자 API 자동 협업의 운영 성공은 미입증.

## 먼저 읽을 기록
- [최신 main 통합·최종 검증](ai-integration-2026-10-19.md)
- [최신 API 차단 구현·샘플 시험·게시 버전 감사](ai-execution-2026-10-19-free-web-guard.md)
- [현재 재분석·근거·다음 작업](ai-reanalysis-2026-10-19.md)
- [기억 프로토콜](AI-memory-protocol.md)
- [정규 사용자 지침](AI-custom-instructions-ko-1500.md), [동일 표시본](CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md)
- [이전 실행 상세](ai-execution-2026-10-19-automation-and-refresh-status.md)
- Slack 진행 채널: `C0C9649RQAZ`
- 프로젝트: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/automations
- [이 압축 전 전체 색인](https://github.com/watersun79-source/ai-token-optimization/blob/789551c62f6e4f2419de5d79e241f5e3c2ea704e/docs/ai/PROJECT_MEMORY_INDEX.md)

## 기억 유지 적용 — 2026-10-19
- 시작점은 이 색인 하나. 정규 [프로토콜](AI-memory-protocol.md)을 최신 절차로 다시 정리했고 대문자 두 문서는 여기로 연결하는 호환 안내로 통일했다. 옛 프로토콜은 immutable commit 링크로 보존.
- ChatGPT 메모리는 설정 화면에서 ON 확인. ChatGPT 지침과 데스크톱·웹 동기화 Codex 지침을 본문 1,133 UTF-16 단위로 동일 저장하고 각 화면 새로고침 후 값 일치 확인. 정규 지침·표시본도 동일 blob으로 동기화.
- 로컬 Codex 설정 features.memories·generate_memories·use_memories는 true. 메모리 설정은 변경하지 않았다. 외부 도구 대화의 자동 기억 생성 여부나 모든 새 채팅의 전체 자동 복원을 보장하지 않는다.
- 외부 기록을 읽는 지침의 저장과 실제 복원 시험은 구분한다. 새 보고서에서 복원 시험 결과를 확인한다.

## 최신 통합 — 2026-10-19 22:41 KST
- 사용자 “PR #1·#4를 main에 병합” 명시 선택. exact-head 조건으로 PR #1 → PR #4 순서 병합, 둘 다 closed·merged.
- PR #1 병합 `840e7142779d4a66938b334c71ca41f5a92e49b2`; PR #4 병합·최종 main `297d1d2d52e213e0b3c93c93d74e322fb11e744b`.
- 병합 전 통합 파일과 실제 최종 main에서 각각 Python 23/23·JS 32/32·guard 72/72, 총 127/127 통과. diff 검사 통과, 최종 로컬 워크트리 clean.
- 전체 tracked 파일 19개 blob·모드 일치, 차이 0. 이전 main 대비 예상한 9개 파일만 변경. 최종 main [push CI 39262028914](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39262028914) completed/success, 세 검사 단계 모두 성공.
- 기존 main 보존 원칙의 이번 두 PR 병합 예외는 사용자 명시 승인에 한정. Activepieces·예약 변경이나 공급자 생성 호출 없음. 운영 게시·무료 quota·청구 검증 완료로 확대하지 말 것.

## 최종 운영 상태 — 사용자 승인 2026-10-19 22:28 KST
- 사용자가 “두 AI 플로우 비활성화까지 진행”을 명시 선택. 이 승인에 따라 AI3 `kt2N9yCVA3dLkFiNPSMsH`와 협업 `drNhxMhmCo3A0rKV0OhIZ`를 DISABLED로 변경하고 재조회 확인. 기존 게시 구성은 보존.
- 두 AI 플로우의 PRODUCTION RUNNING·QUEUED 각각 0건. 새 트리거 실행 차단 완료. 다른 시스템 전체 API 사용까지 차단했다고 주장하지 말 것.
- Slack `vtRwEYmcwDTunBZut265G`만 ENABLED·published 유지. 기존 ChatGPT AI 예약도 22:29 UI에서 일시 중지 제어와 매시간 표시로 활성 재확인. 일정/상태 변경 없음.
- 사용자 명시 요청 없이 두 AI 플로우를 다시 활성화하지 말 것. 앞선 “활성3개 보존”은 승인 전 관찰이며 현재 상태가 아님.
- guard 검토 플로우 `3kRMmWICEPt0vIarX7kLR`는 DISABLED·미게시로 보존. PR #1·#4는 위 별도 사용자 승인으로 22:41 main 병합 완료.

## 이전 구현 확인 — 2026-10-19 22:24 KST
- [초안 PR #4](https://github.com/watersun79-source/ai-token-optimization/pull/4), head `c35dff3c2087756540694767f99f5424258fed3f`, 당시 미병합(이후 22:41 승인 병합). 로컬 guard 72/72; [CI 39259453101](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39259453101) Python·JS·신규 guard 모두 성공. 독립 검토 결함 없음.
- [API 차단 검토 플로우](https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/flows/3kRMmWICEPt0vIarX7kLR): DISABLED·미게시, 웹훅+CODE 2단계, 제공자·외부HTTP·Slack 없음, 오류 후 계속/재시도 false.
- TESTING 샘플4개 예상 결과 일치: mock/manual_web 허용2, API/권한우회 차단2. 실제 운영 이벤트·공급자 실행 성공으로 표시하지 말 것. CODE 소스 read-back 일치.
- 허용 결과도 제공자·네트워크 실행 권한 false. 수동 자료는 caller_supplied_unverified. 기존 운영 플로우를 보호하는 코드가 아님. 인증 없는 테스트 트리거를 게시/활성화하지 말 것.
- 이번 공급자 생성 API 0회, 기존 운영 실행0, 구매/업그레이드0. 새 TESTING4개, 크레딧 표시 전후402; 계정 청구 전체는 미검증.

## 이전 확인을 이어받은 사실 — 2026-10-19 21:58 KST
- Activepieces 인앱 브라우저 접근 성공, 로그인된 Personal Project 신원 확인. 과거 사이트 접근 차단을 현재 차단으로 반복 보고하지 말 것.
- 21:58 당시의 ENABLED·published 플로우 3개(22:28 사용자 승인으로 두 AI 비활성화됨): AI3 `kt2N9yCVA3dLkFiNPSMsH`, Slack `vtRwEYmcwDTunBZut265G`, 협업 `drNhxMhmCo3A0rKV0OhIZ`. 일반 목록은 10개를 반환했으나 프로젝트 전체 총수로 확정하지 않음.
- 21:58 당시 PR #1 head `5f5393967a862c716b10f5b349016400ea466725`, open·미병합·충돌 없음, 제출 리뷰 0. 이 미병합 상태는 22:41 사용자 승인 병합으로 대체됨. Actions [39244633487](https://github.com/watersun79-source/ai-token-optimization/actions/runs/39244633487) 성공.
- 같은 head 로컬 회귀: Python 23/23, JS 32/32, diff check 통과. 이 결과에 새 코드 변경은 없음.
- AI3 정적검증 7/7 valid. 협업은 4 valid·의도된 OpenAI skip 1, invalid 0. TEST ONLY Concurrent Child Join E2E 폴더 3개 플로우 연결검증 이슈 0.
- Gemini Flash 웹과 Claude Free 웹에서 각각 독립·교차 검토 응답 2개씩, 실제 총 4개 확인. [Gemini](https://gemini.google.com/app/81dde9123f5873d7), [Claude](https://claude.ai/chat/e54a756f-4b9a-43f0-8a2b-135911a1dd42). 이는 수동 웹 경로이며 API 자동 협업이 아님.
- 기존 ChatGPT 예약 AI는 활성·매시간. 최신 표시 결과는 부분 완료. [예약](https://chatgpt.com/scheduled?automationId=6acb017062a08191a4136238b78b313a&automationSource=cloud). 시간대·새 실행 성공은 별도 검증 대상이며 이번 감사에서 일정·상태 변경 없음.

## 미완료와 다음 단계
1. AI3·협업 현재 구성에 공급자 호출 전 무료 잔량·과금 차단 단계 없음. AI3 Claude 검색 상한 5는 저장소 상한 3과 불일치하고 재시도가 켜짐.
2. 버전 이력 직접 확인: 협업 최신·게시 #21; AI3 최신 초안 #3와 게시 #2 분리. AI3 게시 #2를 View로 읽고 검색 상한 5·재시도 true 확인. 기본 MCP 구조는 최신 초안을 읽으므로 게시본과 혼동하지 말 것.
3. 현재 PRODUCTION 조회에서 AI3·Slack 각 0건. 협업 최신 성공은 10월15일이며 당시 버전·사용량·청구 정보 없음. 최근 전체 20건 성공은 TEST ONLY 자식작업. 실제 무료 운영 완료 증거로 사용하지 말 것.
4. ChatGPT 예약과 Activepieces 공급자 실행 사이 연결 근거 미확인. 예약 활성만으로 과금 발생을 추정하지 말 것.
5. 계정별 API 무료 quota·청구 미검증. 공급자 API 호출 금지를 유지하고, 검증된 소비자 웹 검토 경로를 사용.
6. 별도 API 기본 거부 검토본은 구현·TESTING 검증 완료. 기존 운영에는 미적용. 검색·재시도 정책 조정과 운영 적용은 별도 작업이며 무료 웹을 ROUTER로 자동 연결할 수 있다고 가정하지 말 것.
7. 과거 미해결 연구: Tables atomic unique/upsert·경합 안전성, 501건 초과 실제 처리, hosted Cloud custom BARRIER 가능 여부, 과거 5-vs-3 운영 ID 불일치. 위 과거 전체 색인의 근거를 필요할 때만 조회.

## 운영 규칙
- ANALYZE → EXECUTE → VERIFY → 기록 → 다음 실제 작업. 완료·부분 완료·차단·미검증을 구분.
- 사용자 제약: 무료 우선, 유료/미검증 공급자 API·구매·업그레이드 금지. 비밀값·웹훅 인증·헤더·개인 위치를 기록하지 말 것.
- main·운영 플로우·기존 매시간 예약 보존. PR 병합이나 운영 적용은 별도 명시 지시 없이 하지 말 것.
- 연결 상태·모델 목록·공개 무료 요금표는 계정의 남은 무료 quota 증거가 아님. 모의 결과를 실제 모델 응답으로 표시하지 말 것.
- 현재 도구 목록만 사용. 사용자 금지 project-context 도구를 재검색·호출하거나 필수 전제로 삼지 말 것.
- 의미 있는 작업 뒤 GitHub·Slack에 실제 결과를 기록하고 재조회. 실패한 쓰기는 성공으로 보고하지 말 것. 오래된 차단 문구보다 새 직접 관찰을 우선.

## 실행 기록 구분
21:58 재분석: 소비자 웹 응답4개, 새 플로우 시험0, 색인76,201→3,083자로 압축.
22:24 이어서 실행: 별도 guard 소스·테스트·CI·초안 PR#4 및 비활성 플로우 생성, TESTING 샘플4개.
22:28 사용자 승인 후 두 AI 플로우 상태만 DISABLED로 변경. Slack·main·PR#1·예약 보존. 공급자 생성 API·구매·업그레이드0. 계정 전체 기존 구독·청구액은 미검증.

22:41 사용자 별도 승인 후 PR #1·#4 main 병합, 실제 최종 main 로컬 127/127 및 push CI 성공. 새 Gemini·Claude 응답·공급자 API·구매0. 두 검증 워크트리 보존.
