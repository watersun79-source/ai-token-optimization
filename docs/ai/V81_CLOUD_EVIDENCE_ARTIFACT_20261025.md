# AI BOT v8.1 — GitHub 클라우드 증거 자동 보관 (격리 실험)

- 적용 범위: ai/v81-cloud-evidence-artifact-20261025 분기에서 발생한 **push** 실행만. 정각 ChatGPT 예약, main, :15 cron, Activepieces/Slack 운영에는 변경 없음.
- FAST audit가 공식 GitHub Actions schedule-run API를 **GET 전용**으로 조회하고 민감정보가 없는 판정(JSON)을 런너 임시파일에 기록.
- GitHub Actions `actions/upload-artifact` v4.6.2의 고정 SHA로 해당 JSON 1개를 아티팩트로 저장. 보관일 7일. API 토큰·원본 로그·개인 파일은 아티팩트에 저장하지 않음.
- 보호: `contents:read`, `actions:read`만 요청. 아티팩트에는 status/reason/GitHub run ID와 검증 여부, 해시 등 제한 필드만 포함. 공개 저장소의 아티팩트는 공개 가능한 비민감 판정치에 한함.
- 이전 검증이 FAIL이면 실패 그대로 기록; 증거 부재 시 UNVERIFIED/NOT_APPLICABLE. 아티팩트 업로드 성공은 공식 native ChatGPT 회차 성공 증명이 아님.
- 비용: 표준 공개 저장소 GitHub-hosted runner의 무료 조건을 우선 활용. 신규 외부 클라우드/유료 API/신규 정기예약 없음. 계정 전체 청구액은 별도 미검증.
- 원본 확인: GitHub Actions 해당 push run의 `fast-audit` job 결과, artifact 목록, commit SHA를 별개로 재조회.
