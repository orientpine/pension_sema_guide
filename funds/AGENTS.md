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

`fund_data`/`fund_fees`/`fund_classification`은 수기 편집 금지 — `.claude/plugins/investments-portfolio/skills/data-updater/scripts/`로 `resource/*.csv`에서 재생성. `deposit_rates.json`만 수동 갱신.

## TDF 데이터 관리

TDF(Target Date Fund)는 생애주기별 자산배분을 수행하는 펀드로, `tdf_data.json`과 `tdf_fees.json`을 통해 관리한다. 이 문서는 T3/T10/T11의 필드명 계약(single source of truth)이다.

### SCHEMA

**tdf_data.json** = `{ _meta, funds: [...] }`
- `_meta`: version, source, updatedAt, recordCount, freshnessThresholdDays, baseDateNote (기존 필드 유지)
    - `enrichment`: 결정적 TDF 보강 정보
        - `method`: 보강 방법 (예: `"canonical-name-exact"`)
        - `authoritativeFundData`: 권위 있는 펀드 데이터 경로 (`"funds/all/all_fund_data.json"`)
        - `authoritativeFeeData`: 권위 있는 수수료 데이터 경로 (`"funds/all/all_fund_fees.json"`)
        - `sourceCsv`: 원본 CSV 파일명
        - `checkedAt`: 검증 시각
        - `resolvedUnknownCount`: 해소된 미분류 수
        - `unresolvedCount`: 미해결 수
        - `missingCount`: 누락 수
        - `needsReviewCount`: 검토 필요 수
        - `codeNameMismatchCount`: 코드-이름 불일치 수
    - `unresolved`: 사람이 직접 확인해야 하는 미해결 행 배열
        - `{ index, placeholderCode("UNKNOWN_<idx>"), fundName, company, targetYear, shareClass, hedge, reason, candidateCodes:[{fundCode, fundName, shareClass, totalFee, reason}] }`
    - `needsReview`: 자동 해소됐으나 사람 검토 권장 배열 (예: 증권자투자신탁 vs 증권투자신탁 vehicle-token 정규화)
        - `{ index, fundCode, fundName, matchedFundName, reason, differences[], accepted }`
    - `missing`: `all_fund_fees`에 코드가 없거나 총보수가 빈 값이어서 총보수를 채우지 못한 `fundCode` 배열 (빈 총보수는 verified가 아닌 missing으로 표면화)
    - `validationWarnings`: 수익률 드리프트 등 경고 배열
        - `{ index, fundCode, field, tdf, auth, severity("soft") }` (6m/1y/3y 수익률이 0.20%p 초과 차이 시 발생. 기준일 06-04 vs 06-01 드리프트 등)
    - `codeNameMismatch`: 이미 코드가 있는 행의 이름이 해당 `fundCode`의 권위 이름과 canonically 불일치할 때의 **정보성 경고** 배열 (코드는 유지, exit 2 아님 — share class 동일/포맷 차이 포함)
        - `{ index, fundCode, fundName, authoritativeName, reason }` (예: `제1호` vs `1`, `퇴직` vs `퇴직연금`, `주식혼합` vs `채권혼합`. 진짜 잘못된 코드도 여기 표면화되어 사람이 검토)
    - `resolvedFundCodeCount` / `unresolvedFundCodeCount`: 갱신된 정확한 카운트 (기존 `fundCodeSource` 메타의 stale 값을 enrichment가 교정)
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
    - `totalFee`: 총보수 (str, %, 미해결 시 `""`)
    - `ter`: 총비용비율 (str, %, 보조 지표, 미해결 시 `""`)
    - `feeVerification`: 수수료 검증 정보 (새 스키마)
        - `status`: `"verified"` | `"unresolved"` | `"missing"`
        - `authority`: `"official-csv"` | `"none"` (공식 월간 CSV에서 생성된 `all_fund_fees.json`이 권위 소스)
        - `value`: 검증된 값 (str)
        - `agree`: 출처 간 일치 여부 (bool, 코드 정확 매칭 시 `true`)
        - `checkedAt`: 검증 시각
        - `sources`: 출처 상세 목록
            - `{ name, type:"local-authoritative-csv", path, derivedFrom:"funds/all/all_fund_fees.json", fundCode, value, baseDate, note }`

### 관리 규칙

1. **갱신 경로**: 데이터 갱신은 반드시 `update_tdf_data.py --fees` 스크립트를 통한 결정적 로컬 보강(enrichment)을 우선한다. 웹 크롤링은 CSV에 없는 필드(1m/3m/2y/설정후 등)에만 제한적으로 사용한다.
2. **미해결 처리**: 미해결(`unresolved`) 또는 누락(`missing`) 데이터 존재 시 스크립트는 stderr 경고와 함께 종료 코드 2를 반환한다. (`--allow-unresolved` 옵션 사용 시 0 반환)
3. **수동 트리거**: 제로인 등 외부 데이터를 붙여넣어 수동으로 트리거할 수 있다.
4. **신선도 유지**: `freshnessThresholdDays: 30`을 준수하며, 30일 경과 시 경고를 발생시킨다.
5. **수수료 검증**: 총보수는 공식 월간 CSV(`all_fund_fees.json`)를 권위 있는 소스로 사용하여 검증하며, 일치 여부를 `agree` 필드에 기록한다.
6. **안전자산 오분류 금지**: TDF는 위험자산 70% 한도의 예외일 뿐, **안전자산이 아니다.** 문서 내에서 TDF를 안전자산으로 표현하는 것을 엄격히 금지한다.
