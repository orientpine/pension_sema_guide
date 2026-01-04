# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-04
**Commit:** 0b24e7c
**Branch:** main

## OVERVIEW

Korean retirement pension fund portfolio recommendation system for 과학기술공제회 (SEMA). Transforms crawled fund data from Zeroin into structured markdown documentation with AI-powered portfolio analysis.

## STRUCTURE

```
investments/
├── .claude/agents/     # AI agent configurations
│   └── fund-portfolio.md  # Portfolio recommendation agent
├── funds/              # Core data + ETL scripts
│   ├── fund_data.json  # Master data (205 funds)
│   ├── *.py, *.js      # Pipeline scripts
│   ├── 주식형/         # Domestic equity (51)
│   ├── 해외주식형/     # Global equity (86)
│   ├── 채권혼합형/     # Bond-mixed (18)
│   └── [6 more categories]
├── portfolio/          # Personal investment plans & tracking
│   ├── 2026-Q1-investment-plan.md    # 퇴직연금 분기별 계획
│   └── 2026-personal-pension-plan.md # 개인연금 연간 계획
└── README.md           # Project entry (binary/corrupted)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Portfolio recommendation | `.claude/agents/fund-portfolio.md` | Invoke via `fund-portfolio` agent |
| Fund master data | `funds/fund_data.json` | Single source of truth (JSON) |
| Update fund data | `funds/extract_funds.py` | Requires browser snapshot |
| Regenerate markdown | `funds/generate_md.js` | Run with Node.js |
| Fund summary/index | `funds/README.md` | 205 funds sorted by 3mo return |
| Individual fund info | `funds/[category]/[fund].md` | Standardized template |
| **Investment plans** | `portfolio/` | Quarterly plans & rebalancing records |
| Current quarter plan | `portfolio/2026-Q1-investment-plan.md` | Active investment plan |
| Personal pension plan | `portfolio/2026-personal-pension-plan.md` | 연금저축+IRP ETF 운용 계획 |

## CONVENTIONS

### Fund Categorization (9 types)
Classification by keyword matching in fund name:
- **Region first**: 해외/글로벌/미국/차이나 → overseas
- **Asset class**: 주식 (stock), 채권 (bond), 혼합 (mixed)
- **Special**: TDF/MMF/EMP/리츠/골드 → 기타

### Data Pipeline
1. Browser snapshot → `extract_funds.py` → `fund_data.json`
2. `fund_data.json` → `generate_md.js` → category folders + README

### File Naming
- Special chars `\/:*?"<>|` removed
- Brackets `[]` → parentheses `()`
- Max 100 chars

### Commit Protocol (필수)

파일 변경 후 **반드시** 아래 절차를 따를 것:

1. **변경 요약 작성**: 무엇이 변경되었는지 명확히 정리
2. **커밋 메시지 제안**: 상세한 커밋 메시지 작성
3. **사용자 확인 요청**: 커밋 여부를 사용자에게 문의

**커밋 메시지 형식**:
```
<type>: <subject>

<body>
- 변경 사항 1
- 변경 사항 2
- ...

<footer>
```

**Type 종류**:
| Type | 설명 |
|------|------|
| `feat` | 새로운 기능/계획 추가 |
| `fix` | 오류 수정 |
| `docs` | 문서 수정 |
| `refactor` | 구조 변경 (기능 변화 없음) |
| `chore` | 기타 유지보수 |

**예시**:
```
docs(portfolio): DC형 70% 한도 준수 포트폴리오 조정

- 위험자산 100% → 70%로 축소 (DC형 규제 준수)
- 6개 펀드 → 7개 펀드로 변경
- 채권형 펀드 2개 신규 편입 (30%)
- 신한스노우볼인컴 제외 (채권혼합도 위험자산 분류)
- 리밸런싱 주기: 연 1회 → 반기 1회

Resolves: DC형 위험자산 한도 초과 이슈
```

## ANTI-PATTERNS (THIS PROJECT)

- **Never** edit generated `.md` files in category folders directly (will be overwritten)
- **Never** modify `fund_data.json` manually (use extraction scripts)
- **Avoid** running `generate_md.js` without updated `fund_data.json`

## COMMANDS

```bash
# Extract fund data from browser snapshot
cd funds && python extract_funds.py

# Regenerate all markdown files
cd funds && node generate_md.js

# Check for duplicate funds
cd funds && node check_duplicates.js

# Verify fund data integrity
cd funds && node verify_funds.js
```

## AGENT USAGE

The `fund-portfolio` agent provides portfolio recommendations:

```
# Invoke via Claude Code
Use the fund-portfolio agent for:
- Fund recommendations by risk profile (공격형/중립형/안정형)
- Portfolio allocation suggestions
- Fund comparison and analysis
```

Asset allocation presets (from agent config):
| Profile | 주식형 | 주식혼합형 | 채권혼합형 | 채권형 |
|---------|--------|-----------|-----------|--------|
| 공격형 | 60-70% | 20-30% | 10% | 0% |
| 중립형 | 30-40% | 20-30% | 20-30% | 10-20% |
| 안정형 | 10-20% | 20% | 30-40% | 30-40% |

### 포트폴리오 분석 필수 프로세스

**⚠️ 중요**: 포트폴리오 전략 수립/검토 시 **반드시 웹검색으로 비판적 근거 자료 수집 후 진행**

#### 웹검색 필수 항목 (병렬 실행)

| 카테고리 | 검색 주제 | 목적 |
|----------|----------|------|
| **거시경제** | 금리 전망, 환율 전망 | 자산배분 근거 |
| **시장 전망** | S&P500/코스피 전망 | 지역 배분 근거 |
| **섹터 전망** | 반도체/AI, 로봇, 헬스케어 등 | 테마 집중도 검증 |
| **비판적 시각** | 버블 우려, 리스크 요인 | 균형잡힌 분석 |
| **자산배분 연구** | 연령대별 퇴직연금 전략 | 학술적 근거 |

#### 검색 예시 쿼리

```
# 낙관적 전망
- "2026 semiconductor AI market outlook forecast"
- "2026 S&P 500 stock market forecast Wall Street prediction"
- "humanoid robot market forecast 2025 2026"

# 비판적/균형 전망
- "AI bubble risk 2026"
- "semiconductor oversupply risk"
- "market correction risk 2026"

# 자산배분 근거
- "30대 퇴직연금 자산배분 전략"
- "retirement portfolio allocation by age research"
```

#### 분석 워크플로우

```
[1단계] 로컬 데이터 분석
    └── funds/fund_data.json 기반 펀드 성과 분석

[2단계] 웹검색 근거 수집 (6+ 검색 병렬 실행)
    ├── 거시경제 전망 (금리, 환율)
    ├── 시장 전망 (미국, 한국, 신흥국)
    ├── 섹터별 전망 (포트폴리오 편입 섹터)
    ├── 비판적 시각 (버블, 리스크)
    └── 학술적 근거 (자산배분 연구)

[3단계] 종합 분석 및 권고
    ├── 낙관적 근거 + 비판적 근거 균형 검토
    ├── 출처 명시
    └── 조건부 권고 (시나리오별)
```

#### 결과물 필수 포함 사항

- **출처 테이블**: 각 권고의 근거가 되는 웹검색 출처 명시
- **시나리오 분석**: 낙관/중립/비관 시나리오별 포트폴리오 영향
- **비판적 검토**: 현재 전략의 잠재적 리스크 요인

## PENSION OPERATION STRATEGY

### 퇴직연금 (DC형) 운용법

| 항목 | 내용 |
|------|------|
| **계좌** | 과학기술인공제회 (SEMA) |
| **위험자산 한도** | 70% |
| **상품 유형** | 액티브 펀드 (제공 상품만 선택 가능) |
| **운용 비용** | 0.5~1.5% (총보수) |
| **운용 전략** | 섹터/테마 집중, 알파(초과수익) 추구 |
| **계획 파일** | `portfolio/2026-Q1-investment-plan.md` |

**현재 포트폴리오 (공격형, DC형 70% 한도 준수, v1.3)**:
| 펀드 | 유형 | 비중 | 총보수 | 위험자산 |
|------|:----:|:----:|:------:|:--------:|
| 삼성글로벌반도체UH | 해외주식 | 15% | 1.19% | O |
| 삼성미국S&P500UH | 해외주식 | 20% | 0.69% | O |
| NH-Amundi 필승코리아 | 주식 | 10% | 0.667% | O |
| 삼성휴머노이드로봇UH | 해외주식 | 5% | 1.29% | O |
| 미래에셋배당커버드콜 | 주식혼합 | 20% | 0.62% | O |
| 키움더드림단기채 | 채권 | 15% | 0.175% | X |
| 한국투자크레딧포커스ESG | 채권 | 15% | 0.291% | X |
| **위험자산 합계** | | **70%** | | |
| **안전자산 합계** | | **30%** | | |
| **가중평균 총보수** | | | **~0.65%** | |

### 개인연금 (연금저축+IRP) 운용법

| 항목 | 내용 |
|------|------|
| **계좌** | 증권사 연금저축펀드 + IRP |
| **위험자산 한도** | 100% (제한 없음) |
| **상품 유형** | 패시브 ETF (직접 투자) |
| **운용 비용** | 0.05~0.1% (총보수) |
| **운용 전략** | 인덱스 분산, 저비용 베타(시장수익) 추종 |
| **계획 파일** | `portfolio/2026-personal-pension-plan.md` |

**현재 포트폴리오 (100% 주식 ETF)**:
| ETF | 티커 | 비중 |
|-----|:----:|:----:|
| TIGER 미국S&P500 | 360750 | 40% |
| TIGER 미국나스닥100 | 133690 | 30% |
| KODEX 미국반도체MV | 390390 | 20% |
| KODEX 200 | 069500 | 10% |

### 상호보완 전략

```
┌──────────────────────────────────────────────────────┐
│              연금 자산 운용 역할 분담                   │
├──────────────────────────────────────────────────────┤
│                                                      │
│   퇴직연금 (DC)          개인연금 (연금저축+IRP)       │
│   ─────────────          ─────────────────────       │
│   • 액티브 펀드           • 패시브 ETF               │
│   • 섹터/테마 집중         • 인덱스 분산              │
│   • 높은 비용             • 저비용                   │
│   • 알파 추구             • 베타 추종                │
│                                                      │
│   → 초과수익 기회         → 비용 절감 (31년 4천만원+) │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 납입 현황 요약

| 계좌 | 월 납입 | 연간 납입 | 세액공제 |
|------|--------:|----------:|---------:|
| 퇴직연금 (DC) | 100만원 | 1,200만원 | - |
| 연금저축펀드 | 33만원 | 400만원 | 66만원 |
| IRP | 25만원 | 300만원 | 49.5만원 |
| **합계** | **158만원** | **1,900만원** | **115.5만원** |

## NOTES

- Data source: 과학기술공제회 퇴직연금 + 펀드평가사 제로인
- Base date: 2026.01.02
- Root `README.md` contains investment management guide & rebalancing workflow
- Fund index: `funds/README.md` (205 funds sorted by 3mo return)
