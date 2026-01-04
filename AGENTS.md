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
│   └── 2026-Q1-investment-plan.md  # Current quarter plan
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

## NOTES

- Data source: 과학기술공제회 퇴직연금 + 펀드평가사 제로인
- Base date: 2026.01.02
- Root `README.md` contains investment management guide & rebalancing workflow
- Fund index: `funds/README.md` (205 funds sorted by 3mo return)
