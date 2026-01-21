# Fund Data Schema Specification

**Version**: 2.0  
**Last Updated**: 2026-01-21  
**Purpose**: Define JSON schemas for fund_data.json and fund_fees.json based on CSV structure from 과학기술공제회 퇴직연금 상품제안서

---

## Table of Contents

1. [Overview](#overview)
2. [CSV Structure](#csv-structure)
3. [fund_data.json Schema](#fund_datajson-schema)
4. [fund_fees.json Schema](#fund_feesjson-schema)
5. [Column Mapping](#column-mapping)
6. [Data Transformation Rules](#data-transformation-rules)
7. [Removed Fields](#removed-fields)
8. [New Fields](#new-fields)
9. [Version History](#version-history)

---

## Overview

This document defines the JSON schemas for storing Korean retirement pension fund data extracted from CSV files provided by 과학기술공제회 (SEMA). The schemas are designed to:

- Map directly to CSV columns for automated updates
- Include version metadata for tracking data freshness
- Maintain backward compatibility where possible
- Support AI-powered portfolio analysis

**Data Source**: 과학기술공제회 퇴직연금 상품제안서 (CSV format)  
**Update Frequency**: Monthly (기준일 in CSV row 4)  
**Total Funds**: ~205 funds (as of 2026-01-02)

---

## CSV Structure

### File Format

```
Row 1: 사업자명 (Provider name)
Row 2: 제도유형 (System type: DC/IRP)
Row 3: 상품유형 (Product type: 실적배당형 상품)
Row 4: 기준일 (Base date: "YYYY-MM-DD, 제로인")
Row 5: (Empty)
Row 6: (Disclaimer text)
Row 7: (Empty)
Row 8: HEADER ROW (Column names)
Row 9+: DATA ROWS (Fund records)
```

### Metadata Extraction

| Row | Field | Example | Usage |
|-----|-------|---------|-------|
| 1 | 사업자명 | "미래에셋증권" | Provider identification |
| 2 | 제도유형 | "DC/IRP" | System type |
| 3 | 상품유형 | "실적배당형 상품(펀드/ETF)" | Product category |
| 4 | 기준일 | "2025-12-01, 제로인" | **Extract as version date** |

### Header Row (Row 8)

```
펀드코드, 펀드명, 운용회사명, 수익률(10Y), 수익률(7Y), 수익률(5Y), 수익률(3Y), 
수익률(1Y), 수익률(6M), BM수익률(10Y), BM수익률(7Y), BM수익률(5Y), BM수익률(3Y), 
BM수익률(1Y), BM수익률(6M), 위험등급, 비율(%), 1년투자비용(원), 순자산총액(억원), 
설정일, 계열사 여부, 비고
```

---

## fund_data.json Schema

### Structure

```json
{
  "_meta": {
    "version": "2025-12-01",
    "sourceFile": "25년12월_상품제안서_퇴직연금(DCIRP).csv",
    "updatedAt": "2026-01-21T10:30:00+09:00",
    "recordCount": 205
  },
  "funds": [
    {
      "fundCode": "K55105EC1749",
      "name": "삼성KODEXAI전력핵심설비증권상장지수투자신탁[주식]",
      "company": "삼성운용",
      "riskLevel": 2,
      "riskName": "높은위험",
      "return10y": "",
      "return7y": "",
      "return5y": "",
      "return3y": "",
      "return1y": "171.97",
      "return6m": "91.58",
      "netAssets": "100780000",
      "inceptionDate": "20240708",
      "isAffiliate": false,
      "fundType": "ETF"
    }
  ]
}
```

### Field Specifications

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `fundCode` | string | Yes | 펀드코드 (unique identifier) | "K55105EC1749" |
| `name` | string | Yes | 펀드명 (fund name) | "삼성글로벌반도체증권자투자신탁UH[주식]_Cpe(퇴직)" |
| `company` | string | Yes | 운용회사명 (asset management company) | "삼성자산운용" |
| `riskLevel` | integer | Yes | 위험등급 (1-6, 1=highest risk) | 2 |
| `riskName` | string | Yes | 위험등급명 (risk level name) | "높은위험" |
| `return10y` | string | No | 10년 연평균 수익률 (%) | "18.33" or "" |
| `return7y` | string | No | 7년 연평균 수익률 (%) | "23.25" or "" |
| `return5y` | string | No | 5년 연평균 수익률 (%) | "37.18" or "" |
| `return3y` | string | No | 3년 연평균 수익률 (%) | "65.15" or "" |
| `return1y` | string | No | 1년 수익률 (%) | "152.04" or "" |
| `return6m` | string | No | 6개월 수익률 (%) | "51.96" or "" |
| `netAssets` | string | Yes | 순자산총액 (천원 단위) | "43740000" (억원 → 천원 변환) |
| `inceptionDate` | string | Yes | 설정일 (YYYYMMDD) | "20110405" |
| `isAffiliate` | boolean | Yes | 계열사 여부 | true or false |
| `fundType` | string | Yes | 펀드 유형 (from 비고 column) | "ETF" or "" |

### _meta Field Specification

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `version` | string | 기준일 from CSV row 4 (YYYY-MM-DD) | "2025-12-01" |
| `sourceFile` | string | Original CSV filename | "25년12월_상품제안서_퇴직연금(DCIRP).csv" |
| `updatedAt` | string | ISO 8601 timestamp of update execution | "2026-01-21T10:30:00+09:00" |
| `recordCount` | integer | Total number of funds | 205 |

---

## fund_fees.json Schema

### Structure

```json
{
  "_meta": {
    "version": "2025-12-01",
    "sourceFile": "25년12월_상품제안서_퇴직연금(DCIRP).csv",
    "updatedAt": "2026-01-21T10:30:00+09:00",
    "recordCount": 205
  },
  "fees": {
    "K55105EC1749": {
      "fundCode": "K55105EC1749",
      "fundName": "삼성KODEXAI전력핵심설비증권상장지수투자신탁[주식]",
      "totalFee": "0.46",
      "annualCost": "4600"
    }
  }
}
```

### Field Specifications

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `fundCode` | string | Yes | 펀드코드 (primary key) | "K55105EC1749" |
| `fundName` | string | Yes | 펀드명 (for reference) | "삼성글로벌반도체증권자투자신탁UH[주식]_Cpe(퇴직)" |
| `totalFee` | string | Yes | 비율(%) - 합성총보수·비용 | "1.27" |
| `annualCost` | string | Yes | 1년투자비용(원) | "12700" |

### Key Design Decision

**Primary Key**: `fundCode` (preferred over `fundName`)

**Rationale**:
- fundCode is unique and stable
- fundName can be very long and may have minor variations
- fundCode enables efficient lookups and joins

---

## Column Mapping

### CSV → fund_data.json

| CSV Column | JSON Field | Transformation |
|------------|------------|----------------|
| 펀드코드 | fundCode | Direct mapping |
| 펀드명 | name | Direct mapping |
| 운용회사명 | company | Direct mapping |
| 위험등급 | riskLevel, riskName | Parse "N등급(위험명)" → riskLevel: N, riskName: "위험명" |
| 수익률(10Y) | return10y | Direct mapping (empty string if blank) |
| 수익률(7Y) | return7y | Direct mapping (empty string if blank) |
| 수익률(5Y) | return5y | Direct mapping (empty string if blank) |
| 수익률(3Y) | return3y | Direct mapping (empty string if blank) |
| 수익률(1Y) | return1y | Direct mapping (empty string if blank) |
| 수익률(6M) | return6m | Direct mapping (empty string if blank) |
| 순자산총액(억원) | netAssets | **Multiply by 10000** (억원 → 천원) |
| 설정일 | inceptionDate | Direct mapping (YYYYMMDD format) |
| 계열사 여부 | isAffiliate | "계열사" → true, "" → false |
| 비고 | fundType | Direct mapping ("ETF" or "") |

### CSV → fund_fees.json

| CSV Column | JSON Field | Transformation |
|------------|------------|----------------|
| 펀드코드 | fundCode | Direct mapping |
| 펀드명 | fundName | Direct mapping |
| 비율(%) | totalFee | Direct mapping |
| 1년투자비용(원) | annualCost | Direct mapping |

---

## Data Transformation Rules

### 1. 위험등급 Parsing

**Input Format**: `"N등급(위험명)"`

**Examples**:
- `"1등급(매우 높은 위험)"` → `riskLevel: 1, riskName: "매우높은위험"`
- `"2등급(높은 위험)"` → `riskLevel: 2, riskName: "높은위험"`
- `"4등급(보통 위험)"` → `riskLevel: 4, riskName: "보통위험"`

**Parsing Logic**:
```python
import re

def parse_risk_level(risk_str):
    match = re.match(r'(\d+)등급\((.+)\)', risk_str)
    if match:
        level = int(match.group(1))
        name = match.group(2).replace(' ', '')  # Remove spaces
        return level, name
    return None, None
```

### 2. 순자산 Unit Conversion

**Input**: 억원 (hundred million KRW)  
**Output**: 천원 (thousand KRW)

**Conversion**:
```python
net_assets_thousand = float(csv_value) * 10000
```

**Examples**:
- CSV: `"10,078"` (억원) → JSON: `"100780000"` (천원)
- CSV: `"4,916"` (억원) → JSON: `"49160000"` (천원)

**Note**: Remove commas from CSV value before conversion.

### 3. Empty Return Values

**Handling**:
- CSV empty cell → JSON empty string `""`
- Do NOT use `null` or `0`

**Rationale**: Empty string distinguishes "no data" from "zero return"

### 4. 계열사 여부 Boolean Conversion

**Mapping**:
- CSV: `"계열사"` → JSON: `true`
- CSV: `""` (empty) → JSON: `false`

### 5. Date Format

**inceptionDate**:
- CSV: `"20240708"` → JSON: `"20240708"` (no change)
- Format: YYYYMMDD (8 digits)

**_meta.version**:
- Extract from CSV row 4: `"2025-12-01, 제로인"`
- Parse date part: `"2025-12-01"`

**_meta.updatedAt**:
- ISO 8601 format with timezone: `"2026-01-21T10:30:00+09:00"`

---

## Removed Fields

The following fields exist in the current fund_data.json but are **NOT** in the CSV and should be **REMOVED**:

| Field | Reason for Removal |
|-------|-------------------|
| `index` | Not in CSV; can be derived from array position |
| `return1m` | Not in CSV; replaced by return10y, return7y, return5y |
| `return3m` | Not in CSV; replaced by return10y, return7y, return5y |
| `return2y` | Not in CSV; replaced by return10y, return7y, return5y |
| `returnTotal` | Not in CSV; ambiguous definition |

**Migration Impact**: Existing markdown files and portfolio analysis may reference these fields. Update generation scripts accordingly.

---

## New Fields

The following fields are **NEW** in the CSV and should be **ADDED**:

| Field | Source | Description |
|-------|--------|-------------|
| `fundCode` | CSV: 펀드코드 | Unique fund identifier (primary key) |
| `return10y` | CSV: 수익률(10Y) | 10-year annualized return (%) |
| `return7y` | CSV: 수익률(7Y) | 7-year annualized return (%) |
| `return5y` | CSV: 수익률(5Y) | 5-year annualized return (%) |
| `inceptionDate` | CSV: 설정일 | Fund inception date (YYYYMMDD) |
| `isAffiliate` | CSV: 계열사 여부 | Whether fund is from affiliated company |
| `fundType` | CSV: 비고 | Fund type (e.g., "ETF") |

**Benefits**:
- `fundCode`: Enables stable fund identification across updates
- `return10y/7y/5y`: Provides longer-term performance data
- `inceptionDate`: Allows age-based filtering and analysis
- `isAffiliate`: Supports conflict-of-interest analysis
- `fundType`: Distinguishes ETFs from mutual funds

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-02 | Initial schema (browser snapshot extraction) |
| 2.0 | 2026-01-21 | CSV-based schema redesign |

### Changes in v2.0

**Added**:
- `_meta` field for version management
- `fundCode` as primary identifier
- `return10y`, `return7y`, `return5y` fields
- `inceptionDate`, `isAffiliate`, `fundType` fields
- fund_fees.json schema

**Removed**:
- `index` field
- `return1m`, `return3m`, `return2y`, `returnTotal` fields

**Modified**:
- `netAssets`: Now in 천원 (thousand KRW) instead of mixed units
- `riskLevel`: Parsed from CSV instead of hardcoded

---

## Implementation Notes

### Backward Compatibility

**Breaking Changes**:
- Field removals: `index`, `return1m`, `return3m`, `return2y`, `returnTotal`
- Field additions: `fundCode`, `return10y`, `return7y`, `return5y`, `inceptionDate`, `isAffiliate`, `fundType`

**Migration Strategy**:
1. Update `generate_md.js` to use new field names
2. Update portfolio analysis agents to use new return periods
3. Regenerate all markdown files after first CSV import

### Data Quality Checks

**Required Validations**:
1. `fundCode` uniqueness across all records
2. `riskLevel` in range 1-6
3. `netAssets` > 0
4. `inceptionDate` valid date (YYYYMMDD)
5. Return values: numeric or empty string
6. `totalFee` and `annualCost` consistency

### Error Handling

**Empty/Missing Values**:
- Return fields: Use empty string `""`
- Required fields: Raise error if missing
- Numeric fields: Validate format before conversion

**Invalid Data**:
- Log warnings for unparseable 위험등급
- Skip rows with missing fundCode or fundName
- Report total skipped rows in _meta

---

## Example Records

### fund_data.json Example

```json
{
  "_meta": {
    "version": "2025-12-01",
    "sourceFile": "25년12월_상품제안서_퇴직연금(DCIRP).csv",
    "updatedAt": "2026-01-21T10:30:00+09:00",
    "recordCount": 2
  },
  "funds": [
    {
      "fundCode": "K55105EC1749",
      "name": "삼성KODEXAI전력핵심설비증권상장지수투자신탁[주식]",
      "company": "삼성운용",
      "riskLevel": 2,
      "riskName": "높은위험",
      "return10y": "",
      "return7y": "",
      "return5y": "",
      "return3y": "",
      "return1y": "171.97",
      "return6m": "91.58",
      "netAssets": "100780000",
      "inceptionDate": "20240708",
      "isAffiliate": false,
      "fundType": "ETF"
    },
    {
      "fundCode": "KR5225A18083",
      "name": "미래에셋TIGER200중공업증권상장지수투자신탁(주식)",
      "company": "미래에셋운용",
      "riskLevel": 1,
      "riskName": "매우높은위험",
      "return10y": "18.33",
      "return7y": "23.25",
      "return5y": "37.18",
      "return3y": "65.15",
      "return1y": "152.04",
      "return6m": "51.96",
      "netAssets": "43740000",
      "inceptionDate": "20110405",
      "isAffiliate": true,
      "fundType": "ETF"
    }
  ]
}
```

### fund_fees.json Example

```json
{
  "_meta": {
    "version": "2025-12-01",
    "sourceFile": "25년12월_상품제안서_퇴직연금(DCIRP).csv",
    "updatedAt": "2026-01-21T10:30:00+09:00",
    "recordCount": 2
  },
  "fees": {
    "K55105EC1749": {
      "fundCode": "K55105EC1749",
      "fundName": "삼성KODEXAI전력핵심설비증권상장지수투자신탁[주식]",
      "totalFee": "0.46",
      "annualCost": "4600"
    },
    "KR5225A18083": {
      "fundCode": "KR5225A18083",
      "fundName": "미래에셋TIGER200중공업증권상장지수투자신탁(주식)",
      "totalFee": "0.43",
      "annualCost": "4300"
    }
  }
}
```

---

## References

- CSV Source: `resource/25년12월_상품제안서_퇴직연금(DCIRP).csv`
- Current fund_data.json: `funds/fund_data.json`
- Current fund_fees.json: `funds/fund_fees.json`
- Project Documentation: `AGENTS.md`

---

*This schema specification is the authoritative source for CSV-to-JSON conversion logic. All extraction scripts must conform to this specification.*
