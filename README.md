# Pension SEMA Guide

과학기술인공제회(SEMA) DC형 퇴직연금 포트폴리오를 AI 멀티에이전트 시스템으로 분석·추천하는 오픈 가이드입니다.

> **🔓 공개 저장소입니다.** 개인정보(투자자 프로필·잔고·분석 산출물)는 저장소에 포함되지 않으며,
> 로컬의 `confidentialData/` 디렉토리(gitignore 대상)에만 보관됩니다.

---

## 빠른 시작

### 1. 플러그인 등록

이 저장소는 Claude Code 플러그인을 내장(vendoring)하고 있습니다.

```
/plugin marketplace add .
```

`.claude/settings.json`에서 `investments-portfolio@pension-sema-guide` 플러그인이 활성화됩니다.

### 2. 포트폴리오 생성

`confidentialData/cbd.md`에 투자자 프로필을 작성한 후 명령을 실행합니다:

```
/investments-portfolio:portfolio-analyze 나를 위한 새로운 포트폴리오를 구성해줘.

| 항목 | 내용 |
|------|------|
| **생년** | (예: 19XX년) |
| **은퇴 예정** | 65세 |
| **투자 성향** | **공격형** (장기투자) |
| **위험 수용도** | 높음 (단기 손실 감내 가능) |
```

### 3. 결과 확인

분석 보고서는 개인정보를 포함하므로 `confidentialData/`에 저장됩니다.
공개 예시는 `portfolios/samples/sample-aggressive/`에서 익명화된 형태로 확인할 수 있습니다:

```
portfolios/samples/sample-aggressive/
├── 00-macro-outlook.md        # 거시경제 전망
├── 01-fund-analysis.md        # 펀드 분석 및 추천
├── 02-compliance-report.md    # DC형 규제 준수 검증
├── 03-output-verification.md  # 환각 방지 출력 검증
└── 04-portfolio-summary.md    # 최종 포트폴리오 요약
```

### 4. 펀드 데이터 업데이트 (매월)

```bash
SCRIPTS="plugins/investments-portfolio/skills/data-updater/scripts"

# 1) 미래에셋 게시판에서 최신 xlsx 자동 다운로드 + CSV 변환 (openpyxl 필요)
python $SCRIPTS/fetch_latest_proposal.py --out-dir resource --convert

# 2) CSV → JSON 변환 (분류 자동 재생성)
python $SCRIPTS/update_fund_data.py \
  --file "resource/26년06월_상품제안서_퇴직연금(DCIRP).csv" \
  --output-dir "funds"
```

> `xlsx_to_csv.py`(변환) · `fetch_latest_proposal.py`(다운로드)만 `openpyxl`이 필요하고,
> `update_fund_data.py`는 표준 라이브러리만 사용합니다.

---

## 멀티에이전트 워크플로우

```
[사용자 요청 + 투자자 프로필]
     │
     ▼
[macro-outlook]         거시경제 동향, 시장 전망, 자산배분 권고
     │
     ▼
[fund-portfolio]        펀드 데이터 기반 포트폴리오 구성
     │
     ▼
[compliance-checker]    DC형 위험자산 70% 한도, 단일펀드 40% 한도 검증
     │
     ▼
[output-critic]         출처 검증, 환각(hallucination) 탐지, 신뢰도 점수
     │
     ▼
[portfolio-analyze]     최종 통합 보고서
```

| 에이전트 | 출력 | 역할 |
|----------|------|------|
| **macro-outlook** | `00-macro-outlook.md` | 거시경제·시장 전망 |
| **fund-portfolio** | `01-fund-analysis.md` | 펀드 선별·비중 배분 |
| **compliance-checker** | `02-compliance-report.md` | 규제 준수 검증 |
| **output-critic** | `03-output-verification.md` | 환각 방지·출처 검증 |
| **portfolio-analyze** | `04-portfolio-summary.md` | 최종 통합 |

---

## 프로젝트 구조

```
pension_sema_guide/
├── plugins/                # 🔌 내장 플러그인 (vendored)
│   └── investments-portfolio/
│       ├── agents/         #   3개 에이전트
│       ├── commands/       #   포트폴리오 분석 명령
│       └── skills/         #   11개 전문 스킬
├── .claude-plugin/
│   └── marketplace.json    # 플러그인 마켓플레이스 매니페스트
├── funds/                  # 펀드 데이터 (제로인 기반)
│   ├── fund_data.json      #   투자가능 펀드
│   ├── fund_fees.json      #   수수료 정보
│   ├── fund_classification.json  #   자산 분류
│   ├── deposit_rates.json  #   예금 금리
│   └── all/                #   전체 펀드
├── portfolios/samples/     # 익명화된 공개 예시
├── consultations/          # 투자 컨설테이션 보고서 (비개인)
├── resource/               # SEMA 상품제안서 CSV/XLSX
├── docs/                   # 기술 문서·개선 계획
├── index-data.json         # 시장 지수 데이터
├── confidentialData/       # 🔒 개인정보 (gitignore — 저장소에 포함 안 됨)
└── AGENTS.md               # 프로젝트 지식베이스
```

> 🔒 `confidentialData/`는 개인별 데이터(투자자 프로필·잔고·실제 분석 결과) 보관소이며
> gitignore 처리되어 저장소에 포함되지 않습니다.

## 펀드 데이터

| 파일 | 설명 |
|------|------|
| `fund_data.json` | 투자가능 펀드 기본정보·수익률 |
| `fund_fees.json` | 펀드 총보수·연간비용 |
| `fund_classification.json` | 카테고리·위험자산 분류 |
| `deposit_rates.json` | 원리금보장형 예금 금리 |
| `all/all_fund_data.json` | 전체 펀드 (투자불가 포함) |

- **데이터 출처**: 과학기술인공제회 상품제안서 (제로인 평가 데이터)

---

*Multi-Agent Portfolio System*
