# DATA: funds/

펀드 마스터 데이터 (제로인 평가 기반). `_meta`가 single source of truth — `README.md`는 stale(2015펀드/5분류) 무시.

## SUBSET vs FULL

| | top-level `funds/` | `funds/all/` |
|---|---|---|
| 범위 | 투자 가능 subset (206) | 전체 universe (2037) |
| 파일 | fund_data / fund_fees / fund_classification | all_fund_data / all_fund_fees / all_fund_classification |

동일 스키마 패밀리, 필터링 범위만 다름. `_meta.missing`: `["K55223C80096"]`.

## SCHEMA

**fund_data.json** = `{ _meta, funds: [...] }`
- `_meta`: version `2026-03-01`, sourceFile `26년03월_상품제안서_퇴직연금(DCIRP).csv`, recordCount 206
- per-fund: `fundCode, name, company, riskLevel(int), riskName, return10y..return6m(str), netAssets(str), inceptionDate, isAffiliate(bool), fundType`

**fund_classification.json** = `{ "펀드명": { category, riskAsset, assetClass, region, themes, hedged, riskLevel, source, generatedAt } }`
- 9 categories: 기타(13), 주식형(58), 주식혼합형(2), 채권형(18), 채권혼합형(20), 해외주식형(69), 해외주식혼합형(4), 해외채권형(14), 해외채권혼합형(8)

**fund_fees.json** = `{ _meta, fees: { fundCode: { fundCode, fundName, totalFee, annualCost } } }`

**deposit_rates.json** = `{ _meta, rates: [...], summary }`
- rate: `id, institution, productName, type, term, termMonths, rate, unit, earlyWithdrawal`
- `_meta.freshnessThresholdDays`: 30 (원리금보장형 금리 비교용)

## REGEN

`fund_data`/`fund_fees`/`fund_classification`은 수기 편집 금지 — `plugins/investments-portfolio/skills/data-updater/scripts/`로 `resource/*.csv`에서 재생성. `deposit_rates.json`만 수동 갱신.
