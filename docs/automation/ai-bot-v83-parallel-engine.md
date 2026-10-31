# AI BOT v8.3.0 — 적응형 병렬 작업 엔진 (격리 검증 후보)

## 범위
- 새 모듈: `tools/adaptive_parallel_v83.mjs`, 회귀: `tools/adaptive_parallel_v83.test.mjs`.
- 기존 v8.2.2 소스 기반 격리 브랜치 `ai/v83-parallel-engine-20261030`.
- 실제 입력 `enqueue({id,kind,payload})` 즉시 큐 접수 → 비동기 `handler` 동시 수행 → 각 Promise 완료 통지. `whenIdle()`로 처리 중 작업을 모두 합류한다.
- `onEvent` 콜백을 통해 `task_accepted`, `task_started`, `task_retry`, `task_complete`, `concurrency_changed`, `backpressure` 이벤트 관찰 가능.
- 기본 동시 실행 2 / 최대 8 / 설정 상한 16, 기본 수용 64 / 최대 1024 작업. 결과가 연속 성공한 경우에만 백로그를 보고 1개씩 확장, 4회 중 2회 이상 실패하면 동시 실행 수 축소.
- 같은 프로세스 내 중복 ID는 기존 Promise 재사용, 작업 완료 ID 기록은 기본 256개만 보관. ID 이력의 영속성은 없음.

## 안전성·한계
- 본 소스는 **프로세스 내 비동기 실행기**일 뿐, 24시간 호스팅 서비스·지속 큐·외부 웹훅·GitHub/Slack 연동·실시간 UI 구독이 아님.
- `kind`는 `offline_check`와 `read_only`만 수용. 실제 외부 시스템의 읽기 전용 보장은 호출자가 주입하는 신뢰된 `handler`와 권한 설정이 해야 하며 엔진만으로 외부 권한을 통제하지 못함.
- 동작 중인 작업은 `close()`로 중단하지 않음. 대기열만 취소하고 이미 실행된 handler는 완료될 때까지 대기. 작업별 타임아웃/강제 취소·지속 실패 백오프·영속 재시작 복구·크로스 프로세스 중복 차단은 미구현.
- 재시도는 `retryable: true` 표식 오류에 한해 최대 1회(설정 0~2회) 수행. 쓰기·결제·외부 모델 호출은 입력 단계에서 거부하지만 주입된 handler 자체의 행동을 검사하지는 않음.
- 이벤트에는 사용자 입력과 오류 메시지·스택을 노출하지 않으며, 안전한 오류 코드만 출력한다.
- Gemini·Claude 연결이나 여러 LLM API 호출을 수행했다는 증거가 아님.
- 운영 AI BOT v8.1, ChatGPT 예약 2개, Activepieces 기존 플로우, GitHub main 및 `.github/workflows/ai-r16-hourly.yml` pinned SHA 절대 변경 없음.

## 실제 검증 계획
1. `node --test tools/adaptive_parallel_v83.test.mjs`에서 제어된 비동기 Promise로 동시 실행 **2개 겹침**, 최대 동시 수 2 초과 금지, 합류 결과, 중복 ID 1회 처리, 실패 재시도, 실패시 오류 문자열 보호, 용량 초과 거부, 동시 실행 수 자동 증감, 이벤트 오류 격리 등 총 14개 테스트 수행.
2. 격리 PR을 생성해 GitHub Actions `.github/workflows/validate.yml`의 **공식 실행번호·원본 작업 로그**로 통과 확인. CI 성공은 격리 런타임 코드의 검증이며 항상 켜진 운영 엔진의 존재 증명이 아님.
3. 운영 승격 전 별도 조건: 영속 작업 큐·인증된 이벤트 진입·최소 권한·중복 방지·강제 취소/타임아웃·실패 백오프·실제 레이턴시 벤치마크·스마트폰 대시보드 연동을 각각 격리 검증.
4. 배포/본선 병합은 기존 보호 정책과 별도 승인 필요.

## 버전 정책
v8.2.2는 본선 검증 계획기(격리 후보), v8.3.0은 **병렬 작업 엔진 추가 버전**. 실제 개발 코드와 테스트가 반영된 시점에만 버전을 올리고, 운영판 v8.1은 변경하지 않음.
