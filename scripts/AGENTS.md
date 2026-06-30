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
- **date_sync**: markdown 날짜 리터럴 ↔ SSOT 주석 정합성 + `tdf_data.json.baseDateNote` 동기화
- **freshness**: `funds/deposit_rates.json.updatedAt` 신선도 (임계 초과 시 위반)
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
