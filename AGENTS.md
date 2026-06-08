# PROJECT KNOWLEDGE BASE

**Generated:** 2026-06-07
**Commit:** ec07a7f
**Branch:** main

## OVERVIEW

Korean retirement pension fund portfolio recommendation system for 과학기술공제회 (SEMA). Multi-agent system for portfolio analysis with hallucination prevention. Fund data sourced from Zeroin, stored as JSON.

## STRUCTURE

```
pension_sema_guide/
├── AGENTS.md                   # This file (project knowledge base)
├── README.md                   # Public guide & quick start
│
├── .claude/                    # Claude Code project config
│   ├── settings.json           # enabledPlugins + extraKnownMarketplaces (pension-sema-guide)
│   └── plugins/                # Vendored marketplace + plugins (NOT a submodule)
│       ├── .claude-plugin/
│       │   └── marketplace.json  # Marketplace manifest (name: pension-sema-guide)
│       ├── investments-portfolio/
│       │   ├── .claude-plugin/   # plugin.json manifest
│       │   ├── agents/           # 3 agents (fund-portfolio, compliance-checker, output-critic)
│       │   ├── commands/         # portfolio-analyze (orchestrator)
│       │   └── skills/           # specialized skills (+ data-updater/scripts)
│       ├── macro-analysis/       # 7 macro agents
│       ├── stock-consultation/   # stock/ETF multi-agent
│       └── equity-research/      # equity research analyst
│
├── funds/                      # Core fund data (public, non-personal)
│   ├── fund_data.json          # Master data (206 investable funds)
│   ├── fund_fees.json          # Fee data
│   ├── fund_classification.json # Category classification (9 types)
│   ├── deposit_rates.json      # Deposit rate data
│   └── all/                    # Full fund set (2037 funds)
│
├── portfolios/samples/         # Anonymized PUBLIC example reports only
│   └── sample-aggressive/
│       ├── 00-macro-outlook.md       # 거시경제 전망
│       ├── 01-fund-analysis.md       # 펀드 분석
│       ├── 02-compliance-report.md   # 규제 준수 검증
│       ├── 03-output-verification.md # 출력 검증
│       └── 04-portfolio-summary.md   # 최종 요약
│
├── consultations/              # Investment consultation reports (non-personal)
├── resource/                   # Source CSV/XLSX from SEMA
├── docs/                       # Reference documentation
├── scripts/                    # verify_no_pii.sh, verify_plugin.sh
│
└── confidentialData/           # 🔒 개인정보 보관소 (GITIGNORED — 저장소 미포함)
    ├── cbd.md                  #   투자자 프로필
    ├── nouse/                  #   개인 투자계획·잔고
    └── portfolios/             #   실제(개인) 분석 산출물
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Portfolio Analysis** | `.claude/plugins/investments-portfolio/` | Vendored multi-agent plugin |
| Plugin manifest | `.claude/plugins/.claude-plugin/marketplace.json` | Marketplace: pension-sema-guide |
| Fund master data | `funds/fund_data.json` | Single source of truth (206 funds) |
| Fund categories | `funds/fund_classification.json` | 9 categories |
| Fund data schema | `funds/AGENTS.md` | Schema reference |
| Plugin internals | `.claude/plugins/investments-portfolio/AGENTS.md` | Agent orchestration flow |
| Fee data | `funds/fund_fees.json` | Fund fee information |
| Deposit rates | `funds/deposit_rates.json` | Bank deposit rates |
| Public sample reports | `portfolios/samples/` | Anonymized examples ONLY |
| Consultation reports | `consultations/` | Investment consultations (non-personal) |
| Source CSV files | `resource/` | Monthly CSV from SEMA |
| Reference docs | `docs/` | Architecture & improvement plans |
| **Personal data (🔒)** | `confidentialData/` | GITIGNORED — never committed |

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

### 개인정보 보관 정책 (confidentialData)

- **이 저장소는 공개(Public) 저장소입니다.** 개인정보는 절대 커밋하지 않는다.
- 개인별 데이터(투자자 프로필 `cbd.md`, 개인 투자계획·잔고, 실제 분석 산출물 등)는
  **반드시 `confidentialData/` 디렉토리에만 저장**한다.
- `confidentialData/`는 `.gitignore`에 등록되어 있어 저장소에 포함되지 않는다.
- 공개 가능한 예시는 **익명화**하여 `portfolios/samples/`에 둔다 (실명·생년·소속·계좌 금지).
- 커밋 전 `scripts/verify_no_pii.sh`로 PII 누출이 없는지 검증할 것.

## NOTES

- **Data source**: 과학기술공제회 퇴직연금 + 펀드평가사 제로인
- **Base date**: 2026-03-01 (from `funds/fund_data.json` `_meta.version`, sourceFile `26년03월_상품제안서_퇴직연금(DCIRP).csv`)
- **NOTE**: `funds/README.md`는 구버전(2015펀드/5분류)으로 stale — 실제 기준은 `funds/fund_data.json` `_meta`(206 funds, 1 missing K55223C80096)
- **Plugin**: `.claude/plugins/`는 vendored 마켓플레이스(`pension-sema-guide`) + 4개 플러그인(서브모듈 아님). 마켓플레이스 매니페스트는 `.claude/plugins/.claude-plugin/marketplace.json`, 각 플러그인 source는 `./<name>`(마켓플레이스 루트 `.claude/plugins` 기준 상대경로).
- **Plugin registration**: `.claude/settings.json`의 `extraKnownMarketplaces`(directory source, `path: ./.claude/plugins`)로 프로젝트를 열고 신뢰하면 자동 등록·프롬프트. 수동 등록 시 `/plugin marketplace add ./.claude/plugins` 후 `investments-portfolio@pension-sema-guide` 활성화
- **PII 검증**: `scripts/verify_no_pii.sh` (히스토리 전수 스캔), `scripts/verify_plugin.sh` (플러그인 매니페스트 검증)
