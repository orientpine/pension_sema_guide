# FUNDS MODULE

## OVERVIEW

ETL pipeline and data storage for 205 Korean retirement pension funds.

## STRUCTURE

```
funds/
├── fund_data.json      # Master JSON (1996 funds)
├── fund_fees.json      # Fee data (1996 fees)
├── fund_classification.json # Auto-generated (9 categories)
├── scripts/
│   ├── update_fund_data.py  # CSV → JSON pipeline
│   └── classify_funds.js    # Auto-classification
├── archive/            # Backup files with date suffix
├── generate_md.js      # JSON → Markdown generation (optional)
├── verify_funds.js     # Data integrity checks
├── check_duplicates.js # Duplicate detection
├── README.md           # Generated index (205 funds)
└── [9 category dirs]/  # Generated fund markdown files
```

## SCRIPTS

| Script | Language | Purpose | Input → Output |
|--------|----------|---------|----------------|
| `scripts/update_fund_data.py` | Python | CSV → JSON pipeline | CSV → `fund_data.json` + `fund_fees.json` + archive |
| `scripts/classify_funds.js` | Node.js | Auto-classify funds | `fund_data.json` → `fund_classification.json` |
| `generate_md.js` | Node.js | Generate documentation | `fund_data.json` → `*.md` (optional) |
| `verify_funds.js` | Node.js | Validate consistency | - |
| `check_duplicates.js` | Node.js | Find naming collisions | - |

## FUND CATEGORIES

| Folder | Type | Count |
|--------|------|-------|
| `주식형/` | Domestic equity | 51 |
| `해외주식형/` | Global equity | 86 |
| `채권혼합형/` | Bond-mixed | 18 |
| `기타/` | TDF/MMF/REITs/Gold | 12 |
| `해외채권혼합형/` | Global bond-mixed | 11 |
| `해외채권형/` | Global bond | 11 |
| `채권형/` | Domestic bond | 10 |
| `해외주식혼합형/` | Global equity-mixed | 4 |
| `주식혼합형/` | Domestic equity-mixed | 2 |

## CLASSIFICATION LOGIC

`generate_md.js` → `getFundType()`:

```
1. Check overseas keywords: 해외, 글로벌, 미국, 차이나, Global, USA...
2. Check asset keywords: 채권혼합 → 채권 → 주식혼합 → 주식
3. Check special: TDF, MMF, EMP, 리츠, 골드 → 기타
4. Default: 기타
```

## FUND MARKDOWN TEMPLATE

Every generated `.md` file contains:
1. **Header**: `# [Name]` + risk badge
2. **기본 정보**: 위험등급, 펀드유형, 순자산, 운용사
3. **수익률 정보**: 1개월 ~ 설정이후 (7 periods)
4. **투자 유의사항**: Standard disclaimers
5. **Footer**: Base date + source

## DATA SCHEMA (`fund_data.json`)

**Structure (v2.0)**:
```json
{
  "_meta": {
    "version": "2025-12-01",
    "sourceFile": "25년12월_상품제안서_퇴직연금(DCIRP).csv",
    "updatedAt": "2026-01-21T16:18:38+09:00",
    "recordCount": 1996
  },
  "funds": [
    {
      "fundCode": "K55105EC1749",
      "name": "펀드명",
      "company": "운용사명",
      "riskLevel": 2,           // 1-6 (1=highest risk)
      "riskName": "높은위험",
      "return10y": "",          // NEW: Long-term returns
      "return7y": "",
      "return5y": "",
      "return3y": "",
      "return1y": "112.59",
      "return6m": "54.29",
      "netAssets": "32510078",  // KRW thousands (no commas)
      "inceptionDate": "20240708",
      "isAffiliate": false,
      "fundType": "ETF"
    }
  ]
}
```

See `SCHEMA.md` for complete specification.

## ANTI-PATTERNS

- **Never** edit files in category folders (auto-generated)
- **Never** change `fund_data.json` manually (use update_fund_data.py)
- **Avoid** running `generate_md.js` without updated `fund_data.json`

## WORKFLOW

### Monthly Data Update (CSV-based)

```bash
# 1. Update fund data from CSV
python scripts/update_fund_data.py --file ../resource/YYYY년MM월_상품제안서_퇴직연금(DCIRP).csv

# Output:
# - fund_data.json (1996 funds)
# - fund_fees.json (1996 fees)
# - fund_classification.json (auto-generated, 9 categories)
# - archive/fund_data_YYYY-MM-DD.json (backup)

# 2. Optional: Regenerate markdown documentation
node generate_md.js        # Regenerates all 205+ files
node verify_funds.js       # Validate output
```

### Dry-run Mode

```bash
# Preview changes without modifying files
python scripts/update_fund_data.py --dry-run --file ../resource/YYYY년MM월_상품제안서_퇴직연금(DCIRP).csv
```
