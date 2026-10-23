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
