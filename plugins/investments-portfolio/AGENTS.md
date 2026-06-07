# PLUGIN: investments-portfolio

Vendored Claude Code plugin. DC 연금 포트폴리오 분석 멀티에이전트. 환각 방지가 핵심 설계.

## STRUCTURE

```
investments-portfolio/
├── .claude-plugin/plugin.json   # name/version 1.2.0
├── commands/portfolio-analyze.md # 오케스트레이터 (진입점)
├── agents/                       # 3 agents (model: opus)
└── skills/                       # 11 skills
    └── data-updater/scripts/     # CSV→JSON ETL (python)
```

## ORCHESTRATION (portfolio-analyze.md)

> 오케스트레이터는 **반드시 Task 도구로만** 하위 에이전트 호출. 직접 분석/검증 금지.

```
0.1 index-fetcher (blocking)        → index-data.json, 99-index-data.md
0.2 ‖ rate / sector / risk / leadership-analyst (parallel)
0.3 macro-synthesizer (blocking)    → macro-outlook.json, 00-macro-outlook.md
0.4 macro-critic (blocking)         → FAIL → 0.3 재시도 (max 2)
1   fund-portfolio (blocking)       → 01-fund-analysis.md
2   compliance-checker (blocking)   → FAIL → 1 재호출 (max 3) → 02-compliance-report.md
3   output-critic (blocking)        → 03-output-verification.md
4   직접 조합                        → 04-portfolio-summary.md
```

**주의**: 0.x의 macro 에이전트(index-fetcher, *-analyst, macro-synthesizer/critic)는 이 플러그인 `agents/`에 없음 — command가 외부/공유 에이전트로 참조. 이 플러그인이 정의하는 건 3개뿐.

## AGENTS (frontmatter)

| Agent | tools | skills |
|-------|-------|--------|
| fund-portfolio | Read,Glob,Grep,WebSearch,WebFetch,Write | analyst-common, file-save-protocol, bogle-principles, dc-pension-rules, fund-selection-criteria, fund-output-template, perspective-balance, devil-advocate |
| compliance-checker | Read,Bash,Write | file-save-protocol |
| output-critic | Read,Grep,Write | file-save-protocol, devil-advocate |

## SKILLS (11) — 3 그룹

- **환각 방지**: web-search-verifier(3출처 교차검증+original_text 강제), analyst-common, perspective-balance(Bull/Bear/Base), devil-advocate, file-save-protocol(저장 환각 방지)
- **도메인 규칙**: dc-pension-rules(canonical 70%/40% 한도), bogle-principles, fund-selection-criteria
- **출력 포맷**: macro-output-template, fund-output-template, file-save-protocol
- **ETL**: data-updater

## DC HARD LIMITS — canonical: `skills/dc-pension-rules/SKILL.md`

- 위험자산 70% 한도 (채권혼합형 포함), 단일 펀드 40% 한도, 섹터/테마 집중 규칙(예: Tech/AI 40%)
- `agents/fund-portfolio.md` + `agents/compliance-checker.md`에 하드게이트로 재강제

## DATA PIPELINE — `skills/data-updater/scripts/`

- `update_fund_data.py --file <CSV>` → `fund_data.json`, `fund_fees.json` (+ `all/all_*`) → 체인으로 `classify_funds.py` 호출
- `classify_funds.py`: fund_data → `fund_classification.json` / `all_fund_classification.json` (키워드 기반 category/riskAsset/assetClass/region/themes/hedged/riskLevel)
- `deposit_rates.json`은 스크립트 산출물 아님 — 스킬 Phase 5 사용자 입력으로만 갱신

## ANTI-PATTERNS (절대 금지)

- 오케스트레이터: Task 없이 단계 수행, fund_data.json 직접 읽고 추천, DC 70% 직접 계산
- fund-portfolio: 파일 Read 없이 추천, 누락 파일에 추정 데이터, 근거 없는 "인기/성과 우수" 표현, 예금 vs 채권 비교 없이 채권 추천
- compliance-checker: 70%→71% 해석, 40% 초과 허용
- data-updater: 스크립트 못 찾으면 자체 Python 대체(금지), 예금금리 웹검색(금지, 사용자 입력만)
