# 날짜/SSOT 레지스트리

대상: `.claude/plugins` 하위 모든 `.md` 파일의 `YYYY-MM-DD` 리터럴 전수 추출 결과.

분류 기준:
- `SEMANTIC`: 에이전트가 기준일/데이터 버전의 진실값으로 비교·표기하는 날짜. SSOT 포인터를 반드시 지정한다.
- `ILLUSTRATIVE`: frontmatter/변경이력 날짜, 샘플 경로 날짜, fenced 예시 출력블록·예시 JSON 내부 날짜.
- 모호한 항목은 fail-closed 원칙상 SEMANTIC으로 분류해야 하나, 본 레지스트리에서는 주변 ±3라인 확인 결과 모호 항목이 없었다.

- grep occurrence count: `114`
- SEMANTIC rows with missing ssot-pointer: `0`

| file:line | literal | class | ssot-pointer | 처리방침 |
|---|---|---|---|---|
| .claude/plugins/investments-portfolio/agents/compliance-checker.md:630 | 2026-01-05 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/agents/compliance-checker.md:631 | 2026-06-07 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/agents/fund-portfolio.md:1140 | 2026-06-07 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/agents/output-critic.md:70 | 2026-06-04 | SEMANTIC | funds/tdf_data.json#_meta.version | remove-rule |
| .claude/plugins/investments-portfolio/agents/output-critic.md:70 | 2026-03-01 | SEMANTIC | funds/fund_data.json#_meta.version | remove-rule |
| .claude/plugins/investments-portfolio/agents/output-critic.md:378 | 2026-06-04 | SEMANTIC | funds/tdf_data.json#_meta.version | remove-rule |
| .claude/plugins/investments-portfolio/agents/output-critic.md:378 | 2026-03-01 | SEMANTIC | funds/fund_data.json#_meta.version | remove-rule |
| .claude/plugins/investments-portfolio/agents/output-critic.md:710 | 2026-01-05 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/agents/output-critic.md:711 | 2026-06-07 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/agents/output-critic.md:714 | 2026-03-01 | SEMANTIC | funds/fund_data.json#_meta.version | remove-rule |
| .claude/plugins/investments-portfolio/agents/output-critic.md:717 | 2026-06-04 | SEMANTIC | funds/tdf_data.json#_meta.version | remove-rule |
| .claude/plugins/investments-portfolio/commands/portfolio-analyze.md:136 | 2026-02-02 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/commands/portfolio-analyze.md:187 | 2026-06-08 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/commands/portfolio-analyze.md:194 | 2026-06-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/commands/portfolio-analyze.md:195 | 2026-06-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/commands/portfolio-analyze.md:196 | 2026-06-04 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/commands/portfolio-analyze.md:197 | 2026-06-07 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/commands/portfolio-analyze.md:669 | 2026-02-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/commands/portfolio-analyze.md:670 | 2026-06-08 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/analyst-common/SKILL.md:228 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/bogle-principles/SKILL.md:181 | 2026-01-15 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/data-updater/SKILL.md:277 | 2026-01-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/data-updater/SKILL.md:278 | 2026-01-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/data-updater/SKILL.md:286 | 2026-01-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/data-updater/SKILL.md:288 | 2026-01-21 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/data-updater/SKILL.md:327 | 2026-01-21 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/data-updater/SKILL.md:337 | 2026-01-31 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/data-updater/SKILL.md:339 | 2026-01-31 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/data-updater/SKILL.md:560 | 2026-01-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/data-updater/scripts/README.md:252 | 2026-01-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/data-updater/scripts/README.md:292 | 2026-01-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/data-updater/scripts/README.md:294 | 2026-01-21 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/dc-pension-rules/SKILL.md:381 | 2026-01-15 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/dc-pension-rules/SKILL.md:382 | 2026-01-31 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/devil-advocate/SKILL.md:252 | 2026-01-31 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/file-save-protocol/SKILL.md:88 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/file-save-protocol/SKILL.md:216 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/file-save-protocol/SKILL.md:275 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/file-save-protocol/SKILL.md:276 | 2026-02-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/fund-output-template/SKILL.md:409 | 2026-01-15 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/fund-output-template/SKILL.md:410 | 2026-06-07 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/fund-output-template/SKILL.md:411 | 2026-01-30 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/fund-selection-criteria/SKILL.md:278 | 2026-02-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/fund-selection-criteria/SKILL.md:598 | 2026-01-15 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/fund-selection-criteria/SKILL.md:599 | 2026-06-07 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/macro-output-template/SKILL.md:437 | 2026-01-15 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/macro-output-template/SKILL.md:438 | 2026-01-30 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/macro-output-template/SKILL.md:439 | 2026-02-01 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/perspective-balance/SKILL.md:198 | 2026-01-31 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/web-search-verifier/SKILL.md:359 | 2026-01-12 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/investments-portfolio/skills/web-search-verifier/SKILL.md:360 | 2026-01-12 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/index-fetcher.md:125 | 2026-01-10 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/index-fetcher.md:144 | 2026-01-06 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/index-fetcher.md:206 | 2026-01-21 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/leadership-analyst.md:652 | 2026-01-06 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/leadership-analyst.md:653 | 2026-01-21 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/macro-critic.md:453 | 2024-11-28 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/macro-critic.md:490 | 2026-01-11 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/macro-critic.md:491 | 2024-11-28 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/macro-critic.md:523 | 2024-11-28 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/macro-critic.md:559 | 2026-01-11 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/macro-critic.md:560 | 2024-11-28 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/macro-critic.md:568 | 2024-11-28 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/macro-critic.md:600 | 2026-01-31 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/macro-synthesizer.md:39 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/macro-synthesizer.md:456 | 2026-01-31 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/rate-analyst.md:197 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/risk-analyst.md:229 | 2026-01-21 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/macro-analysis/agents/sector-analyst.md:239 | 2026-01-21 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/bear-case-critic.md:110 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/bear-case-critic.md:463 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/bear-case-critic.md:473 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/bear-case-critic.md:483 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/bear-case-critic.md:493 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/bear-case-critic.md:514 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/bear-case-critic.md:653 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/bear-case-critic.md:654 | 2026-01-20 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/materials-organizer.md:80 | 2026-01-15 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/materials-organizer.md:117 | 2026-01-15 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/materials-organizer.md:168 | 2026-01-15 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/materials-organizer.md:243 | 2026-01-15 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-critic.md:995 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:395 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:401 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:407 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:413 | 2025-12-31 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:420 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:443 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:449 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:455 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:461 | 2025-12-31 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:468 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:489 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:600 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-screener.md:601 | 2026-01-20 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-valuation.md:113 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-valuation.md:477 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-valuation.md:493 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-valuation.md:502 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-valuation.md:510 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-valuation.md:518 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-valuation.md:538 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-valuation.md:659 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/agents/stock-valuation.md:660 | 2026-01-20 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/commands/stock-consult.md:78 | 2026-02-02 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/commands/stock-consult.md:82 | 2026-02-02 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/commands/stock-consult.md:572 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/commands/stock-consult.md:573 | 2026-02-02 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/skills/analyst-common-stock/SKILL.md:242 | 2026-01-20 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/skills/file-save-protocol-stock/SKILL.md:85 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/skills/file-save-protocol-stock/SKILL.md:215 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/skills/file-save-protocol-stock/SKILL.md:226 | 2026-01-20 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/skills/stock-data-verifier/SKILL.md:562 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
| .claude/plugins/stock-consultation/skills/stock-data-verifier/SKILL.md:563 | 2026-01-14 | ILLUSTRATIVE | — | annotate-illustrative |
