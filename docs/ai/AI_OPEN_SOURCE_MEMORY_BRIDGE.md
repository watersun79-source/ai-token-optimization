# AI: 공개 오픈소스 기억 구조 적용 (2026-10-21)

## 실제 적용
- 코드: [tools/ai_memory_bridge.py](../../tools/ai_memory_bridge.py)
- 테스트: [tests/test_ai_memory_bridge.py](../../tests/test_ai_memory_bridge.py)
- 기준 자료: 기존 \`PROJECT_MEMORY_INDEX.md\` / \`AI-memory-protocol.md\` / 진단 Markdown
- 적용 브랜치: \`ai/continuation-readonly-audit-2026-10-18\` (운영 main/예약 미변경)

## 참고한 검증된 공개 설계
1. [tigerless-labs/agent-memory](https://github.com/tigerless-labs/agent-memory): Markdown 원본 + 삭제/재생성 가능한 SQLite 검색 인덱스, 단계별 짧은 검색.
2. [jayzeng/agentmemory](https://github.com/jayzeng/agentmemory): 로컬 우선 Markdown 기억, 일일 로그 개념.
3. [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph): 실행 ID별 checkpoint·근거 귀속 개념.

**설계를 참고해 표준 라이브러리만으로 경량 구현했다. 해당 upstream 패키지를 설치하거나 원본 코드를 복사한 것은 아니다.** 모델/API 요금 0; 인증 정보 접근 없음.

## 사용 (로컬 Python)
\`\`\`bash
python tools/ai_memory_bridge.py sync --db .ai-memory-cache.sqlite docs/ai/PROJECT_MEMORY_INDEX.md docs/ai/AI-memory-protocol.md
python tools/ai_memory_bridge.py recall --db .ai-memory-cache.sqlite "무인 기억 복원" --limit 3
python tools/ai_memory_bridge.py audit /path/to/official-run-evidence.json
python -m unittest discover -s tests -p test_ai_memory_bridge.py -v
\`\`\`

\`sync\`: 파일 변경분만 갱신; 검색 결과는 최대 3개 간결 발췌와 SHA256 캐시 체크섬을 제공. GitHub blob SHA(40자리)와 로컬 SHA256(64자리)은 서로 다르므로 혼동 금지. 로컬 SQLite는 복원 가능한 캐시이며 원본 Markdown이 진실의 출처다. 장기 사용 시 \`.ai-memory-cache.sqlite\`를 Git에 커밋하지 말 것.

\`audit\`: 공식 회차 ID, 일정한 실행 창, GitHub 3건의 blob SHA·Slack 메시지 ts, 도구·원본 기록 귀속을 입력받아 **형식 및 일치 조건만 검사**한다. PASS_SCHEMA_ONLY라도 플랫폼 제공 증거의 진위까지 증명하지 않는다. 현재 ChatGPT 예약 조회에서 원시 로그/공식 회차 ID가 제공되지 않으면 UNVERIFIED다.

## 운영 경계
- 이 도구는 별도 실행 프로그램이다. ChatGPT 예약이 GitHub 파일을 읽는 것만으로 **Python이 자동 실행되지는 않는다**.
- Activepieces 운영 플로우나 예약을 변경·중지하지 않는다. ChatGPT 내부 실행 로그에 접근하거나 정책 차단을 우회하지 않는다.
- 기존 거절된 GitHub/Slack 정규 예약 쓰기를 다시 시도하지 않는다.
- 실제 무인 성공은 같은 정규 실행의 원본 읽기 결과로 독립 입증될 때만 완료 처리한다.
