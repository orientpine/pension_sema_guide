---
name: data-updater
description: "CSV에서 펀드 데이터를 추출하여 fund_data.json, fund_fees.json, fund_classification.json을 생성/업데이트하는 스킬. 예금금리 데이터(deposit_rates.json) 업데이트도 지원한다. 펀드 데이터 업데이트가 필요하거나 CSV 파일을 JSON으로 변환하고 싶을 때 사용한다."
tools: Bash, Read, Write, mcp_question
---

# Fund Data Updater

## Overview

과학기술공제회 퇴직연금 CSV 파일을 읽어 Python 스크립트를 통해
펀드 데이터 JSON 파일을 자동 생성하는 스킬이다.

핵심 기능:
- CSV 파일 파싱 및 검증
- fund_data.json 생성 (펀드 기본 정보 및 수익률)
- fund_fees.json 생성 (펀드 수수료 정보)
- fund_classification.json 자동 생성 (펀드 분류)
- **투자 가능 펀드 필터링** (investable_codes.json 기반)
- **funds/all/ 폴더에 전체 펀드 데이터 저장** (2015개)
- **deposit_rates.json 업데이트 (예금금리 - 사용자 입력 필수)**
- 기존 파일 자동 백업 (archive/ 디렉토리)

> **⚠️ 중요**: 예금금리는 과학기술인공제회 공개 페이지(원리금보장형상품, menuNo=200059)에서 **기준일과 함께** 확인하고,
> 사용자가 포털에서 본 값이 있으면 대조한다. 기준일 없는 값은 쓰지 않는다.

---

## 사용자 입력 스키마

### 필수 입력

| 항목 | 설명 | 예시 |
|------|------|------|
| CSV 파일 경로 | 과학기술공제회 퇴직연금 CSV 파일 | `resource/26년01월_상품제안서_퇴직연금(DCIRP).csv` |

### 선택 입력

| 항목 | 설명 | 기본값 |
|------|------|--------|
| 출력 디렉토리 | JSON 파일 저장 위치 | 자동 감지 (investments/funds/) |
| dry-run 모드 | 미리보기 (파일 생성 없이 결과만 출력) | false |

---

## Workflow

```
[Phase -1: xlsx 자동 다운로드 + CSV 변환 (선택, openpyxl 필요)]
    |
    +-- Step -1-1. 최신 xlsx 다운로드
    |   +-- fetch_latest_proposal.py 실행 (미래에셋 게시판 categoryId=1494)
    |   +-- 모든 DCIRP xlsx 첨부 중 파일명 YY년MM월 최신본 선택
    |   +-- (2026-11 수정) urllib 기본 Connection: close 요청에서는 게시판 HTML 본문이 잘려 첨부가 0개로 보였다 → keep-alive로 받도록 고쳤다. 실패하면 종료 코드 1과 함께 멈추고 기존 데이터를 덮어쓰지 않는다
    |   +-- resource/{게시판 제공 파일명}.xlsx 저장
    |
    +-- Step -1-2. CSV 변환 (--convert)
    |   +-- xlsx_to_csv.py 로 '실적배당형(펀드, ETF)' 시트 -> CSV
    |   +-- 숫자 서식 적용, 25컬럼, UTF-8 BOM, CRLF (resource/*.csv 형식 동일)
    |   +-- 명령: python scripts/fetch_latest_proposal.py --out-dir resource --convert
    |
    +-- (수동 변환만 필요할 때)
        +-- python scripts/xlsx_to_csv.py --src <xlsx> --dst <csv>

[Phase 0: 입력 검증]
    |
    +-- Step 0-1. CSV 파일 확인
    |   +-- 사용자 제공 경로 존재 여부 확인
    |   +-- 파일 확장자 (.csv) 확인
    |   +-- 인코딩 검증 (UTF-8 필수)
    |
    +-- Step 0-2. 출력 폴더 설정
    |   +-- funds/ 폴더 존재 확인 (없으면 생성)
    |   +-- archive/ 폴더 존재 확인 (없으면 생성)
    |   +-- 기존 JSON 파일 백업 준비
    |
    +-- Step 0-3. Python 환경 확인
        +-- Python 3.10+ 설치 여부 확인
        +-- 필수 패키지: 표준 라이브러리만 (외부 패키지 불필요)

[Phase 1: Dry-run 실행 (권장)]
    |
    +-- Step 1-1. 미리보기 실행
    |   +-- --dry-run 옵션으로 스크립트 실행
    |   +-- CSV 메타데이터 확인 (사업자명, 기준일 등)
    |   +-- 펀드 개수 확인
    |
    +-- Step 1-2. 샘플 데이터 검토
        +-- 처음 3개 펀드 데이터 미리보기
        +-- 사용자에게 확인 요청 (진행 여부)

[Phase 2: 데이터 변환]
    |
    +-- Step 2-1. Python 스크립트 찾기 및 실행
    |   +-- 상대경로 참조: scripts/update_fund_data.py (스킬 루트 기준)
    |   +-- 실패 시 Glob 폴백: **/investments-portfolio/skills/data-updater/scripts/update_fund_data.py
    |   +-- Glob도 실패 시: Glob: **/update_fund_data.py
    |   +-- 찾은 경로로 실행: python {경로} --file [csv_file_path]
    |   +-- 스크립트를 찾지 못하면: 즉시 중단, 사용자에게 경로 확인 요청
    |   +-- 절대 금지: 스크립트를 못 찾았을 때 자체 Python 코드를 작성하여 대체하지 않음
    |
    +-- Step 2-2. 자동 분류 실행
    |   +-- update_fund_data.py가 자동으로 classify_funds.py 호출
    |   +-- fund_classification.json 자동 생성
    |
    +-- Step 2-3. 결과 확인
        +-- 생성된 JSON 파일 목록 확인
        +-- 펀드 개수 및 분류 통계 확인

[Phase 3: 검증]
    |
    +-- Step 3-1. 파일 검증
    |   +-- fund_data.json 존재 및 JSON 유효성 확인
    |   +-- fund_fees.json 존재 및 JSON 유효성 확인
    |   +-- fund_classification.json 존재 확인
    |
    +-- Step 3-2. 메타데이터 검증
        +-- _meta.version 확인 (CSV 기준일과 일치)
        +-- _meta.recordCount 확인 (펀드 개수)
        +-- _meta.updatedAt 확인 (현재 시간)

[Phase 4: 완료 보고]
    |
    +-- Step 4-1. 실행 보고서 생성
    |   +-- 포함 내용:
    |       - 입력 CSV 파일명 및 기준일
    |       - 생성된 JSON 파일 목록
    |       - 펀드 개수 및 분류 통계
    |       - 아카이브된 파일 목록
    |
    +-- Step 4-2. 사용자 안내
        +-- 생성 완료 알림
        +-- funds/ 폴더 위치 안내
        +-- 다음 단계 안내 (포트폴리오 분석 등)

[Phase 5: 예금금리 업데이트 (선택)]
    |
    +-- Step 5-0. 예금금리 업데이트 필요 여부 확인
    |   +-- deposit_rates.json 존재 확인
    |   +-- _meta.version 기준 경과일 계산
    |   +-- 30일 이상 경과 시 업데이트 권장 (정합성 게이트는 예금 기준일 30일과 적용기간·가산기간 만료도 위반으로 본다)
    |
    +-- Step 5-1. 공제회 공개 페이지 조회 (기준일 필수)
    |   +-- https://www.sema.or.kr/sema/annty/guidance/fundProduct.do?menuNo=200059
    |   +-- [기준일:YYYY.MM.DD], 기본금리·특별가산·가산기간, 은행 금리 적용기간, 중도해지·만기 규칙
    |   +-- 사용자 포털 값이 있으면 대조 (불일치 시 중단·보고), 페이지 접근 불가 시에만 사용자에게 질문
    |
    +-- Step 5-2. deposit_rates.json 업데이트
    |   +-- _meta.version: 페이지 기준일 (YYYY-MM-DD)
    |   +-- _meta.updatedAt: 현재 ISO 8601 타임스탬프
    |   +-- rates 배열 업데이트
    |
    +-- Step 5-3. 업데이트 완료 확인
        +-- JSON 유효성 검사
        +-- 업데이트 내역 보고

[Phase 6: TDF 데이터 업데이트 (수동)]
    |
    +-- Step 6-0. 월간 상품제안서 기준 갱신 (Phase 2 뒤, 자동)
    |   +-- python scripts/update_tdf_data.py --from-proposal --fees
    |   +-- 기존 75개 TDF 행을 funds/all/all_fund_data.json 기준일로: 6M/1Y(누적)·3Y(연환산→누적)·위험등급·순자산(천원)
    |   +-- 상품제안서에 없는 1M/3M/2Y/설정후는 빈 값 (_meta.returnsBasis), 상품제안서에 없는 코드는 _meta.notInProposal
    |   +-- 포털 표가 있으면 아래 Step 6-1~6-2로 빈 구간을 채운다
    |
    +-- Step 6-1. TDF 원본 데이터 확보
    |   +-- 사용자로부터 TDF 수익률 표(Markdown/Text) 붙여넣기 받기
    |   +-- 임시 파일 저장 (예: resource/tdf-raw.md)
    |
    +-- Step 6-2. update_tdf_data.py 실행
    |   +-- python scripts/update_tdf_data.py --input resource/tdf-raw.md --base-date YYYY-MM-DD
    |   +-- --base-date = 포털 TDF 표에 적힌 수익률 기준일(필수). 모르면 형에게 묻고, 없으면 저장하지 않는다(exit 2)
    |   +-- tdfQualified는 펀드명 '적격' 표기가 있을 때만 true (근거 없으면 false→유형 기준 70% 판정)
    |   +-- tdf_data.json 생성 확인
    |
    +-- Step 6-3. 총보수 3출처 더블체크 (수동)
    |   +-- 대상: KOFIA 공시, FunETF, 펀드닥터
    |   +-- 불일치 시 사용자 확인 및 수동 보정
    |   +-- tdf_fees.json 생성/업데이트
    |
    +-- Step 6-4. 신선도 및 검증
        +-- 30일 경과 시 갱신 안내
        +-- CSV 파이프라인(Phase 0-4)과 분리됨을 명시
```

---

## 스크립트 실행 방식

### 스크립트 참조 및 실행 (CRITICAL)

스크립트는 이 스킬의 상대경로에 위치합니다:

scripts/update_fund_data.py
scripts/classify_funds.py
scripts/update_tdf_data.py

**실행 순서:**

**Step 1. 상대경로로 실행** (최우선)
```bash
python scripts/update_fund_data.py --file [csv_file_path]
python scripts/classify_funds.py funds
python scripts/update_tdf_data.py --input [tdf_table_path] --base-date YYYY-MM-DD
```

**Step 2. 상대경로 실패 시 Glob 폴백**
```
Glob: **/investments-portfolio/skills/data-updater/scripts/update_fund_data.py
Glob: **/investments-portfolio/skills/data-updater/scripts/classify_funds.py
```

**Step 3. Glob도 실패 시 확장 탐색**
```
Glob: **/update_fund_data.py
Glob: **/classify_funds.py
```

**절대 금지**: 스크립트를 찾지 못했을 때 자체적으로 Python 코드를 작성하지 마세요.
반드시 에러를 보고하고 사용자에게 경로 확인을 요청하세요.

### 실행 명령어

```bash
# Dry-run (미리보기) - 권장
python scripts/update_fund_data.py \
  --file [csv_file_path] \
  --dry-run

# 실제 실행 (자동 경로 감지)
python scripts/update_fund_data.py \
  --file [csv_file_path]

# 실제 실행 (출력 경로 지정)
python scripts/update_fund_data.py \
  --file [csv_file_path] \
  --output-dir [output_directory]
```

### 분류만 재실행 (선택)

```bash
python scripts/classify_funds.py funds   # funds/fund_data.json → funds/fund_classification.json
```

분류 규칙(위험자산 riskStatus·환헤지)은 `scripts/fund_name_rules.py` 하나에 있고 `update_tdf_data.py`도 같은 규칙을 쓴다. 근거는 `dc-pension-rules` 스킬 §2.

### 스크립트 옵션

| 스크립트 | 옵션 | 필수 | 설명 |
|---------|------|:----:|------|
| update_fund_data.py | `--file` | O | CSV 파일 경로 |
| update_fund_data.py | `--output-dir` | X | 출력 디렉토리 (기본: 자동 감지) |
| update_fund_data.py | `--dry-run` | X | 미리보기 모드 |
| classify_funds.py | (위치 인자) | X | funds 디렉터리 (기본: 자동 감지). fund_data.json을 읽고 같은 곳에 fund_classification.json을 쓴다 |
| update_tdf_data.py | `--input` | 표 모드 O | TDF 표 파일 경로 |
| update_tdf_data.py | `--base-date` | 표 모드 O | 표의 수익률 기준일 YYYY-MM-DD (`_meta.version`과 연령대 기준년도가 된다) |
| update_tdf_data.py | `--output` | X | 출력 JSON 경로 |
| update_tdf_data.py | `--from-proposal` | X | 기존 tdf_data.json 행을 상품제안서(all_fund_data) 기준일로 갱신 |
| update_tdf_data.py | `--fees` | X | all_fund_fees 기준 fundCode·총보수 결정적 보강 (tdf_fees 기준일도 따라감) |

### 의존성

- Python 3.10+
- `update_fund_data.py` / `classify_funds.py` / `fetch_latest_proposal.py`: 표준 라이브러리만 사용
- `xlsx_to_csv.py`: **openpyxl 필요** (`pip install openpyxl`)

---

## Output Structure

### 출력 디렉토리 구조

```
funds/
├── fund_data.json              # 필터링된 펀드 (206개)
├── fund_fees.json              # 필터링된 수수료 정보
├── fund_classification.json    # 필터링된 펀드 분류
├── tdf_data.json               # TDF 펀드 데이터 (Phase 6)
├── tdf_fees.json               # TDF 수수료 정보 (Phase 6)
├── investable_codes.json       # 투자 가능 펀드 코드 목록
├── deposit_rates.json          # 예금금리 정보
├── all/                        # 전체 펀드 데이터
│   ├── all_fund_data.json      # 전체 펀드 (2015개)
│   ├── all_fund_fees.json      # 전체 수수료 정보
│   └── all_fund_classification.json  # 전체 펀드 분류
└── archive/                    # 이전 버전 백업
    ├── fund_data_2026-01-01.json
    └── fund_fees_2026-01-01.json
```

### fund_data.json 구조

```json
{
  "_meta": {
    "version": "YYYY-MM-DD",
    "sourceFile": "26년01월_상품제안서_퇴직연금(DCIRP).csv",
    "updatedAt": "2026-01-21T21:00:00+09:00",
    "recordCount": 206,
    "missing": []
  },
  "funds": [
    {
      "fundCode": "K55105EC1749",
      "name": "펀드명",
      "company": "운용사명",
      "riskLevel": 2,
      "riskName": "높은위험",
      "return10y": "",
      "return7y": "",
      "return5y": "",
      "return3y": "70.34",
      "return1y": "178.03",
      "return6m": "30.03",
      "netAssets": "50840000",
      "inceptionDate": "20220627",
      "isAffiliate": false,
      "fundType": "ETF"
    }
  ]
}
```

### fund_classification.json 구조

```json
{
  "펀드명": {
    "category": "해외주식형",
    "riskAsset": true,
    "assetClass": "equity",
    "region": "global",
    "themes": ["semiconductor", "ai"],
    "hedged": false,
    "riskLevel": 2,
    "source": "fund_data.json + keyword classification",
    "generatedAt": "2026-01-21"
  }
}
```

### deposit_rates.json 구조

```json
{
  "_meta": {
    "version": "YYYY-MM-DD",
    "source": "과학기술인공제회 퇴직연금 원리금보장형 운용방법 안내",
    "updatedAt": "2026-01-31T12:00:00+09:00",
    "recordCount": 4,
    "freshnessThresholdDays": 30,
    "note": "30일 경과 시 데이터 업데이트 필요"
  },
  "rates": [
    {
      "id": "sema-1y",
      "institution": "과학기술인공제회",
      "productName": "과학기술인공제회 퇴직연금 운용방법 (1년)",
      "type": "원리금보장형운용방법",
      "term": "1년",
      "termMonths": 12,
      "rate": 4.9,
      "unit": "%"
    },
    {
      "id": "woori-1y",
      "institution": "우리은행",
      "productName": "우리은행 정기예금 1년",
      "type": "원리금보장형운용방법",
      "term": "1년",
      "termMonths": 12,
      "rate": 2.75,
      "unit": "%"
    }
  ],
  "summary": {
    "highestRate": {
      "institution": "과학기술인공제회",
      "rate": 4.9,
      "term": "1년"
    },
    "institutions": ["과학기술인공제회", "우리은행"]
  }
}
```

---

## 예금금리 업데이트 (Phase 5)

### 출처: 과학기술인공제회 공개 페이지 (기준일 필수) + 사용자 포털 값 대조

원리금보장형 금리는 공제회 공개 페이지에 기준일과 함께 게시된다.

- URL: https://www.sema.or.kr/sema/annty/guidance/fundProduct.do?menuNo=200059 (퇴직연금 > 원리금보장형상품)
- 페이지 상단 `[기준일:YYYY.MM.DD]`를 반드시 읽어 `_meta.version`/`sourceBaseDate`에 기록한다. 기준일을 못 찾으면 갱신하지 않는다.
- 표의 기간·금리·일반/특별 중도해지 규칙과 표 아래 ※ 주석(특별가산금리·가산기간·회원지급률, 은행 금리 적용기간, 만기 처리)을 모두 옮긴다.
  - 공제회 상품: `rate`(회원지급률), `baseRate`(기본), `bonusRate`·`bonusPeriod`(특별가산), `maturityRule`(재예치)
  - 은행 상품: `rate`, `appliesFrom`·`appliesTo`(적용기간), `maturityRule`(자동연장 없음 → 현금성자산), `depositProtection`
- 사용자가 포털 화면 값을 주면 `_meta.ownerPortalCheck`에 대조 결과(`matches`, 값, 확인 시각)를 남긴다. 불일치면 갱신을 멈추고 사용자에게 알린다.
- 페이지에 접근할 수 없을 때만 사용자에게 포털 값을 직접 묻는다 (아래 질문 예시).

### 사용자 질문 예시 (페이지 접근 불가 시, mcp_question 사용)

```
과학기술인공제회 퇴직연금 원리금보장형 금리를 확인해주세요 (페이지 기준일 포함):
- 과학기술인공제회 퇴직연금 운용방법(1년): _____ % (기본/가산 구분)
- 우리은행 정기예금 1년·6개월·3개월: _____ % (적용기간)
```

### 업데이트 수행 방법

공개 페이지(및 사용자 포털 값 대조)로 금리를 확인한 후:

```python
# deposit_rates.json 업데이트
import json
from datetime import datetime

# 현재 파일 읽기
with open('funds/deposit_rates.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 메타데이터 업데이트
data['_meta']['version'] = page_base_date  # 페이지 [기준일:YYYY.MM.DD] → 'YYYY-MM-DD' (현재 날짜 아님)
data['_meta']['updatedAt'] = datetime.now().isoformat()

# 금리 업데이트 (공개 페이지 값, 사용자 포털 값과 대조)
for rate in data['rates']:
    if rate['id'] == 'sema-1y':
        rate['rate'] = 5.7  # 회원지급률 = 기본 5.2 + 특별가산 0.5
    elif rate['id'] == 'woori-1y':
        rate['rate'] = 3.7  # 2026-11-01~11-30 적용

# 요약 업데이트
data['summary']['highestRate']['rate'] = max(r['rate'] for r in data['rates'])

# 저장
with open('funds/deposit_rates.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

---

## TDF 데이터 업데이트 (Phase 6)

### ⚠️ 중요: 수동 트리거 및 분리된 파이프라인

**TDF 데이터 업데이트는 CSV 파이프라인(Phase 0-4)과 완전히 분리되어 있습니다.**

- CSV 파일에는 TDF 수익률 데이터가 포함되어 있지 않거나 형식이 다를 수 있음
- 따라서 사용자가 직접 TDF 수익률 표를 붙여넣어야 함 (수동 트리거)
- `deposit_rates.json`과 마찬가지로 필요 시에만 업데이트 수행

### 워크플로우 상세

1. **원본 데이터 확보**: 사용자가 SEMA 포털 등에서 복사한 TDF 수익률 표를 Markdown 또는 Text 형식으로 제공
2. **스크립트 실행**: `update_tdf_data.py`를 사용하여 `tdf_data.json` 생성
3. **총보수 3출처 더블체크 (필수)**:
   - TDF는 총보수 체계가 복잡하므로 반드시 3개 출처 교차 검증 필요
   - 출처: **KOFIA(금융투자협회) 공시, FunETF, 펀드닥터**
   - 데이터 불일치 또는 미해결 데이터 발생 시 반드시 **사람(사용자) 확인** 절차를 거침
4. **파일 생성**: 검증된 데이터를 바탕으로 `tdf_data.json` 및 `tdf_fees.json` 생성/업데이트

### 신선도 관리

- **30일 경과 시**: 데이터가 오래되었음을 알리고 업데이트 권장
- `tdf_data.json`의 `_meta.version` 또는 `_meta.updatedAt`을 기준으로 판단

---

## Usage Example

### 입력 예시 1: 펀드 데이터 업데이트

```
data-updater 스킬을 사용해서 펀드 데이터를 업데이트해줘.
CSV 파일: resource/26년01월_상품제안서_퇴직연금(DCIRP).csv
```

또는 간단히:

```
펀드 데이터 업데이트해줘
```

### 입력 예시 2: 예금금리 업데이트

```
예금금리 데이터도 업데이트해줘
```

또는:

```
data-updater 스킬로 예금금리 업데이트 해줘.
과학기술인공제회 1년: 4.9%
우리은행 1년: 2.75%
```

### 수행 절차

**펀드 데이터 업데이트 (Phase 0-4):**
1. **Phase 0**: CSV 파일 확인, UTF-8 인코딩 검증
2. **Phase 1**: Dry-run으로 미리보기, 2015개 펀드 발견
3. **Phase 2**: Python 스크립트 실행, JSON 파일 생성
4. **Phase 3**: 생성된 파일 검증
5. **Phase 4**: 완료 보고서 생성

**예금금리 업데이트 (Phase 5, 선택):**
6. **Phase 5**: 사용자에게 예금금리 확인 요청 → deposit_rates.json 업데이트

**TDF 데이터 업데이트 (Phase 6, 선택):**
7. **Phase 6**: 사용자로부터 TDF 표 수집 → update_tdf_data.py 실행 → 3출처 더블체크 → tdf_data.json/tdf_fees.json 생성

### 출력 파일

1. `funds/fund_data.json`: 펀드 마스터 데이터 (2015개)
2. `funds/fund_fees.json`: 펀드 수수료 정보
3. `funds/fund_classification.json`: 펀드 분류 정보
4. `funds/deposit_rates.json`: 예금금리 정보 (Phase 5 실행 시)
5. `funds/tdf_data.json`: TDF 펀드 데이터 (Phase 6 실행 시)
6. `funds/tdf_fees.json`: TDF 수수료 정보 (Phase 6 실행 시)

---

## 에러 처리

| 에러 | 원인 | 해결 |
|------|------|------|
| `File not found` | CSV 파일 경로 오류 | 경로 확인, 절대 경로 사용 |
| `UnicodeDecodeError` | 인코딩 오류 | CSV 파일을 UTF-8로 재저장 |
| `Header not found` | CSV 형식 오류 | "펀드코드" 포함 헤더 확인 |
| `Output directory not found` | 경로 감지 실패 | `--output-dir` 옵션 사용 |

상세한 에러 처리 및 디버깅 방법은 `./scripts/README.md` 참조.

---

## CSV 파일 형식

### 예상 구조

```
Row 1: 사업자명     | 미래에셋증권
Row 2: 제도유형     | DC/IRP
Row 3: 상품유형     | 실적배당형 상품(펀드/ETF)
Row 4: 기준일       | YYYY-MM-DD, 제로인
Row 5-7: (빈 행 또는 기타)
Row 8: 헤더         | 펀드코드 | 펀드명 | 운용회사명 | 위험등급 | ...
Row 9+: 데이터      | K55105EC1749 | 펀드명 | 운용사 | 2등급(높은위험) | ...
```

### 필수 컬럼

| 컬럼명 | 용도 |
|--------|------|
| 펀드코드 | 고유 식별자 |
| 펀드명 | 펀드 이름 |
| 운용회사명 | 운용사 |
| 위험등급 | "N등급(위험명)" 형식 |
| 순자산총액(억원) | 순자산 (억원 단위) |
| 수익률(6M), (1Y), (3Y), (5Y), (7Y), (10Y) | 기간별 수익률 |
| 설정일 | 펀드 설정일 |
| 비율(%) | 총보수 |
| 1년투자비용(원) | 연간 비용 |

---

## 관련 플러그인

| 플러그인/에이전트 | 역할 | 연계 |
|------------------|------|------|
| portfolio-analyze | 포트폴리오 분석 오케스트레이션 명령 | fund_data.json, fund_fees.json, tdf_data.json, tdf_fees.json 신선도 다중 검사 (deposit_rates.json 존재 확인) |
| fund-portfolio | 펀드 추천 | fund_data.json, fund_classification.json, deposit_rates.json 사용 |
| compliance-checker | DC 규제 검증 | fund_classification.json, deposit_rates.json 사용 |
| fund-selection-criteria | 펀드 선택 기준 | deposit_rates.json으로 예금 vs 채권 비교 |
| data-updater | 데이터 변환 | 현재 스킬 |

---

## Resources

### 스크립트 위치

- **메인 스크립트**: `scripts/update_fund_data.py` (Glob으로 절대경로 확보 후 실행)
- **분류 스크립트**: `scripts/classify_funds.py` (Glob으로 절대경로 확보 후 실행)
- **TDF 스크립트**: `scripts/update_tdf_data.py` (Glob으로 절대경로 확보 후 실행)
- **상세 문서**: `scripts/README.md`

### 성능

- 2,015개 펀드 처리 시간: 약 1-2초
- 메모리 사용량: 약 50MB
