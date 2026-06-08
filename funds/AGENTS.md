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

## TDF 데이터 관리

TDF(Target Date Fund)는 생애주기별 자산배분을 수행하는 펀드로, `tdf_data.json`과 `tdf_fees.json`을 통해 관리한다. 이 문서는 T3/T10/T11의 필드명 계약(single source of truth)이다.

### SCHEMA

**tdf_data.json** = `{ _meta, funds: [...] }`
- `_meta`: version `2026-06-04`, source `펀드평가사 제로인`, updatedAt, recordCount, freshnessThresholdDays `30`, baseDateNote `"fund_data.json 기준일 2026-03-01과 상이. 직접 교차비교 금지"`
- per-fund:
    - `fundCode`: 펀드 고유 코드 (str)
    - `name`: 펀드명 (str)
    - `company`: 운용사 (str)
    - `targetYear`: 목표 연도 (int, 예: 2055)
    - `recommendedAgeBand`: 추천 연령대 (list [min, max], 예: [20, 35])
    - `hedge`: 환헤지 여부 (`"UH"`, `"H"`, `null`)
    - `tdfQualified`: 적격 TDF 여부 (bool) - DC/IRP 위험자산 70% 한도 예외(100% 편입 가능) 상품
    - `riskName`: 위험등급명 (str)
    - `riskLevel`: 위험등급 (int, 1~6)
    - `return1m`, `return3m`, `return6m`, `return1y`, `return2y`, `return3y`, `returnSinceInception`: 수익률 (str, %, 결측 시 `""`). `returnSinceInception`은 설정후 수익률을 의미함.
    - `netAssets`: 순자산총액 (str, **천원 단위**)

**tdf_fees.json** = `{ _meta, fees: { [fundCode]: { ... } } }`
- `_meta`: version, feeSource, updatedAt, recordCount
- per-fee:
    - `fundCode`: 펀드 고유 코드 (str)
    - `fundName`: 펀드명 (str)
    - `totalFee`: 총보수 (str, %)
    - `ter`: 총비용비율 (str, %, 보조 지표)
    - `feeVerification`: 수수료 검증 정보
        - `value`: 검증된 값
        - `sources`: 출처 목록 (list)
        - `agree`: 출처 간 일치 여부 (bool)
        - `checkedAt`: 검증 시각

### 관리 규칙

1. **갱신 경로**: 데이터 갱신은 반드시 `update_tdf_data.py` 스크립트를 통해서만 수행한다.
2. **수동 트리거**: 제로인 등 외부 데이터를 붙여넣어 수동으로 트리거할 수 있다.
3. **신선도 유지**: `freshnessThresholdDays: 30`을 준수하며, 30일 경과 시 경고를 발생시킨다.
4. **수수료 검증**: 총보수는 최소 3개 이상의 출처를 통해 더블체크한다.
5. **충돌 해결**: 출처 간 데이터 충돌 시 `agree: false`로 마킹하고 사람이 직접 확인하여 수정한다.
6. **안전자산 오분류 금지**: TDF는 위험자산 70% 한도의 예외일 뿐, **안전자산이 아니다.** 문서 내에서 TDF를 안전자산으로 표현하는 것을 엄격히 금지한다.
