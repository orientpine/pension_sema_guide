"""RED: authoritative fee reconciliation (Oracle design B/F)."""
from update_tdf_data import reconcile_fee


def test_reconcile_returns_string_value(auth_fees):
    r = reconcile_fee("K55223D29737", auth_fees)
    assert r["status"] == "verified"
    assert r["value"] == "0.69"
    assert isinstance(r["value"], str)


def test_reconcile_missing_code(auth_fees):
    r = reconcile_fee("K_DOES_NOT_EXIST", auth_fees)
    assert r["status"] == "missing"
    assert r["value"] == ""


def test_reconcile_present_but_empty_fee_is_missing():
    fees = {"fees": {"K_EMPTY": {"fundCode": "K_EMPTY", "fundName": "x", "totalFee": "", "annualCost": "0"}}}
    r = reconcile_fee("K_EMPTY", fees)
    assert r["status"] == "missing"
    assert r["value"] == ""
