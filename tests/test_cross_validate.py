"""RED: soft cross-validation of overlapping returns + riskLevel (Oracle design F)."""
from update_tdf_data import cross_validate_tdf_row


def _auth(r6m, r1y, r3y, risk):
    return {"return6m": r6m, "return1y": r1y, "return3y": r3y, "riskLevel": risk}


def _tdf(r6m, r1y, r3y, risk):
    return {"return6m": r6m, "return1y": r1y, "return3y": r3y, "riskLevel": risk}


def test_returns_within_tolerance_no_warning():
    w = cross_validate_tdf_row(_tdf("27.38", "52.53", "105.28", 3), _auth("27.40", "52.50", "105.30", 3))
    assert w == []


def test_return_diff_over_tolerance_soft_warning():
    w = cross_validate_tdf_row(_tdf("27.38", "52.53", "105.28", 3), _auth("27.40", "55.00", "105.30", 3))
    sev = [x["severity"] for x in w]
    assert "soft" in sev
    assert all(s != "needsReview" for s in sev)  # returns are soft only


def test_risk_level_mismatch_needs_review():
    w = cross_validate_tdf_row(_tdf("27.38", "52.53", "105.28", 2), _auth("27.38", "52.53", "105.28", 3))
    sev = [x["severity"] for x in w]
    assert "needsReview" in sev
