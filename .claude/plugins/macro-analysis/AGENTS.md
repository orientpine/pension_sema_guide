# PLUGIN: macro-analysis

공용 거시경제 에이전트 라이브러리. **command 없음, 스킬 없음 — 에이전트 7개뿐.** `investments-portfolio`와 `stock-consultation`이 `Task(subagent_type="macro-analysis:*")`로 재사용.

plugin.json: version 1.0.1.

## AGENTS (7) — agents/

| Agent | 역할 | 출력 |
|-------|------|------|
| index-fetcher | 지수/환율 수집 (S&P500, NASDAQ, KOSPI, KOSDAQ, USD/KRW) | `index-data.json`, index MD |
| rate-analyst | Fed/BOK 금리 + USD/KRW 전망 | `rate-analysis.json` |
| sector-analyst | 5개 섹터 전망 | `sector-analysis.json` |
| risk-analyst | 지정학/경제/시장 리스크 + Bull/Base/Bear | `risk-analysis.json` |
| leadership-analyst | 7개국 정치/중앙은행 동향 | `leadership-analysis.json` |
| macro-synthesizer | 위 5개 JSON을 **직접 Read**해 종합 | `macro-outlook.json`, `00-macro-outlook.md` |
| macro-critic | 독립 재검색으로 종합 결과 검증 (PASS/FAIL) | 검증 리포트 |

## FLOW (caller가 오케스트레이션)

```
index-fetcher (blocking)
  → rate / sector / risk / leadership (parallel)
  → macro-synthesizer (blocking, JSON만 Read)
  → macro-critic (FAIL → synthesizer 재시도 max 2)
```

출력 파일명/경로는 caller command가 prompt로 지정 (이 플러그인은 고정 파일명 강제 안 함).

## CONVENTIONS

- 각 analyst는 **웹검색 도구를 직접 호출** + 3출처 교차검증 + 원문(`original_text`) 인용.
- `macro-synthesizer`는 prompt 본문 데이터가 아니라 **하위 JSON 파일에서만** 수치를 가져옴. 재해석/재계산 금지.
- `macro-critic`은 synthesizer 결과를 신뢰하지 않고 S&P500/KOSPI/Fed/BOK를 **독립 재검색**해 ±1% 대조.

## ANTI-PATTERNS

- macro-synthesizer가 수치를 생성/추정 — JSON에 없으면 비움.
- analyst가 단일 출처로 수치 확정.
- 이 플러그인을 단독 진입점으로 호출 — command가 없으므로 항상 caller 워크플로우(0.x 단계)에서 호출됨.
