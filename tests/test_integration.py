"""Regression: assert the PERSISTED real tdf_*.json reflect the deterministic enrichment.

These assertions are idempotent-stable (data values + unresolved gap), independent of
how many times `--fees` has run. The from-scratch enrichment algorithm (resolve counts,
vehicle needsReview, key migration, re-run idempotency) is proven in test_enrich.py.
"""
import json

import pytest

# Codes whose fee was corrected to the official CSV (2026-06). The persisted fee must keep
# following funds/all/all_fund_fees.json as the monthly CSV moves.
FEE_FIXES = {
    "K55223D29737", "K55101DR7009", "K55213D64958", "K55301BU5479", "K55301BU6253",
    "K55301BT5183", "K55105CK1592", "K55301BU6139", "K55105D34223", "K55301BS2942",
}
MIGRATED_CODES = {
    "K55105D43299", "K55105D32763", "K55105D43000", "K55105D42499",
    "K55105D41665", "K55101BT7439", "K55105D38935", "K55210D57370",
    "K55210BR6431",  # the former C-p typo row, corrected to C-r
}
RESOLVED_PLACEHOLDERS = {
    "UNKNOWN_18", "UNKNOWN_43", "UNKNOWN_46", "UNKNOWN_48",
    "UNKNOWN_53", "UNKNOWN_59", "UNKNOWN_69", "UNKNOWN_72", "UNKNOWN_52",
}


@pytest.fixture
def tdf_fees(repo_root):
    return json.loads((repo_root / "funds" / "tdf_fees.json").read_text(encoding="utf-8"))


@pytest.fixture
def auth_fee(repo_root):
    fees = json.loads((repo_root / "funds" / "all" / "all_fund_fees.json").read_text(encoding="utf-8"))["fees"]
    return lambda code: fees[code]["totalFee"]


@pytest.fixture
def tdf_data(repo_root):
    return json.loads((repo_root / "funds" / "tdf_data.json").read_text(encoding="utf-8"))


def test_ten_fee_corrections_persisted(tdf_fees, auth_fee):
    fees = tdf_fees["fees"]
    for code in FEE_FIXES:
        assert fees[code]["totalFee"] == auth_fee(code)
        assert isinstance(fees[code]["totalFee"], str)


def test_unknown_keys_migrated(tdf_fees):
    fees = tdf_fees["fees"]
    for code in MIGRATED_CODES:
        assert code in fees and fees[code]["fundCode"] == code
    for placeholder in RESOLVED_PLACEHOLDERS:
        assert placeholder not in fees


def test_cp_typo_resolved_to_cr(tdf_fees, auth_fee):
    fees = tdf_fees["fees"]
    assert "UNKNOWN_52" not in fees
    assert fees["K55210BR6431"]["totalFee"] == auth_fee("K55210BR6431")
    assert fees["K55210BR6431"]["feeVerification"]["status"] == "verified"


def test_no_unresolved_after_typo_fix(tdf_data):
    meta = tdf_data["_meta"]
    assert meta["unresolvedFundCodeCount"] == 0
    assert meta["unresolved"] == []
    assert meta["missing"] == []


def test_provenance_authoritative(tdf_fees):
    fv = tdf_fees["fees"]["K55223D29737"]["feeVerification"]
    assert fv["status"] == "verified"
    assert fv["authority"] == "official-csv"
    assert fv["agree"] is True


def test_record_count_and_order(tdf_data, tdf_fees):
    assert len(tdf_data["funds"]) == 75
    assert tdf_fees["_meta"]["recordCount"] == 75
    assert tdf_data["funds"][0]["fundCode"] == "K55223D29737"


def test_2030_row_resolved_and_no_c_p_left(tdf_data):
    assert not any("종류C-p" in f["name"] for f in tdf_data["funds"])
    row = [f for f in tdf_data["funds"] if "마음편한" in f["name"] and "2030" in f["name"]]
    assert len(row) == 1
    assert row[0]["fundCode"] == "K55210BR6431"
    assert "종류C-r" in row[0]["name"]


def test_code_name_mismatch_surfaced_as_list(tdf_data):
    cnm = tdf_data["_meta"]["codeNameMismatch"]
    assert isinstance(cnm, list)
    assert tdf_data["_meta"]["enrichment"]["codeNameMismatchCount"] == len(cnm)
