# AI BOT v8.4.2 · Render 비공개 실시간 관제 · 수동 배포 가이드

> **상태:** 원본 도구의 신규 Render 서비스 생성 요청은 안전 검사를 통과하지 못했다. 실제 배포 성공을 주장하지 않는다. 새 서비스 생성은 별도 사용자 승인/Render Dashboard 경로에서만 수행한다. 이 문서는 절차이며 배포 자동 실행 파일이 아니다.

## 가장 간단한 Render Blueprint 배포 방법

**실행 전:** Render Workspace의 월간 무료 사용량을 확인한다. 사용량 여유가 없거나 비용 선택 화면이 나오면 배포를 중단한다.

1. [Render에 격리 서비스 배포](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fwatersun79-source%2Fai-token-optimization%2Ftree%2Fai%2Fv842-live-readonly-20261031) 를 열어 Render 계정으로 로그인한다.
2. 선택한 저장소가 `watersun79-source/ai-token-optimization`, 브랜치가 반드시 `ai/v842-live-readonly-20261031`인지 확인한다. `main`이면 취소한다.
3. Blueprint가 **기존 3개 서비스가 아니라 새 Free Web Service 1개만** 만들며, 자동 배포가 Off인 것을 확인한다. 다른 서비스가 나타나면 취소한다.
4. `REALTIME_VIEW_SECRET` 입력창에 **사용자 기기에서 새로 생성한 24자 이상 난수**를 입력한다. 이 입력은 Render 대시보드 안에서만 수행한다. 비밀번호를 다른 곳에 붙여 넣지 않는다.
5. 금액이 표시되지 않는 Free 요금제 및 총 무료 사용량을 확인한 뒤, 본인이 `Deploy Blueprint`를 누른다.
6. Render의 Deploys 페이지에서 최신 배포가 `live`가 된 뒤 서비스 URL을 확인한다. 건강검사 `/healthz` HTTP 200과 로그인 전 `/api/snapshot` HTTP 401을 확인한다.
7. 화면에서 기존 Render의 응답 상태만 관측하며, **Neon 및 native 예약은 UNVERIFIED**임을 유지한다.

Blueprint 파일: [render.yaml](https://github.com/watersun79-source/ai-token-optimization/blob/ai/v842-live-readonly-20261031/render.yaml). 이 설정 파일은 비밀키를 저장하지 않고, Render 초기 배포 때 입력을 요구하는 `sync: false`를 사용한다. **이 문서만 클릭하거나 GitHub에 푸시해서는 Render 서비스가 만들어지지 않는다.**

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

## 실제 장애 대응: Blueprint 생성 후 MISSING_VIEW_SECRET (2026-10-31)

**Render 원본 확인:** 신규 Free Web Service 2개가 생성되었고, 모두 `update_failed`이다. 두 서비스 모두 Build는 성공했지만 시작 직후 `MISSING_VIEW_SECRET` 출력 후 프로세스가 종료됐다. 이 문제는 앱 테스트 실패가 아니라 **실행 환경변수 미설정**이 원인이다.

- 첫 번째(원본): `ai-bot-v842-live-readonly-20261031` · `srv-dbisffe7bikc73dogp60`
- 두 번째(화면의 접미사 포함): `ai-bot-v842-live-readonly-20261031-1vz0` · `srv-dbisgrm7bikc73dojvug`
- **절대로 새 Blueprint를 추가 생성하지 않는다.** 두 기존 서비스 모두 삭제하거나 변경하기 전에 별도 확인이 필요하다.
- **복구 대상은 한 개만 선택한다.** 화면에 보인 `-1vz0`를 복구하려면 그 서비스의 Render Dashboard → Environment로 이동한다.
- Environment Variables에서 Key `REALTIME_VIEW_SECRET`를 추가하고 사용자 기기에서 만든 충분히 긴(24자 이상) 무작위 Value를 입력한다. **채팅, GitHub, D1에는 그 값을 남기지 않는다.**
- `Save and deploy`를 선택해 환경변수가 실제 프로세스에 반영되도록 한다. `Save only`는 즉시 적용되지 않는다. **Blueprint 다시 생성/재동기화가 필요하지 않다.**
- Deploys가 `live`인지 확인한다. `/healthz`가 200, 미로그인 `/api/snapshot`이 401인지 확인한다.
- 다른 중복 Free 서비스는 사용자 승인 없이 삭제·정지·변경하지 않는다. 월간 Free 사용량 소모 여부를 Render 대시보드에서 확인한다.

Render 공식 출처: <https://render.com/docs/configure-environment-variables>, <https://render.com/docs/blueprint-spec>. 특히 `sync: false`는 기존 Blueprint 재동기화 시 값을 다시 물어보지 않는다.

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
