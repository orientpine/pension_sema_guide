"""From-scratch enrich_tdf_rows over synthetic UNKNOWN rows + auth fixtures.

Proves the resolve/migrate/needsReview/unresolved behavior deterministically without
depending on the mutable real data files, and asserts re-run idempotency (recompute,
not preserve) of the per-run _meta counts.
"""
import copy

from update_tdf_data import enrich_tdf_rows


def _row(code, name, year, hedge, risk=3):
    return {
        "fundCode": code, "name": name, "company": "", "targetYear": year,
        "hedge": hedge, "riskLevel": risk,
        "return6m": "", "return1y": "", "return3y": "",
    }


def _fee(code, name, total=""):
    return {"fundCode": code, "fundName": name, "totalFee": total, "ter": ""}


EMP = "삼성 글로벌 EMP 적격 TDF 2055 증권자투자신탁[주식혼합-재간접형]_Cpe(퇴직연금)"
VEHICLE = "신한빠른대응적격TDF2040증권투자신탁(H)[주식혼합-재간접형](종류C-re)"
CP = "신한마음편한적격TDF2030증권투자신탁[주식혼합-재간접형](종류C-p)"
KB = "KB온국민적격TDF2055증권자투자신탁(주식혼합-재간접형)(UH)C-퇴직e"


def _synthetic():
    tdf_data = {"_meta": {"recordCount": 4}, "funds": [
        _row("UNKNOWN_1", EMP, 2055, None),
        _row("UNKNOWN_2", VEHICLE, 2040, "H"),
        _row("UNKNOWN_3", CP, 2030, None),
        _row("K55223D29737", KB, 2055, "UH"),
    ]}
    tdf_fees = {"_meta": {"recordCount": 4}, "fees": {
        "UNKNOWN_1": _fee("UNKNOWN_1", EMP),
        "UNKNOWN_2": _fee("UNKNOWN_2", VEHICLE),
        "UNKNOWN_3": _fee("UNKNOWN_3", CP),
        "K55223D29737": _fee("K55223D29737", KB, "0.605"),  # wrong fee to be corrected
    }}
    return tdf_data, tdf_fees


def test_resolves_migrates_and_corrects(auth_data, auth_fees):
    tdf_data, tdf_fees = _synthetic()
    res = enrich_tdf_rows(tdf_data, tdf_fees, auth_data, auth_fees)
    fees = res["tdf_fees"]["fees"]

    assert res["summary"]["resolvedUnknownCount"] == 2
    assert res["summary"]["unresolvedCount"] == 1
    assert res["exit_code"] == 2

    # migrations: placeholders rewritten to real codes
    assert "K55105D43299" in fees and "UNKNOWN_1" not in fees
    assert "K55210D57370" in fees and "UNKNOWN_2" not in fees
    # unresolved C-p kept as placeholder with empty fee
    assert "UNKNOWN_3" in fees and fees["UNKNOWN_3"]["totalFee"] == ""
    # already-coded wrong fee overwritten by authoritative value
    assert fees["K55223D29737"]["totalFee"] == "0.69"


def test_vehicle_resolution_flagged_needs_review(auth_data, auth_fees):
    tdf_data, tdf_fees = _synthetic()
    res = enrich_tdf_rows(tdf_data, tdf_fees, auth_data, auth_fees)
    nr = res["tdf_data"]["_meta"]["needsReview"]
    assert any(item["fundCode"] == "K55210D57370" for item in nr)


def test_unresolved_candidate_surfaced(auth_data, auth_fees):
    tdf_data, tdf_fees = _synthetic()
    res = enrich_tdf_rows(tdf_data, tdf_fees, auth_data, auth_fees)
    unresolved = res["tdf_data"]["_meta"]["unresolved"]
    assert len(unresolved) == 1
    assert any(c["fundCode"] == "K55210BR6431" for c in unresolved[0]["candidateCodes"])


def test_rerun_is_idempotent_and_recomputes(auth_data, auth_fees):
    tdf_data, tdf_fees = _synthetic()
    first = enrich_tdf_rows(tdf_data, tdf_fees, auth_data, auth_fees)
    second = enrich_tdf_rows(
        copy.deepcopy(first["tdf_data"]), copy.deepcopy(first["tdf_fees"]), auth_data, auth_fees
    )
    # nothing left to resolve on the second pass -> recomputed (not stale-preserved)
    assert second["summary"]["resolvedUnknownCount"] == 0
    # the unresolvable C-p row persists as a gap; exit stays 2
    assert second["summary"]["unresolvedCount"] == 1
    assert second["exit_code"] == 2
    # data stays correct across the idempotent re-run
    assert second["tdf_fees"]["fees"]["K55223D29737"]["totalFee"] == "0.69"
    assert second["tdf_fees"]["fees"]["K55105D43299"]["fundCode"] == "K55105D43299"


def test_code_name_mismatch_surfaced(auth_data, auth_fees):
    tdf_data = {"_meta": {}, "funds": [
        {"fundCode": "K55210BR6431", "name": CP, "company": "", "targetYear": 2030,
         "hedge": None, "riskLevel": 3, "return6m": "", "return1y": "", "return3y": ""},
    ]}
    tdf_fees = {"_meta": {}, "fees": {"K55210BR6431": _fee("K55210BR6431", CP)}}
    res = enrich_tdf_rows(tdf_data, tdf_fees, auth_data, auth_fees)

    assert res["summary"]["codeNameMismatchCount"] == 1
    mismatch = res["tdf_data"]["_meta"]["codeNameMismatch"]
    assert mismatch[0]["fundCode"] == "K55210BR6431"
    assert "C-r" in mismatch[0]["authoritativeName"]


def test_already_coded_vehicle_flags_needs_review(auth_data, auth_fees):
    tdf_data = {"_meta": {}, "funds": [
        {"fundCode": "K55210D57370", "name": VEHICLE, "company": "", "targetYear": 2040,
         "hedge": "H", "riskLevel": 3, "return6m": "", "return1y": "", "return3y": ""},
    ]}
    tdf_fees = {"_meta": {}, "fees": {"K55210D57370": _fee("K55210D57370", VEHICLE)}}
    res = enrich_tdf_rows(tdf_data, tdf_fees, auth_data, auth_fees)
    nr = res["tdf_data"]["_meta"]["needsReview"]
    assert any(i["fundCode"] == "K55210D57370" and "vehicle" in i["differences"] for i in nr)


def test_already_coded_vehicle_flags_needs_review(auth_data, auth_fees):
    tdf_data = {"_meta": {}, "funds": [
        {"fundCode": "K55210D57370", "name": VEHICLE, "company": "", "targetYear": 2040,
         "hedge": "H", "riskLevel": 3, "return6m": "", "return1y": "", "return3y": ""},
    ]}
    tdf_fees = {"_meta": {}, "fees": {"K55210D57370": _fee("K55210D57370", VEHICLE)}}
    res = enrich_tdf_rows(tdf_data, tdf_fees, auth_data, auth_fees)

    nr = res["tdf_data"]["_meta"]["needsReview"]
    assert any(i["fundCode"] == "K55210D57370" and "vehicle" in i["differences"] for i in nr)
