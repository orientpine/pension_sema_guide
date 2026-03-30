# Researcher Pension AI (Private)

과학기술인공제회 DC형 퇴직연금 포트폴리오를 AI 멀티에이전트 시스템으로 분석·추천합니다.

> **🔒 이 저장소는 개인정보가 포함된 Private 저장소입니다.**  
> Public 버전: [orientpine/researcher-pension-ai](https://github.com/orientpine/researcher-pension-ai)

---

## 빠른 시작

### 1. 포트폴리오 생성

`cbd.md`에 투자자 프로필을 작성한 후 명령을 실행합니다:

```
/investments-portfolio:portfolio-orchestrator 나를 위한 새로운 포트폴리오를 구성해줘.

| 항목 | 내용 |
|------|------|
| **생년** | 1992년 |
| **은퇴 예정** | 65세 |
| **투자 성향** | **공격형** (30년+ 장기투자) |
| **위험 수용도** | 높음 (단기 -30% 손실 감내 가능) |
```

### 2. 결과 확인

`portfolios/` 디렉토리에 보고서가 자동 생성됩니다:

```
portfolios/2026-03-30-aggressive-abc123/
├── 00-macro-outlook.md        # 거시경제 전망
├── 01-fund-analysis.md        # 펀드 분석 및 추천
├── 02-compliance-report.md    # DC형 규제 준수 검증
├── 03-output-verification.md  # 환각 방지 출력 검증
└── 04-portfolio-summary.md    # 최종 포트폴리오 요약
```

### 3. 펀드 데이터 업데이트

```bash
# CSV → JSON 변환
python scripts/update_fund_data.py \
  --file "resource/26년03월_상품제안서_퇴직연금(DCIRP).csv" \
  --output-dir "funds"
```

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
[portfolio-orchestrator] 최종 통합 보고서
```

| 에이전트 | 출력 | 역할 |
|----------|------|------|
| **macro-outlook** | `00-macro-outlook.md` | 거시경제·시장 전망 |
| **fund-portfolio** | `01-fund-analysis.md` | 펀드 선별·비중 배분 |
| **compliance-checker** | `02-compliance-report.md` | 규제 준수 검증 |
| **output-critic** | `03-output-verification.md` | 환각 방지·출처 검증 |
| **portfolio-orchestrator** | `04-portfolio-summary.md` | 최종 통합 |

---

## 프로젝트 구조

```
investmunts_cbd/
├── cbd.md                  # 🔒 투자자 프로필 (개인정보)
├── funds/                  # 펀드 데이터 (제로인 기반)
│   ├── fund_data.json      #   투자가능 펀드 (206개)
│   ├── fund_fees.json      #   수수료 정보
│   ├── fund_classification.json  #   자산 분류
│   ├── deposit_rates.json  #   예금 금리
│   └── all/                #   전체 펀드 (2,015개)
├── portfolios/             # 생성된 포트폴리오 보고서
├── consultations/          # 투자 컨설테이션 보고서
├── resource/               # 🔒 SEMA 원본 CSV/XLSX
├── nouse/                  # 🔒 개인 투자계획·잔고 현황
├── docs/                   # 기술 문서·개선 계획
├── index-data.json         # 시장 지수 데이터
└── AGENTS.md               # 프로젝트 지식베이스
```

> 🔒 표시 항목은 개인정보 포함 — Public 저장소에서 제외됨

## 펀드 데이터

| 파일 | 설명 | 레코드 수 |
|------|------|-----------|
| `fund_data.json` | 투자가능 펀드 기본정보·수익률 | 206개 |
| `fund_fees.json` | 펀드 총보수·연간비용 | 206개 |
| `fund_classification.json` | 카테고리·위험자산 분류 | 206개 |
| `deposit_rates.json` | 원리금보장형 예금 금리 | - |
| `all/all_fund_data.json` | 전체 펀드 (투자불가 포함) | 2,015개 |

- **데이터 출처**: 과학기술인공제회 상품제안서 (제로인 평가 데이터)
- **기준일**: 2026-03-01

---

*Multi-Agent Portfolio System v3.0*
