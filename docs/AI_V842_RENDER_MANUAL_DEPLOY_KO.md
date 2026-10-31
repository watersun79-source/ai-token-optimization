# AI BOT v8.4.2 · Render 비공개 실시간 관제 · 수동 배포 가이드

> **상태:** 원본 도구의 신규 Render 서비스 생성 요청은 안전 검사를 통과하지 못했다. 실제 배포 성공을 주장하지 않는다. 새 서비스 생성은 별도 사용자 승인/Render Dashboard 경로에서만 수행한다. 이 문서는 절차이며 배포 자동 실행 파일이 아니다.

## 기존 상태 및 범위

- 리포지토리: `watersun79-source/ai-token-optimization`
- 격리 브랜치: `ai/v842-live-readonly-20261031` (다른 브랜치와 GitHub `main` 변경 금지)
- 기존 Render 서비스 3개는 변경하지 않는다.
- 이 서버는 **기존 격리 Render 서비스의 공개 `/healthz`만 읽는 UI**다.
- Neon SQL·D1·ChatGPT native per-run은 이 서버의 직접 데이터 소스가 아니며 **UNVERIFIED**로 표시된다.
- 화면을 보는 동안만 SSE로 Render 상태를 약 30초마다 확인하고 변경을 표시한다. 영구 모니터/무인 복구/실시간 공용 메모리 동기화는 아니다.
- Node 18 이상, 유료 모델 API 호출/DB 비밀번호/웹훅 키 필요 없음.

## 생성 전에 확인할 사항

1. 기존 Render Free 서버 3개의 사용량을 **Billing → Monthly Included Usage**에서 확인한다. Render Free는 워크스페이스당 월 750 free instance-hours(공유)이므로 서비스 추가 시 운영 시간과 중단 위험을 검토한다.
2. 새 Render Free 서비스는 유휴 15분 후 절전된다. 사용자가 화면을 열어보면 콜드 스타트 이후 복구되지만, 24시간 무중단 서비스가 아니다.
3. Render 계정에 예상 외 과금 가능성이 있는 설정을 자동 활성화하지 않는다.
4. 비밀값을 ChatGPT, GitHub 소스, Issues/PR, 로그나 D1에 쓰지 않는다. 이전 시도에 사용된 어떠한 비밀 문자열도 재사용하지 않는다.

## Render Dashboard에서 새 독립 서비스 생성 (사용자 직접 실행)

1. <https://dashboard.render.com/web/new> 에서 GitHub 저장소 `watersun79-source/ai-token-optimization`을 연결한다.
2. Service name: `ai-bot-v842-live-readonly-20261031` (중복 시 고유 이름 선택).
3. Branch: `ai/v842-live-readonly-20261031`.
4. Language: `Node`, Region: `Singapore`, Instance Type: `Free` (무료 한도 확인 후).
5. Build Command: `true`.
6. Start Command: `node tools/realtime_dashboard_v842.mjs`.
7. Auto-Deploy: `Off` (운영 배포 자동화와 분리).
8. Health Check Path: `/healthz`.
9. Render **Environment**에서 `REALTIME_VIEW_SECRET`를 생성하여 등록한다. Linux/macOS의 `openssl rand -base64 48` 또는 Python의 `python -c "import secrets; print(secrets.token_urlsafe(48))"`로 **본인 기기에서만** 비밀값을 만들고 UI에 붙여 넣는다. 24자 이상 필요하며 고유하고 무작위여야 한다.
10. `Create Web Service`로 배포한다. **결제 플랜은 바꾸지 않는다.**

## 배포 직후 확인 (실제 URL로 교체)

- `GET https://<new-service>.onrender.com/healthz`: HTTP 200, `{"status":"ok","scope":"isolated-no-secrets",...}` 기대.
- `GET https://<new-service>.onrender.com/api/snapshot` (미로그인): HTTP **401** 기대.
- `GET https://<new-service>.onrender.com/` (미로그인): 로그인 화면만 노출 기대.
- 비밀번호 입력 뒤 화면의 Render 상태를 확인: HTTP 200이어도 Neon DB `intake_enabled:false` 또는 `database_connection_verified:false`면 **DB 연결 미준비(DEGRADED)**로 표시해야 한다.
- 부팅 ID가 달라지면 상태 이벤트를 추가해야 한다.
- Neon·ChatGPT 예약·D1은 **미검증**을 유지한다.
- `Network`/응답/로그에 `REALTIME_VIEW_SECRET` 원문이 반환되면 즉시 운영 중지 및 키 교체 후 보안 점검한다.

## 자동 점검/CI 범위

`node --test tools/realtime_dashboard_v842.test.mjs`

GitHub Actions `validate.yml`은 이 격리 PR에서만 Node 테스트를 실행하며, **Render를 생성·배포·수정하지 않는다**. 실제 Render 서비스가 생성되었는지는 연결된 Render 앱 `list_services`의 신규 서비스 ID, 배포 `live` 및 공개 `/healthz`를 별도로 확인해야 PASS다.

## 참고

- <https://render.com/docs/free>
- <https://render.com/docs/web-services>
- <https://render.com/docs/configure-environment-variables>
