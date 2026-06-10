# SSOT 목록 확정

이 문서는 독립 SSOT 포인터와 gate 기준을 고정한다. 서로 다른 기준일/우주(universe)는 동등 비교하지 않는다.

| SSOT 파일 | JSON 포인터 | 현재값 | 의미 | 게이트 용도 |
|---|---|---|---|---|
| `funds/fund_data.json` | `funds/fund_data.json#_meta.version` | `2026-06-01` | 투자가능 펀드 기준일(월간 sync) | 기본 펀드 기준선 |
| `funds/fund_data.json` | `funds/fund_data.json#_meta.missing` | `['K55205BU9205','K55223C80096']` | 누락 코드(의도된 제외) | dangling 오탐 방지 |
| `funds/tdf_data.json` | `funds/tdf_data.json#_meta.version` | `2026-06-04` | TDF 별도 기준일 | TDF gate 기준선 |
| `funds/tdf_data.json` | `funds/tdf_data.json#_meta.baseDateNote` | `fund_data.json 기준일 2026-03-01과 상이. 직접 교차비교 금지` | TDF는 별도 universe/기준일 | cross-compare 금지 |
| `funds/tdf_fees.json` | `funds/tdf_fees.json#_meta.version` | `2026-06-07` | TDF 수수료 기준일 | TDF 수수료 동기화 |
| `funds/deposit_rates.json` | `funds/deposit_rates.json#_meta.version` | `2026-02-28` | 예금 금리 기준일 | 원리금보장형 비교 기준 |
| `funds/deposit_rates.json` | `funds/deposit_rates.json#_meta.updatedAt` | `2026-03-30T14:40:00+09:00` | 마지막 수동 갱신 시각 | staleness 판정 |
| `funds/deposit_rates.json` | `funds/deposit_rates.json#_meta.freshnessThresholdDays` | `30` | 신선도 임계값 | 30일 초과 시 stale 경고 |
| `funds/fund_fees.json` | `funds/fund_fees.json#_meta.version` | `2026-06-01` | 펀드 총보수 기준일 | fee join 기준 |
| `funds/all/all_fund_data.json` | `funds/all/all_fund_data.json#_meta.version` | `2026-06-01` | 전체 universe 원장 | TDF enrichment 권위 소스 |
| `funds/all/all_fund_fees.json` | `funds/all/all_fund_fees.json#_meta.version` | `2026-06-01` | 전체 universe 수수료 원장 | TDF fee enrichment 권위 소스 |

## 의미 정리

- **sync**: `fund_data`, `fund_fees`, `all_fund_data`, `all_fund_fees`는 동일 월간 CSV 기준으로 동기화된 원장이다.
- **staleness**: `deposit_rates`는 `freshnessThresholdDays=30`으로 별도 신선도 판정만 수행한다.
- **separate universe**: `tdf_data`는 TDF 전용 기준일/수익률 체계이며 `fund_data`와 직접 교차비교하지 않는다.
- **authority**: `funds/all/*`는 TDF deterministic enrichment의 권위 소스다.

## 제외 목록

| 항목 | 이유 | 게이트 처리 |
|---|---|---|
| `funds/fund_data.json#_meta.missing`의 `K55205BU9205`, `K55223C80096` | 원장에 누락된 의도적 제외 코드 | dangling link로 보지 않음 |
| `funds/README.md` | 구버전(STALE) 문서 | gate truth에서 제외 |

## 게이트 실행 런북 (필수)

**모든 데이터 갱신 후 정합성 게이트 통과 필수.** 갱신이 완료된 것으로 간주되려면 게이트가 exit 0 이어야 한다.

```bash
python3 scripts/verify_consistency.py   # exit 0 확인 (1=불일치, 2=내부 에러)
```

- 자동 갱신 스크립트(`update_fund_data.py`, `update_tdf_data.py`, `classify_funds.py`, `fetch_latest_proposal.py`)는 성공 경로 끝에서 위 게이트를 자동 호출하며, 실패 시 종료 코드 비-0 으로 갱신을 차단한다.
- `deposit_rates.json` **수동 갱신** 후에는 반드시 `python3 scripts/verify_consistency.py` 를 직접 실행하여 Check C(freshness) 통과를 확인한다.
- 로컬 커밋 차단: `bash scripts/install-hooks.sh` 로 pre-commit 훅을 설치하면 커밋 전 게이트 + pytest 가 자동 실행된다.
- CI: `.github/workflows/consistency-gate.yml` 가 push/PR 마다 동일 게이트 + pytest 를 재실행한다.
