"""RED: deterministic name->code resolution with guard rails (Oracle design A)."""
from update_tdf_data import build_authoritative_index, resolve_tdf_row


def _row(name, year=None, hedge=None):
    return {"fundCode": "UNKNOWN_X", "name": name, "targetYear": year, "hedge": hedge}


def test_resolve_emp_2055_exact(auth_data, auth_fees):
    idx = build_authoritative_index(auth_data, auth_fees)
    r = resolve_tdf_row(
        _row("삼성 글로벌 EMP 적격 TDF 2055 증권자투자신탁[주식혼합-재간접형]_Cpe(퇴직연금)", 2055, None),
        43, idx,
    )
    assert r["status"] == "resolved"
    assert r["fundCode"] == "K55105D43299"
    assert r["needsReview"] is False


def test_resolve_vehicle_variant_needs_review(auth_data, auth_fees):
    idx = build_authoritative_index(auth_data, auth_fees)
    # tdf uses 증권투자신탁; authoritative uses 증권자투자신탁
    r = resolve_tdf_row(
        _row("신한빠른대응적격TDF2040증권투자신탁(H)[주식혼합-재간접형](종류C-re)", 2040, "H"),
        18, idx,
    )
    assert r["status"] == "resolved"
    assert r["fundCode"] == "K55210D57370"
    assert r["needsReview"] is True
    assert "vehicle" in r["differences"]


def test_unresolved_c_p_only_c_r_with_candidate(auth_data, auth_fees):
    idx = build_authoritative_index(auth_data, auth_fees)
    r = resolve_tdf_row(
        _row("신한마음편한적격TDF2030증권투자신탁[주식혼합-재간접형](종류C-p)", 2030, None),
        52, idx,
    )
    assert r["status"] == "unresolved"
    assert r["fundCode"] is None
    cand = [c["fundCode"] for c in r["candidateCodes"]]
    assert "K55210BR6431" in cand, "the C-r class must be surfaced as a candidate, not auto-resolved"


def test_share_class_p2e_vs_pe2_not_resolved(auth_data, auth_fees):
    idx = build_authoritative_index(auth_data, auth_fees)
    r = resolve_tdf_row(
        _row("미래에셋ETF로자산배분적격TDF2045증권자투자신탁(주식혼합-재간접형)종류C-Pe2", 2045, None),
        99, idx,
    )
    assert r["status"] != "resolved"


def test_hedge_h_vs_uh_not_resolved(auth_data, auth_fees):
    idx = build_authoritative_index(auth_data, auth_fees)
    # authoritative 2060 is UH; query is (H)
    r = resolve_tdf_row(
        _row("한국투자적격TDF알아서2060증권자투자신탁(H)(주식혼합-재간접형)(C-Re)", 2060, "H"),
        98, idx,
    )
    assert r["status"] != "resolved"


def test_adjacent_year_2040_not_matched_to_2045(auth_data, auth_fees):
    idx = build_authoritative_index(auth_data, auth_fees)
    r = resolve_tdf_row(
        _row("미래에셋전략배분적격TDF2040혼합자산자투자신탁종류C-P2e", 2040, None),
        97, idx,
    )
    assert r["status"] != "resolved"
