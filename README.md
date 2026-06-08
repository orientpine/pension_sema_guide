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

---

## 무엇을 할 수 있나요?

| 하고 싶은 일                          | 사용하는 명령 / 에이전트                                 | 결과물                                                      |
| ------------------------------------- | -------------------------------------------------------- | ----------------------------------------------------------- |
| **내 퇴직연금 포트폴리오 구성** | `/investments-portfolio:portfolio-analyze`             | 5단계 분석 보고서(거시경제 → 펀드 → 규제 → 검증 → 요약) |
| **주식·ETF 투자 상담**         | `/stock-consultation:stock-consult`                    | 스크리닝·밸류에이션·반론·검증 상담 보고서                |
| **개별 기업 리서치**            | `@equity-research` 에이전트 (티커와 함께 호출)         | 기관급 리서치 리포트                                        |
| **거시경제 전망**               | `macro-analysis` 공용 에이전트 (위 명령들이 내부 호출) | 지수·금리·섹터·리스크·리더십 분석                       |

> 핵심 설계 원칙은 **환각 방지**입니다. 모든 수치는 출처를 명시하고, 3개 출처 교차검증·출력 검증 에이전트를 거칩니다.

---

## 사전 준비

- **Claude Code** (플러그인/마켓플레이스 지원 버전)
- **Python 3** (펀드 데이터 업데이트 시) — 대부분 표준 라이브러리만 사용
- **openpyxl** (xlsx → CSV 변환 시에만 필요): `pip install openpyxl`

---

## 빠른 시작

### 1. 플러그인 등록

이 저장소는 Claude Code 마켓플레이스 + 4개 플러그인을 `.claude/plugins/`에 내장(vendoring)하고 있습니다.
`.claude/settings.json`에 마켓플레이스(`extraKnownMarketplaces`)와 활성 플러그인(`enabledPlugins`, 4개 모두 `true`)이 등록되어 있어,
**프로젝트를 열고 폴더를 신뢰(trust)하면** Claude Code가 자동으로 설치를 안내합니다.

수동으로 등록하려면:

```
/plugin marketplace add ./.claude/plugins
```

이후 `pension-sema-guide` 마켓플레이스의 4개 플러그인(`investments-portfolio`, `macro-analysis`, `stock-consultation`, `equity-research`)이 활성화됩니다.

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

분석으로 끝이 아닙니다. **이 프로젝트의 최종 목적은 추천 포트폴리오를 실제 과학기술인공제회 DC형 퇴직연금 포털에 정확히 입력하는 것**입니다.
포털에서 펀드 비중을 설정할 때는 보고서를 옆에 띄워두고 **에이전트와 적극적으로 대화하며** 진행하세요. 혼자 입력하다 막히면 멈추지 말고 바로 물어보세요.

### 에이전트와 함께 입력하는 방법

1. `04-portfolio-summary.md`의 **추천 펀드 표**(펀드명·비중·유형)를 펼쳐 둡니다.
2. SEMA 포털의 펀드 비중 설정 화면을 열고, **필요한 영역을 복사·붙여넣기하면서** 그때그때 에이전트에게 확인을 요청하세요.
3. 입력이 끝나면 **비중 합계 100%·위험자산 70% 한도**가 맞는지 에이전트에게 최종 검증을 요청하세요.

### 이렇게 물어보세요 (대화 예시)

- “포털에서 *키움더드림단기채*가 검색이 안 돼. 같은 역할(안전자산·단기채)을 할 대체 펀드를 추천해줘.”
- “지금까지 입력한 비중이 15/15/5/20/10/5/15 인데, 합계랑 위험자산 비중이 규제에 맞아?”
- “포털 펀드명이 보고서랑 살짝 달라(‘ACE’ vs ‘KBSTAR’ 등). 같은 펀드가 맞는지 코드로 확인해줘.”
- “이 펀드가 신규 설정이라 포털에 없네. 비중을 어디로 옮기면 자산배분이 안 깨질까?”
- “자동 납입(정기 매수) 비중도 이 포트폴리오랑 똑같이 맞춰야 할까?”

> **왜 대화형으로 하나요?** SEMA 포털의 펀드 라인업·명칭·코드는 보고서 작성 시점과 미묘하게 다를 수 있고,
> 일부 추천 펀드는 신규 설정이라 포털에 없을 수 있습니다. 이런 차이는 **입력 중에 즉시 에이전트와 맞춰가며 해결**하는 것이
> 가장 안전합니다. 한 번에 다 입력하고 끝내기보다, **물어보고 → 입력하고 → 검증하고**를 반복하세요.

### 입력 완료 후 체크리스트 (보고서의 실행 체크리스트와 동일)

- [ ] 추천 펀드 비중을 SEMA 포털에 모두 설정했는가
- [ ] 비중 합계 = 100% 인가
- [ ] 위험자산 비중 ≤ 70% 인가 (DC형 법정 한도)
- [ ] 단일 펀드 비중 ≤ 40% 인가
- [ ] 자동 납입(정기 매수) 비중을 동일하게 맞췄는가

---

## 멀티에이전트 워크플로우 (포트폴리오 분석)

`/investments-portfolio:portfolio-analyze`는 아래 단계를 오케스트레이션합니다. 거시경제 단계는 `macro-analysis` 플러그인의
공용 에이전트들이 수행하고, 이후 펀드 선별·규제 검증·출력 검증을 거쳐 최종 보고서로 통합됩니다.

```
[사용자 요청 + 투자자 프로필(명령 프롬프트에 인라인 입력)]
     │
     ▼
[거시경제 분석]   macro-analysis 에이전트(지수·금리·섹터·리스크·리더십) → 종합/검증
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

## 플러그인 구성

마켓플레이스 `pension-sema-guide`에 4개 플러그인이 vendoring되어 있습니다. (서브모듈이 아닌 내장 디렉토리)

### 1. `investments-portfolio` (v1.2.0) — 포트폴리오 분석의 중심

3 에이전트 · 1 명령 · 11 스킬

| 종류     | 이름                        | 역할                               |
| -------- | --------------------------- | ---------------------------------- |
| 명령     | `portfolio-analyze`       | 포트폴리오 분석 오케스트레이터     |
| 에이전트 | `fund-portfolio`          | 퇴직연금 펀드 포트폴리오 추천      |
| 에이전트 | `compliance-checker`      | DC형 규제 준수 검증                |
| 에이전트 | `output-critic`           | 출력 검증·환각 탐지               |
| 스킬     | `web-search-verifier`     | 3개 출처 교차검증 웹검색 프로토콜  |
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

### 2. `macro-analysis` (v1.0.1) — 공용 거시경제 에이전트

7 에이전트 (명령·스킬 없음). 다른 플러그인이 내부에서 재사용합니다.

| 에이전트               | 역할                                                |
| ---------------------- | --------------------------------------------------- |
| `index-fetcher`      | 지수·환율 데이터 수집                              |
| `rate-analyst`       | Fed/BOK 금리 + USD/KRW 전망                         |
| `sector-analyst`     | 5개 핵심 섹터 전망                                  |
| `risk-analyst`       | 지정학·경제·시장 리스크 + Bull/Base/Bear 시나리오 |
| `leadership-analyst` | 주요 7개국 정치·중앙은행 동향                      |
| `macro-synthesizer`  | 하위 분석 결과 종합 보고서 작성                     |
| `macro-critic`       | 종합 결과 검증                                      |

### 3. `stock-consultation` (v1.0.1) — 주식/ETF 상담

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

### 4. `equity-research` (v1.0.0) — 기업 리서치

1 에이전트 (명령·스킬 없음).

| 에이전트                    | 역할                                       |
| --------------------------- | ------------------------------------------ |
| `equity-research-analyst` | 기관급 주식 리서치 분석 (티커와 함께 호출) |

---

## 펀드 데이터

데이터는 **과학기술인공제회 상품제안서(제로인 평가 데이터)** 기반이며, JSON으로 저장됩니다.
각 파일의 정확한 기준일·레코드 수는 항상 파일 안의 `_meta` 블록을 신뢰하세요.

| 파일                                       | 내용                                   | 레코드 수 | 기준일(`_meta.version`) | 조인 키                             |
| ------------------------------------------ | -------------------------------------- | :-------: | :-----------------------: | ----------------------------------- |
| `funds/fund_data.json`                   | 투자가능 펀드 기본정보·수익률         |    205    |        2026-06-01        | `fundCode`(요율) / `name`(분류) |
| `funds/fund_fees.json`                   | 펀드 총보수·연간비용                  |    205    |        2026-06-01        | `fundCode`                        |
| `funds/fund_classification.json`         | 카테고리·위험자산 분류 (9개 유형)     |    205    |     (생성 시각 기준)     | `펀드명`                          |
| `funds/tdf_data.json`                    | TDF 마스터 (결정적 enrichment)         |    75    |        2026-06-04        | `fundCode`                        |
| `funds/tdf_fees.json`                    | TDF 수수료/요율                        |    75    |        2026-06-07        | `fundCode`                        |
| `funds/deposit_rates.json`               | 원리금보장형 예금 금리 (수동 업데이트) |     4     |        2026-02-28        | (단독 조회)                         |
| `funds/investable_codes.json`            | 투자가능 펀드 코드 허용목록            |    207    |            —            | (필터용)                            |
| `funds/all/all_fund_data.json`           | 전체 펀드 마스터 (투자불가 포함)       |   2104   |        2026-06-01        | `fundCode`                        |
| `funds/all/all_fund_fees.json`           | 전체 펀드 수수료                       |   2104   |        2026-06-01        | `fundCode`                        |
| `funds/all/all_fund_classification.json` | 전체 펀드 분류                         |   2104   |     (생성 시각 기준)     | `펀드명`                          |

> ⚠️ **TDF는 별도 기준일**(`tdf_data.json` 2026-06-04, 75개)을 사용하므로 `fund_data.json`(205개)과 **직접 교차비교하지 마세요.**
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
python $SCRIPTS/update_tdf_data.py --input resource/tdf-raw.md --fees
```

> ⚠️ **유지보수 주의 (게시판/양식 변경 시)**
>
> - 미래에셋 게시판 구조가 바뀌면 `fetch_latest_proposal.py`의 첨부 파싱 정규식(`attachmentId`·`(DCIRP).xlsx`)을 점검하세요.
> - 상품제안서 xlsx 양식이 바뀌면 `xlsx_to_csv.py`의 시트명(`실적배당형(펀드, ETF)`)·컬럼 수(25)를 점검하세요.
> - 회귀 검증: 과거 월 xlsx를 변환해 커밋된 `resource/*.csv`와 **byte 단위 일치**하는지 확인하세요.

---

## 테스트

`tests/`는 TDF enrichment 파이프라인(`update_tdf_data.py`)의 결정성을 검증합니다.
이름 정규화·펀드코드 해석·수수료 매칭·수익률 드리프트 경고·전체 enrichment·CLI·통합 테스트로 구성됩니다.

```bash
python3 -m pytest          # pytest.ini: testpaths=tests
```

> ⚠️ **알려진 이슈**: `tests/conftest.py`의 `SCRIPTS_DIR` 경로 처리에 주의가 필요합니다 (저장소 루트에서 실행 권장).
> 자세한 내용과 import-path 주의사항은 `tests/AGENTS.md`를 참고하세요.

---

## 프로젝트 구조

```
pension_sema_guide/
├── .claude/                        # 🔌 Claude Code 설정 + 내장 마켓플레이스/플러그인
│   ├── settings.json               #   enabledPlugins(4개) + extraKnownMarketplaces
│   └── plugins/                    #   vendored 마켓플레이스 + 4개 플러그인
│       ├── .claude-plugin/
│       │   └── marketplace.json    #     마켓플레이스 매니페스트 (pension-sema-guide)
│       ├── investments-portfolio/  #     3 에이전트 + portfolio-analyze + 11 스킬
│       ├── macro-analysis/         #     7 공용 거시경제 에이전트
│       ├── stock-consultation/     #     5 에이전트 + stock-consult + 3 스킬
│       └── equity-research/        #     1 에이전트 (기업 리서치)
├── funds/                          # 펀드 데이터 (제로인 기반) — funds/AGENTS.md 참고
│   ├── fund_data.json              #   투자가능 펀드 (205)
│   ├── fund_fees.json              #   수수료 정보 (205)
│   ├── fund_classification.json    #   자산 분류 (205, 9개 유형)
│   ├── tdf_data.json               #   TDF 마스터 (75, 별도 기준일)
│   ├── tdf_fees.json               #   TDF 수수료 (75)
│   ├── deposit_rates.json          #   예금 금리 (수동 업데이트)
│   ├── investable_codes.json       #   투자가능 코드 허용목록 (207)
│   └── all/                        #   전체 펀드 (2104, *_all_*)
├── tests/                          # TDF enrichment pytest 스위트
├── portfolios/samples/             # 익명화된 공개 예시 (sample-aggressive)
├── consultations/                  # 주식/ETF 상담 보고서 (비개인)
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
