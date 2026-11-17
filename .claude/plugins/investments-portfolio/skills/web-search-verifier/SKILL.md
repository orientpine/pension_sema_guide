---
name: web-search-verifier
description: "주장 종류별 출처 기준(공식 사실=발표 기관 1차 출처, 시장 숫자=독립 3출처 교차검증, 해석=해석 표시) 웹검색 프로토콜. 환각 방지 첫 번째 방어선. 모든 거시경제 데이터 수집 시 필수 사용."
tools: WebSearch, WebFetch
---

# 웹검색 교차검증 스킬

## ⚠️ CRITICAL: 스킬 사용 방법 (반드시 숙지)

> **이 스킬은 "함수"가 아닙니다. 지침 문서입니다.**
> 
> - ❌ `search_rate("fed_funds")` 같은 함수 호출은 **작동하지 않습니다**
> - ✅ 에이전트가 아래 '1차 출처 직접 조회' 엔드포인트를 `WebFetch`로, 모자라면 `WebSearch`를 **직접 호출**해야 합니다
> - ✅ 이 스킬은 **검색 쿼리 패턴과 검증 절차**를 안내하는 문서입니다

### 올바른 사용 방법

```
1. 이 스킬 문서를 읽고 검색 쿼리 패턴 파악
2. 1차 출처 엔드포인트를 WebFetch로 직접 조회, 모자라면 WebSearch 직접 호출
3. 검색 결과에서 데이터 추출
4. 주장 종류별 출처 기준(아래 표)으로 확정 — 시장 숫자는 3개 출처 교차 검증
5. 출력 스키마에 맞춰 결과 포장
```

### 잘못된 사용 방법 (환각 발생)

```
❌ "search_rate() 호출" (존재하지 않는 함수)
❌ "스킬이 알아서 검색해줌" (스킬은 문서일 뿐)
❌ 예시 데이터의 숫자를 그대로 사용 (하드코딩된 오래된 값)
```

---

## Overview

이 스킬은 거시경제 데이터(지수, 금리, 환율) 수집 시 **환각을 방지**하기 위한 표준 프로토콜입니다.
모든 수치·사실은 **에이전트가 직접 조회**(아래 1차 출처 엔드포인트를 먼저, 모자라면 웹검색)하고, **주장 종류별 출처 기준**(공식 사실은 발표 기관 1차 출처, 시장 숫자는 3개 이상의 독립 출처 교차 검증)을 통과한 뒤에만 사용 가능합니다.

## 주장 종류별 출처 기준 (먼저 종류를 정한다)

> **결과 본 뒤 바꾼 정의 (2026. 11. 17., 소유자 질문 "검증을 통과 못하는 건 검증 방법이 잘못된 것은 아니야?")**
> 옛 정의(v2.1): 모든 수치·사실은 독립 3출처, 같은 통신사 재게시·같은 기관의 여러 페이지는 1개로 셈.
> 옛 정의의 값: 2026. 11. 17. 실제 포트폴리오 상담에서 7개국 중앙은행 기준금리 7/7 null, 리더십 `decision_usable=false` → 지역 판단 전체가 배분 근거에서 빠짐.
> 이유: 기준금리·현직 인물은 **발표 기관 한 곳이 원천**이라 독립 3출처는 구조적으로 불가능하고, 보도는 그 발표를 옮긴 것일 뿐이다.
> 바꾼 것은 **주장 종류별 출처 규칙**이다. 시장 숫자 기준은 낮추지 않았다(그대로 3출처).

| 종류 (`claim_type`) | 예 | 확정 조건 | 못 채우면 |
|---|---|---|---|
| `official_fact` 공식 사실 | 중앙은행 기준금리·결정일, 현직 지도자·장관·총재 이름과 직함 | **발표 기관 호스트의 1차 출처 1곳**: `url`·`accessed_at`(조회 시각, 분석일 7일 이내)·`original_text`(원문 그대로) 필수. 금리는 `value`·`decision_date`도 필수. 출처 중 값이 다른 것이 하나라도 있으면 `VALUE_MISMATCH`로 실패. 발표 기관 사이트가 이 호스트에서 열리지 않을 때만 옛 규칙(원발행자가 다른 독립 3출처, 같은 값)으로 확정 | null + 사유, 본문에 숫자·이름을 쓰지 않는다 |
| `market_number` 시장 숫자 | 지수 종가, 환율, 시장금리 | **그대로**: 호스트가 다른 독립 3출처, 같은 기준일, ±1% 이내 (`index_status.py`가 판정) | null + `failed_items` |
| `interpretation` 해석 | 정책 성향(매파·확장 등), 지역 확대/유지/축소, 시나리오 | `claim_type: "interpretation"`·`is_inference: true` 표시 + 근거 원문·출처. 배분에는 **방향(확대·유지·축소)만** 쓰고 수치 비중을 만들지 않는다 | 표시 없으면 배분 근거로 쓰지 않는다 |

- 발표 기관 호스트 목록과 판정은 `.claude/plugins/macro-analysis/scripts/claim_status.py`(`ISSUERS`) 하나로 한다. 리더십 결과는 `python3 .claude/plugins/macro-analysis/scripts/claim_status.py {output_path}/leadership-analysis.json --as-of YYYY-MM-DD`로 판정하고, `decision_usable`은 파일이 스스로 적은 값이 아니라 이 출력값을 쓴다(7개국 지도자·기준금리가 모두 확정되고 해석 위반이 없을 때 true).
- 국가별 기준금리 정의(무엇을 적을지): 미국 FOMC 연방기금금리 목표 범위, 중국 인민은행 7일물 역레포 금리(공개시장 정책금리), 한국 한국은행 기준금리, 일본 일본은행 무담보 콜 익일물 유도 목표, 인도 RBI 정책 레포금리, 베트남 SBV 재융자금리(refinancing rate), 인도네시아 BI-Rate. 현재 금리를 보여 주는 발표 기관 페이지나 최신 결정문을 열고, 결정문을 쓸 때는 같은 기관의 회의 일정·결정 목록으로 그 뒤 결정이 없었는지 확인해 `original_text`에 함께 남긴다.
- 보도(AP·Reuters·Bloomberg 등)는 공식 사실의 **값 충돌 확인용**으로 남길 수 있다. 확정 근거로 세지 않는다.

## 1차 출처 직접 조회 (검색보다 먼저)

검색 결과 요약이나 앱 셸 페이지(본문 없이 스크립트만 있는 Reuters·AP 등)는 원문을 읽을 수 없어 출처로 세지 않는다. 아래 엔드포인트는 값을 기계가 읽을 수 있게 돌려주므로 `WebFetch`(omo: `webfetch` 또는 eval js `fetch`)로 직접 열어 값·기준일·원문 조각을 기록한다. 호스트가 다르면 독립 출처로 본다. 시장 숫자는 세 곳의 **같은 기준일** 값이 ±1% 안이어야 `verified: true`다(규칙은 그대로). Fed 목표 범위·한국은행 기준금리 줄은 공식 사실이라 발표 기관 엔드포인트(연준·뉴욕 연준 / ECOS·한국은행) 1곳으로 확정하고, 나머지 열은 값 충돌 확인용이다.

| 시리즈 | 1차·기계 판독 출처 (호스트가 다른 것끼리 세 곳 이상) | 읽을 필드 |
|---|---|---|
| KOSPI | 한국은행 ECOS `https://ecos.bok.or.kr/api/StatisticSearch/{KEY}/json/kr/1/20/802Y001/D/{YYYYMMDD}/{YYYYMMDD}/0001000` (KEY 없으면 `sample`, 10행 제한) · 네이버 `https://m.stock.naver.com/api/index/KOSPI/basic` · Yahoo `https://query1.finance.yahoo.com/v8/finance/chart/%5EKS11?range=5d&interval=1d` | ECOS `TIME`·`DATA_VALUE`, 네이버 `closePrice`·`localTradedAt`, Yahoo `indicators.quote[0].close`·`timestamp` |
| KOSDAQ | ECOS 같은 표 항목 `0089000` · 네이버 `.../api/index/KOSDAQ/basic` · Yahoo `%5EKQ11` | 위와 같음 |
| S&P 500 | Yahoo `%5EGSPC` · 네이버 `https://api.stock.naver.com/index/.INX/basic` · CNBC `https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols=.SPX&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json` | 종가·거래일 |
| NASDAQ | Yahoo `%5EIXIC` · 네이버 `.../index/.IXIC/basic` · Nasdaq `https://api.nasdaq.com/api/quote/COMP/info?assetclass=index` · CNBC `.IXIC` | 종가·거래일 |
| USD/KRW, EUR/KRW, JPY/KRW(100엔) | 서울외국환중개 매매기준율 `http://www.smbs.biz/Flash/TodayExRate_flash.jsp?tr_date={YYYY-MM-DD}` · ECOS `731Y001`(원/달러 `0000001`) · 네이버 `https://m.stock.naver.com/front-api/marketIndex/productDetail?category=exchange&reutersCode=FX_USDKRW` · Yahoo `KRW=X`·`EURKRW=X`·`JPYKRW=X` | 기준율 종류(매매기준율/고시/시장)와 단위(엔은 100엔)를 함께 적는다 |
| Fed 목표 범위 | 연준 FOMC 성명 `https://www.federalreserve.gov/newsevents/pressreleases/monetary{YYYYMMDD}a.htm`(최신 회의 날짜는 `https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm`) · 뉴욕 연준 `https://markets.newyorkfed.org/api/rates/unsecured/effr/last/1.json`(`targetRateFrom`·`targetRateTo`) · 독립 보도 1곳(본문을 읽을 수 있는 기사) | 결정일과 그 뒤 회의가 없었는지 |
| 한국은행 기준금리 | ECOS `722Y001` 항목 `0101000` · 한국은행 기준금리 추이 `https://www.bok.or.kr/portal/singl/baseRate/list.do?dataSeCd=01&menuNo=200643` · 독립 보도 1곳 | 변경일과 최근 금통위 동결 여부 |

- 2026. 11. 17. 이 저장소 운영 호스트 기준 접속 불가: FRED CSV(시간 초과), stooq(JS 확인 페이지), KRX 정보데이터시스템(`LOGOUT`, 로그인 필요). 열리면 쓸 수 있지만 위 표만으로 세 곳을 채울 수 있다.
- 미국 지수는 미국 장 마감일(한국 날짜로는 다음 날) 종가를 쓴다. 세 출처의 기준일이 다르면 가장 최근의 공통 기준일로 맞춘다(Yahoo 일별 배열에서 그 날 값을 고른다).
- `data_quality.skill_verified`는 **출력에 남은 모든 수치·사실이** 자기 종류의 출처 기준(위 표)을 통과했을 때 true다. 통과 못 한 수치(예: 정량 전망)는 null과 사유로 두고 `failed_items`에 적는다. null로 둔 항목은 본문에서 숫자로 쓰지 않는다.

---

## 절대 규칙 (Zero Tolerance)

### 금지 사항 (NEVER)
- ❌ 웹검색 없이 숫자 생성 → 즉시 FAIL
- ❌ 시장 숫자를 단일 출처로 확정 → 최소 3개 필수 (공식 사실은 발표 기관 1차 출처 1곳으로 확정, 발표 기관이 아닌 단일 출처로는 확정 금지)
- ❌ 출처 URL 없이 데이터 반환 → 검증 불가
- ❌ 7일 이상 오래된 데이터 사용 → 최신성 위반
- ❌ Blocklist 출처 사용 → 신뢰도 위반

### 필수 사항 (MUST)
- ✅ 모든 주장에 `claim_type`(official_fact / market_number / interpretation)을 정하고 그 기준으로 확정
- ✅ 시장 숫자: 최소 3개 독립 출처에서 교차 검증, 출처 간 ±1% 이내 일치
- ✅ 공식 사실: 발표 기관 1차 출처(URL·조회 시각·원문) 필수, 값이 다른 출처가 있으면 FAIL
- ✅ 해석: 해석 표시, 배분에는 방향만
- ✅ 모든 데이터에 [출처: URL, 날짜] 태그 포함
- ✅ 검증 실패 시 FAIL 반환 (추정값 금지)
- ✅ **원문 인용 필수** (v2.0 신규) - 숫자를 포함한 검색 결과 원문을 그대로 인용

---

## ⚠️ 원문 인용 규칙 (v2.0 신규 - CRITICAL)

> **환각 방지의 핵심**: 검색 결과에서 숫자를 추출할 때 반드시 **원문을 그대로 인용**해야 합니다.
> 원문과 보고 값이 일치하지 않으면 **FAIL**입니다.

### 올바른 숫자 추출 방법

```
1. 웹검색 실행
2. 검색 결과에서 숫자가 포함된 문장을 **그대로 복사**
3. 원문에서 숫자 추출
4. 추출한 숫자와 원문을 함께 보고
```

### 출력 형식 (필수)

모든 수치 데이터는 다음 형식으로 보고해야 합니다:

```json
{
  "value": 6936,
  "original_text": "The US500 fell to 6936 points on January 12, 2026",
  "source": "Trading Economics",
  "url": "https://tradingeconomics.com/united-states/stock-market"
}
```

### 검증 규칙

| 규칙 | 설명 | 위반 시 |
|:-----|:-----|:--------|
| **원문 필수** | `original_text` 필드 없으면 무효 | FAIL |
| **숫자 일치** | `value`가 `original_text` 내 숫자와 일치해야 함 | FAIL |
| **복사 금지** | 이전 결과나 예시 값을 복사하면 안 됨 | FAIL |

### 원문 인용 예시

**✅ 올바른 예시**:
```json
{
  "index": "S&P 500",
  "value": 6936,
  "original_text": "The main stock market index of United States, the US500, fell to 6936 points on January 12, 2026",
  "source_url": "https://tradingeconomics.com/united-states/stock-market"
}
```

**❌ 잘못된 예시 (환각 위험)**:
```json
{
  "index": "S&P 500",
  "value": 5906,
  "original_text": null,
  "source_url": "https://tradingeconomics.com/united-states/stock-market"
}
```
→ 원문 없이 숫자만 보고하면 검증 불가능

---

## 검색 프로토콜

### 1. 지수 데이터 검색

**데이터 유형**: 지수 (Index)

> ⚠️ 아래는 **검색 패턴 가이드**입니다. `search_index()`라는 함수는 **존재하지 않습니다**.
> 반드시 `WebSearch`를 **직접 호출**하세요.

**지원 지수**:
- S&P 500, NASDAQ, Dow Jones
- KOSPI, KOSDAQ
- USD/KRW, EUR/KRW, JPY/KRW

**검색 쿼리 패턴** (3개 병렬 실행):

| # | 패턴 | 대상 출처 |
|:-:|:-----|:---------|
| 1 | `"[index] price today site:investing.com OR site:bloomberg.com"` | 글로벌 금융 |
| 2 | `"[지수] 종가 site:tradingeconomics.com"` | 금융 데이터 |
| 3 | `"[index] quote site:finance.yahoo.com OR site:marketwatch.com"` | 시세 사이트 |

**검증 절차**:
1. 3개 검색 결과에서 수치 추출
2. 날짜 일치 확인 (동일 거래일)
3. 값 일치 확인 (±1% 이내)
4. 1차 출처 포함 확인

**출력 스키마 (v2.0 업데이트)**:
```json
{
  "index": "S&P 500",
  "value": "[SEARCH_RESULT - 웹검색 결과로 대체]",
  "unit": "pt",
  "date": "[SEARCH_DATE - 검색 시점 날짜]",
  "verified": true,
  "variance": "[CALCULATED - 출처 간 편차 계산]",
  "original_text": "[REQUIRED - 숫자를 포함한 검색 결과 원문]",
  "sources": [
    {
      "name": "Trading Economics",
      "url": "[ACTUAL_URL]",
      "value": "[ACTUAL_VALUE]",
      "original_text": "[EXACT_QUOTE - 이 출처에서 숫자가 포함된 문장]",
      "tier": 2
    },
    {
      "name": "Bloomberg",
      "url": "[ACTUAL_URL]",
      "value": "[ACTUAL_VALUE]",
      "original_text": "[EXACT_QUOTE]",
      "tier": 1
    }
  ]
}

⚠️ CRITICAL (v2.0):
1. `original_text` 필드는 **필수**입니다. 없으면 FAIL.
2. `value`는 반드시 `original_text` 내의 숫자와 일치해야 합니다.
3. 예시 값을 그대로 사용하지 마세요.
```

### 2. 금리 데이터 검색

**데이터 유형**: 금리 (Interest Rate)

> ⚠️ 아래는 **검색 패턴 가이드**입니다. `search_rate()`라는 함수는 **존재하지 않습니다**.
> 반드시 `WebSearch`를 **직접 호출**하세요.

**지원 금리**:
- fed_funds: 미국 기준금리
- bok_base: 한국 기준금리
- us_10y_treasury: 미국 10년물 국채

**검색 쿼리 패턴**:

| 금리 | 1차 출처 쿼리 | 2차 출처 쿼리 |
|:-----|:-------------|:-------------|
| Fed | `"federal funds rate site:federalreserve.gov"` | `"fed rate site:tradingeconomics.com"` |
| BOK | `"기준금리 site:bok.or.kr"` | `"korea rate site:tradingeconomics.com"` |

**검증 절차**:
1. 공식 출처(1차) 검색
2. 교차검증 출처(2차) 검색
3. 값 일치 확인
4. FOMC/금통위 결정일 확인
5. 다음 회의 일정 확인

**출력 스키마 (v2.0 업데이트)**:
```json
{
  "rate_type": "fed_funds",
  "value": "[SEARCH_RESULT - 웹검색으로 확인한 실제 금리]",
  "decision_date": "[SEARCH_RESULT - 최근 FOMC/금통위 결정일]",
  "next_meeting": "[SEARCH_RESULT - 다음 회의 예정일]",
  "verified": true,
  "original_text": "[REQUIRED - 금리 수치가 포함된 검색 결과 원문]",
  "sources": [
    {
      "name": "Federal Reserve",
      "url": "[ACTUAL_URL]",
      "value": "[ACTUAL_VALUE]",
      "original_text": "[EXACT_QUOTE - 공식 출처의 금리 언급 원문]",
      "official": true
    },
    {
      "name": "Trading Economics",
      "url": "[ACTUAL_URL]",
      "value": "[ACTUAL_VALUE]",
      "original_text": "[EXACT_QUOTE]",
      "official": false
    }
  ]
}

⚠️ CRITICAL (v2.0):
1. `original_text` 필드는 **필수**입니다. 없으면 FAIL.
2. `value`는 반드시 `original_text` 내의 숫자와 일치해야 합니다.
3. 금리의 경우 "3.50-3.75%" 형식으로 범위 표기 가능.
4. 예시 값을 그대로 사용하면 환각(hallucination)이 발생합니다.
```

---

## 허용 출처 (Allowlist)

### Tier 1: 공식 출처 (필수 1개 이상)

| 데이터 | 출처 | URL |
|:-------|:-----|:----|
| 미국 주식/경제 | FRED | fred.stlouisfed.org |
| 미국 금리 | Federal Reserve | federalreserve.gov |
| 한국 주식 | 한국거래소 | krx.co.kr |
| 한국 금리 | 한국은행 | bok.or.kr |
| 글로벌 | Bloomberg | bloomberg.com |

### Tier 2: 교차검증 출처

| 출처 | URL | 커버리지 |
|:-----|:----|:---------|
| Trading Economics | tradingeconomics.com | 글로벌 |
| Investing.com | investing.com | 글로벌 |
| Yahoo Finance | finance.yahoo.com | 글로벌 |
| MarketWatch | marketwatch.com | 미국 중심 |

### Tier 3: 보조 출처

| 출처 | URL | 용도 |
|:-----|:----|:-----|
| 한국경제 | hankyung.com | 한국 시장 |
| 연합뉴스 | yna.co.kr | 한국 경제 |
| Reuters | reuters.com | 글로벌 뉴스 |
| FT | ft.com | 글로벌 금융 |

### Blocklist (금지)

- 개인 블로그
- 위키피디아 (실시간 데이터용)
- 커뮤니티 사이트
- 신뢰도 미검증 사이트

---

## 검증 실패 처리

### 실패 유형별 대응

| 실패 유형 | 코드 | 대응 |
|:----------|:-----|:-----|
| 출처 부족 | `INSUFFICIENT_SOURCES` | 추가 검색 시도 (최대 3회) |
| 값 불일치 | `VALUE_MISMATCH` | 범위로 표현 또는 1차 출처 우선 |
| 날짜 불일치 | `DATE_MISMATCH` | 가장 최신 날짜 출처 우선 |
| 1차 출처 없음 | `NO_PRIMARY_SOURCE` | 경고 + 2차 출처로 진행 |
| 전체 실패 | `COMPLETE_FAILURE` | FAIL 반환, 수동 확인 요청 |

### 실패 출력 스키마

```json
{
  "index": "KOSPI",
  "value": null,
  "verified": false,
  "error": {
    "code": "VALUE_MISMATCH",
    "reason": "출처 간 5.2% 차이 (허용: ±1%)",
    "details": {
      "source1": {"name": "A", "value": 4500},
      "source2": {"name": "B", "value": 4735}
    }
  },
  "recommendation": "수동 확인 필요"
}
```

---

## 사용 예시

### 에이전트에서 스킬 사용

```markdown
# index-fetcher 에이전트

## 데이터 수집

1. web-search-verifier 스킬 로드 확인 (검색 패턴 가이드로 참조)
2. S&P 500 수집:
   - WebSearch(query="S&P 500 price today") **직접 호출**
   - 검색 결과에서 original_text 추출
   - verified: true 확인
3. KOSPI 수집:
   - WebSearch(query="KOSPI 지수 현재") **직접 호출**
   - 검색 결과에서 original_text 추출
   - verified: true 확인

## 검증 실패 시

verified: false인 경우:
- 해당 지수는 "데이터 수집 실패" 명시
- 추정값 생성 금지
- 에러 코드 전달
```

---

## 리소스

- 허용 출처: 위 "Tier 1/2/3 출처" 섹션 참조
- 검색 패턴: 위 "검색 전략" 섹션 참조

---

## 메타 정보

```yaml
version: "2.2"
created: "2026-01-12"
updated: "2026-01-12"
author: "Claude"
purpose: "환각 방지 웹검색 표준화"
dependencies:
  - WebSearch
  - WebSearch
  - WebFetch
consumers:
  - index-fetcher
  - rate-analyst
  - sector-analyst
  - risk-analyst
  - leadership-analyst
  - macro-synthesizer
changes_v2.2:
  - "주장 종류별 출처 기준 추가(결과 본 뒤 바꾼 정의, 옛 정의와 값은 본문 표 위에 기록): 공식 사실=발표 기관 1차 출처, 시장 숫자=3출처 그대로, 해석=해석 표시·방향만. 판정 스크립트 macro-analysis/scripts/claim_status.py"
changes_v2.1:
  - "범위 검증 (Sanity Check) 제거 - 대폭락 시 정상 데이터 reject 문제"
changes_v2.0:
  - "원문 인용 필수화 (original_text 필드)"
  - "S&P 500 첫자리 오류 환각 방지"
```
