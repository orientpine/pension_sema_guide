"""--from-proposal: TDF rows re-based on the monthly 상품제안서 (all_fund_data) base date."""
from update_tdf_data import refresh_from_proposal

TDF = {
    "_meta": {"version": "2026-06-04", "freshnessThresholdDays": 30},
    "funds": [
        {"fundCode": "K55223D29737", "name": "KB 온국민 적격TDF 2055", "targetYear": 2055,
         "riskLevel": 2, "riskName": "높은위험", "return1m": "13.87", "return3m": "21.31",
         "return6m": "27.38", "return1y": "52.53", "return2y": "66.64", "return3y": "105.28",
         "returnSinceInception": "28.24", "netAssets": "272500638"},
        {"fundCode": "K00000000000", "name": "상품제안서에 없는 TDF 2040", "targetYear": 2040,
         "return6m": "1.00", "return1y": "2.00", "return3y": "3.00", "return1m": "0.5"},
    ],
}
ALL = {
    "_meta": {"version": "2026-10-30", "sourceFile": "26년11월_상품제안서_퇴직연금(DCIRP).csv"},
    "funds": [
        {"fundCode": "K55223D29737", "riskLevel": 3, "riskName": "다소높은위험",
         "return6m": "-5.71", "return1y": "6.56", "return3y": "18.99", "netAssets": "71720000"},
    ],
}


def test_rebases_numbers_on_proposal_and_blanks_absent_horizons():
    out = refresh_from_proposal(TDF, ALL)
    row = out["funds"][0]
    assert out["_meta"]["version"] == "2026-10-30"
    assert (row["return6m"], row["return1y"]) == ("-5.71", "6.56")
    assert row["return3y"] == "68.47"  # (1.1899^3 - 1) * 100, 연환산 -> 3년 누적
    assert (row["riskLevel"], row["riskName"]) == (3, "다소높은위험")
    assert row["netAssets"] == "717200000"  # 7172억원 -> 천원
    assert all(row[f] == "" for f in ("return1m", "return3m", "return2y", "returnSinceInception"))


def test_row_missing_from_proposal_keeps_no_stale_numbers():
    out = refresh_from_proposal(TDF, ALL)
    row = out["funds"][1]
    assert out["_meta"]["notInProposal"] == ["K00000000000"]
    assert all(row[f] == "" for f in ("return1m", "return6m", "return1y", "return3y"))
