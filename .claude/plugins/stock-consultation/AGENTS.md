# PLUGIN: stock-consultation

주식/ETF 투자 상담 멀티에이전트. 진입점 `commands/stock-consult.md`. 거시 파트는 `macro-analysis` 7개 에이전트를 재사용하고, 종목 파트는 이 플러그인 로컬 에이전트 5개를 사용 (총 12개 서브에이전트).

## STRUCTURE

```
stock-consultation/
├── commands/stock-consult.md   # 오케스트레이터 (진입점)
├── agents/                      # 5 local agents
└── skills/                      # 3 skills
```

## ORCHESTRATION (stock-consult.md)

> 오케스트레이터는 **Task 도구로만** 하위 호출. 직접 웹검색/밸류에이션/검증 금지.

```
세션 폴더 생성 (consultations/YYYY-MM-DD-{ticker|portfolio-theme}-{6자리})
0   macro-analysis 0.1~0.4 재사용 (index→4병렬→synth→critic)
0.5 materials-organizer (옵션: materials_path 제공 시만)
1   stock-screener (포트폴리오/테마 요청만, 단일 종목은 SKIP)
2   stock-valuation  (종목별 N회) → 02-valuation-{ticker}.*
3   bear-case-critic (종목별 N회) → 03-bear-case-{ticker}.*
4   stock-critic (blocking)       → 04-final-verification.* (신뢰도 A~F)
5   직접 조합                      → 05-consultation-summary.md
```

## AGENTS (5 local) — agents/

| Agent | 역할 | 비고 |
|-------|------|------|
| materials-organizer | 사용자 제공 로컬 md 정리 | **웹검색 금지**, 옵션 단계 |
| stock-screener | 후보 종목/ETF 스크리닝 | 포트폴리오 요청만 |
| stock-valuation | PER/PBR/PEG 단순 밸류에이션 | 종목당 ≤3p |
| bear-case-critic | 종목별 반대 논거/리스크 | 일반 시장 비관론 금지 |
| stock-critic | 최종 검증 (출처/과신/면책) | 1회 |

## SKILLS (3) — skills/

- `stock-data-verifier` — 주식/ETF 3출처 교차검증, 원문 인용
- `analyst-common-stock` — 웹검색 직접 호출 공통 규칙
- `file-save-protocol-stock` — JSON+MD 동시 저장 강제

## CONVENTIONS

- 데이터 소스 화이트리스트: 한국=네이버금융/KRX/증권사, 미국=Yahoo/Bloomberg/MarketWatch. **블랙리스트**: 블로그/커뮤니티/유튜브/위키.
- 모든 결과는 JSON+MD 둘 다 저장.
- `05-consultation-summary.md` 말미에 Bogle 면책조항 **필수** 첨부.

## ANTI-PATTERNS

- DCF/Monte Carlo 등 복잡 모델, 구체적 목표주가, "반드시/확실히/무조건" 매수·매도 강권 — 금지.
- 오케스트레이터가 Task 없이 단계 직접 수행하거나 서브에이전트 결과를 생성(환각).
- 파일명은 command 기준 per-ticker 네이밍(`02-valuation-{ticker}.json`, `03-bear-case-{ticker}.json`)으로 command↔agent↔`file-save-protocol-stock` 3자 통일됨. 단일 고정명(`02-valuation-report.json` 등) 재도입 금지 — 다종목 1세션 시 파일 덮어쓰기 발생.
