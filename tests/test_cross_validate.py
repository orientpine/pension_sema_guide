"""Soft cross-validation of overlapping returns + riskLevel.

Unit contract under test: auth(all_fund_data) 3Y is 연환산(annualized), tdf 3Y is
누적(cumulative). cross_validate_tdf_row normalizes tdf 누적→연환산 before thresholding;
6M/1Y are 누적 on both sides. Tolerance is 5.0%p (absorbs base-date drift).
"""
from update_tdf_data import cross_validate_tdf_row


def _auth(r6m, r1y, r3y, risk):
    return {"return6m": r6m, "return1y": r1y, "return3y": r3y, "riskLevel": risk}


def _tdf(r6m, r1y, r3y, risk):
    return {"return6m": r6m, "return1y": r1y, "return3y": r3y, "riskLevel": risk}


def test_returns_within_tolerance_no_warning():
    # tdf 3Y=105.28 누적 -> 27.09 연환산 vs auth 25.92 연환산 = 1.17%p < tol; 6M/1Y drift < tol
    w = cross_validate_tdf_row(
        _tdf("27.38", "52.53", "105.28", 3), _auth("25.55", "49.04", "25.92", 3)
    )
    assert w == []


def test_cumulative_vs_annualized_3y_no_false_warning():
    # regression: the original bug compared 누적 105.28 against 연환산 25.92 (≈79%p) and
    # warned on every TDF. After normalization this must NOT raise a return3y warning.
    w = cross_validate_tdf_row(
        _tdf("27.38", "52.53", "105.28", 3), _auth("27.38", "52.53", "25.92", 3)
    )
    assert all(x["field"] != "return3y" for x in w)


def test_return_diff_over_tolerance_soft_warning():
    # 1Y 52.53 vs 60.00 (both 누적) = 7.47%p > 5.0 tol -> soft, returns are never needsReview
    w = cross_validate_tdf_row(
        _tdf("27.38", "52.53", "105.28", 3), _auth("27.40", "60.00", "25.92", 3)
    )
    sev = [x["severity"] for x in w]
    assert "soft" in sev
    assert all(s != "needsReview" for s in sev)


def test_gross_3y_mismatch_still_warns_after_normalization():
    # tdf 3Y=105.28 -> 27.09 연환산; auth 40.00 연환산 -> 12.91%p > tol -> genuine soft warning
    w = cross_validate_tdf_row(
        _tdf("27.38", "52.53", "105.28", 3), _auth("27.38", "52.53", "40.00", 3)
    )
    assert any(x["field"] == "return3y" and x["severity"] == "soft" for x in w)


def test_risk_level_mismatch_needs_review():
    w = cross_validate_tdf_row(
        _tdf("27.38", "52.53", "105.28", 2), _auth("25.55", "49.04", "25.92", 3)
    )
    sev = [x["severity"] for x in w]
    assert "needsReview" in sev
