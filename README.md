# AI Token Optimization

목표: Activepieces에서 여러 AI를 협업시키되 API 호출과 토큰을 최소화하고, 실제 검증되지 않은 실행을 완료로 보고하지 않는다.

## 현재 운영 원칙
- 기본 경로는 짧은 답변이 가능한 저비용/무료 모델부터 사용한다.
- 간단한 질문은 AI 호출 1회로 끝낸다.
- 복잡하거나 검증이 필요한 요청만 두 번째 모델로 전달한다.
- 세 번째 모델 호출은 독립적인 검증 가치가 있을 때만 허용한다.
- 최신 정보가 필요할 때만 웹 검색을 사용하고 검색 횟수를 제한한다.
- API 키와 비밀값은 GitHub에 저장하지 않는다. Activepieces의 Connections/Secrets에 보관한다.
- 샘플 테스트 성공과 실제 운영 웹훅 성공을 구분한다.

## Activepieces 플로우
이 저장소는 문서와 정적 설정 검증용이다. Activepieces 플로우의 실제 상태는 Activepieces에서 별도로 확인한다.

1. EVOLUTION MAX ULTRA: Claude 단일 호출 경로
2. ChatGPT + Gemini: OpenAI 초안 → Gemini 최종 답변
3. Gemini + Claude: Gemini 초안 → Claude 최종 검토

모델 이름/가용성 및 요금은 계정과 시점에 따라 달라질 수 있으므로 무료라고 단정하지 말고 실제 사용량과 청구 내역을 확인한다.

## 검증
`python -m unittest discover -s tests -v`

GitHub Actions는 설정 파일과 테스트를 검사한다. 이것은 Activepieces 실서비스 실행이나 AI 응답 품질을 보증하지 않는다.


## 자동 실행
GitHub Actions는 `main` 브랜치에 변경 사항이 푸시되거나 Pull Request가 열릴 때 정책 테스트를 자동 실행하도록 설정되어 있다. 실행 결과는 저장소의 Actions 탭에서 확인한다.
