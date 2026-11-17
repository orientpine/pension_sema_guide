"""update_tdf_data.py: 적격 근거 없는 TDF는 면제하지 않음(04), --input 표의 기준일은 입력값(05)."""
import json
import sys

import pytest

import update_tdf_data
from update_tdf_data import parse_tdf_table, refresh_from_proposal

QUALIFIED = "KB 온국민 적격TDF 2055 증권 자투자신탁(주식혼합-재간접형)(UH) C-퇴직e"
NOT_QUALIFIED_BOND_MIXED = "KB온국민TDF2020증권투자신탁(채권혼합-재간접형)C-퇴직e"
NOT_QUALIFIED_EQUITY_MIXED = "가상운용TDF2050증권자투자신탁(주식혼합-재간접형)C-e"


def _row(n, name):
    return f"{n}. {name} | 다소높은위험3 | 1.00 | 2.00 | 3.00 | 4.00 | 5.00 | 6.00 | 7.00 | 1000 | 가상운용"


TABLE = "\n".join(
    _row(i + 1, name) for i, name in enumerate([QUALIFIED, NOT_QUALIFIED_BOND_MIXED, NOT_QUALIFIED_EQUITY_MIXED])
)


def test_04_tdf_without_qualification_evidence_is_not_exempt():
    rows = {r["name"]: r for r in parse_tdf_table(TABLE)}
    assert rows[QUALIFIED]["tdfQualified"] is True
    assert rows[NOT_QUALIFIED_BOND_MIXED]["tdfQualified"] is False
    assert rows[NOT_QUALIFIED_EQUITY_MIXED]["tdfQualified"] is False
    assert rows[NOT_QUALIFIED_EQUITY_MIXED].get("riskStatus") == "risk"


def test_04_proposal_refresh_rederives_stored_true_without_evidence():
    stored = {
        "_meta": {"version": "2026-06-04"},
        "funds": [
            {"fundCode": "K1", "name": NOT_QUALIFIED_EQUITY_MIXED, "tdfQualified": True, "targetYear": 2050},
            {"fundCode": "K2", "name": QUALIFIED, "tdfQualified": True, "targetYear": 2055},
        ],
    }
    out = refresh_from_proposal(stored, {"_meta": {"version": "2026-10-30"}, "funds": []})
    by_code = {f["fundCode"]: f for f in out["funds"]}
    assert by_code["K1"]["tdfQualified"] is False
    assert by_code["K2"]["tdfQualified"] is True


def _run_cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["update_tdf_data.py", *args])
    return update_tdf_data.main()


def test_05_table_input_requires_base_date_and_writes_nothing(tmp_path, monkeypatch):
    src = tmp_path / "tdf-raw.md"
    src.write_text(TABLE, encoding="utf-8")
    out = tmp_path / "tdf_data.json"
    assert _run_cli(monkeypatch, "--input", str(src), "--output", str(out)) == 2
    assert not out.exists()


@pytest.mark.parametrize("base_date,band_2055", [("2026-10-30", [25, 35]), ("2030-01-31", [30, 40])])
def test_05_table_input_uses_given_base_date(tmp_path, monkeypatch, base_date, band_2055):
    src = tmp_path / "tdf-raw.md"
    src.write_text(TABLE, encoding="utf-8")
    out = tmp_path / "tdf_data.json"
    assert _run_cli(monkeypatch, "--input", str(src), "--output", str(out), "--base-date", base_date) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["_meta"]["version"] == base_date
    rows = {r["name"]: r for r in data["funds"]}
    # targetYear 2055, 은퇴 60세 -> 1995년생; 2026년 31세 -> [25, 35], 2030년 35세 -> [30, 40]
    assert rows[QUALIFIED]["recommendedAgeBand"] == band_2055
