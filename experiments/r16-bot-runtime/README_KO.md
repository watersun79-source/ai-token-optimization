# R16 BOT v6 — 실제 검사 입력과 실행 기록 연결

v5는 테스트 파일 3개만 해시로 확인해 runtime·역할 목록·공유 TSV·측정기 변경을 놓쳤다.
v6는 실행 코드/테스트/설정 파일 7개와 정규화한 evidence 입력의 해시를 기록·대조한다.
생성되는 polyglot 건수와 notice는 입력 해시에서 제외하며 건수는 측정 결과와 별도 대조한다.
예전 V5 기록은 미검증으로 처리하고 새 실측으로만 V6 기록을 생성한다.
소스가 측정 도중 바뀌면 기록 생성을 거부한다.

Python 표준 라이브러리, Java, Node.js만 사용한다. 외부 패키지·모델 API·네트워크 호출은 없다.
Java 컴파일러가 명령으로 없으면 OpenJDK 소스 실행기로 실제 Java 코드를 실행한다.

```bash
python3 measure_runtime.py
python3 -m unittest -v test_v5_receipt test_receipt_source_binding
python3 install_local.py
python3 batch_validate_100.py
python3 .local_install/bin/ai-bot-M01
```

100개는 단일 Python 엔진의 규칙 역할이다. 배치 검사는 100개 독립 LLM/프로세스가 아니다.
PASS는 입력 스냅샷·로컬 소스와 테스트 기록의 일치이며 최신 외부 상태를 인증하지 않는다.
로컬 실행 기록은 서명되지 않았고 SLSA 인증·공식 예약 원장이 아니다.
기존 예약 설정·main·운영 Activepieces·Slack 흐름은 이 프로그램에서 수정하지 않는다.

설계 참고: [SLSA verification](https://slsa.dev/spec/v1.2/verifying-artifacts)의 대상 해시 대조 원칙.
[slsa-verifier](https://github.com/slsa-framework/slsa-verifier) Apache-2.0 라이선스 확인;
이번에는 코드 복제·설치·서명 검증을 수행하지 않았다.
입력의 자체 SHA 검사와 신뢰된 공급자의 진위 인증을 구분한다.


## R16 백그라운드 협업 준비 (실제 서버 배포 전)

`background_coordinator.py`는 외부 AI 모델 호출 없이 기존 오프라인 100개 규칙 검사와 필요한 역할 선택을 반복할 수 있는 **명시적 실행 프로그램**이다.
코드 추가만으로 ChatGPT 앱/기존 예약 AI 또는 클라우드 서비스에 자동 연결되지 않는다.

- 사전 조건: 항상 켜져 있는 Linux/Unix 실행 호스트 + Python 3.12, Java 21, Node.js 24, 테스트 입력/로컬 설치 완료
- 선행 명령: `python measure_runtime.py`, `python install_local.py`
- **안전한 1회 시험:** `python background_coordinator.py --goal audit --state-dir .supervisor_state`
- **호스트가 준비된 뒤 명시적으로 실행하는 반복 모드:** `python background_coordinator.py --repeat --interval 3600 --goal audit --state-dir .supervisor_state`
- 장시간 실행 시에는 실제 호스트의 서비스 관리 도구(systemd 등)에서 시작·재시작·로그를 관리해야 한다. 이 저장소는 별도 서비스를 자동 설치·활성화하지 않는다.
- `--repeat --max-runs 1`은 CI에서 사용하는 1회 제한 모드이며 상시 실행 증거가 아니다.
- `background_latest.json`은 원자적으로 갱신하는 *로컬 실행 결과*다. 공식 ChatGPT 예약 run ID나 GitHub/Slack 무인 tool-call 원장을 증명하지 않는다.
- 같은 `--state-dir`에서 두 반복 프로그램이 겹치면 잠금으로 두 번째 프로세스를 차단한다. 잠금 파일 심볼릭 링크도 거부한다.
- 반복 간격 최소 3600초. 예약 슬롯 정각 동기화 또는 무중단 실행 보장은 없다. 서버 중지·재부팅·요금/무료 한도를 확인해야 한다.
- 새 운영 스케줄·ChatGPT 기존 매시간 예약·GitHub main·Activepieces 운영 플로우·알림은 **변경하지 않는다**.

참고: [systemd.service의 Restart=on-failure](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html).
실제 서버/계정·요금·권한 확인 전에는 별도 배포를 수행하지 않는다.


## R16 실제 역할별 규칙 실행 증거

이전 `bot_coordinator.py`는 역할 ID를 **선택만** 하고 `batch_validate_100.py`를 실행해,
실제로 선택된 역할의 개별 규칙 실행 결과가 없었다. 해당 결함을 수정했다.

- 전체 100개 오프라인 규칙 무결성 검사는 기존과 같이 유지한다.
- 이에 추가해 `evaluate_selected_rules()`가 목표별 필요한 BOT 규칙만 `runner.validate()`로 직접 실행한다.
- `audit` 목표는 `E01..E10`(예약 원장 검증) 및 `G01..G10`(GitHub 증거 형식) 총 **20개**를 검사한다.
- `selected_statuses`, `selected_outcome`, `executed_selected_rule_checks`를 반환하고
  `background_latest.json` 로컬 기록에도 표시한다.
- 검증되지 않은 공식 예약 원장(E 계열)은 **UNVERIFIED**이며, 전체 실행 과정의 `status: PASS`가
  이 항목의 통과를 의미하지 않는다. `selected_outcome: UNVERIFIED`로 명시한다.
- 값이 일치하는 것처럼 보이는 `G` 계열도 **오프라인 스냅샷 형식 검사**일 뿐, GitHub API 최신 상태를 인증하지 않는다.
- 실제 외부 LLM 호출·Gemini/Claude 독립 협력·ChatGPT 예약 원시 로그 연동은 수행하지 않는다.

설계 참고: [LangGraph 조건부 edges](https://github.com/langchain-ai/docs/blob/main/src/oss/langgraph/graph-api.mdx)와
[CrewAI 순차 협업](https://github.com/crewAIInc/crewAI). 둘 다 개념만 참고했고 패키지 설치·공급자 API 호출·코드 복제는 하지 않았다.
