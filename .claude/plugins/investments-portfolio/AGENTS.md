# PLUGIN: investments-portfolio

Vendored Claude Code plugin. DC 연금 포트폴리오 분석 멀티에이전트. 환각 방지가 핵심 설계.

## STRUCTURE

```
investments-portfolio/
├── .claude-plugin/plugin.json   # name/version 1.2.0
├── commands/portfolio-analyze.md # 오케스트레이터 (진입점)
├── agents/                       # 3 agents (opus; compliance-checker: sonnet)
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

## TDF SUPPORT POLICY — canonical: `skills/dc-pension-rules/SKILL.md`

- **자산 3-상태 분류**: 위험자산(70% 산입), 안전자산(제외), **적격TDF(면제)**.
- **70% 한도 면제**: 적격TDF는 위험자산이나 70% 한도 계산(분자)에서 제외 (`nonExemptRiskWeight` 수식 적용).
- **3지선다 게이트**: 포트폴리오 구성 시 `예금 | TDF | 채권` 중 하나를 반드시 포함하여 안전성 확보.
- **데이터 관리**: `tdf_data.json`, `tdf_fees.json` 사용. `update_tdf_data.py`로 갱신.
- **환각 방지**: TDF 인지 (데이터 소스, 수수료 검증, 적격성 판정, 연령 매핑 4개 게이트).

### TDF 핵심 금지사항
- **TDF ≠ 안전자산**: TDF는 위험자산의 예외일 뿐 안전자산이 아님. 혼동 금지.
- **40% 한도**: 일반 펀드 40%는 하드 리밋, 적격TDF 40% 초과는 자체 권고(Warning) 사항.
- **추정 금지**: 데이터 누락 시 과거 성과나 수수료를 임의로 추정하여 추천 금지.

## DATA PIPELINE — `skills/data-updater/scripts/`

매월: `fetch_latest_proposal.py`(최신 xlsx 다운로드) → `xlsx_to_csv.py`(xlsx→resource CSV) → `update_fund_data.py`(CSV→JSON, 분류 자동) → `classify_funds.py`(분류 재생성).

- `fetch_latest_proposal.py`: 미래에셋 게시판(categoryId=1494)에서 파일명 `YY년MM월` 최신 DCIRP xlsx 선택. `--convert`로 변환 연결. stdlib(urllib)만.
- `xlsx_to_csv.py`: `실적배당형(펀드, ETF)` 시트→CSV. 숫자서식 적용(2자리/천단위), 25컬럼, BOM, CRLF. Excel 15유효자리+ROUND_HALF_UP 재현. **openpyxl 필요**. 26년03월 역검증 byte-identical.
- `update_fund_data.py`/`classify_funds.py`: stdlib만.

## ANTI-PATTERNS (절대 금지)

- 오케스트레이터: Task 없이 단계 수행, fund_data.json 직접 읽고 추천, DC 70% 직접 계산
- fund-portfolio: 파일 Read 없이 추천, 누락 파일에 추정 데이터, 근거 없는 "인기/성과 우수" 표현, 예금 vs 채권 비교 없이 채권 추천
- compliance-checker: 70%→71% 해석, 40% 초과 허용, **적격TDF를 안전자산으로 오분류** (면제 위험자산임)
- data-updater: 스크립트 못 찾으면 자체 Python 대체(금지), 예금금리 웹검색(금지, 사용자 입력만)
- **TDF 공통**: 적격TDF 40% 초과를 ERROR로 처리(WARNING 대상), 총보수 추정(데이터 미존재 시 사람 확인 필수)
