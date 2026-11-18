# Pension SEMA Guide

**과학기술인공제회(SEMA) DC형 퇴직연금**을 위한 AI 멀티에이전트 포트폴리오 가이드입니다.
거시경제 분석부터 펀드 선별, 규제 검증, 환각(hallucination) 방지 검증까지 **하나의 명령으로** 수행하고,
그 결과를 **실제 SEMA 시스템에 입력하는 단계까지** 함께 도와주는 것을 목표로 합니다.

> **이 프로젝트가 도와주는 일**
>
> 1. 나에게 맞는 DC형 퇴직연금 포트폴리오를 **분석·추천**받기
> 2. DC형 규제(위험자산 70% 한도 등) 준수 여부를 **자동 검증**
> 3. 완성된 포트폴리오를 **과학기술인공제회 포털에 직접 입력**할 때 옆에서 도와주기

> **🔓 공개 저장소입니다.** 개인정보(투자자 프로필·잔고·실제 분석 산출물)는 저장소에 포함되지 않으며,
> 로컬의 `confidentialData/` 디렉토리(gitignore 대상)에만 보관됩니다.

> **🤖 도리 시스템이 관리하는 저장소입니다.** 저장소 주인의 AI 에이전트 모음인 **도리 시스템**이 이 저장소를 돌보고,
> 재정·경제·자산 담당 도리인 **금돌(금도리)**이 데이터 갱신·분석·문서 정리를 맡아 씁니다.
> 일을 시키는 방법은 [도리에게 일 시키기](#도리에게-일-시키기)를 보세요.

---

## 무엇을 할 수 있나요?

이 프로젝트의 **메인 기능은 SEMA DC형 퇴직연금 포트폴리오 생성**입니다.
주식·ETF 상담과 개별 기업 리서치는 같은 환각 방지 설계를 공유하는 **추가(보조) 기능**입니다.

### 🎯 메인 기능 — SEMA 퇴직연금 포트폴리오 생성

| 하고 싶은 일                    | 사용하는 명령 / 에이전트                     | 결과물                                                      |
| ------------------------------- | -------------------------------------------- | ----------------------------------------------------------- |
| **내 퇴직연금 포트폴리오 구성** | `/investments-portfolio:portfolio-analyze` | 5단계 분석 보고서(거시경제 → 펀드 → 규제 → 검증 → 요약) |

### ➕ 추가 기능

| 하고 싶은 일             | 사용하는 명령 / 에이전트                 | 결과물                                   |
| ------------------------ | ---------------------------------------- | ---------------------------------------- |
| **주식·ETF 투자 상담** | `/stock-consultation:stock-consult`    | 스크리닝·밸류에이션·반론·검증 상담 보고서 |
| **개별 기업 리서치**   | `@equity-research` 에이전트 (티커와 함께 호출) | 기관급 리서치 리포트                |
| **퇴직연금 세금 상담** | `/pension-tax-advisor:tax-consult` | 납입→운용→수령 절세 상담, 3중 검증, 보류 안전 |

> ⚙️ **공용 엔진** — `macro-analysis`(지수·금리·섹터·리스크·리더십)는 위 기능들이 **내부에서 호출**하는 공용 거시경제 분석 엔진으로, 사용자가 직접 실행하는 기능이 아닙니다.

> 핵심 설계 원칙은 **환각 방지**입니다. 모든 수치는 출처를 명시하고, 주장 종류별 출처 기준(공식 사실=발표 기관 1차 출처, 시장 숫자=3개 출처 교차검증, 해석=해석 표시)과 출력 검증 에이전트를 거칩니다.

---

## 도리가 관리하는 저장소

이 저장소는 사람이 Claude Code로 직접 쓸 수도 있지만(아래 [빠른 시작](#빠른-시작)), 평소에는 **도리 시스템**이 관리합니다.

- **도리 시스템**: 저장소 주인이 디스코드로 일을 맡기는 AI 코딩 에이전트 모음입니다. 도리마다 맡은 분야가 있고, 서로 일을 넘겨 가며 함께 일합니다.
- **금돌(금도리)**: 재정·경제·자산 담당 도리로, 이 저장소의 주 작성자입니다. 펀드·TDF·예금·세법 데이터 갱신, 분석 플러그인(`.claude/plugins/`) 수정, 테스트·정합성 검증, 문서 정리를 합니다.
- **올라오는 길**: 공개 저장소이므로 도리는 커밋마다 개인정보 검사([개인정보 보호 정책](#개인정보-보호-정책))를 거친 뒤 이 저장소에 **바로 올립니다**. 검사에 걸린 변경은 올리지 않고, 무엇이 걸렸는지 저장소 주인에게 알립니다.

### 도리에게 일 시키기

디스코드의 **금돌 채널**에서 금돌에게 평소 말로 부탁하면 됩니다. 명령어를 외울 필요는 없고, 금돌이 알맞은 명령·스크립트를 골라 실행한 뒤 결과와 근거(출처·기준일)를 채널로 답합니다.

| 이렇게 말하면                                                                  | 금돌이 하는 일                                                                                             |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| "이번 달 상품제안서 나왔어. 펀드·TDF 데이터 갱신하고 정합성 검사까지 돌려줘." | `data-updater` 스크립트로 `funds/*.json` 갱신 → `verify_consistency.py`·pytest 실행 → 바뀐 점 요약 + 푸시 |
| "내 DC 포트폴리오 다시 짜줘. 프로필은 지난번이랑 같아."                        | `portfolio-analyze` 실행. 결과는 `confidentialData/`에만 저장하고 채널에는 요약만                        |
| "포털 매도 화면 붙여넣을게. 정수 %로 몇 % 넣으면 돼?"                         | 목표 비중을 포털 입력 단위로 환산·검산 ([4. SEMA 시스템에 입력하기](#4-sema-시스템에-입력하기-가장-중요한-단계)) |
| "IRP·연금저축 세액공제 올해 기준으로 다시 확인해줘."                           | `tax-consult` 실행. 세법 파라미터가 오래됐으면 law.go.kr 현행 조문으로 재확인                              |
| "이 ETF 지금 사도 돼? 근거랑 반론 같이."                                       | `stock-consult`로 근거·반론·검증 보고서 작성. 사고팔지는 주인이 결정                                      |
| "README 테스트 수가 실제랑 안 맞아. 돌려 보고 고쳐줘."                         | 테스트를 실제로 돌려 확인 → 문서 수정 → 푸시                                                                 |

**금돌이 하는 일과 하지 않는 일**

| 하는 일 ✅                                               | 하지 않는 일 ⛔                                                         |
| ------------------------------------------------------- | ---------------------------------------------------------------------- |
| 읽기·분석·정리·제안 (숫자마다 출처·기준일, 추정은 추정이라고 표시) | 이체·송금·매매(주식·코인·외환 주문)·결제·청약·대출 신청 — 시켜도 실행은 주인이 직접 |
| 공개 자료로 펀드·세법 데이터 갱신, 플러그인·스크립트·문서 수정 | 은행·증권·카드 계좌 로그인, 비밀번호·인증서·OTP·카드 번호 받기·저장하기 |
| 테스트·정합성 게이트 실행, 결과를 커밋·푸시하기       | 주인 재정 자료(잔액·거래 내역·소득)를 공개 저장소에 커밋하기          |
| 포털 입력값 환산·검산 도와주기                            | 포털에 대신 로그인하거나 대신 입력하기 — 입력은 주인이 직접             |

투자 판단은 근거와 위험을 함께 보여 줄 뿐, **결정과 실행은 언제나 저장소 주인이 합니다.**

---

## 사전 준비

- **Claude Code** (플러그인/마켓플레이스 지원 버전)
- **Python 3** (펀드 데이터 업데이트 시) — 대부분 표준 라이브러리만 사용
- **openpyxl** (xlsx → CSV 변환 시에만 필요): `pip install openpyxl`

---

## 빠른 시작

### 1. 플러그인 등록

이 저장소는 Claude Code 마켓플레이스 + 5개 플러그인을 `.claude/plugins/`에 내장(vendoring)하고 있습니다.
`.claude/settings.json`에 마켓플레이스(`extraKnownMarketplaces`)와 활성 플러그인(`enabledPlugins`, 5개 모두 `true`)이 등록되어 있어,
**프로젝트를 열고 폴더를 신뢰(trust)하면** Claude Code가 자동으로 설치를 안내합니다.

수동으로 등록하려면:

```
/plugin marketplace add ./.claude/plugins
```

이후 `pension-sema-guide` 마켓플레이스의 5개 플러그인(`investments-portfolio`, `macro-analysis`, `stock-consultation`, `equity-research`, `pension-tax-advisor`)이 활성화됩니다.


### 2. 포트폴리오 분석 실행 (투자자 프로필 인라인 입력)

`portfolio-analyze` 명령에 **투자자 프로필을 함께 입력**하여 실행합니다.
명령은 입력한 프롬프트에서 생년·투자 성향 등 투자자 정보를 직접 파싱합니다(별도 파일을 읽지 않습니다).

```
/investments-portfolio:portfolio-analyze 나를 위한 새로운 포트폴리오를 구성해줘.

| 항목 | 내용 |
|------|------|
| **생년** | (예: 1985년) |
| **은퇴 예정** | 65세 |
| **투자 성향** | 공격형 (장기투자) |
| **위험 수용도** | 높음 (단기 손실 감내 가능) |
```

> 💡 프로필을 매번 입력하기 번거롭다면 `confidentialData/investor-profile.md`(gitignore 대상)에 저장해 두고 복사해 붙여넣으세요.
> 단, 명령이 이 파일을 **자동으로 읽지는 않으므로** 실행할 때 반드시 프롬프트에 프로필을 포함해야 합니다.

명령을 실행하면 아래 5단계 멀티에이전트 워크플로우가 순차 실행되어, 추천 펀드 목록·비중·규제 준수 여부·신뢰도 점수가 담긴
최종 보고서가 생성됩니다. 산출물은 개인정보를 포함하므로 `confidentialData/`에 저장됩니다.

### 3. 결과 확인

공개 예시는 `portfolios/samples/sample-aggressive/`에서 익명화된 형태로 확인할 수 있습니다:

```
portfolios/samples/sample-aggressive/
├── 00-macro-outlook.md        # 거시경제 전망 + 자산배분 권고
├── 01-fund-analysis.md        # 펀드 선별 및 비중 배분
├── 02-compliance-report.md    # DC형 규제 준수 검증
├── 03-output-verification.md  # 환각 방지·출처 검증, 신뢰도 점수
├── 04-portfolio-summary.md    # 최종 통합 보고서 (추천 펀드 표 + 실행 체크리스트)
├── index-data.json            # 시장 지수 스냅샷 (근거 데이터)
├── rate-analysis.json         # 금리/환율 분석 근거
├── risk-analysis.json         # 리스크/시나리오 분석 근거
└── sector-analysis.json       # 섹터 전망 분석 근거
```

최종 보고서(`04-portfolio-summary.md`)에는 **추천 펀드명 + 비중 표**와 **실행 체크리스트**가 들어 있어,
이 표를 그대로 들고 SEMA 포털에 입력하면 됩니다.

---

## 4. SEMA 시스템에 입력하기 (가장 중요한 단계)

목표 비중과 포털 입력 비율의 환산은 `dc_limits.py`로 실행합니다. Python 표준 라이브러리와 Decimal만 사용하며, 기본 출력은 한국어 표이고 `--json`을 붙이면 기계가 읽는 JSON입니다. JSON의 계산된 십진수는 정밀도를 보존하는 문자열, 정수 입력 비율은 숫자로 출력합니다. 로그인·주문·입력은 사용자가 직접 합니다.

### 실행

저장소 루트에서 실행합니다. `--funds-dir` 기본값은 `funds`입니다.

```bash
DC=.claude/plugins/investments-portfolio/skills/dc-pension-rules/scripts/dc_limits.py
python3 "$DC" check --allocation /개인자료경로/target.json
python3 "$DC" portal --holdings /개인자료경로/holdings.json \
  --target /개인자료경로/target.json --contributions /개인자료경로/contributions.json
```

공개된 가상 자료로 먼저 확인할 수 있습니다.

```bash
python3 "$DC" check --allocation tests/fixtures/dc_limits/allocation.json \
  --funds-dir tests/fixtures/dc_limits --json
python3 "$DC" portal --holdings tests/fixtures/dc_limits/holdings.json \
  --target tests/fixtures/dc_limits/target.json --funds-dir tests/fixtures/dc_limits
```

### JSON 입력 계약

배분(`check --allocation`, `portal --target`)은 객체 배열입니다. 펀드 참조는 `fundCode` 또는 **정확한** `name`이며 둘 다 주면 일치해야 합니다. 원리금보장 상품은 `kind: "principalGuaranteed"`와 `name`으로 지정하며, `name`은 `--funds-dir`의 `deposit_rates.json`에 있는 `productName` 또는 `id`여야 합니다(목록에 없거나 펀드명이면 exit 2 — 위험펀드를 예금으로 적어 한도를 피하는 입력 차단). 예시의 `"예금"`은 테스트 픽스처 이름이고, 실제 데이터에서는 `"과학기술인공제회 퇴직연금 운용방법 (1년)"`처럼 씁니다. 포털 환산은 정수 매도(내림·올림)로 입력했을 때 한도를 넘는 방식이 있으면 전체 판정을 FAIL로 내고 `unsafeIntegerSell`에 그 방식을 적습니다. `weight`는 음수 없는 십진수 또는 십진 문자열(단위 %)이며 합계가 정확히 100이어야 합니다. 같은 펀드를 코드와 이름으로 나눠 적어도 합산하여 집중도를 검사합니다.

```json
[
  {"fundCode": "R1", "weight": "40"},
  {"name": "위험나", "weight": "30"},
  {"kind": "principalGuaranteed", "name": "예금", "weight": "30"}
]
```

위 코드는 가상 fixture 전용입니다. 실제 입력은 `funds/fund_data.json`과 `funds/tdf_data.json`의 코드·이름을 사용합니다. 분류는 `fund_classification.json`의 이름 키와 TDF 자체 필드에서 읽습니다. `riskStatus`가 없는 구자료는 `riskAsset: true`를 위험, `false`를 확인 필요한 비위험으로 읽고, 둘 다 없으면 미확인으로 산입합니다. 알 수 없거나 이름이 중복된 펀드는 추측하지 않고 종료 코드 2를 반환합니다.

보유(`--holdings`)도 같은 참조의 배열이며 `weight` 대신 `evalAmount`(음수 없는 원 단위 정수 또는 정수 문자열)를 넣습니다. 총평가액 0은 오류입니다. 목표에서 빠진 보유 상품은 목표 0, 보유하지 않은 목표 상품은 신규 매수로 계산하고 별도 안내합니다.

```json
[
  {"fundCode": "R1", "evalAmount": 60000},
  {"kind": "principalGuaranteed", "name": "예금", "evalAmount": 40000}
]
```

부담금(`--contributions`, 생략 가능)은 `기본`, `일시전환`, `경영성과` 세 키를 **모두** 가진 객체이며 각 값은 위 배분 배열입니다. 예를 들어 원리금보장 상품만 설정하는 가상 입력은 다음과 같습니다.

```json
{
  "기본": [{"kind": "principalGuaranteed", "name": "예금", "weight": "100"}],
  "일시전환": [{"kind": "principalGuaranteed", "name": "예금", "weight": "100"}],
  "경영성과": [{"kind": "principalGuaranteed", "name": "예금", "weight": "100"}]
}
```

### 출력 해석과 확인

매도는 각 보유 상품 평가액 대비 정확한 비율과 정수 내림·올림 비율, 각각의 목표 대비 매도금액 오차를 표시합니다. 매수는 부족액을 매도 재원으로 나눈 뒤 최대잉여 방식으로 정수화하여 합계 100을 보장합니다. 동률은 소수부, 부족액 내림차순, 이름 오름차순으로 풉니다. 부담금도 같은 방식으로 각 칸을 합계 100으로 만들고 **원안과 정수화 후 배분 모두** 검사합니다.

예시 보유 총액 100,000원에서 위험가 목표 40%, 위험나 목표 30%, 예금 목표 30%이면 위험가 20,000원(보유액의 약 33.3333%), 예금 10,000원(25%)을 팔고, 재원 30,000원의 100%를 위험나에 매수합니다. 위험가를 정수 33%로 팔면 목표 매도액보다 200원 적고, 34%면 400원 많습니다.

`targetCheck`는 원안, `postTradeCheck`는 **정확한 매도비율 + 정수 매수비율**의 결과입니다. 원 단위 오차표와 `integerSellScenarios.floor/ceil`에서 정수 매도 내림·올림 각각의 거래 후 한도와 오차도 확인합니다. 두 정수 시나리오는 대안이므로 주 판정 종료 코드에는 합치지 않습니다. 매도할 금액이 없으면 매수 목록은 빈 배열입니다. 평가액 고정·수수료 없음 가정으로 원 미만 계산값을 유지하며, 실제 체결가격·좌수·결제 반올림은 포털 예상금액과 대조해야 합니다.

경계는 스크립트 옆 **`dc_limits_config.json` 한 곳**의 `riskLimitPct`와 `inclusive`로 관리합니다. 기본값은 근로자퇴직급여보장법 시행령 제26조 / 퇴직연금감독규정 제11조①의 “70%를 초과할 수 없음”에 따라 **70.00% 통과, 70.01% 실패**입니다(확인일 2026-11-17). SEMA 포털도 부담금 투자비율에서 비TDF 위험자산 합 **정확히 70%를 통과**시킨다는 것을 소유자 화면으로 확인했습니다(2026-11-17, `dc_limits_config.json`의 `portalBoundarySource`). 포털이 펀드별로 위험자산을 어떻게 표시하는지는 아직 확인하지 못했습니다.

위험·미확인·비적격 TDF는 한도 분자에 포함하며, `tdfQualified == true`인 TDF는 분자에서만 제외합니다. 비위험 분류의 `needsConfirmation` 금액까지 더했을 때 한도를 넘으면 `PASS_PENDING_CONFIRMATION`과 포털·규약 확인 대상 목록을 출력합니다. 일반·비적격 TDF 단일 펀드 한도 초과는 ERROR, 적격 TDF 초과는 WARNING, 원리금보장은 단일 펀드 검사 면제입니다.

`check --mode holdings`는 **평가액 변동만으로 초과한 보유분**에만 사용합니다. 이 모드의 `MARKET_DRIFT_OVER_LIMIT`는 “위반 아님, 다음 변경 시 조정”이며 퇴직연금감독규정 제13조②에 따라 운용관리기관 통보가 필요합니다. 초과 원인을 자동 증명하지 않으므로 신규 제안이나 매매에는 기본 `proposal` 검사를 사용합니다.

종료 코드는 PASS·PASS_PENDING_CONFIRMATION·MARKET_DRIFT_OVER_LIMIT가 0, FAIL·ERROR가 1, 알 수 없는 펀드가 2입니다. `portal`은 원안·정확 매도 후·부담금 원안 및 정수화 후 검사 중 하나라도 실패하면 1을 반환합니다.

---

## 멀티에이전트 워크플로우 (포트폴리오 분석)

`/investments-portfolio:portfolio-analyze`는 아래 단계를 오케스트레이션합니다. 거시경제 단계는 `macro-analysis` 플러그인의
공용 에이전트들이 수행하고, 이후 펀드 선별·규제 검증·출력 검증을 거쳐 최종 보고서로 통합됩니다.

```
[사용자 요청 + 투자자 프로필(명령 프롬프트에 인라인 입력)]
     │
     ▼
[거시경제 분석]   macro-analysis 에이전트(지수·금리·섹터·리스크·리더십) → 종합/검증
                  (지수 수집이 일부·전부 실패해도 index_status.py가 결측을 표시하고 DC 배분은 계속)
     │            └─► 00-macro-outlook.md
     ▼
[fund-portfolio]  펀드 데이터 기반 포트폴리오 구성 (Bogle 원칙·저비용·인덱스 우선)
     │            └─► 01-fund-analysis.md
     ▼
[compliance-checker]  DC형 위험자산 70% 한도, 단일펀드 40% 한도, 비중 합계 100% 검증
     │            └─► 02-compliance-report.md
     ▼
[output-critic]   출처 검증, 환각 탐지, 과신 표현 제어, 신뢰도 점수 산출
     │            └─► 03-output-verification.md
     ▼
[최종 통합]       추천 펀드 표 + 핵심 지표 + 실행 체크리스트
                  └─► 04-portfolio-summary.md
```

| 단계 | 담당                        | 출력                          | 역할                               |
| ---- | --------------------------- | ----------------------------- | ---------------------------------- |
| 1    | `macro-analysis` 에이전트 | `00-macro-outlook.md`       | 거시경제·시장 전망, 자산배분 권고 |
| 2    | `fund-portfolio`          | `01-fund-analysis.md`       | 펀드 선별·비중 배분               |
| 3    | `compliance-checker`      | `02-compliance-report.md`   | DC형 규제 준수 검증                |
| 4    | `output-critic`           | `03-output-verification.md` | 환각 방지·출처 검증·신뢰도 점수  |
| 5    | `portfolio-analyze`(조율) | `04-portfolio-summary.md`   | 최종 통합 보고서                   |

---

## 퇴직연금 세금 상담 예제 (`/pension-tax-advisor:tax-consult`)

추가 기능인 `tax-consult`는 **납입 → 운용 → 수령** 3단계의 연금·퇴직연금 절세를 상담하는 오케스트레이터입니다.
`portfolio-analyze`와 마찬가지로 **투자자 프로필을 프롬프트에 인라인으로 입력**하면(개인정보 파일을 자동으로 읽지 않습니다),
교육 → 전략 → **3중 검증** → 최종 요약 파이프라인이 순차 실행됩니다. 모든 세제 수치는 `funds/pension_tax_params.json`(현행 조문 앵커)에서
`parameter_id`로 로드해 **python3로 독립 재계산**하고, 검증을 통과하지 못한 항목은 숫자를 만들어내지 않고 **"보류"**로 표시합니다.

### 1. 실행 (프로필 인라인 입력)

```
/pension-tax-advisor:tax-consult 내 연금계좌 절세 상담을 해줘.

| 항목 | 내용 |
|------|------|
| **총급여** | 6,000만원 (고소득) |
| **나이 / 수령 개시** | 45세 / 65세 (20년 후) |
| **계좌 구성** | IRP + 연금저축 (DC는 직장에서 별도 운용) |
| **연간 납입** | IRP 600만원 + 연금저축 300만원 |
```

> 💡 프로필에는 개인정보가 포함되므로 실행 결과는 모두 `confidentialData/tax/`(gitignore 대상) 하위에만 저장됩니다.

### 2. 멀티에이전트 워크플로우

```
[프로필 인라인 입력]
     │
     ▼
[0. 신선도 체크]   funds/pension_tax_params.json 90일 초과 시 → tax-law-updater (BLOCKING)
     │
     ▼
[tax-knowledge-educator]  납입·운용·수령 3단계 세제 교육 (개인 맞춤 아님)
     │            └─► 00-educator.md
     ▼
[tax-strategy-planner]    개인 맞춤 절세 전략 초안 (미검증 파라미터는 보류)
     │            └─► 01-strategy.md
     ▼
[C4 3중 검증]  calc-verifier(python3 재계산) → critic(A~F 채점) → devil-advocate(반론)
     │            └─► 02-calc-verify.json/.md · 03-critic.json/.md
     │            ✗ C/D/E/F·중대 반론 → planner 재시도(최대 3회) → 초과 시 "제공 보류"
     ▼
[04-summary 재검증]  검증 통과(A/B) 금액만 인용 + parameter_id 1:1 매핑 → 재검증 후 확정
                  └─► 04-summary.md
```

| 단계 | 담당 에이전트 | 산출물 | 게이트 |
| ---- | ------------- | ------ | ------ |
| 0 | `tax-law-updater` | (파라미터 갱신) | 90일 초과 시에만 · BLOCKING |
| 1 | `tax-knowledge-educator` | `00-educator.md` | BLOCKING |
| 2 | `tax-strategy-planner` | `01-strategy.md` | BLOCKING |
| 3 | `tax-calc-verifier` → `tax-critic` → devil-advocate¹ | `02-calc-verify.*` · `03-critic.*` | A/B 통과 · 미통과 3회 시 보류 |
| 4 | `tax-consult`(조율) | `04-summary.md` | 재검증(calc→critic) 후 확정 |

> ¹ devil-advocate는 별도 에이전트가 아니라 `tax-critic`이 보유한 반론 스킬입니다(에이전트는 5개).

### 3. 산출물 구조

개인정보 보호를 위해 모든 파일은 `confidentialData/tax/{YYYY-MM-DD}-{slug}-{6자리}/` 하위에만 JSON+MD로 저장됩니다(공개 저장소에 커밋되지 않습니다).

```
confidentialData/tax/{YYYY-MM-DD}-{slug}-{6자리}/
├── 00-educator.md            # 납입·운용·수령 3단계 세제 교육
├── 01-strategy.md            # 개인 맞춤 절세 전략 초안
├── 02-calc-verify.json/.md   # python3 독립 재계산 검증
├── 03-critic.json/.md        # A~F 신뢰도 채점 + 반론(devil-advocate)
└── 04-summary.md             # 최종 요약 (검증 통과 금액만 + 검증 부록)
```

### 4. 최종 요약(`04-summary.md`) 예시 발췌

> 위 익명 프로필에 대한 최종 요약의 일부입니다. `tax-critic` **A등급 PASS**를 받은, `parameter_id`로 재계산된 금액만 포함됩니다.

| 항목 | 금액 | parameter_id | 조문 | 등급 |
|------|-----:|--------------|------|:----:|
| 연간 세액공제 | **1,080,000원** | `[id:연금계좌_세액공제한도] × [id:공제율_국세기준_고소득]` | 소득세법 §59의3 제1항 | ✅ A |
| 분리과세 경계 | 15,000,000원 | `[id:사적연금_분리과세_경계]` | 소득세법 §14 제3항 및 §20의3 | ✅ A |

**보류(미검증) 항목** — 숫자를 생성하지 않고 세무사 확인을 권고합니다.

| parameter_id | 조문 | 상태 |
|--------------|------|------|
| `연금소득세율_70세미만` | 소득세법 §20의3 | 보류(미검증) |
| `퇴직소득세_감면율_11년_20년` | 소득세법 §22 제3항 | 보류(미검증) |

> ⚠️ **면책**: 본 상담은 정보 제공 목적이며 공인 세무사의 자문을 대체하지 않습니다. 세법·파라미터는 변경될 수 있으므로 실행 전 최신 조문(law.go.kr)을 재확인하세요.

### 5. 공개 예시

익명화된 전체 예시는 `portfolios/samples/sample-tax-consult/`에서 5단계 산출물(`00-educator` → `01-strategy` → `02-calc-verify` → `03-critic` → `04-summary`)로 확인할 수 있습니다. 실명·생년·소속·계좌 등 개인정보는 포함되어 있지 않습니다.

---

## 플러그인 구성

마켓플레이스 `pension-sema-guide`에 5개 플러그인이 vendoring되어 있습니다. (서브모듈이 아닌 내장 디렉토리)

역할 위계는 다음과 같습니다.

| 구분            | 플러그인               | 위치                                          |
| --------------- | ---------------------- | --------------------------------------------- |
| 🎯 **메인 기능** | `investments-portfolio` | SEMA 퇴직연금 포트폴리오 생성 (이 프로젝트의 핵심) |
| ⚙️ **공용 엔진** | `macro-analysis`       | 메인·추가 기능이 내부 호출하는 거시경제 분석 엔진 |
| ➕ **추가 기능** | `stock-consultation`   | 주식/ETF 투자 상담                            |
| ➕ **추가 기능** | `equity-research`      | 개별 기업 리서치                              |
| ➕ **추가 기능** | `pension-tax-advisor`  | 퇴직연금·연금계좌 세금 상담                   |

### 🎯 메인 기능

#### 1. `investments-portfolio` (v1.2.0) — 포트폴리오 분석의 중심

3 에이전트 · 1 명령 · 11 스킬

| 종류     | 이름                        | 역할                               |
| -------- | --------------------------- | ---------------------------------- |
| 명령     | `portfolio-analyze`       | 포트폴리오 분석 오케스트레이터     |
| 에이전트 | `fund-portfolio`          | 퇴직연금 펀드 포트폴리오 추천      |
| 에이전트 | `compliance-checker`      | DC형 규제 준수 검증                |
| 에이전트 | `output-critic`           | 출력 검증·환각 탐지               |
| 스킬     | `web-search-verifier`     | 주장 종류별 출처 기준 웹검색 프로토콜(시장 숫자 3출처)  |
| 스킬     | `analyst-common`          | 분석 에이전트 공통 규칙            |
| 스킬     | `bogle-principles`        | John Bogle / Vanguard 투자 철학    |
| 스킬     | `dc-pension-rules`        | DC형 퇴직연금 규제 준수 규칙       |
| 스킬     | `fund-selection-criteria` | 펀드 선택 기준·점수 체계          |
| 스킬     | `fund-output-template`    | 펀드 포트폴리오 보고서 출력 템플릿 |
| 스킬     | `macro-output-template`   | 거시경제 보고서 출력 템플릿        |
| 스킬     | `perspective-balance`     | Bull/Bear 균형 분석                |
| 스킬     | `devil-advocate`          | 반론·리스크 발굴                  |
| 스킬     | `file-save-protocol`      | 분석 결과 파일 저장 프로토콜       |
| 스킬     | `data-updater`            | CSV→JSON 펀드 데이터 업데이트     |

### ⚙️ 공용 엔진

#### 2. `macro-analysis` (v1.0.1) — 공용 거시경제 에이전트

7 에이전트 (명령·스킬 없음). 메인·추가 기능 플러그인이 내부에서 재사용하며, **사용자가 직접 실행하는 기능은 아닙니다.**

| 에이전트               | 역할                                                |
| ---------------------- | --------------------------------------------------- |
| `index-fetcher`      | 지수·환율 데이터 수집                              |
| `rate-analyst`       | Fed/BOK 금리 + USD/KRW 전망                         |
| `sector-analyst`     | 5개 핵심 섹터 전망                                  |
| `risk-analyst`       | 지정학·경제·시장 리스크 + Bull/Base/Bear 시나리오 |
| `leadership-analyst` | 주요 7개국 정치·중앙은행 동향                      |
| `macro-synthesizer`  | 하위 분석 결과 종합 보고서 작성                     |
| `macro-critic`       | 종합 결과 검증                                      |

### ➕ 추가 기능

#### 3. `stock-consultation` (v1.0.1) — 주식/ETF 상담

5 에이전트 · 1 명령 · 3 스킬. Bogle/Vanguard 철학 기반.

| 종류     | 이름                         | 역할                         |
| -------- | ---------------------------- | ---------------------------- |
| 명령     | `stock-consult`            | 주식/ETF 상담 오케스트레이터 |
| 에이전트 | `materials-organizer`      | 사용자 제공 자료 정리·요약  |
| 에이전트 | `stock-screener`           | 주식/ETF 후보 스크리닝       |
| 에이전트 | `stock-valuation`          | 개별 종목 심층 밸류에이션    |
| 에이전트 | `bear-case-critic`         | 반대 논거·리스크 분석       |
| 에이전트 | `stock-critic`             | 최종 검증                    |
| 스킬     | `stock-data-verifier`      | 주식/ETF 데이터 교차검증     |
| 스킬     | `analyst-common-stock`     | 주식/ETF 분석 공통 규칙      |
| 스킬     | `file-save-protocol-stock` | 결과 파일 저장 프로토콜      |

#### 4. `equity-research` (v1.0.0) — 기업 리서치

1 에이전트 (명령·스킬 없음).

| 에이전트                    | 역할                                       |
| --------------------------- | ------------------------------------------ |
| `equity-research-analyst` | 기관급 주식 리서치 분석 (티커와 함께 호출) |

#### 5. `pension-tax-advisor` (v1.0.0) — 퇴직연금 세금 상담

5 에이전트 · 1 명령 · 3 스킬. law.go.kr 출처 등급제 + 3중 검증(재계산→비판→반론) 기반 환각 방지.

| 종류     | 이름                       | 역할                                            |
| -------- | -------------------------- | ----------------------------------------------- |
| 명령     | `tax-consult`            | 절세 상담 오케스트레이터 (read-time 신선도·C4 3중 검증) |
| 에이전트 | `tax-knowledge-educator` | 납입·운용·수령 3단계 세제 기초 교육            |
| 에이전트 | `tax-strategy-planner`   | 개인 맞춤 절세 전략 (미검증 시 보류·강한 면책)  |
| 에이전트 | `tax-calc-verifier`      | python3 독립 재계산 검증 (LLM 암산 금지)        |
| 에이전트 | `tax-critic`             | 조문·basis·미검증·미래시행 탐지, A~F 채점      |
| 에이전트 | `tax-law-updater`        | 90일 법령 자동 재확인 (law.go.kr 현행 앵커)     |
| 스킬     | `pension-tax-rules`      | 납입/운용/수령 규칙 + 계산식 스펙 (parameter_id 참조) |
| 스킬     | `tax-law-verifier`       | 출처 등급제·EXACT 법령 검증                     |
| 스킬     | `file-save-protocol-tax` | 세금 상담 결과 저장 프로토콜                     |
---

## 펀드 데이터

데이터는 **과학기술인공제회 상품제안서(제로인 평가 데이터)** 기반이며, JSON으로 저장됩니다.
각 파일의 정확한 기준일·레코드 수는 항상 파일 안의 `_meta` 블록을 신뢰하세요.

| 파일                                       | 내용                                   | 레코드 수 | 기준일(`_meta.version`) | 조인 키                             |
| ------------------------------------------ | -------------------------------------- | :-------: | :-----------------------: | ----------------------------------- |
| `funds/fund_data.json`                   | 투자가능 펀드 기본정보·수익률         |    204    |        2026-10-30        | `fundCode`(요율) / `name`(분류) |
| `funds/fund_fees.json`                   | 펀드 총보수·연간비용                  |    204    |        2026-10-30        | `fundCode`                        |
| `funds/fund_classification.json`         | 카테고리·위험자산 분류 (9개 유형)     |    204    |     (생성 시각 기준)     | `펀드명`                          |
| `funds/tdf_data.json`                    | TDF 마스터 (결정적 enrichment)         |    75    |        2026-10-30        | `fundCode`                        |
| `funds/tdf_fees.json`                    | TDF 수수료/요율                        |    75    |        2026-10-30        | `fundCode`                        |
| `funds/deposit_rates.json`               | 원리금보장형 예금 금리 (공제회 공개 페이지, 기준일 필수) |     4     |        2026-10-31        | (단독 조회)                         |
| `funds/investable_codes.json`            | 투자가능 펀드 코드 허용목록            |    207    |            —            | (필터용)                            |
| `funds/all/all_fund_data.json`           | 전체 펀드 마스터 (투자불가 포함)       |   2169   |        2026-10-30        | `fundCode`                        |
| `funds/all/all_fund_fees.json`           | 전체 펀드 수수료                       |   2169   |        2026-10-30        | `fundCode`                        |
| `funds/all/all_fund_classification.json` | 전체 펀드 분류                         |   2169   |     (생성 시각 기준)     | `펀드명`                          |

> ⚠️ **TDF는 별도 파일·단위**입니다. `update_tdf_data.py --from-proposal`로 갱신하면 상품제안서와 같은 기준일이지만, SEMA 포털 표(`--input <표> --base-date <표의 기준일>`, 기준일 없으면 저장 안 함)로 갱신하면 기준일이 달라지고 수익률이 전 구간 누적이므로 `fund_data.json`(204개)과 **직접 교차비교하지 마세요.**
> `tdf_data.json`의 `baseDateNote`에도 명시되어 있습니다.
>
> ⚠️ `funds/README.md`는 **구버전(STALE)** 문서입니다. 펀드 수·분류 기준은 항상 각 JSON의 `_meta`를 따르세요.
> 데이터 스키마·조인 키 상세는 `funds/AGENTS.md`를 참고하세요.

---

## 펀드 데이터 업데이트 (매월)

스크립트는 `data-updater` 스킬 디렉토리에 있습니다. `update_fund_data.py`·`classify_funds.py`·`update_tdf_data.py`는
**표준 라이브러리만** 사용하고, **`xlsx_to_csv.py`만 `openpyxl`이 필요**합니다 (`fetch_latest_proposal.py`는 `--convert` 시에만 간접 필요).

```bash
SCRIPTS=".claude/plugins/investments-portfolio/skills/data-updater/scripts"

# 1) 미래에셋 게시판에서 최신 xlsx 자동 다운로드 + CSV 변환 (openpyxl 필요)
python $SCRIPTS/fetch_latest_proposal.py --out-dir resource --convert

# 2) CSV → JSON 변환 (fund_data / fund_fees / fund_classification 자동 재생성)
python $SCRIPTS/update_fund_data.py \
  --file "resource/26년06월_상품제안서_퇴직연금(DCIRP).csv" \
  --output-dir "funds"
```

선택 검증·재생성:

```bash
# 변경 사항만 미리보기
python $SCRIPTS/update_fund_data.py --file "resource/...csv" --output-dir funds --dry-run

# 분류만 재생성
python $SCRIPTS/classify_funds.py \
  --fund-data "funds/fund_data.json" --output "funds/fund_classification.json"
```

TDF 업데이트 (별도 흐름):

```bash
# 1) TDF 표를 resource/tdf-raw.md 에 붙여넣기
# 2) 파싱 → tdf_data.json 생성 (요율 enrichment는 --fees)
python $SCRIPTS/update_tdf_data.py --input resource/tdf-raw.md --base-date YYYY-MM-DD --fees
```

> ⚠️ **유지보수 주의 (게시판/양식 변경 시)**
>
> - 미래에셋 게시판 구조가 바뀌면 `fetch_latest_proposal.py`의 첨부 파싱 정규식(`attachmentId`·`(DCIRP).xlsx`)을 점검하세요.
> - 상품제안서 xlsx 양식이 바뀌면 `xlsx_to_csv.py`의 시트명(`실적배당형(펀드, ETF)`)·컬럼 수(25)를 점검하세요.
> - 회귀 검증: 과거 월 xlsx를 변환해 커밋된 `resource/*.csv`와 **byte 단위 일치**하는지 확인하세요.

---

## 테스트 및 정합성 검증

이 프로젝트는 데이터의 결정성과 일관성을 보장하기 위해 두 단계의 검증 체계를 갖추고 있습니다.

### 1. 단위 및 통합 테스트 (pytest)

`tests/`는 TDF enrichment 파이프라인(`update_tdf_data.py`)의 결정성을 검증합니다.
이름 정규화·펀드코드 해석·수수료 매칭·수익률 드리프트 경고·전체 enrichment·CLI·통합 테스트로 구성됩니다.

```bash
python3 -m pytest          # 364 passed (GREEN, 2026-11-18)
```

### 2. 정합성 게이트 (Consistency Gate)

데이터 업데이트나 프롬프트 수정 후, 전체 시스템의 정합성을 검증하는 게이트를 실행합니다.

```bash
python3 scripts/verify_consistency.py
```

- **검증 항목**: dangling references, 날짜 동기화, 데이터 신선도, 중복 테스트, 플러그인 매니페스트 정합성 등 5개 항목
- **결과**: Exit 0 (정상), Exit 1 (불일치 감지), Exit 2 (내부 에러)

---

## 프로젝트 구조

```
pension_sema_guide/
├── .claude/                        # 🔌 Claude Code 설정 + 내장 마켓플레이스/플러그인
│   ├── settings.json               #   enabledPlugins(5개) + extraKnownMarketplaces
│   └── plugins/                    #   vendored 마켓플레이스 + 5개 플러그인
│       ├── .claude-plugin/
│       │   └── marketplace.json    #     마켓플레이스 매니페스트 (pension-sema-guide)
│       ├── investments-portfolio/  #     3 에이전트 + portfolio-analyze + 11 스킬
│       ├── macro-analysis/         #     7 공용 거시경제 에이전트
│       ├── stock-consultation/     #     5 에이전트 + stock-consult + 3 스킬
│       ├── equity-research/        #     1 에이전트 (기업 리서치)
│       └── pension-tax-advisor/    #     5 에이전트 + tax-consult + 3 스킬
├── funds/                          # 펀드 데이터 (제로인 기반) — funds/AGENTS.md 참고
│   ├── fund_data.json              #   투자가능 펀드 (205)
│   ├── fund_fees.json              #   수수료 정보 (205)
│   ├── fund_classification.json    #   자산 분류 (205, 9개 유형)
│   ├── tdf_data.json               #   TDF 마스터 (75, 별도 기준일)
│   ├── tdf_fees.json               #   TDF 수수료 (75)
│   ├── deposit_rates.json          #   예금 금리 (수동 업데이트)
│   ├── investable_codes.json       #   투자가능 코드 허용목록 (207)
│   └── all/                        #   전체 펀드 (2169, *_all_*)
├── tests/                          # TDF enrichment pytest 스위트
├── portfolios/samples/             # 익명화된 공개 예시 (sample-aggressive)
├── consultations/                  # 주식/ETF 상담 보고서 (비개인 — 보유·금액·계좌가 들어가면 confidentialData/consultations/, verify_no_pii.sh가 검사)
├── resource/                       # SEMA 상품제안서 CSV/XLSX (원본)
├── docs/                           # 기술 문서
├── scripts/                        # verify_no_pii.sh, verify_plugin.sh
├── index-data.json                 # 시장 지수 데이터 스냅샷
├── pytest.ini                      # testpaths=tests
├── confidentialData/               # 🔒 개인정보 (gitignore — 저장소 미포함)
└── AGENTS.md                       # 프로젝트 지식베이스
```

---

## 개인정보 보호 정책

이 저장소는 **공개(Public)** 저장소입니다. 개인정보는 절대 커밋하지 않습니다.

- 개인별 데이터(투자자 프로필 `investor-profile.md`, 개인 투자계획·잔고, 실제 분석 산출물)는 **반드시 `confidentialData/`에만** 저장합니다.
- `confidentialData/`는 `.gitignore`에 등록되어 저장소에 포함되지 않습니다.
- 공개 가능한 예시는 **익명화**하여 `portfolios/samples/`에 둡니다 (실명·생년·소속·계좌 금지).
- 도리(금돌)도 같은 규칙을 따릅니다. 주인의 재정 자료는 `confidentialData/`와 도리 작업 환경 안에만 두고, 이 저장소에는 개인정보 검사를 통과한 변경만 바로 올립니다.
- 커밋 전 PII 누출 여부를 검증하세요:

```bash
scripts/verify_no_pii.sh      # 히스토리 전수 PII 스캔
scripts/verify_plugin.sh      # 플러그인 매니페스트 검증
```

---

## 면책 조항

1. 과거 수익률은 미래 수익률을 보장하지 않습니다.
2. 본 가이드는 정보 제공 목적이며, 투자 권유가 아닙니다. 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.
3. DC형 퇴직연금 규제는 변경될 수 있으니 입력 전 최신 규정과 포털 안내를 확인하세요.
4. 데이터 기준일이 지난 경우 펀드 라인업·수익률이 실제 포털과 다를 수 있습니다.

---

- **데이터 출처**: 과학기술인공제회 퇴직연금 상품제안서 + 펀드평가사 제로인(Zeroin)
- **마켓플레이스**: `pension-sema-guide`

*Multi-Agent Portfolio System for SEMA DC Pension*
