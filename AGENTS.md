# PROJECT KNOWLEDGE BASE

**Generated:** 2026-06-08
**Commit:** 04aa5b0
**Branch:** main

## OVERVIEW

Korean retirement pension fund portfolio recommendation system for 과학기술공제회 (SEMA). Prompt-defined multi-agent system (no app runtime — logic lives in plugin markdown + a Python ETL/TDF-enrichment toolchain). Fund data sourced from 제로인(Zeroin), stored as JSON. Hallucination prevention is the core design constraint.

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
│       ├── investments-portfolio/  # AGENTS.md — 3 agents + portfolio-analyze + 11 skills
│       ├── macro-analysis/          # AGENTS.md — 7 shared macro agents (no command)
│       ├── stock-consultation/      # AGENTS.md — 5 agents + stock-consult command + 3 skills
│       └── equity-research/         # single equity-research-analyst agent
│
├── funds/                      # Core fund data (public, non-personal) — see funds/AGENTS.md
│   ├── fund_data.json          # Master data (205 investable funds)
│   ├── fund_fees.json          # Fee data (key: fundCode)
│   ├── fund_classification.json # Category classification (key: 펀드명, 9 types)
│   ├── tdf_data.json           # TDF master (75 funds, deterministic enrichment)
│   ├── tdf_fees.json           # TDF fees
│   ├── deposit_rates.json      # Deposit rates (manual-update only)
│   └── all/                    # Full universe (2104 funds, *_all_* — authoritative for TDF enrichment)
│
├── tests/                      # pytest suite for TDF enrichment (update_tdf_data.py)
├── index-data.json             # Market index data (index-fetcher output snapshot)
├── pytest.ini                  # testpaths=tests
│
├── portfolios/samples/         # Anonymized PUBLIC example reports only
│   └── sample-aggressive/      # 00-macro → 01-fund → 02-compliance → 03-verify → 04-summary
│
├── consultations/              # Stock/ETF consultation reports (non-personal)
├── resource/                   # Source CSV/XLSX from SEMA (monthly 상품제안서)
├── docs/                       # Reference documentation
├── scripts/                    # verify_no_pii.sh, verify_plugin.sh
│
└── confidentialData/           # 🔒 개인정보 보관소 (GITIGNORED — 저장소 미포함)
    ├── investor-profile.md                  #   투자자 프로필
    ├── nouse/                  #   개인 투자계획·잔고
    └── portfolios/             #   실제(개인) 분석 산출물
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Portfolio Analysis** | `.claude/plugins/investments-portfolio/` | Vendored multi-agent plugin |
| Plugin manifest | `.claude/plugins/.claude-plugin/marketplace.json` | Marketplace: pension-sema-guide |
| Fund master data | `funds/fund_data.json` | Single source of truth (205 funds, `_meta.version`) |
| Fund data schema | `funds/AGENTS.md` | Schema + join keys + TDF contract |
| Portfolio plugin | `.claude/plugins/investments-portfolio/AGENTS.md` | Orchestration + DC limits + anti-patterns |
| Macro agents | `.claude/plugins/macro-analysis/AGENTS.md` | 7 shared agents (reused by other plugins) |
| Stock/ETF consult | `.claude/plugins/stock-consultation/AGENTS.md` | stock-consult orchestration |
| Data ETL scripts | `.claude/plugins/investments-portfolio/skills/data-updater/scripts/` | CSV→JSON, TDF enrichment |
| TDF enrichment tests | `tests/AGENTS.md` | pytest suite (⚠ import-path gotcha) |
| Public sample reports | `portfolios/samples/` | Anonymized examples ONLY |
| Source CSV files | `resource/` | Monthly 상품제안서 CSV/XLSX |
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
- 개인별 데이터(투자자 프로필 `investor-profile.md`, 개인 투자계획·잔고, 실제 분석 산출물 등)는
  **반드시 `confidentialData/` 디렉토리에만 저장**한다.
- `confidentialData/`는 `.gitignore`에 등록되어 있어 저장소에 포함되지 않는다.
- 공개 가능한 예시는 **익명화**하여 `portfolios/samples/`에 둔다 (실명·생년·소속·계좌 금지).
- 커밋 전 `scripts/verify_no_pii.sh`로 PII 누출이 없는지 검증할 것.

## NOTES

- **Data source**: 과학기술공제회 퇴직연금 + 펀드평가사 제로인
- **Base date**: `funds/fund_data.json` `_meta`(version 2026-06-01, sourceFile `26년06월_상품제안서_퇴직연금(DCIRP).csv`, recordCount 205, missing `["K55205BU9205","K55223C80096"]`). `funds/all/` = 2104. TDF는 별도 기준일(`tdf_data.json` 2026-06-04, 75개) — 직접 교차비교 금지.
- **STALE**: `funds/README.md`(구버전 2015펀드/5분류) 무시. 실제 기준은 항상 각 JSON의 `_meta`.
- **Plugin**: `.claude/plugins/`는 vendored 마켓플레이스(`pension-sema-guide`) + 4개 플러그인(서브모듈 아님). 마켓플레이스 매니페스트는 `.claude/plugins/.claude-plugin/marketplace.json`, 각 플러그인 source는 `./<name>`(마켓플레이스 루트 `.claude/plugins` 기준 상대경로).
- **Plugin registration**: `.claude/settings.json`의 `extraKnownMarketplaces`(directory source, `path: ./.claude/plugins`)로 프로젝트를 열고 신뢰하면 자동 등록·프롬프트. 수동 등록 시 `/plugin marketplace add ./.claude/plugins` 후 `investments-portfolio@pension-sema-guide` 활성화
- **PII 검증**: `scripts/verify_no_pii.sh` (히스토리 전수 스캔), `scripts/verify_plugin.sh` (플러그인 매니페스트 검증)
- **Tests broken**: `tests/conftest.py`의 `SCRIPTS_DIR`가 `plugins/...`(`.claude/` 누락)를 가리켜 `update_tdf_data` import 실패 → 5개 테스트 collection 에러. 자세한 내용은 `tests/AGENTS.md`.
