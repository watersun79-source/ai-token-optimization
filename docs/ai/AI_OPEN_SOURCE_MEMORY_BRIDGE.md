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


## 구식 기억 캐시 정리 및 무료 자동 검증 (2026-10-21)

구식 지시가 검색 결과에 남는 실제 버그를 재현했다. 과거 문서와 현재 문서를 함께 색인하고 현재 문서만 다시 `sync`하면 오래된 문서가 캐시에 남았다. 이를 위해 **명시적 전체 목록**에만 적용하는 `--prune` 옵션을 추가했다.

```bash
# 기억의 현재 원본 파일 목록이 완전할 때만 --prune 사용
python tools/ai_memory_bridge.py sync --db .ai-memory-cache.sqlite --prune \
  docs/ai/PROJECT_MEMORY_INDEX.md docs/ai/AI-memory-protocol.md
# 특정 파일만 추가로 색인할 땐 --prune 없이 사용
python tools/ai_memory_bridge.py sync --db .ai-memory-cache.sqlite docs/ai/AI-memory-protocol.md
```

`--prune`은 원본 Markdown을 지우지 않고 **로컬 SQLite 검색 캐시에서만** 명시 목록 밖 항목을 삭제한다. 완전한 목록이 아닌 상태에서 사용하면 필요한 캐시까지 정리될 수 있으므로 주의. 변경 없이 기존 문서를 추가로 색인하는 호출은 기존 동작 유지.

회귀 테스트는 기존 10건에 구식 기억 제거/기존 증분 동작 보존 2건을 더한 **12건**이다. 별도의 로컬 동작 시험에서 12/12 통과했고, GitHub에 올라간 코드·테스트 파일도 저장 후 SHA 재조회로 확인했다. GitHub Actions에서 그 버전의 실행 통과 여부는 별도 확인해야 한다.

GitHub Actions 비운영 브랜치 전용 검증: [`.github/workflows/ai-memory-bridge.yml`](../../.github/workflows/ai-memory-bridge.yml). 기억 브랜치에서 코드/테스트/워크플로 변경 시 Python 컴파일·12개 회귀 시험을 시도한다. 퍼블릭 저장소의 표준 ubuntu-latest runner만 사용하고 GitHub Actions는 읽기 전용 권한, artifact/유료 AI API 미사용. **자동화 CI 성공과 ChatGPT 정규 예약의 무인 기억 복원 성공은 서로 다른 검증 대상**이다. 기존 ChatGPT 예약/운영 main은 건드리지 않았다.
