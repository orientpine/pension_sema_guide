"""R05: 지수 결측은 실패 종료 대신 사용 가능한 범위를 반환한다."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / ".claude/plugins/macro-analysis/scripts/index_status.py"
NAMES = ("KOSPI", "KOSDAQ", "S&P 500", "NASDAQ", "USD/KRW", "EUR/KRW", "JPY/KRW")


def series(name: str, date: str = "2026-11-16") -> dict:
    """독립 출처 세 곳이 동일 기준일에 확인한 합성 시리즈."""
    return {
        "name": name, "value": 100, "verified": True,
        "sources": [
            {"url": f"https://source{i}.example/quote", "observed_value": 100,
             "date": date, "original_text": f"{date}: 100"}
            for i in range(3)
        ],
    }


def run_status(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess:
    path = tmp_path / "index-data.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path), "--as-of", "2026-11-17"],
        capture_output=True, text=True, check=False,
    )


@pytest.mark.parametrize("shape", ["list", "grouped", "keyed"])
@pytest.mark.parametrize("count,mode", [(7, "full"), (3, "partial"), (0, "none")])
def test_index_status_modes_for_both_schema_shapes(tmp_path: Path, shape: str, count: int, mode: str) -> None:
    rows = [series(name) for name in NAMES[:count]]
    indices = rows
    if shape == "grouped":
        indices = {"stock_indices": rows[:4], "currencies": rows[4:]}
    if shape == "keyed":
        indices = {row["name"]: row for row in rows}
    result = run_status(tmp_path, {"timestamp": "2026-11-16T22:04:23+09:00", "indices": indices})
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["mode"] == mode
    assert report["usable"] == list(NAMES[:count])
    assert report["missing"] == list(NAMES[count:])


@pytest.mark.parametrize("date,age,status,mode", [
    ("2026-11-10", 7, "verified", "partial"),
    ("2026-11-09", 8, "stale", "none"),
])
def test_index_status_stale_boundary_reports_age(tmp_path: Path, date: str, age: int, status: str, mode: str) -> None:
    result = run_status(tmp_path, {"indices": [series("KOSPI", date)]})
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["mode"] == mode
    assert report["series"]["KOSPI"]["status"] == status
    assert report["series"]["KOSPI"]["age_days"] == age


@pytest.mark.parametrize("defect", ["unverified", "one_source", "disagreement", "duplicate_source", "future", "no_quote", "mixed_dates"])
def test_index_status_rejects_unusable_verification(tmp_path: Path, defect: str) -> None:
    row = series("KOSPI")
    if defect == "unverified":
        row["verified"] = False
    if defect == "one_source":
        row["sources"] = row["sources"][:1]
    if defect == "disagreement":
        row["sources"][0]["observed_value"] = 102
    if defect == "duplicate_source":
        row["sources"][0]["url"] = row["sources"][1]["url"]
    if defect == "future":
        row = series("KOSPI", "2026-11-18")
    if defect == "no_quote":
        del row["sources"][0]["original_text"]
    if defect == "mixed_dates":
        row["sources"][0]["date"] = "2026-11-15"
    result = run_status(tmp_path, {"indices": [row]})
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["mode"] == "none"
    assert report["series"]["KOSPI"]["status"] == "missing"


@pytest.mark.parametrize("content", ["{", "[]"])
def test_index_status_unreadable_input_is_nonzero(tmp_path: Path, content: str) -> None:
    path = tmp_path / "broken.json"
    path.write_text(content, encoding="utf-8")
    result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, check=False)
    assert result.returncode != 0
