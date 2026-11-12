# TOP10 통합 단계: 격리 어댑터 실행

2026-11-12 KST. 10개 프로젝트 대응 로컬 계약 어댑터 적용·테스트. **실제 upstream SDK 설치·실행·배포가 아니라 격리 인터페이스 검증**이다.

| 대상 | 로컬 적용 기능 | upstream 실제 실행 |
|---|---|---|
| LangGraph | 상태 전이/체크포인트 계약 | 미실행 |
| Activepieces | 미배포 플로우 계획 | 미실행 |
| OpenHands | 리뷰 제안 식별자 | 미실행 |
| Mem0 | 휘발성 기억 제안 | 미실행 |
| Langfuse | 미전송 trace 형식 | 미실행 |
| Microsoft Agent Framework | 역할 순서 | 미실행 |
| CrewAI | 3역할 배치 | 미실행 |
| Letta | 휘발성 세션 | 미실행 |
| OpenAI Agents SDK | 핸드오프/무권한 도구 | 미실행 |
| Flowise | EOL 설치 차단, 시각화 계약 | 미실행 |

선택식 권고: orchestration=LangGraph, memory=Mem0, observability=Langfuse, automation=Activepieces. 다른 실행 엔진·기억 백엔드는 중복 실행하지 않는다.

실행: `python3 experiments/oss-top10-safe-adoption/ten_adapter_runtime.py --goal "Evidence audit"`

테스트: `python3 -m unittest discover -s tests -p "test_oss_top10_*.py" -v`

안전: 기존 main, PR #29, 예약, D1 NO_WRITE, Activepieces 운영, Site, 비밀키 보호. 라이브 모드·설치·유료 모델·운영 쓰기 경로는 fail-closed. 운용 통합에는 별도 실제 upstream SDK·설정·무료 한도 확인 및 CI/실환경 검증 필요.
