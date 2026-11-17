# SCRIPTS: scripts/

저장소 전역 **검증/CI 도구** (stdlib·bash만). 데이터 ETL(`.claude/plugins/investments-portfolio/skills/data-updater/scripts/`)과 별개 — 여기는 정합성·PII·플러그인 매니페스트·git hook을 검증한다.

## FILES

| 파일 | 역할 | Exit |
|------|------|------|
| verify_consistency.py | 정합성 게이트 (권위 소스, 695 LOC, stdlib) | 0 ok / 1 위반 / 2 내부에러 |
| verify_no_pii.sh | PII 문자열·경로 스캔 (전체 git history + 워킹트리) | 0 clean / 1 발견 |
| verify_plugin.sh | **SUPERSEDED** — investments-portfolio 전용 매니페스트 5종 얕은 검사 (jq 필요) | 0 / 1 |
| install-hooks.sh | `.git/hooks/pre-commit` 설치 (gate + pytest) | — |

## verify_consistency.py — 5 CHECKS

`python3 scripts/verify_consistency.py [--root PATH] [--only CHECK]`

- **dangling**: 선언 없는 `subagent_type=` / `@mention` / `/plugin:command` / `skills_reference` 참조 탐지
- **date_sync**: markdown 날짜 리터럴 ↔ SSOT 주석 정합성 + `tdf_data.json.baseDateNote` 동기화. 날짜의 실제 경과일은 freshness가 담당한다.
- **freshness**: 기존 `_meta.updatedAt` 임계 검사에 더해 원천·적용기간·개별 검증일을 독립 검사한다.
  - `fund_data.json`·`tdf_data.json`의 `_meta.version`: 45일 초과 시 위반. 전월 말 실적을 담는 월간 상품제안서의 최장 31일 주기 + 다음 게시/수집 여유 14일이다. 생성만 다시 해도 원천 기준일이 새로워지지 않으며 한 달 누락을 허용하지 않는다.
  - `deposit_rates.json`: `_meta.sourceBaseDate`는 기존 `freshnessThresholdDays`(30일), 각 상품의 `appliesFrom`~`appliesTo`와 `bonusPeriod.from`~`bonusPeriod.to`는 한국 달력일 양끝 포함으로 검사한다. 시작 전/종료 후는 위반이다.
  - `pension_tax_params.json`: 검증된 파라미터의 `lastVerifiedAt`은 tax-law-updater 규약대로 90일 초과 시 위반. `seed`·`unverified`는 확정 계산 보류 규약을 유지하며 stderr JSON으로 개별 보고하고 실패시키지 않는다.
  - 필수 원천 기준일이나 검증 완료 값의 확인일이 없거나 잘못되었으면 위반. 날짜는 KST 달력일, 타임스탬프는 경과 일수로 판정하며 임계일 당일은 통과한다.
- **dup_test**: 중복 pytest 함수명
- **manifest**: marketplace.json / plugin.json(4개) / settings.json 정합성 — verify_plugin.sh를 대체하는 권위 검사

frozen dataclass(`Violation{file,line,ssot,message_ko}`, `Args`). `validate_root()`가 필수 입력 경로 존재를 먼저 확인.

## WHEN TO RUN

- 데이터 갱신(`update_fund_data.py`/`update_tdf_data.py`) 또는 프롬프트(.md) 수정 후 **필수**: `python3 scripts/verify_consistency.py` (Exit 0 이어야 완료로 간주).
- 커밋 전 PII: `scripts/verify_no_pii.sh`.
- 자동화: `scripts/install-hooks.sh` → pre-commit이 gate + `pytest -q` 실행.
- CI: `.github/workflows/consistency-gate.yml`가 push/PR마다 gate + `pytest -q` 실행 (Python 3.12, `pip install pytest`).
- 게이트 자체 회귀: `tests/test_verify_consistency.py` (17 tests).

## ANTI-PATTERNS

- verify_plugin.sh를 권위 검사로 사용 — SUPERSEDED. 매니페스트 검증은 verify_consistency.py의 manifest 체크.
- verify_no_pii.sh에 PII 리터럴 하드코딩 — 의도적으로 런타임 fragment 조립(self-match·filter-repo mangling 방지). 통짜 문자열 추가 금지.
- gate 위반·PII 발견을 무시하고 커밋 — pre-commit hook과 CI에서 차단됨.
