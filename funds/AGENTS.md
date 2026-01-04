# FUNDS MODULE

## OVERVIEW

ETL pipeline and data storage for 205 Korean retirement pension funds.

## STRUCTURE

```
funds/
├── fund_data.json      # Master JSON (source of truth)
├── fund_crawler.py     # Data classes + parsing logic
├── extract_funds.py    # Snapshot → JSON extraction
├── generate_md.js      # JSON → Markdown generation
├── verify_funds.js     # Data integrity checks
├── check_duplicates.js # Duplicate detection
├── cleanup_duplicates.js
├── README.md           # Generated index (205 funds)
└── [9 category dirs]/  # Generated fund markdown files
```

## SCRIPTS

| Script | Language | Purpose | Input → Output |
|--------|----------|---------|----------------|
| `extract_funds.py` | Python | Parse browser snapshot | `.log` → `fund_data.json` |
| `generate_md.js` | Node.js | Generate documentation | `fund_data.json` → `*.md` |
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

```json
{
  "index": 1,
  "name": "펀드명",
  "riskLevel": 2,           // 1-6 (1=highest risk)
  "riskName": "높은위험",
  "return1m": "8.02",       // Percentage strings
  "return3m": "31.31",
  "return6m": "54.29",
  "return1y": "112.59",
  "return2y": "82.07",
  "return3y": "152.16",
  "returnTotal": "112.60",
  "netAssets": "32,510,078", // KRW thousands
  "company": "운용사명"
}
```

## ANTI-PATTERNS

- **Never** edit files in category folders (auto-generated)
- **Never** change `fund_data.json` without re-running `generate_md.js`
- **Avoid** hardcoding snapshot paths in `extract_funds.py`

## WORKFLOW

```bash
# Full refresh cycle
python extract_funds.py    # Update snapshot_path first!
node generate_md.js        # Regenerates all 205+ files
node verify_funds.js       # Validate output
```
