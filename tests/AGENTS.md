# TESTS: tests/

`update_tdf_data.py`(TDF 결정적 보강) + 정합성 게이트(`scripts/verify_consistency.py`)의 pytest 스위트. `pytest.ini`(repo root) `testpaths=tests`. stdlib만, 네트워크 없음 — `conftest.py`가 in-memory authoritative 슬라이스(adversarial TDF 케이스 7종) 제공.

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
| test_year_derive.py | 기준년도/연령대 산출 (`_derive_current_year`) |
| test_from_proposal.py | `--from-proposal` TDF 상품제안서 기준 갱신 (`refresh_from_proposal`) |
| test_verify_consistency.py | 정합성 게이트 자체 검증 (dangling/date/freshness — 원천 기준일·적용기간·파라미터별 확인일 포함/dup/manifest) |
| test_classify_risk.py | `classify_funds.py` 위험자산(riskStatus, 감독규정 제11조①)·환헤지(UH 우선)·지역(해외 이름이 korea 기본값으로 빠지지 않게) 분류 |
| test_tdf_limits.py | TDF 적격 근거(`tdfQualified`)와 `--input --base-date` 기준일 |
| test_dc_limits.py | `dc_limits.py` 70%·40%·합계 판정과 포털 매도·매수·부담금 3칸 환산, 환헤지 `hedgeMix`(참고 목표, 판정 무관) |
| test_index_status.py | `index_status.py` 지수 수집 full/partial/none·7일 신선도 |
| test_claim_status.py | `claim_status.py` 주장 종류별 출처 기준(공식 사실=발표 기관 1차 출처, 재게시·비발표기관·오래된 조회·값 충돌은 실패, 해석은 방향만, 표시 금리=검증 값)과 리더십 `decision_usable` |
| test_fund_score.py | `fund_score.py` 펀드 점수: 과거 수익률은 점수에 없음(같은 지수면 싼 펀드가 이김, 수익률을 바꿔도 점수 불변), 섹터 테마만 분산 감점, 규모는 청산 위험 문턱만이라 더 크고 비싼 펀드가 싼 펀드를 이기지 못함, 보수는 구간 없이 연속 |
| test_verify_no_pii.py | `verify_no_pii.sh` 공개 경로의 개인 보유정보 검사 |
| test_fetch_latest_proposal.py | 상품제안서 게시판 파싱·최신월 선택(오프라인 픽스처) |
| test_tax_rule_regressions.py | 연금 인출순서·분리과세 선택·퇴직소득 원천징수 적용비율 |
| test_policy_alloc.py | `policy_alloc.py`·`tilt_validation.py`: 같은 입력 같은 바이트, 과거 수익률 무시, 위험 목표 한도 초과·단일 40% 초과는 오류(재시도 없음), 지표 출처 규칙(공식 1차 / 시장 독립 2곳 같은 기준일·같은 값 / 계산 지표는 구성 지표 둘 다), 결측은 지난 신호 유지, 6개월 주기·2%p 유지·경보, 기울기 상한·위험 합 불변, 단기 기울이기 기본 꺼짐과 검증 보고서·규칙·코드 해시 관문, 워크포워드가 같은 달 자료를 못 봄, 밴드 안 HOLD·밖 안전한 정수 매도만, 70% 근처 좁은 밴드, 정책 밖 펀드, 제안을 보유로 넣으면 거부, 오래된·미래 기준일 관측은 결측, 같은 등록 도메인 두 출처는 한 곳, 경보 확인(`--acknowledge-alerts`), 검증 보고서는 비용·검증 기준·기본 비중까지 묶임, 자료 빈 달은 검증 표본에서 뺌, 단기 설정만 바뀌면 장기 결정 유지, 적격TDF 면제 묶음(70% 분자 제외, 위험 이동에서 고정, TDF는 면제 묶음에만·면제 묶음은 TDF만) |
| test_agent_tools.py | 플러그인 에이전트·스킬 frontmatter `tools`와 본문 호출이 실제 있는 도구 이름만 쓰는지(거시 실패 원인 H1) |

## RUN

`python3 -m pytest` (repo root) → 371 passed (2026-11-18 기준, 세법·정책 배분 테스트 포함).

## PATH CONFIGURATION

스크립트 경로는 `.claude/plugins/...` 전체를 사용하며, `conftest.py:14` (`SCRIPTS_DIR`) 및 `test_cli.py:11` (`SCRIPT`)에 올바르게 설정되어 있습니다. 저장소 루트에서 실행 시 모든 테스트가 정상적으로 수집(collection)되고 통과합니다.

## CONVENTIONS

- 픽스처 fund 코드/이름은 실제 적격TDF 사례(KB/삼성/신한/미래에셋/한국투자) 기반 — adversarial(연도 인접·share class 충돌·헤지 불일치) 검증용. 임의 변경 금지.
- 단위 테스트는 `funds/` 실데이터를 읽지 않음 — fixture 슬라이스만 사용. 예외: `test_cli.py`·`test_integration.py`는 저장된 실데이터가 `funds/all/` 권위 값과 맞는지 본다(고정 리터럴 대신 권위 파일과 비교 — 월간 갱신에도 깨지지 않게).
