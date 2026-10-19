# AI — 현재 상태와 지속 기억

최종 지침 적용 확인: 2026-10-20 병렬 협동 본문 1,477 단위 ChatGPT·Codex 저장 후 새로고침·재열기 일치. 최초1133·후속1290 기록 보존. main·CI·운영 상태는 00:14 독립 재조회.
작업 브랜치: `ai/continuation-readonly-audit-2026-10-18`
판정: 이번 Gemini·Claude 무료 웹 독립2개·교차2개 실제 응답과 양쪽 생성 중 표시로 병렬 검토 확인, ChatGPT/Codex 현재1477지침 저장 재조회 일치. main·PR #1/#4 병합·기존127/127·CI성공 보존, 두 AI DISABLED·Slack ENABLED를00:14 다시 읽음. 과거1133의복원6/6·승인후기록복구2/2는 당시 검증. 사용자요청의새기록과정규무인자동저장은구분하며, 후자는여전히미검증.

## 먼저 읽을 기록
- [2026-10-20 실제 무료 웹 병렬 협동·새1477지침 적용](ai-parallel-review-2026-10-20.md)
- [2026-10-20 00:20 정규 예약 무인 자동 저장 — 증거 대조 및 미검증 범위](ai-scheduled-unattended-write-check-2026-10-20-0020.md)
- [2026-10-20 00:13 재분석 — 예약·저장·문서 불일치·비용 감사](ai-execution-2026-10-20-0013-readonly-reanalysis.md)
- [23시 예약 결과 — 사용자 승인 원격 기록 복구](ai-23h-remote-record-recovery-2026-10-19.md)
- [최신 기억 유지 적용·복원 검증](memory-maintenance-2026-10-19.md)
- [최신 main 통합·최종 검증](ai-integration-2026-10-19.md)
- [최신 API 차단 구현·샘플 시험·게시 버전 감사](ai-execution-2026-10-19-free-web-guard.md)
- [현재 재분석·근거·다음 작업](ai-reanalysis-2026-10-19.md)
- [기억 프로토콜](AI-memory-protocol.md)
- [정규 사용자 지침](AI-custom-instructions-ko-1500.md), [동일 표시본](CHATGPT_CUSTOM_INSTRUCTIONS_1500_KO.md)
- [이전 실행 상세](ai-execution-2026-10-19-automation-and-refresh-status.md)
- Slack 진행 채널: `C0C9649RQAZ`
- 프로젝트: https://cloud.activepieces.com/projects/Fr9OAsxi4FbVSVLZkexYi/automations
- [이 압축 전 전체 색인](https://github.com/watersun79-source/ai-token-optimization/blob/789551c62f6e4f2419de5d79e241f5e3c2ea704e/docs/ai/PROJECT_MEMORY_INDEX.md)


## 2026-10-20 00:13 KST 재검증 — 별도 AI 대화의 당시 관찰
- 현재 기존 ChatGPT `AI` 예약: `automations.peek`로 **활성**, 매시간 정각/Asia-Seoul 확인. 마지막 제공 실행 메타데이터는 10월19일 **23:57:47 KST**이며, **00시 정규 예약 원격 자동 저장 결과를 증명하지 않음**.
- GitHub REST의 main SHA `297d1d2d52e213e0b3c93c93d74e322fb11e744b`, PR #1·#4 `merged=true` 재확인. 이미 성공한 127/127과 분리복원6/6은 재시험하지 않음.
- 이번 브라우저 연결은 originating browser context 부재로 실패; Activepieces 프로젝트 호출 0회, 현재 실행은 47개 도구 카탈로그 확인만. 과거 정상 접근/두 AI DISABLED 확인을 이번 세션의 재검증으로 오인하지 않음.
- [Issue #3](https://github.com/watersun79-source/ai-token-optimization/issues/3)의 옛 PR 미병합 문구와 main README의 옛 프로젝트명·호출 경로 설명이 최신 상태와 불일치. **Issue와 main README는 보호 범위로 미수정**. main 정책파일의 정적 `cost_guard`는 paid_api=false·미검증 무료 quota 차단을 확인했지만 운영 적용 증거는 아님.
- 상세 근거·테스트 ID·비용·차단·다음 목표는 [이번 재분석 보고서](ai-execution-2026-10-20-0013-readonly-reanalysis.md). 정규 예약 **무인 자동 GitHub/Slack 저장은 여전히 미검증**.

## 기억 유지 적용 — 2026-10-19
- 시작점은 이 색인 하나. 정규 [프로토콜](AI-memory-protocol.md)을 최신 절차로 다시 정리했다. 대문자 색인은 호환 안내이며, 대문자 프로토콜은 Windows 경로 충돌에 대비해 정규 프로토콜과 전체 동일한 본문으로 유지한다. 옛 프로토콜은 immutable commit 링크로 보존. Windows 읽기 일관성을 위해 대소문자만 다른 두 프로토콜은 전체 동일 본문 미러로 유지하며, 양쪽 blob d88a4b7b2ecb413aa5a79a0bb48cce7ec6128c49 일치를 root와 별도 에이전트가 각각 확인.
- ChatGPT 메모리는 설정 화면에서 ON 확인. ChatGPT 지침과 데스크톱·웹 동기화 Codex 지침을 본문 1,133 UTF-16 단위로 동일 저장하고 각 화면 새로고침 후 값 일치 확인. 정규 지침·표시본도 동일 blob으로 동기화.
- 로컬 Codex 설정 features.memories·generate_memories·use_memories는 true. 메모리 설정은 변경하지 않았다. 외부 도구 대화의 자동 기억 생성 여부나 모든 새 채팅의 전체 자동 복원을 보장하지 않는다.
- 별도 에이전트(fork_turns=none)가 시작 주소만으로 문서·Slack을 읽어 최신 결정·main·테스트·운영 보존·지침 동일성·복원 범위 6/6 충족. 전체 사용자 새 채팅 자동 실행의 검증으로 확대하지 않는다.
- 기존 매시간 AI 예약 프롬프트도 같은 정확한 시작 주소로 연결했다. 없는 프로젝트 컨텍스트 설정 도구를 복구하도록 반복시키던 전제를 제거하고, 현재 실제 도구·프로젝트 신원 확인과 미완료 목표 선택으로 바꿨다. 본문1,781 단위 저장 후 새로고침 재조회 일치, 매시간·활성 확인. 일정/상태/제목 변경·중복 예약 없음. 23시 정규 실행은23:22 종료표시·23:23 새결과와 원본 AI대화 메시지1bebc4da-4f9b-480d-8e08-7fa179c9130b를 확인했다. 최신색인·Slack읽기·두PR병합/main복원은 성공 보고. 자동 GitHub보고서작성·Slack전송은 안전검사 차단 보고(구체사유미제공), 예약브라우저접근 실패 보고. 현재채팅에서 관찰결과를 별도로 보존했으며 예약의 자동저장성공으로 표시하지 않는다. 임시 확인 heartbeat ai-23은 새결과 확인 후23:25 PAUSED. 기존 매시간 AI예약은 활성 유지.

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

22:58 기억 유지 보완: ChatGPT/Codex/예약 지침 3곳 저장·reload 재조회 일치. 지침1133 UTF16·예약1781. 프로토콜/호환진입점 통일, 독립 문서 QA6개·분리 문맥 복원6/6. 다음 정규 예약 실행 결과는 최신 보고서에서 별도 확인.

23:27 후속 결과: 예약 실행의 기억 복원 성공과 자동 외부 쓰기 차단을 구분해 보존. 별도 AI대화에 지정 기억브랜치·Slack 기록 승인 전달문안을 로컬 outputs에 준비했으며, 직접 사용자 승인 전에는 다른 대화로 전송하지 않음. 자동 기록의 무인 완료 판정은 보류.

23:31 사용자 승인 후속 복구: 사용자가 ‘모두’로 승인한 지정 범위 문안을 원본 AI 대화에 한 번 전달. AI 후속 턴4fbf710e-028e-4638-ba21-21595101ee5b가 새 [복구 보고서](ai-23h-remote-record-recovery-2026-10-19.md)(커밋5076daff2989112e992290b7cc97d6f9b062e14f)·색인(커밋87e9606a4e40aaf6b4b179aaa2dcf476bbbda207)·[Slack 답글1792420262.121779](https://chatgpt-mor9047.slack.com/archives/C0C9649RQAZ/p1792420262121779)을 작성. root와 별도 에이전트가 실제 재조회해 2/2 확인. 23시 정규 자동 저장 실패를 성공으로 바꾸지 않는다.

23:36 후속 확인: 기존 임시 체크 ai-23를 ‘AI 기억 자동 기록 검증’으로 갱신·활성화. 다음 정규 실행(10월20일00시 또는 그 이후 첫 실행)의 새 GitHub·Slack 자동 기록만 관찰하고, 변화 없을 때 조용히 대기하며 결과 확인 뒤 이 체크만 중지. 기존 매시간 AI 예약·main·운영 상태는 보존. 신규 업무 실행·중복 예약·추가 채팅 메시지 없음.

23:57 새 맞춤 지침: 사용자 프롬프트 요청·후속 ‘진행’에 따라 현재 ChatGPT·Codex 본문1,290을 파일과 전체 문자열 대조해 확인. ChatGPT는 이미 저장돼 있어 root쓰기0, Codex는1133백업→1290저장→새로고침·재열기확인. 정규지침·표시본 같은 본문/1290머리글로 갱신(blob ca8719e0f1673a277fad221371f8c9e6eaed1eea). 프로토콜 양쪽은 최초1133과 후속1290확인을 구분. 과거 분리복원6/6은 새본문의 재시험이 아님. 기존 매시간 예약·main·운영 상태·기억/개인정보 설정 변경 없음. 정규 자동 저장은 다음 실행 결과에서 별도 검증.

00:01 추가 관찰: 원본 AI 새응답fac94f86-a173-4ec6-821f-41c4b4beb614는 기존 승인전달 턴에 추가돼23:57:38에 종료. 신규보고서ai-automation-visibility-2026-10-19.md 생성이 ‘This tool call was blocked by OpenAI's safety checks.’로 거절됐으며 구체기준미제공, Slack미시도. 23:31실제복구성공을 취소하거나00시정규실행성공/실패로 오인하지 않음. root가 거절파일을 대신 생성하지 않음. 00:01예약화면은다음59분후·23:57결과표시, 새00시결과아직확인안됨. 로컬ai-23 ACTIVE와cloud목록은별도환경으로구분.

2026-10-20 병렬 협동: 동일 최신자료를 Claude00:16:17.708/Gemini00:16:18.051에 각각전송, 양쪽생성중표시 동시관찰. 교차검토도00:18:24.561/.903양쪽생성중확인. 실제새응답독립2+교차2=4개, 원문00:20:55.330재조회. [이번보고서](ai-parallel-review-2026-10-20.md)에모델오류정정·채택/미채택근거·수동요청vs무인기록구분보존. 지침1477본문 ChatGPT/Codex저장→reload재열기exact, 정규지침·표시본같은blob5106e5bfe0aa310626d1d4588c9d0148224b71be, 프로토콜두파일같은blob4c47025aeae379af00c0190edd22d595a97b4adc. 회귀127·분리복원6/6재시험0, 운영/main/기존매시간예약/기억스위치변경0, 공급자생성API·구매0. ai-23후속확인유지.
