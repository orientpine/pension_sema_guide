# 날짜 리터럴 주석 규약 (fail-closed)

**문서 목적**: 로직 파일(agent / skill / command 등 동작 정의 마크다운)에 박힌 **날짜 리터럴**이
어떤 SSOT(Single Source Of Truth)를 의미하는지 **명시적으로 주석(마커)으로 선언**하도록 강제하는 규약을 정의한다.
이 문서는 **스펙(규약)만** 정의하며 게이트 구현은 포함하지 않는다.

---

## 1. 개요 — fail-closed 원칙

날짜 리터럴(`\d{4}-\d{2}-\d{2}` 형태)이 로직 파일에 그대로 박혀 있으면,
원본 데이터(`funds/*.json`의 `_meta.version`)가 갱신될 때 **소리 없이 드리프트(silent drift)**한다.
실제로 `output-critic.md`에는 `fund_data.json` 기준일이 `2026-03-01`로 박혀 있으나
현재 SSOT(`funds/fund_data.json#_meta.version`)는 `2026-06-01`이다 — 이미 드리프트가 발생한 사례다.

이를 막기 위해 본 규약은 **fail-closed**를 채택한다.

> **fail-closed 정의**: 로직 파일 내 날짜 리터럴은 **마커가 없으면 무조건 게이트 FAIL**이다.
> 미주석 = 위반. 게이트는 "안전하면 통과"가 아니라 "선언되지 않으면 차단"으로 동작한다.

근거: 누락된 의미(semantic) 날짜를 놓쳐 조용히 드리프트하는 것보다,
무해한 날짜에 대해 **false positive(오탐)**를 내고 사람이 한 번 분류하는 편이 안전하다.
오탐 비용은 "마커 한 줄 추가" 또는 "면제 맥락으로 이동"으로 끝나지만,
미탐 비용은 "잘못된 기준일로 산출된 보고서"라는 환각 방지 설계의 실패다.

---

## 2. 마커 문법 (2종)

로직 파일의 날짜 리터럴 **바로 위 줄** 또는 **같은 줄 끝**에 다음 두 마커 중 하나를 붙인다.

### 2.1 semantic-date (의미 있는 기준일)

해당 날짜가 **특정 SSOT의 값을 인용**한 것임을 선언한다. **포인터(SSOT 경로 + JSON pointer)가 필수**다.

```
<!-- semantic-date:funds/fund_data.json#_meta.version -->
```

문법: `<!-- semantic-date:<파일경로>#<JSON-pointer> -->`

- `<파일경로>`: 저장소 루트 기준 상대경로 (예: `funds/fund_data.json`, `funds/tdf_data.json`, `funds/deposit_rates.json`)
- `<JSON-pointer>`: `#` 뒤에 점/슬래시 표기 경로 (예: `_meta.version`, `_meta.updatedAt`)
- 게이트는 이 마커가 붙은 날짜 리터럴을 **포인터가 가리키는 그 파일·그 필드의 현재 값과만** 비교한다.

### 2.2 illustrative-date (예시/설명용 날짜)

해당 날짜가 **SSOT를 인용하지 않는 순수 예시·설명·포맷 견본**임을 선언한다. 포인터 없음.

```
<!-- illustrative-date -->
```

- 게이트는 이 마커가 붙은 날짜를 **비교 대상에서 제외**한다.
- 단, 남용을 막기 위해 **misannotation 가드**(§7)의 검사를 받는다.

---

## 3. 적용 규칙 — 로직 파일 내 날짜 리터럴 처리

### 3.1 대상 파일

다음 동작 정의 파일을 **로직 파일**로 간주한다.

- `.claude/plugins/**/agents/*.md`
- `.claude/plugins/**/skills/**/SKILL.md`
- `.claude/plugins/**/commands/*.md`

### 3.2 핵심 규칙 (fail-closed)

| 상황 | 판정 |
|------|------|
| 로직 파일 내 날짜 리터럴 + `semantic-date` 마커(포인터 포함) | 통과 후보 → §6 per-SSOT 비교 수행 |
| 로직 파일 내 날짜 리터럴 + `illustrative-date` 마커 | 제외 (단 §7 가드 적용) |
| 로직 파일 내 날짜 리터럴 + **마커 없음** | **FAIL** (fail-closed 기본값) |
| 허용 맥락(§4)에 해당하는 날짜 | 면제 (마커 불필요) |
| 제외 목록(§5)에 해당하는 토큰 | 검사 안 함 |

> 날짜 리터럴 탐지 정규(기본): `\b\d{4}-\d{2}-\d{2}\b`

---

## 4. 허용 맥락 (주석 면제 — 정확히 3가지)

다음 3가지 맥락의 날짜는 **마커 없이도 면제**된다. fail-closed를 약화시키지 않기 위해
**아래 3가지 외의 면제는 추가하지 않는다.**

### 4.1 Frontmatter 메타데이터 면제

YAML frontmatter(파일 최상단 `---` ~ `---` 블록) 내에서
키가 `created:` 또는 `updated:`로 시작하는 줄의 날짜.

- 조건 정규: `^\s*(created|updated):\s*\d{4}-\d{2}-\d{2}`
- 근거: 파일 자체의 생성/수정 메타데이터이며 SSOT 인용이 아니다.

### 4.2 경로/식별자 패턴 면제

`날짜 + 대문자`로 이어지는 토큰 — 날짜 바로 뒤에 `-` 와 대문자가 붙는 경우.
주로 경로 세그먼트, 티커, 식별자(예: `2026-06-01-AGGRESSIVE`, `2026-06-04-KODEX`)에서 발생한다.

- 조건 정규: `\d{4}-\d{2}-\d{2}-[A-Z]`
- 근거: 날짜로 보이지만 실제로는 복합 식별자의 일부이며 SSOT 기준일이 아니다.

### 4.3 Fenced 코드/예시 블록 면제

펜스(```` ``` ```` 또는 `~~~`)로 열고 닫힌 fenced block **내부**의 날짜.

- 조건: 한 줄이 펜스 여는 토큰(``` ``` ```` 또는 `~~~`, 선택적 언어 지시자 포함)으로 시작하면 블록 진입,
  동일 펜스 토큰으로 닫는 줄까지를 블록 내부로 본다. 블록 내부의 모든 날짜는 면제.
- 여닫힘 추적 정규(라인 기준): `^\s*(```|~~~)` 토글로 in-block 상태를 켜고/끈다.
- 근거: 코드 예시·JSON 스키마 견본·CLI 출력 견본의 날짜는 설명용이며 실제 인용이 아니다.

---

## 5. 제외 목록 (검사 자체를 하지 않는 토큰/파일)

다음은 날짜로 보이거나 날짜를 담지만 **드리프트 대상이 아니므로 검사에서 제외**한다.

### 5.1 `_meta.missing` 코드

`funds/fund_data.json#_meta.missing`에 등재된 누락 펀드코드. 날짜가 아닌 식별자다.

- 제외 코드: `K55205BU9205`, `K55223C80096`
- 이 토큰들은 날짜 정규에 걸리지 않지만, 혼동 방지를 위해 명시적으로 제외 목록에 둔다.

### 5.2 STALE README

`funds/README.md`는 **구버전(STALE)** 문서다(2,015펀드 / 5분류 / `2026-01-01` 등 옛 값 포함).
truth source가 아니므로 이 파일의 날짜 리터럴은 **규약 검사 대상에서 전면 제외**한다.

---

## 6. per-SSOT 원칙 (semantic 마커의 핵심)

> **모든 `semantic-date` 마커는 반드시 포인터를 포함하며, 게이트는 그 포인터가 가리키는 SSOT와만 비교한다.**

### 6.1 SSOT 목록 (현재 기준)

| SSOT 포인터 | 현재 값 | 비고 |
|-------------|---------|------|
| `funds/fund_data.json#_meta.version` | `2026-06-01` | 투자가능 펀드 205 |
| `funds/tdf_data.json#_meta.version` | `2026-06-04` | TDF 75 (**별도 기준일**) |
| `funds/deposit_rates.json#_meta.version` | (파일의 `_meta.version`) | 예금 금리, `updatedAt`/`freshnessThresholdDays` 동반 |

### 6.2 왜 per-SSOT인가 — 교차비교 금지

`fund_data`(2026-06-01)와 `tdf_data`(2026-06-04)는 **서로 다른 기준일이 정상**이다(`funds/AGENTS.md`, `tdf_data.json#baseDateNote`).
따라서 "두 SSOT의 날짜가 같은지" 비교하는 것은 **틀린 검사**다.

- semantic 마커의 포인터는 **각 날짜를 자기 자신의 SSOT에만 묶는다(per-SSOT)**.
- 게이트는 `funds/fund_data.json#_meta.version` 마커가 붙은 날짜는 오직 그 파일의 그 필드와 비교하고,
  `tdf_data.json` 마커가 붙은 날짜는 오직 tdf SSOT와 비교한다.
- **두 SSOT 날짜를 서로 비교하는 일은 절대 없다.**

---

## 7. misannotation 가드 (illustrative 남용 방지)

`illustrative-date`로 의미 있는 기준일을 위장(misannotation)해 fail-closed를 우회하는 것을 막는다.

> **가드 규칙**: `illustrative-date` 마커가 붙은 날짜의 **같은 줄 또는 인접(±1줄)**에
> 다음 **기준일 신호 키워드**가 함께 나타나면 **suspicious(의심) 위반**으로 표면화한다.

- 신호 키워드: `기준일`, `version`, `baseDate`, `_meta`, `as of`, `기준`
- 의도: 진짜 설명용 날짜라면 이 키워드와 함께 쓸 이유가 거의 없다.
  함께 쓰였다면 실제로는 SSOT 인용일 가능성이 높으므로 `semantic-date`로 재선언하거나 리터럴을 제거해야 한다.
- 판정: 이 가드에 걸린 항목은 자동 통과시키지 않고 **사람 검토 대상**으로 남긴다(fail-closed 일관).

---

## 8. 처리 방침 (위반 발견 시)

게이트가 미주석 날짜(FAIL) 또는 misannotation 의심을 표면화하면, 다음 중 하나로 처리한다.

### 8.1 remove-rule (권장 — 특히 교차비교 패턴)

날짜 **리터럴을 제거**하고, 그 자리에 "런타임에 SSOT를 읽어 사용/비교하라"는 **RULE 문장**으로 대체한다.

> **교차비교 패턴은 반드시 이 방식으로 처리한다.**
> 즉, **교차비교는 리터럴 제거 + RULE화 처리 — 두 값을 비교하지 않는다.**
> 서로 다른 SSOT의 기준일을 문서에 박아 비교하는 대신,
> "각 펀드는 자신의 소스 파일 `_meta.version`을 읽어 검증하라"처럼 **읽어서 비교하라**로 표현한다.

예시(개념):
- Before: "`tdf_data.json` 기준일은 2026-06-04, `fund_data.json` 기준일은 2026-03-01으로 상이하다"
- After: "각 SSOT의 `_meta.version`을 **읽어** 확인하라. 두 기준일은 상이할 수 있으므로 **교차비교(우열 판단)하지 않는다.**" (리터럴 제거)

### 8.2 build-stamp (semantic 유지가 필요할 때)

문서에 실제 기준일 노출이 꼭 필요하면, `semantic-date` 마커(포인터 포함)를 붙이고
값은 SSOT에서 **빌드 시 스탬프(주입)**되도록 한다. 게이트가 per-SSOT로 일치 검증한다.

### 8.3 annotate-illustrative (순수 예시일 때만)

날짜가 진짜 예시·포맷 견본이면 `illustrative-date` 마커를 붙인다.
단 §7 misannotation 가드를 통과해야 하며(기준일 신호 키워드 인접 금지),
가능하면 §4.3 fenced 블록 안으로 옮겨 면제 처리하는 편이 더 안전하다.

---

## 9. 요약

- **fail-closed**: 로직 파일 날짜 리터럴은 마커 없으면 FAIL.
- **마커 2종**: `semantic-date:<경로>#<pointer>`(포인터 필수) / `illustrative-date`.
- **허용 맥락 3종만**: frontmatter(`created:`/`updated:`), 경로패턴(`\d{4}-\d{2}-\d{2}-[A-Z]`), fenced 블록.
- **제외**: `_meta.missing` 코드(K55205BU9205, K55223C80096), STALE `funds/README.md`.
- **per-SSOT**: semantic 마커는 자기 SSOT와만 비교 — 서로 다른 SSOT 교차비교 금지.
- **misannotation 가드**: illustrative + 기준일 키워드 인접 = 의심 위반.
- **처리 방침**: 교차비교는 리터럴 제거 + RULE화(권장), 그 외 build-stamp 또는 annotate-illustrative.
