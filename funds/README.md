# 펀드 데이터 디렉토리

## 개요

과학기술공제회 퇴직연금 DC/IRP 펀드 데이터를 JSON 형식으로 관리합니다.

## 파일 구조

```
funds/
├── fund_data.json              # 펀드 기본 정보 및 수익률 (전체 2,015개)
├── fund_fees.json              # 펀드 수수료 정보
├── fund_classification.json    # 펀드 분류 (위험/안전자산)
├── deposit_rates.json          # 예금 금리 정보
├── README.md                   # 이 파일
├── investable/                 # 실제 투자 가능 펀드 (fund_data 교집합 206개)
│   └── investable_funds.json   # 투자 가능 펀드(fund_data 스키마) 목록
└── archive/                    # 이전 버전 백업
    ├── fund_data_YYYY-MM-DD_HHMMSS.json
    └── fund_fees_YYYY-MM-DD_HHMMSS.json
```

## 데이터 파일 설명

### fund_data.json

펀드의 기본 정보와 수익률 데이터를 포함합니다.

**구조:**
```json
{
  "_meta": {
    "version": "2026-01-01",           // 데이터 기준일
    "sourceFile": "CSV 파일명",
    "updatedAt": "ISO 8601 timestamp",
    "recordCount": 2015                // 총 펀드 수
  },
  "funds": [
    {
      "fundCode": "K55232DU8475",      // 펀드 고유 코드
      "name": "펀드명",
      "company": "운용사명",
      "riskLevel": 2,                   // 위험등급 (1-6)
      "riskName": "높은",               // 위험등급명
      "return10y": "",                  // 10년 수익률 (%)
      "return7y": "",                   // 7년 수익률 (%)
      "return5y": "",                   // 5년 수익률 (%)
      "return3y": "70.34",             // 3년 수익률 (%)
      "return1y": "178.03",            // 1년 수익률 (%)
      "return6m": "30.03",             // 6개월 수익률 (%)
      "netAssets": "508400000000",     // 순자산총액 (원)
      "inceptionDate": "20220627",     // 설정일 (YYYYMMDD)
      "isAffiliate": false,            // 계열사 여부
      "fundType": "ETF"                // 펀드 유형 (ETF/펀드/기타)
    }
  ]
}
```

**위험등급:**
- 1등급: 매우 높은 위험
- 2등급: 높은 위험
- 3등급: 다소 높은 위험
- 4등급: 보통 위험
- 5등급: 낮은 위험
- 6등급: 매우 낮은 위험

### fund_fees.json

펀드의 수수료 정보를 포함합니다.

**구조:**
```json
{
  "_meta": { ... },
  "fees": {
    "K55232DU8475": {
      "fundCode": "K55232DU8475",
      "fundName": "펀드명",
      "totalFee": "0.52",              // 총보수 (%)
      "annualCost": "5200"             // 연간 투자비용 (원, 1억원 기준)
    }
  }
}
```

### fund_classification.json

펀드의 자산 분류 정보를 포함합니다.

**구조:**
```json
{
  "펀드명": {
    "category": "주식형",              // 카테고리
    "riskAsset": true,                // 위험자산 여부
    "assetClass": "equity",           // 자산군
    "region": "domestic",             // 지역
    "themes": ["nuclear"],            // 테마
    "hedged": false,                  // 환헤지 여부
    "riskLevel": 2,                   // 위험등급
    "source": "enhanced keyword classification v2",
    "generatedAt": "2026-01-21"
  }
}
```

**카테고리:**
- 주식형: 국내 주식형 펀드
- 해외주식형: 해외 주식형 펀드
- 채권형: 채권형 펀드
- 혼합형: 혼합형 펀드
- MMF: 머니마켓펀드

**자산군 (assetClass):**
- equity: 주식
- bond: 채권
- money_market: 머니마켓
- mixed: 혼합

**지역 (region):**
- domestic: 국내
- global: 해외

**테마 예시:**
- semiconductor: 반도체
- ai: 인공지능
- defense: 방산
- nuclear: 원자력
- energy: 전력/에너지
- renewable: 신재생에너지
- hydrogen: 수소
- gold: 금/골드
- robotics: 로봇

### investable/investable_funds.json

`fund_data.json`에서 **investable 목록(209개)**과 이름이 매칭되는 펀드만 추출한 **교집합 데이터**입니다.

- 현재 매칭: **206개**
- 미매칭 1개: fund_data.json에 존재하지 않음
  - KB스타 한국 인덱스 증권 자투자신탁(주식) C-퇴직e 클래스
  - 현금성 상품 2개는 원본에만 존재하며 제외됨

**구조:**
`fund_data.json`과 동일한 스키마를 사용합니다.

```json
{
  "_meta": {
    "version": "2026-01-01",
    "sourceFile": "26년01월_상품제안서_퇴직연금(DCIRP).csv",
    "updatedAt": "2026-01-21T22:07:46.467353+09:00",
    "recordCount": 206
  },
  "funds": [
    {
      "fundCode": "K55366BU9598",
      "name": "iM에셋월드골드증권자투자신탁(주식-재간접형)(UH)(C-Rpe)",
      "company": "iM에셋운용",
      "riskLevel": 1,
      "riskName": "매우 높은",
      "return10y": "",
      "return7y": "25.00",
      "return5y": "23.36",
      "return3y": "47.42",
      "return1y": "126.73",
      "return6m": "66.78",
      "netAssets": "43600000000",
      "inceptionDate": "20170929",
      "isAffiliate": false,
      "fundType": "기타"
    }
  ]
}
```

**fund_data.json vs investable_funds.json:**

| 구분 | fund_data.json | investable_funds.json |
|------|----------------|----------------------|
| 펀드 수 | 2,015개 | 206개 |
| 용도 | 전체 펀드 정보 | investable 교집합 |
| 스키마 | fund_data 기준 | fund_data 동일 |

## 데이터 업데이트

### 자동 업데이트 스크립트

CSV 파일에서 JSON 데이터를 자동으로 생성합니다.

**1. 미리보기 (dry-run):**
```bash
python scripts/update_fund_data.py \
  --file "resource/26년01월_상품제안서_퇴직연금(DCIRP).csv" \
  --output-dir "funds" \
  --dry-run
```

**2. 실제 업데이트:**
```bash
python scripts/update_fund_data.py \
  --file "resource/26년01월_상품제안서_퇴직연금(DCIRP).csv" \
  --output-dir "funds"
```

**3. 분류만 재생성:**
```bash
python scripts/classify_funds.py \
  --fund-data "funds/fund_data.json" \
  --output "funds/fund_classification.json"
```

### 업데이트 워크플로우

1. CSV 파일을 `resource/` 디렉토리에 저장
2. `update_fund_data.py` 스크립트로 JSON 생성
3. 기존 파일은 자동으로 `archive/` 디렉토리에 백업
4. `fund_classification.json`은 자동 생성

## 현재 데이터 통계 (2026-01-01 기준)

### 전체 통계
- 총 펀드 수: 2,015개 (fund_data.json)
- **투자 가능 펀드: 206개** (investable_funds.json, 현금성 상품 2개 제외)
- 위험자산: 1,836개 (91.1%)
- 안전자산: 179개 (8.9%)

### 카테고리별 분포
| 카테고리 | 펀드 수 | 비율 |
|----------|---------|------|
| 주식형 | 1,081 | 53.6% |
| 해외주식형 | 717 | 35.6% |
| 채권형 | 178 | 8.8% |
| 혼합형 | 38 | 1.9% |
| MMF | 1 | 0.0% |

### 위험등급 분포
| 등급 | 펀드 수 | 비율 |
|------|---------|------|
| 1등급 | 164 | 8.1% |
| 2등급 | 951 | 47.2% |
| 3등급 | 279 | 13.8% |
| 4등급 | 342 | 17.0% |
| 5등급 | 240 | 11.9% |
| 6등급 | 39 | 1.9% |

### 펀드 유형 분포
| 유형 | 펀드 수 | 비율 |
|------|---------|------|
| ETF | 962 | 47.7% |
| 기타 | 785 | 39.0% |
| 펀드 | 268 | 13.3% |

## 데이터 사용 예시

### Python

```python
import json

# 펀드 데이터 로드
with open('funds/fund_data.json', 'r', encoding='utf-8') as f:
    fund_data = json.load(f)

# 모든 펀드 조회
funds = fund_data['funds']

# 특정 펀드 찾기
target_fund = next(f for f in funds if f['fundCode'] == 'K55232DU8475')
print(f"펀드명: {target_fund['name']}")
print(f"1년 수익률: {target_fund['return1y']}%")

# 수수료 정보 로드
with open('funds/fund_fees.json', 'r', encoding='utf-8') as f:
    fee_data = json.load(f)

fee_info = fee_data['fees']['K55232DU8475']
print(f"총보수: {fee_info['totalFee']}%")

# 분류 정보 로드
with open('funds/fund_classification.json', 'r', encoding='utf-8') as f:
    classifications = json.load(f)

classification = classifications[target_fund['name']]
print(f"카테고리: {classification['category']}")
print(f"위험자산: {classification['riskAsset']}")

# 투자 가능 펀드 조회
with open('funds/investable/investable_funds.json', 'r', encoding='utf-8') as f:
    investable = json.load(f)

# 수익률 상위 10개 펀드 (1년 기준)
top_funds = sorted(investable['funds'], key=lambda x: x['returns']['1y'], reverse=True)[:10]
for fund in top_funds:
    print(f"{fund['name']}: {fund['returns']['1y']}%")
```

## 관련 스크립트

- `scripts/update_fund_data.py`: CSV → JSON 변환 (fund_data.json, fund_fees.json 생성)
- `scripts/classify_funds.py`: 펀드 분류 (fund_classification.json 생성)

## 데이터 신선도

데이터는 매월 초 과학기술공제회에서 제공하는 CSV 파일을 기준으로 업데이트됩니다.

**최신 업데이트:**
- 기준일: 2026-01-01
- 업데이트 시각: 2026-01-21T22:07:46+09:00
- 소스 파일: 26년01월_상품제안서_퇴직연금(DCIRP).csv

## 주의사항

1. 수익률은 세전 기준이며, 과거 수익률이 미래 수익률을 보장하지 않습니다.
2. 총보수는 매년 변동될 수 있으며, 실제 비용은 다를 수 있습니다.
3. 펀드 분류는 펀드명 기반 키워드 매칭으로 자동 생성되므로, 일부 오분류가 있을 수 있습니다.
4. 위험자산/안전자산 분류는 위험등급(1-3등급: 위험자산)을 기준으로 합니다.

## 라이선스

이 데이터는 과학기술공제회에서 제공하는 공개 데이터를 기반으로 합니다.
