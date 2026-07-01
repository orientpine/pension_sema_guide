# 포트폴리오 예시 (익명화)

이 디렉토리는 멀티에이전트 시스템이 생성하는 포트폴리오·세금 상담 보고서의 **익명화된 예시**입니다.

- 실제 개인정보(이름·생년·소속·계좌)는 포함되어 있지 않습니다.
- 투자자 프로필은 가상의 값으로 대체되었습니다.
- 실제 분석 결과는 `confidentialData/`(gitignore 대상)에 저장되며 공개되지 않습니다.

## 구조

```
sample-aggressive/
├── 00-macro-outlook.md        # 거시경제 전망
├── 01-fund-analysis.md        # 펀드 분석 및 추천
├── 02-compliance-report.md    # DC형 규제 준수 검증
├── 03-output-verification.md  # 환각 방지 출력 검증
└── 04-portfolio-summary.md    # 최종 포트폴리오 요약
```

```
sample-tax-consult/            # /pension-tax-advisor:tax-consult 출력 예시
├── 00-educator.md             # 납입·운용·수령 3단계 세제 교육
├── 01-strategy.md             # 개인 맞춤 절세 전략 초안
├── 02-calc-verify.json/.md    # python3 독립 재계산 검증
├── 03-critic.json/.md         # A~F 신뢰도 채점 + 반론(devil-advocate)
└── 04-summary.md              # 최종 요약 (검증 통과 금액만 + 검증 부록)
```
