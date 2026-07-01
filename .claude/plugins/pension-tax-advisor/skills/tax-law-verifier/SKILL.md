---
name: tax-law-verifier
description: "세법 파라미터 법령 검증 스킬. 출처 등급제(law-primary-anchor/law-text/corroborating)와 EXACT 일치 검증 프로토콜. verified 인정은 law.go.kr 현행 조문 앵커 1건 + 총 ≥3 독립 공식출처 EXACT 동일값일 때만."
tools: WebSearch, WebFetch
---

# 세법 파라미터 법령 검증 스킬 (tax-law-verifier)

## ⚠️ CRITICAL: 스킬 사용 방법 (반드시 숙지)

> **이 스킬은 "함수"가 아닙니다. 지침 문서입니다.**
>
> - ❌ `verify_tax("연금저축_세액공제한도")` 같은 함수 호출은 **작동하지 않습니다**
> - ✅ 에이전트가 `WebSearch` / `WebFetch` 도구를 **직접 호출**해야 합니다
> - ✅ 이 스킬은 **출처 등급제·검증 절차·증거 스키마**를 안내하는 문서입니다
> - ✅ 검증 대상 값은 `funds/pension_tax_params.json`의 `parameters` 객체이며, evidence[] 스키마는 이 파일과 **동일**해야 합니다

### 올바른 사용 방법

```
1. 이 스킬 문서를 읽고 출처 등급제·EXACT 검증 규칙 파악
2. law.go.kr에서 현행 조문을 WebFetch로 직접 조회 → original_text·값 추출
3. taxlaw.nts.go.kr / nts.go.kr 등에서 보강·교차검증
4. 출처 간 EXACT(±0) 일치 여부 확인
5. evidence[] 스키마에 맞춰 결과 기록 (verificationStatus 판정)
```

### 잘못된 사용 방법 (환각 발생)

```
❌ "verify_tax() 호출" (존재하지 않는 함수)
❌ "스킬이 알아서 검증해줌" (스킬은 지침 문서일 뿐)
❌ law.go.kr 조회 없이 taxlaw/블로그 수치만으로 verified 승격
❌ ±1% 오차 허용 (법정 이산값은 EXACT ±0만 인정)
```

---

## Overview

이 스킬은 한국 세법 파라미터(세액공제율·한도·연금소득세율·퇴직소득세 감면율 등)를 **현행 법령 조문에 근거해 검증**하기 위한 표준 프로토콜입니다.
모든 세법 수치는 **에이전트가 직접 WebFetch/WebSearch로 law.go.kr 현행 조문을 조회**하고, **총 3개 이상의 독립 공식출처에서 EXACT(±0) 동일값**을 확인한 뒤에만 `verified`로 승격할 수 있습니다.

**환각 방지 3대 축**:
1. **law.go.kr 현행 조문 앵커 필수** — 국가법령정보센터 현행 조문이 verified의 필수 앵커
2. **EXACT 일치** — 법정 이산값은 ±0 (±1% 허용 금지)
3. **original_text 원문 인용 강제** — 수치가 포함된 조문 원문 없으면 FAIL

---

## Section 1. 출처 등급제 (Source Tier System)

세법 검증에 사용하는 출처는 3개 등급으로 분류합니다. 각 evidence 레코드의 `sourceTier` 필드에 해당 등급을 기록합니다.

| 등급 | 이름 | 도메인 | 역할 |
|------|------|--------|------|
| `law-primary-anchor` | 국가법령정보 현행 조문 앵커 | law.go.kr | **verified의 필수 앵커.** 현행 조문의 정확한 값·시행일 확인 |
| `law-text` | 국세법령정보시스템 | taxlaw.nts.go.kr | **보강 출처. 단독으로는 앵커 불가** |
| `corroborating` | 보강 출처 | nts.go.kr, moef.go.kr, fss.or.kr, sema.or.kr | 값 교차검증용. **단독 verified 불가** |

### 등급별 규칙 요약

- **law-primary-anchor (law.go.kr)**: 현행 조문의 값·시행일을 확정하는 **필수 앵커**. verified 인정에는 이 등급 **1건 이상**이 반드시 포함되어야 함.
- **law-text (taxlaw.nts.go.kr)**: 국세청 국세법령정보시스템. 조문 해석·집행 기준 보강용. **단독 앵커 불가** — 이것만으로는 verified 승격 불가.
- **corroborating**: 국세청 안내·기획재정부·금융감독원·과학기술인공제회 등 공식 안내 자료. 값 교차검증에만 사용. **단독 verified 불가**.

---

## Section 2. verified 인정 기준 (CRITICAL)

`verificationStatus: "verified"`로 승격하려면 **아래 조건을 모두** 충족해야 합니다.

1. **law.go.kr 현행 조문 앵커(law-primary-anchor) 1건 필수** — 없으면 verified 절대 불가
2. **총 ≥3 독립 공식출처 EXACT 동일값** — 법정 이산값 **±0, EXACT** (±1% 허용 금지)
3. **taxlaw.nts.go.kr(law-text) 단독 앵커 불가** — law-text만으로는 앵커 자격 없음
4. **corroborating 단독 verified 불가** — 보강 출처만으로는 verified 승격 불가
5. **taxlaw·corroborating 단독 verified 금지** — law-primary-anchor 없이 law-text·corroborating 조합만으로 verified 승격 금지

### ✅ verified 인정 조합 (예)

| law-primary-anchor | law-text | corroborating | 총 출처 | 판정 |
|:---:|:---:|:---:|:---:|:---:|
| 1 (law.go.kr) | 1 (taxlaw) | 1 (nts.go.kr) | 3, EXACT 동일 | ✅ **verified** |
| 1 (law.go.kr) | 0 | 2 (nts.go.kr, sema.or.kr) | 3, EXACT 동일 | ✅ **verified** |

### ❌ verified 불가 조합 (예)

| law-primary-anchor | law-text | corroborating | 총 출처 | 판정 |
|:---:|:---:|:---:|:---:|:---:|
| 0 | 1 (taxlaw) | 2 | 3 | ❌ **금지** (앵커 없음) |
| 0 | 2 | 1 | 3 | ❌ **금지** (taxlaw·corroborating 단독 verified 금지) |
| 1 (law.go.kr) | 1 | 0 | 2 | ❌ **금지** (총 <3) |
| 1 (law.go.kr) | 1 | 1 | 3, 값 불일치 | ❌ **needs_review** (EXACT 아님) |

> **핵심 불변식**: `verified ⟺ (law-primary-anchor ≥ 1) AND (독립 공식출처 총 ≥ 3) AND (모든 출처 값이 EXACT ±0 동일)`

---

## Section 3. evidence[] 레코드 필수 필드

각 evidence 레코드는 **아래 6개 필드를 모두** 포함해야 합니다. 하나라도 누락되면 **FAIL** 처리하고 verified로 승격하지 않습니다.

| 필드 | 설명 | 누락 시 |
|------|------|:-------:|
| `sourceUrl` | 법령 페이지 URL | FAIL |
| `sourceTier` | `"law-primary-anchor"` \| `"law-text"` \| `"corroborating"` | FAIL |
| `original_text` | **수치가 포함된 원문 인용 (필수, 없으면 FAIL)** | FAIL |
| `조문` | 조문 번호 (예: `"소득세법 제59조의3 제1항"`) | FAIL |
| `시행일` | 시행일 (YYYY-MM-DD) | FAIL |
| `collectedAt` | 수집 시각 (ISO 8601, 예: `"YYYY-MM-DDT00:00:00+09:00"`) <!-- illustrative-date --> | FAIL |

### ⚠️ original_text 규칙 (환각 방지 핵심)

> **수치를 추출할 때 반드시 조문 원문을 그대로 인용**해야 합니다.
> `original_text` 안의 숫자와 파라미터 `value`가 일치하지 않으면 **FAIL**입니다.

- `original_text`에는 검증 대상 수치가 **문장 형태로 포함**되어 있어야 함
- 예시 값을 복사하거나, 수치만 적고 원문을 비우면 **검증 불가 → FAIL**
- `조문`·`시행일`은 `original_text`가 인용된 실제 조문과 일치해야 함

---

## Section 4. 검증 프로토콜 (Verification Protocol)

파라미터 1건을 검증하는 표준 절차입니다. `WebFetch`/`WebSearch`를 **직접 호출**하세요.

1. **law.go.kr에서 현행 조문 검색** → `original_text`와 값 추출 (law-primary-anchor 확보)
2. **taxlaw.nts.go.kr에서 보강 확인** (law-text)
3. **nts.go.kr / fss.or.kr / sema.or.kr에서 교차검증** (corroborating)
4. **3개 출처 모두 EXACT 동일값** → `verified` 가능
5. **하나라도 불일치** → 불일치 기록 + 최신 유효 조문 재확인 (`needs_review`)
6. **law.go.kr 도달 불가** → **FAIL (추정 금지)** — verified 승격 불가, seed/unverified 유지

### 검증 쿼리 패턴 (가이드)

> ⚠️ 아래는 **검색 패턴 가이드**입니다. `verify_tax()` 같은 함수는 **존재하지 않습니다.**
> 반드시 `WebFetch`(조문 URL 직접) / `WebSearch`를 **직접 호출**하세요.

| # | 대상 | 쿼리/URL 패턴 | 등급 |
|:-:|:-----|:-------------|:-----|
| 1 | 현행 조문 앵커 | `WebFetch("https://law.go.kr/법령/소득세법/제59조의3")` | law-primary-anchor |
| 2 | 국세 집행 기준 | `WebFetch("https://taxlaw.nts.go.kr/법령/소득세법/제59조의3")` | law-text |
| 3 | 국세청 안내 교차검증 | `WebSearch("연금계좌 세액공제율 site:nts.go.kr")` | corroborating |

---

## Section 5. FAIL 처리 (FAIL Handling)

| 상황 | 처리 | verificationStatus |
|------|------|:------------------:|
| law.go.kr 현행 조문 앵커 없음 | **verified 승격 불가** | `seed` / `unverified` 유지 |
| 출처 간 값 불일치 | 불일치 기록 + 재확인 | `needs_review` |
| 법정 이산값 ±오차 (EXACT 아님) | **FAIL (EXACT만 인정)** | `needs_review` |
| blog/community/위키 등 금지 출처 | **출처 무효 처리** | 카운트 제외 |
| law.go.kr 도달 불가 | **FAIL (추정 금지)** | 기존 상태 유지 |

### 절대 규칙 (Zero Tolerance)

- ❌ law.go.kr 조회 없이 verified 승격 → 즉시 FAIL
- ❌ law-text·corroborating 조합만으로 verified → 금지
- ❌ ±1% 오차 허용 → **법정 이산값은 EXACT ±0만 인정**
- ❌ `original_text` 없이 수치만 기록 → FAIL
- ❌ 출처 도달 불가 시 추정값 생성 → **절대 금지 (FAIL)**

---

## Section 6. evidence[] 출력 스키마

`funds/pension_tax_params.json`의 `parameters.<id>.evidence[]`와 **동일한 스키마**로 기록합니다.

```json <!-- illustrative: 15% 세액공제율 verified 예시 -->
[
  {
    "sourceUrl": "https://law.go.kr/법령/소득세법/제59조의3",
    "sourceTier": "law-primary-anchor",
    "original_text": "총급여액 5천500만원 이하 거주자의 세액공제율은 100분의 15이다.",
    "조문": "소득세법 제59조의3 제1항",
    "시행일": "2023-01-01",
    "collectedAt": "2026-07-01T00:00:00+09:00"
  },
  {
    "sourceUrl": "https://taxlaw.nts.go.kr/법령/소득세법/제59조의3",
    "sourceTier": "law-text",
    "original_text": "총급여액 5천500만원 이하자의 연금계좌 세액공제율은 15%이다.",
    "조문": "소득세법 제59조의3 제1항",
    "시행일": "2023-01-01",
    "collectedAt": "2026-07-01T00:00:00+09:00"
  },
  {
    "sourceUrl": "https://www.nts.go.kr/nts/cm/cntnts/cntntsView.do?mi=2304&cntntsId=238938",
    "sourceTier": "corroborating",
    "original_text": "총급여 5,500만원 이하자는 연금계좌 납입액의 15%를 세액공제한다.",
    "조문": "국세청 연말정산 안내",
    "시행일": "2023-01-01",
    "collectedAt": "2026-07-01T00:00:00+09:00"
  }
]
```

> 위 예시는 law-primary-anchor 1건 + law-text 1건 + corroborating 1건 = 총 3건이 **EXACT 15%로 일치**하므로 `verified` 인정 조합입니다. <!-- illustrative -->

---

## Section 7. 금지 출처 (Blocklist)

아래 출처는 **공식 법령이 아니므로** evidence로 인정하지 않습니다. verified 카운트에서 제외합니다.

- ❌ 개인 블로그 (naver/tistory/brunch 등)
- ❌ 위키피디아 / 나무위키 등 위키
- ❌ 커뮤니티 사이트 (카페·포럼·Q&A)
- ❌ 세무법인 홈페이지 (공식 법령 아님)
- ❌ PwC / Deloitte / EY / KPMG 등 컨설팅 보고서 — **단독 seed 불가, verified 절대 불가**

> 컨설팅·세무법인 자료는 참고용 리드로만 사용하고, 반드시 law.go.kr 현행 조문으로 **재확인**해야 합니다.
> WebSearch 사용 시에도 위 블로그·위키·커뮤니티 결과를 evidence로 채택하지 마세요.

---

## Section 8. refreshStatus 갱신 규칙 (for tax-law-updater)

주기적 재검증(freshnessThresholdDays=90 경과 시) 또는 tax-law-updater 실행 시 `refreshStatus`를 아래 규칙으로 갱신합니다.

| law.go.kr 현행값 vs 기존 value | refreshStatus | 추가 처리 |
|------|:-------------:|------|
| **EXACT 동일** (현행값 == 기존 value) | `"ok"` | `lastVerifiedAt` 갱신 |
| **불일치** (현행값 ≠ 기존 value) | `"disproven"` | `proposed`에 새 값 기록, `verificationStatus: "needs_review"` |
| **law.go.kr 도달 불가** | `"pending"` | 기존 verified value **유지** (보류 아님) |

### 핵심 규칙

- `refreshStatus: "ok"` — law.go.kr 현행값이 기존 value와 **EXACT 동일**할 때만. `lastVerifiedAt` 갱신.
- `refreshStatus: "disproven"` — law.go.kr 현행값이 기존 value와 **다를 때**. `proposed`에 제안값 기록, `verificationStatus`를 `needs_review`로 강등.
- `refreshStatus: "pending"` — law.go.kr **도달 불가**. 기존 verified value를 그대로 **유지**.
- **⚠️ pending만으로 유효 verified 값을 오염시키거나 보류시키지 않음** — 도달 불가(pending)는 재확인 실패일 뿐, 이미 검증된 값을 무효화하는 근거가 아님.

---

## Disclaimer

> 이 스킬이 출처 검증을 지원하나, 최종 법적 해석은 세무 전문가에게 확인하세요.

---

## 메타 정보

```yaml
version: "1.0"
created: "2026-07-01"
updated: "2026-07-01"
author: "Claude"
purpose: "세법 파라미터 법령 검증 표준화 (환각 방지)"
consumes:
  - funds/pension_tax_params.json  # parameters[].evidence[] 스키마 (SSOT)
dependencies:
  - WebSearch
  - WebFetch
verified_rule: "law-primary-anchor(law.go.kr) ≥1 AND 독립 공식출처 총 ≥3 AND 모든 값 EXACT ±0 동일"
blocklist: ["개인 블로그", "위키", "커뮤니티", "세무법인 홈페이지", "컨설팅 보고서"]
```
