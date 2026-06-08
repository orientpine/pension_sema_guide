# TESTS: tests/

`update_tdf_data.py`(TDF 결정적 보강)의 pytest 스위트. `pytest.ini`(repo root) `testpaths=tests`. stdlib만, 네트워크 없음 — `conftest.py`가 in-memory authoritative 슬라이스(adversarial TDF 케이스 7종) 제공.

## FILES

| 파일 | 대상 |
|------|------|
| conftest.py | `sys.path` 주입 + `auth_data`/`auth_fees` fixture |
| test_canonicalize.py | 이름 정규화 (vehicle 토큰, share class) |
| test_resolve.py | `resolve_tdf_row`, `build_authoritative_index` |
| test_fee.py | 수수료 매칭/검증 |
| test_cross_validate.py | 수익률 드리프트 경고 |
| test_enrich.py | 보강 파이프라인 전체 |
| test_cli.py / test_integration.py | CLI 종단 동작 |

## RUN

`python3 -m pytest` (repo root) → 38 passed.

## ⚠ PATH GOTCHA

스크립트 경로는 `.claude/plugins/...` 전체를 써야 함 (`conftest.py:14` `SCRIPTS_DIR`, `test_cli.py:11` `SCRIPT`). `.claude/` 세그먼트 누락 시 `update_tdf_data` import 실패(collection 에러) + CLI 테스트 파일 not-found. 새 테스트 추가 시 동일 경로 패턴 사용.

## CONVENTIONS

- 픽스처 fund 코드/이름은 실제 적격TDF 사례(KB/삼성/신한/미래에셋/한국투자) 기반 — adversarial(연도 인접·share class 충돌·헤지 불일치) 검증용. 임의 변경 금지.
- 테스트는 `funds/` 실데이터를 읽지 않음 — fixture 슬라이스만 사용.
