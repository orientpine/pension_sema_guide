# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-31
**Commit:** 3c09eed
**Branch:** main

## OVERVIEW

Korean retirement pension fund portfolio recommendation system for 과학기술공제회 (SEMA). Multi-agent system for portfolio analysis with hallucination prevention. Fund data sourced from Zeroin, stored as JSON.

## STRUCTURE

```
investmunts_cbd/
├── AGENTS.md                   # This file (project knowledge base)
├── README.md                   # Investment management guide & rebalancing workflow
│
├── funds/                      # Core fund data
│   ├── fund_data.json          # Master data (2015 funds)
│   ├── fund_fees.json          # Fee data
│   ├── fund_classification.json # Category classification (6 types)
│   ├── deposit_rates.json      # Deposit rate data
│   └── README.md               # Fund index (sorted by return)
│
├── portfolios/                 # Auto-generated portfolio analysis reports
│   └── YYYY-MM-DD-{profile}-{id}/
│       ├── 00-macro-outlook.md       # 거시경제 전망
│       ├── 01-fund-analysis.md       # 펀드 분석 (or 01-leadership-analyst.md)
│       ├── 02-compliance-report.md   # 규제 준수 검증
│       ├── 03-output-verification.md # 출력 검증
│       └── 04-portfolio-summary.md   # 최종 요약
│
├── consultations/              # Investment consultation reports
│   └── YYYY-MM-DD-{ticker}-{topic}/
│
├── honeypot/                   # Plugin submodule (git submodule)
│   └── plugins/investments-portfolio/
│       ├── agents/             # 12 Multi-agent system
│       ├── skills/             # 11 Specialized skills
│       └── scripts/            # Data pipeline scripts
│
├── resource/                   # Source CSV files from SEMA
├── docs/                       # Reference documentation
└── .sisyphus/                  # Work session artifacts
    ├── plans/                  # Refactoring plans
    └── drafts/                 # Draft documents
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Portfolio Analysis** | `honeypot/plugins/investments-portfolio/` | Multi-agent system |
| Fund master data | `funds/fund_data.json` | Single source of truth (2015 funds) |
| Fund categories | `funds/fund_classification.json` | 6 categories |
| Fee data | `funds/fund_fees.json` | Fund fee information |
| Deposit rates | `funds/deposit_rates.json` | Bank deposit rates |
| Portfolio reports | `portfolios/` | Auto-generated analysis |
| Consultation reports | `consultations/` | Investment consultations |
| Source CSV files | `resource/` | Monthly CSV from SEMA |
| Reference docs | `docs/` | Architecture & improvement plans |

## CONVENTIONS

### Commit Protocol

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

### Language Policy

- 모든 설명과 지침은 항상 한국어로 작성할 것

## NOTES

- **Data source**: 과학기술공제회 퇴직연금 + 펀드평가사 제로인
- **Base date**: 2026.01.21 (from fund_data.json _meta)
- **Submodule**: `honeypot/` is a git submodule - update with `git submodule update --remote`
- **Plugin registration**: Via Claude Code `/plugin marketplace add`
