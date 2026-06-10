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

`python3 -m pytest` (repo root) → 63 passed (현재 기준: update_tdf_data 40 + gate 17 + year derivation 6).

## PATH CONFIGURATION

스크립트 경로는 `.claude/plugins/...` 전체를 사용하며, `conftest.py:14` (`SCRIPTS_DIR`) 및 `test_cli.py:11` (`SCRIPT`)에 올바르게 설정되어 있습니다. 저장소 루트에서 실행 시 모든 테스트가 정상적으로 수집(collection)되고 통과합니다.

## CONVENTIONS

- 픽스처 fund 코드/이름은 실제 적격TDF 사례(KB/삼성/신한/미래에셋/한국투자) 기반 — adversarial(연도 인접·share class 충돌·헤지 불일치) 검증용. 임의 변경 금지.
- 테스트는 `funds/` 실데이터를 읽지 않음 — fixture 슬라이스만 사용.
