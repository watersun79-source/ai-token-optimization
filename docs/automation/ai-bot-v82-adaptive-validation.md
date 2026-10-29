# AI BOT v8.2.1 — 적응형 증거 검증 (격리 후보)

## 상태·범위
- **적용 위치**: `ai/v82-adaptive-validation-20261030` 격리 브랜치.
- **운영 배포**: 미적용. ChatGPT 정각 예약, Activepieces 운영 플로우, GitHub `main`, 기존 `ai-r16-hourly.yml` 체크아웃 고정 SHA를 변경하지 않음.
- **기능**: `tools/adaptive_audit_v82.mjs`가 오프라인 입력 증거를 분석하고 `FAST`, `FULL`, `REUSE`를 선택하는 **판단 계획**만 만듦.
- **검사**: `node --test tools/adaptive_audit_v82.test.mjs` (16개 단위 테스트). 격리 브랜치 `.github/workflows/validate.yml`에 이 검사 단계 연결.
- **주의**: 이 엔진은 GitHub API, 모델 API, Slack, 예약 API를 호출하지 않음. 입력받은 CI 메타데이터는 공식 원본과 별도 대조되기 전까지 인증된 증거가 아님.

## 적응형 정책
1. 최신 본선 SHA·기존 고정 감사 SHA가 잘못됐으면 **차단**, 추정 성공 금지.
2. `main`의 공식 검증 회차 정보가 없거나 24시간을 넘거나 SHA·워크플로 이름이 맞지 않으면 **FAST → 공식 본선 CI 원본 확인**.
3. 본선 CI 실패 메타데이터면 **FULL → 격리 브랜치에서 원인 진단**. 본선 수정은 자동 승인되지 않음.
4. 본선 메타데이터가 일치해도 최신 본선과 고정 소스 동등성이 확인되지 않으면 **FULL → 소스 차이 검증**.
5. 변경 파일에 워크플로·정책·보안 관련 파일이 있으면 **FULL**로 확대. 낮은 위험으로 보여도 입력자가 전달한 CI 성공 정보만으로 **REUSE를 승인하지 않음**. 공식 원본 검증 전에는 재사용 후보(`REUSE_CANDIDATE`)로만 표시.
6. GitHub 오프라인 CI 성공은 ChatGPT native 예약 완료·동일 회차 MCP/Slack 원장의 증거가 아님. `nativeStatus`는 **UNVERIFIED** 고정.

## 이 대화에서 검증한 GitHub 사실
- 본선: `923c281f82023cc6b49f3844bad17f508f1ab203`
- 기존 정시 오프라인 감사 고정 체크아웃: `a88c7993c27404da43cba84a8f69e01a917315a6`
- 두 소스의 일부 필수 감사 실행 파일은 본선의 동일 경로에 없음. 고정 SHA를 자동으로 최신 본선 SHA로 바꾸지 말 것.
- `main` 별도 `.github/workflows/validate.yml`의 실행 `40162713670`은 2026-10-25 `923c281…` SHA로 `completed/success` 확인. 이 5일 전 기록은 현재 시점의 24시간 내 신규 증거가 아님.

## 안전 검증·승격 기준
1. 격리 코드와 테스트 파일을 GitHub에서 재조회하고 SHA/브랜치를 확인.
2. `node --test tools/adaptive_audit_v82.test.mjs`를 별도 실제 Node 런타임 또는 격리 CI에서 실행한 **원본 로그와 회차 ID** 확보. 현재는 원본 테스트 파일을 읽어서 JavaScript 실행 검증한 단계.
3. 기존 `main` Validate 공식 실행 확인 후, 본선 검증과 고정 감사 범위를 분리해 유지.
4. 소스 동등성·비용/권한·원본 테스트가 확보되기 전에는 운영 배포, `main` 병합, 스케줄 변경 금지.

## 보호
API/외부 모델 호출 0 · 자동 dispatch 0 · Slack 발송 0 · 예약 조작 0 · 운영 배포 0.

## v8.2.1 적응형 안전 개선 (2026-10-30)
- 사용자가 제공하는 `parity: EXACT`를 독립 검증된 소스 동일성으로 취급하지 않음. 본선과 감사 소스 SHA가 다른 경우에는 상세 원본 대조 우선.
- `changedPaths`가 빠진 경우 위험도 `UNKNOWN`으로 처리하고 추가 범위 확인을 요구.
- GitHub 워크플로 run의 `head_sha`와 pinned checkout SHA를 구분함. 정기 오프라인 감사의 GitHub run HEAD는 현재 본선일 수 있고, 실제 체크아웃 SHA는 별도 로그로 검증해야 함.
- `validate.yml`이 `schedule` 이벤트를 정상 실행으로 주장하는 잘못된 입력을 거부.
- '일치하는 CI 메타데이터'는 단독으로 검증된 증거가 아님. 낮은 위험의 재사용 후보라도 공식 CI 조회 전 재검사 생략을 승인하지 않음.
- 공식 v8.2.0 격리 PR 테스트: [run 40946427117](https://github.com/watersun79-source/ai-token-optimization/actions/runs/40946427117) PASS.
- **v8.2.1 공식 PR CI**는 후속 SHA의 새 실행 ID·결과를 별도로 확인해야 함.
