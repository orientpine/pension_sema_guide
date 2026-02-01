# 거시경제 에이전트 환각 수정 계획

**문서 버전**: v2.0  
**작성일**: 2026-01-12  
**상태**: 검토 대기  
**변경 사항**: 스킬 기반 아키텍처로 전환

---

## 1. 문제 정의

### 1.1 현상

portfolio-orchestrator 파이프라인의 거시경제 에이전트들이 실시간 데이터를 **허위 생성(hallucination)**하고 있음.

| 에이전트 | 보고값 | 실제값 | 오차율 |
|:---------|-------:|-------:|-------:|
| index-fetcher (S&P 500) | 5,966 | 6,966 | -14% |
| index-fetcher (KOSPI) | 2,586 | 4,586 | -44% |
| rate-analyst (Fed Rate) | 4.25% | 3.50% | +21% |

### 1.2 근본 원인 (테스트 검증 완료)

**2026-01-12 테스트 결과**:

| 조건 | S&P 500 | KOSPI | 결과 |
|:-----|--------:|------:|:----:|
| 웹검색 강제 없음 | 5,966 | 2,586 | **환각** |
| 웹검색 강제 명시 | 6,966.28 | 4,586 | **정확** |

**결론**: 에이전트에 exa 도구가 정의되어 있으나, **명시적 강제 없이는 사용하지 않음**.

### 1.3 영향 범위

```
index-fetcher ──┐
                ├──► macro-synthesizer ──► 최종 보고서 (오염)
rate-analyst ───┘
```

- **직접 영향**: macro-synthesizer 출력 오염
- **간접 영향**: 포트폴리오 권고의 거시경제 근거 신뢰도 저하
- **영향 없음**: fund-portfolio, compliance-checker (로컬 JSON 기반)

---

## 2. 해결 목표

### 2.1 성공 기준

| 항목 | 기준 | 측정 방법 |
|:-----|:-----|:----------|
| 지수 정확도 | 실제값 대비 ±2% 이내 | FRED/Trading Economics 대조 |
| 금리 정확도 | 실제값 일치 | Fed 공식 발표 대조 |
| 출처 커버리지 | 100% 데이터에 출처 명시 | 출력 검증 |
| 교차 검증 | 3개 이상 소스 확인 | 에이전트 로그 확인 |
| **스킬 사용률** | 100% 에이전트가 스킬 로드 | 에이전트 정의 확인 |

### 2.2 비목표 (Out of Scope)

- 실시간 API 연동 (MCP 서버 개발)
- 자동화된 데이터 파이프라인 구축
- 펀드 분석 에이전트 수정 (이미 정상 작동)

---

## 3. 해결 방안: 스킬 기반 아키텍처

### 3.1 아키텍처 비교

#### 기존 방식 (v1.0) - 프롬프트 강화

```
[문제]
agents/
├── index-fetcher.md    (tools: exa... 정의됨)
│   └── 프롬프트에 "웹검색 필수" 추가
│   └── 문제: 에이전트가 무시할 수 있음
└── rate-analyst.md
    └── 프롬프트에 "웹검색 필수" 추가
    └── 문제: 중복 코드, 일관성 없음
```

#### 신규 방식 (v2.0) - 스킬 기반

```
[해결]
skills/
└── web-search-verifier/
    └── SKILL.md    ← 웹검색 프로토콜 중앙 정의
                    ← 도구 캡슐화
                    ← 검증 로직 포함

agents/
├── index-fetcher.md
│   └── skill: web-search-verifier ← 스킬 로드 필수
│   └── 웹검색 도구 직접 노출 안 함
└── rate-analyst.md
    └── skill: web-search-verifier ← 동일 스킬 재사용
```

### 3.2 스킬 기반 아키텍처 장점

| 장점 | 설명 |
|:-----|:-----|
| **명시적 의존성** | 에이전트가 스킬을 로드해야만 웹검색 가능 |
| **중앙 관리** | 검색 규칙 변경 시 스킬 하나만 수정 |
| **재사용성** | index-fetcher, rate-analyst, sector-analyst 등 공유 |
| **캡슐화** | 복잡한 검색/검증 로직을 스킬 내부로 숨김 |
| **테스트 용이** | 스킬 단위 테스트 가능 |
| **감사 추적** | 스킬 사용 여부로 데이터 신뢰도 판단 |

### 3.3 데이터 흐름

```
[Before: 도구 직접 노출]
Agent ──► exa_web_search_exa ──► 결과 (사용 안 할 수 있음)

[After: 스킬 캡슐화]
Agent ──► web-search-verifier 스킬 로드
              │
              ├──► search_and_verify() 함수 호출 (필수)
              │         │
              │         ├──► exa_web_search_exa (내부 호출)
              │         ├──► 3개 소스 교차검증
              │         └──► 출처 URL 포함 결과 반환
              │
              └──► 검증된 데이터만 사용 가능
```

---

## 4. 스킬 설계: web-search-verifier

### 4.1 스킬 개요

| 항목 | 내용 |
|:-----|:-----|
| **이름** | web-search-verifier |
| **목적** | 3개 출처 교차검증 웹검색 프로토콜 |
| **도구** | exa_web_search_exa, websearch_web_search_exa, WebFetch |
| **위치** | `plugins/investments-portfolio/skills/web-search-verifier/` |

### 4.2 디렉토리 구조

```
plugins/investments-portfolio/
├── agents/
│   ├── index-fetcher.md      (수정: 스킬 참조 추가)
│   ├── rate-analyst.md       (수정: 스킬 참조 추가)
│   ├── sector-analyst.md     (수정: 스킬 참조 추가)
│   └── ...
└── skills/
    └── web-search-verifier/
        ├── SKILL.md          (신규: 메인 스킬 정의)
        └── references/
            ├── allowed-sources.md    (신규: 허용 출처 목록)
            └── search-patterns.md    (신규: 검색 쿼리 패턴)
```

### 4.3 SKILL.md 상세 설계

```yaml
---
name: web-search-verifier
description: "3개 출처 교차검증 웹검색 프로토콜. 환각 방지 첫 번째 방어선. 모든 거시경제 데이터 수집 시 필수 사용."
tools: exa_web_search_exa, websearch_web_search_exa, WebFetch
---
```

#### 4.3.1 핵심 규칙 (Critical Rules)

```markdown
# 웹검색 교차검증 스킬

## 절대 규칙 (Zero Tolerance)

### 금지 사항 (NEVER)
- ❌ 웹검색 없이 숫자 생성 → 즉시 FAIL
- ❌ 단일 출처만으로 확정 → 최소 3개 필수
- ❌ 출처 URL 없이 데이터 반환 → 검증 불가
- ❌ 7일 이상 오래된 데이터 사용 → 최신성 위반

### 필수 사항 (MUST)
- ✅ 최소 3개 독립 출처에서 교차 검증
- ✅ 1차 출처 필수 포함 (거래소, 중앙은행, FRED 등)
- ✅ 출처 간 ±1% 이내 일치 확인
- ✅ 모든 데이터에 [출처: URL, 날짜] 태그 포함
```

#### 4.3.2 검색 함수 정의

```markdown
## 검색 함수

### search_index(index_name: str) → IndexResult

지수 데이터 검색 및 교차검증.

**입력**:
- index_name: "S&P 500", "KOSPI", "NASDAQ", "USD/KRW" 등

**프로세스**:
1. 검색 쿼리 3개 병렬 실행:
   - 영문: "[index_name] price today site:investing.com OR site:bloomberg.com"
   - 한글: "[지수명] 종가 site:hankyung.com OR site:yna.co.kr"
   - 금융데이터: "[index_name] site:tradingeconomics.com"
2. 각 검색 결과에서 수치 추출
3. 3개 값 교차검증 (±1% 이내)
4. 검증 성공 시 결과 반환, 실패 시 FAIL

**출력**:
{
  "index": "S&P 500",
  "value": 6966.28,
  "unit": "pt",
  "date": "2026-01-09",
  "verified": true,
  "sources": [
    {"name": "Trading Economics", "url": "https://...", "value": 6966.70},
    {"name": "Morningstar", "url": "https://...", "value": 6966.28},
    {"name": "Markets Insider", "url": "https://...", "value": 6966.28}
  ],
  "variance": "0.01%"
}

**실패 시**:
{
  "index": "S&P 500",
  "value": null,
  "verified": false,
  "error": "CROSS_VERIFICATION_FAILED",
  "reason": "3개 출처 확보 실패 또는 ±1% 초과 불일치"
}
```

```markdown
### search_rate(rate_type: str) → RateResult

금리 데이터 검색 및 교차검증.

**입력**:
- rate_type: "fed_funds", "bok_base", "us_10y_treasury" 등

**프로세스**:
1. 공식 출처 우선 검색:
   - Fed: "Federal Reserve interest rate site:federalreserve.gov"
   - BOK: "한국은행 기준금리 site:bok.or.kr"
2. 교차검증 출처 검색:
   - "fed funds rate site:tradingeconomics.com"
   - "korea interest rate site:bloomberg.com"
3. 공식 출처 값과 교차검증 출처 일치 확인
4. FOMC/금통위 결정일 확인

**출력**:
{
  "rate_type": "fed_funds",
  "value": "4.25-4.50%",
  "decision_date": "2025-12-18",
  "next_meeting": "2026-01-29",
  "verified": true,
  "sources": [
    {"name": "Federal Reserve", "url": "https://...", "value": "4.25-4.50%", "official": true},
    {"name": "Trading Economics", "url": "https://...", "value": "4.25%"}
  ]
}
```

#### 4.3.3 허용 출처 (Allowlist)

```markdown
## 허용 출처

### 1차 출처 (필수 1개 이상 포함)

| 카테고리 | 출처 | URL 패턴 | 우선순위 |
|:---------|:-----|:---------|:--------:|
| 미국 주식 | FRED | fred.stlouisfed.org | 1 |
| 미국 주식 | Bloomberg | bloomberg.com | 1 |
| 한국 주식 | 한국거래소 | krx.co.kr | 1 |
| 미국 금리 | Federal Reserve | federalreserve.gov | 1 |
| 한국 금리 | 한국은행 | bok.or.kr | 1 |

### 2차 출처 (교차검증용)

| 카테고리 | 출처 | URL 패턴 | 우선순위 |
|:---------|:-----|:---------|:--------:|
| 범용 | Trading Economics | tradingeconomics.com | 2 |
| 범용 | Investing.com | investing.com | 2 |
| 범용 | Yahoo Finance | finance.yahoo.com | 2 |
| 범용 | MarketWatch | marketwatch.com | 2 |

### 3차 출처 (보조)

| 카테고리 | 출처 | URL 패턴 | 우선순위 |
|:---------|:-----|:---------|:--------:|
| 뉴스 | 한국경제 | hankyung.com | 3 |
| 뉴스 | 연합뉴스 | yna.co.kr | 3 |
| 뉴스 | Reuters | reuters.com | 3 |

### 금지 출처 (Blocklist)

- 개인 블로그
- 위키피디아 (실시간 데이터용)
- 신뢰도 낮은 사이트
- 출처 불명확한 페이지
```

#### 4.3.4 검증 로직

```markdown
## 검증 로직

### 교차검증 규칙

1. **수치 일치**: 3개 출처 값이 ±1% 이내
2. **날짜 일치**: 모든 출처가 동일 거래일 기준
3. **1차 출처 포함**: 공식 출처 최소 1개 필수
4. **신선도**: 모든 데이터 7일 이내

### 불일치 처리

| 상황 | 처리 |
|:-----|:-----|
| 2개 출처만 일치 | 3번째 출처 재검색, 실패 시 범위로 표현 |
| 1차 출처와 2차 출처 불일치 | 1차 출처 우선, 불일치 명시 |
| 모든 출처 불일치 (±5% 초과) | FAIL 반환, 수동 확인 요청 |

### 출력 형식 강제

모든 출력에 다음 형식 필수:

{value} [출처: {source_name}, {url}, {date}]

예시:
S&P 500: 6,966.28pt [출처: Trading Economics, https://tradingeconomics.com/..., 2026-01-09]
```

---

## 5. 에이전트 수정

### 5.1 index-fetcher.md 수정

**변경 전**:
```yaml
---
name: index-fetcher
tools: Read, Write, exa_web_search_exa, exa_crawling_exa
---
```

**변경 후**:
```yaml
---
name: index-fetcher
tools: Read, Write
skills: web-search-verifier
---

# 지수 데이터 수집 에이전트

## 스킬 사용 필수

> ⚠️ 이 에이전트는 `web-search-verifier` 스킬을 통해서만 데이터를 수집합니다.
> 스킬을 거치지 않은 데이터는 환각으로 간주됩니다.

### 데이터 수집 절차

1. `web-search-verifier` 스킬의 `search_index()` 함수 호출
2. 검증된 결과만 사용
3. `verified: false`인 경우 해당 지수 FAIL 처리

### 금지 사항

- ❌ exa 도구 직접 호출 (스킬 통해서만)
- ❌ 스킬 검증 없이 숫자 출력
- ❌ verified: false 결과 사용
```

### 5.2 rate-analyst.md 수정

**변경 전**:
```yaml
---
name: rate-analyst
tools: Read, exa_web_search_exa, websearch_web_search_exa, WebFetch
---
```

**변경 후**:
```yaml
---
name: rate-analyst
tools: Read
skills: web-search-verifier
---

# 금리 분석 에이전트

## 스킬 사용 필수

> ⚠️ 모든 금리 데이터는 `web-search-verifier` 스킬을 통해 수집합니다.

### 데이터 수집 절차

1. `web-search-verifier` 스킬의 `search_rate()` 함수 호출
2. Fed 금리: `search_rate("fed_funds")`
3. BOK 금리: `search_rate("bok_base")`
4. 검증된 결과만 분석에 사용
```

### 5.3 sector-analyst.md 수정 (해당 시)

```yaml
---
name: sector-analyst
tools: Read
skills: web-search-verifier
---

## 스킬 사용

섹터 전망 데이터 수집 시 `web-search-verifier` 스킬 활용.
```

---

## 6. 구현 계획

### 6.1 작업 목록 (수정됨)

| ID | 작업 | 담당 | 예상 시간 | 의존성 |
|:---|:-----|:-----|:----------|:-------|
| **T0** | **web-search-verifier 스킬 생성** | AI | **45분** | - |
| T1 | index-fetcher 에이전트 수정 | AI | 15분 | T0 |
| T2 | rate-analyst 에이전트 수정 | AI | 15분 | T0 |
| T3 | sector-analyst 에이전트 수정 | AI | 10분 | T0 |
| T4 | macro-synthesizer 검증 로직 추가 | AI | 15분 | T1, T2 |
| T5 | macro-critic 스킬 사용 검증 추가 | AI | 10분 | T4 |
| T6 | marketplace.json 업데이트 | AI | 5분 | T0 |
| T7 | 통합 테스트 | AI | 30분 | T1-T6 |
| T8 | 문서화 및 AGENTS.md 업데이트 | AI | 15분 | T7 |

**총 예상 시간**: 2시간 40분

### 6.2 T0: web-search-verifier 스킬 생성 (상세)

#### 파일 생성 목록

```bash
# 디렉토리 생성
mkdir -p plugins/investments-portfolio/skills/web-search-verifier/references

# 파일 생성
touch plugins/investments-portfolio/skills/web-search-verifier/SKILL.md
touch plugins/investments-portfolio/skills/web-search-verifier/references/allowed-sources.md
touch plugins/investments-portfolio/skills/web-search-verifier/references/search-patterns.md
```

#### SKILL.md 내용 (전체)

```markdown
---
name: web-search-verifier
description: "3개 출처 교차검증 웹검색 프로토콜. 환각 방지 첫 번째 방어선. 모든 거시경제 데이터 수집 시 필수 사용."
tools: exa_web_search_exa, websearch_web_search_exa, WebFetch
---

# 웹검색 교차검증 스킬

## Overview

이 스킬은 거시경제 데이터(지수, 금리, 환율) 수집 시 **환각을 방지**하기 위한 표준 프로토콜입니다.
모든 수치 데이터는 이 스킬을 통해 **3개 이상의 독립 출처에서 교차 검증** 후에만 사용 가능합니다.

---

## 절대 규칙 (Zero Tolerance)

### 금지 사항 (NEVER)
- ❌ 웹검색 없이 숫자 생성 → 즉시 FAIL
- ❌ 단일 출처만으로 확정 → 최소 3개 필수
- ❌ 출처 URL 없이 데이터 반환 → 검증 불가
- ❌ 7일 이상 오래된 데이터 사용 → 최신성 위반
- ❌ Blocklist 출처 사용 → 신뢰도 위반

### 필수 사항 (MUST)
- ✅ 최소 3개 독립 출처에서 교차 검증
- ✅ 1차 출처(공식) 최소 1개 필수 포함
- ✅ 출처 간 ±1% 이내 일치 확인
- ✅ 모든 데이터에 [출처: URL, 날짜] 태그 포함
- ✅ 검증 실패 시 FAIL 반환 (추정값 금지)

---

## 검색 프로토콜

### 1. 지수 데이터 검색

**함수**: `search_index(index_name)`

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

**출력 스키마**:
```json
{
  "index": "S&P 500",
  "value": 6966.28,
  "unit": "pt",
  "date": "2026-01-09",
  "verified": true,
  "variance": "0.01%",
  "sources": [
    {"name": "Trading Economics", "url": "https://...", "value": 6966.70, "tier": 2},
    {"name": "Bloomberg", "url": "https://...", "value": 6966.28, "tier": 1},
    {"name": "Yahoo Finance", "url": "https://...", "value": 6966.28, "tier": 2}
  ]
}
```

### 2. 금리 데이터 검색

**함수**: `search_rate(rate_type)`

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
4. 결정일(FOMC/금통위) 확인
5. 다음 회의 일정 확인

**출력 스키마**:
```json
{
  "rate_type": "fed_funds",
  "value": "4.25-4.50%",
  "decision_date": "2025-12-18",
  "next_meeting": "2026-01-29",
  "verified": true,
  "sources": [
    {"name": "Federal Reserve", "url": "https://...", "value": "4.25-4.50%", "official": true},
    {"name": "Trading Economics", "url": "https://...", "value": "4.25%", "official": false}
  ]
}
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

1. web-search-verifier 스킬 로드 확인
2. S&P 500 수집:
   - search_index("S&P 500") 호출
   - verified: true 확인
   - 결과 사용
3. KOSPI 수집:
   - search_index("KOSPI") 호출
   - verified: true 확인
   - 결과 사용

## 검증 실패 시

verified: false인 경우:
- 해당 지수는 "데이터 수집 실패" 명시
- 추정값 생성 금지
- 에러 코드 전달
```

---

## 메타 정보

```yaml
version: "1.0"
created: "2026-01-12"
author: "Claude"
purpose: "환각 방지 웹검색 표준화"
dependencies:
  - exa_web_search_exa
  - websearch_web_search_exa
  - WebFetch
consumers:
  - index-fetcher
  - rate-analyst
  - sector-analyst
```
```

### 6.3 T6: marketplace.json 업데이트

```json
{
  "name": "investments-portfolio",
  "source": "./plugins/investments-portfolio",
  "description": "DC 연금 포트폴리오 분석 멀티 에이전트 시스템",
  "version": "2.1.0",
  "category": "finance",
  "strict": true,
  "agents": [
    "./agents/index-fetcher.md",
    "./agents/rate-analyst.md",
    // ... 기존 에이전트들
  ],
  "skills": ["./skills"]  // 스킬 디렉토리 추가
}
```

---

## 7. 테스트 계획

### 7.1 단위 테스트: 스킬

| 테스트 | 입력 | 기대 결과 |
|:-------|:-----|:---------|
| 지수 검색 성공 | `search_index("S&P 500")` | verified: true, 3개 출처 |
| 지수 검색 실패 | `search_index("INVALID")` | verified: false, 에러 코드 |
| 금리 검색 성공 | `search_rate("fed_funds")` | verified: true, 공식 출처 포함 |
| 출처 불일치 | 인위적 불일치 | VALUE_MISMATCH 에러 |

### 7.2 통합 테스트: 에이전트

| 테스트 | 시나리오 | 기대 결과 |
|:-------|:---------|:---------|
| index-fetcher | S&P 500 + KOSPI 수집 | 실제값 ±2% 이내 |
| rate-analyst | Fed + BOK 금리 수집 | 실제값 일치 |
| 파이프라인 | portfolio-orchestrator 워크플로우 전체 실행 | 모든 데이터 출처 명시 |

### 7.3 회귀 테스트

| 테스트 | 이전 환각값 | 수정 후 기대값 |
|:-------|:-----------|:--------------|
| S&P 500 | 5,966 | 6,966 ±2% |
| KOSPI | 2,586 | 4,586 ±2% |
| Fed Rate | 4.25% | 실제값 일치 |

---

## 8. 리스크 및 대응

| 리스크 | 영향 | 확률 | 대응 방안 |
|:-------|:----:|:----:|:----------|
| 스킬 로드 실패 | 고 | 낮음 | marketplace.json 검증, 캐시 클리어 |
| 웹검색 결과 불일치 | 중 | 높음 | 범위 표현, 1차 출처 우선 |
| 웹검색 실패/타임아웃 | 중 | 중 | 재시도 로직, FAIL 명시 |
| 에이전트가 스킬 무시 | 고 | 낮음 | macro-critic에서 스킬 사용 여부 검증 |
| 출처 URL 변경 | 저 | 낮음 | 분기별 allowlist 점검 |

---

## 9. 롤백 계획

수정 후 문제 발생 시:

1. **즉시 롤백**: Git에서 이전 에이전트/스킬 정의 복원
2. **캐시 클리어**: `~/.claude/plugins/cache` 삭제
3. **마켓플레이스 재등록**: `/plugin marketplace remove/add`
4. **임시 조치**: 거시경제 섹션에 "참고용" 면책 문구 추가

---

## 10. 승인 및 실행

### 10.1 승인 체크리스트

- [ ] 문제 정의 동의
- [ ] 스킬 기반 아키텍처 동의
- [ ] 스킬 설계 동의
- [ ] 에이전트 수정 범위 동의
- [ ] 리스크 수용

### 10.2 실행 명령

```
승인 후 다음 명령으로 실행:
"스킬 기반 아키텍처로 거시경제 에이전트 수정 진행해줘"
```

---

## 부록

### A. 참고 데이터 소스 목록

| 데이터 | 소스 | URL | Tier |
|:-------|:-----|:----|:----:|
| S&P 500 | FRED | https://fred.stlouisfed.org/series/SP500 | 1 |
| S&P 500 | Yahoo Finance | https://finance.yahoo.com/quote/%5EGSPC | 2 |
| KOSPI | 한국거래소 | https://www.krx.co.kr | 1 |
| KOSPI | Trading Economics | https://tradingeconomics.com/south-korea/stock-market | 2 |
| Fed Rate | Federal Reserve | https://www.federalreserve.gov/monetarypolicy/openmarket.htm | 1 |
| Fed Rate | FRED | https://fred.stlouisfed.org/series/FEDFUNDS | 1 |
| 한국 기준금리 | 한국은행 | https://www.bok.or.kr | 1 |

### B. 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|:----:|:----:|:----------|:-------|
| v1.0 | 2026-01-12 | 최초 작성 (프롬프트 강화 방식) | Claude |
| v2.0 | 2026-01-12 | 스킬 기반 아키텍처로 전환 | Claude |

### C. 관련 문서

- `honeypot/AGENTS.md`: 플러그인 프로젝트 지식베이스
- `honeypot/plugins/investments-portfolio/agents/`: 에이전트 정의
- `honeypot/.claude-plugin/marketplace.json`: 마켓플레이스 등록

---

*이 문서는 검토 후 승인이 필요합니다.*
