"""CLI --fees enrichment: clean data exits 0; an unresolvable row exits 2 (non-silent)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude" / "plugins" / "investments-portfolio" / "skills" / "data-updater" / "scripts" / "update_tdf_data.py"


@pytest.fixture
def staged(tmp_path):
    funds = tmp_path / "funds"
    funds.mkdir()
    shutil.copy(REPO / "funds" / "tdf_data.json", funds / "tdf_data.json")
    shutil.copy(REPO / "funds" / "tdf_fees.json", funds / "tdf_fees.json")
    return funds


def _inject_unresolvable(funds):
    dp, fp = funds / "tdf_data.json", funds / "tdf_fees.json"
    d = json.loads(dp.read_text(encoding="utf-8"))
    f = json.loads(fp.read_text(encoding="utf-8"))
    name = "존재하지않는운용적격TDF9999증권투자신탁[주식혼합-재간접형](종류C-zz)"
    d["funds"].append({"fundCode": "UNKNOWN_TEST", "name": name, "company": "", "targetYear": 9999,
                       "hedge": None, "riskLevel": 3, "return6m": "", "return1y": "", "return3y": ""})
    f["fees"]["UNKNOWN_TEST"] = {"fundCode": "UNKNOWN_TEST", "fundName": name, "totalFee": "", "ter": ""}
    dp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    fp.write_text(json.dumps(f, ensure_ascii=False), encoding="utf-8")


def _run(out_path, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--fees", "--output", str(out_path),
         "--all-dir", str(REPO / "funds" / "all"), *extra],
        capture_output=True, text=True, cwd=str(REPO),
    )


def test_fees_clean_data_exits_0(staged):
    proc = _run(staged / "tdf_data.json")
    assert proc.returncode == 0, proc.stderr
    assert "INFO" in proc.stderr


def test_fees_unresolvable_exits_2_with_warning(staged):
    _inject_unresolvable(staged)
    proc = _run(staged / "tdf_data.json")
    assert proc.returncode == 2, proc.stderr
    assert "WARNING" in proc.stderr
    assert "UNKNOWN_TEST" in proc.stderr


def test_allow_unresolved_exits_0(staged):
    _inject_unresolvable(staged)
    proc = _run(staged / "tdf_data.json", "--allow-unresolved")
    assert proc.returncode == 0, proc.stderr


def test_fees_writes_corrected_files(staged):
    _run(staged / "tdf_data.json")
    fees = json.loads((staged / "tdf_fees.json").read_text(encoding="utf-8"))["fees"]
    assert fees["K55223D29737"]["totalFee"] == "0.69"
    assert "K55210BR6431" in fees and "UNKNOWN_52" not in fees
