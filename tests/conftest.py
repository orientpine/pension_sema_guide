"""Shared pytest fixtures for TDF deterministic-enrichment tests.

Adds the data-updater scripts dir to sys.path so `update_tdf_data` is importable
as a module, and exposes small in-memory authoritative slices plus the repo root.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "investments-portfolio" / "skills" / "data-updater" / "scripts"

# Make update_tdf_data importable as a top-level module.
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


def _fund(code, name, risk_level, r6m, r1y, r3y):
    return {
        "fundCode": code,
        "name": name,
        "company": "",
        "riskLevel": risk_level,
        "riskName": "",
        "return10y": "",
        "return7y": "",
        "return5y": "",
        "return3y": r3y,
        "return1y": r1y,
        "return6m": r6m,
        "netAssets": "0",
        "inceptionDate": "",
        "isAffiliate": False,
        "fundType": "",
    }


def _fee(code, name, total):
    return {"fundCode": code, "fundName": name, "totalFee": total, "annualCost": "0"}


@pytest.fixture
def auth_data():
    """Tiny authoritative all_fund_data slice covering the adversarial cases."""
    funds = [
        # KB qualified TDF 2055 UH (S1)
        _fund("K55223D29737", "KB온국민적격TDF2055증권자투자신탁(주식혼합-재간접형)(UH)C-퇴직e", 3, "27.38", "52.53", "105.28"),
        # 삼성 EMP 2055 (UNKNOWN_43 target)
        _fund("K55105D43299", "삼성글로벌EMP적격TDF2055증권자투자신탁[주식혼합-재간접형]_Cpe(퇴직연금)", 3, "18.86", "32.68", "66.21"),
        # 신한 빠른대응 2040 C-re, vehicle = 증권자투자신탁 (S4 / UNKNOWN_18 target)
        _fund("K55210D57370", "신한빠른대응적격TDF2040증권자투자신탁(H)[주식혼합-재간접형](종류C-re)", 3, "21.82", "39.20", "67.37"),
        # 신한 마음편한 2030 C-r ONLY (S2 — no C-p variant)
        _fund("K55210BR6431", "신한마음편한적격TDF2030증권투자신탁[주식혼합-재간접형](종류C-r)", 3, "15.59", "27.96", "52.93"),
        # adjacent year 2045 (S5 — must NOT match a 2040 query)
        _fund("K55301BU5479", "미래에셋전략배분적격TDF2045혼합자산자투자신탁종류C-P2e", 3, "19.06", "37.55", "71.97"),
        # share-class C-P2e (S5 — must NOT match C-Pe2)
        _fund("K55301BT5183", "미래에셋ETF로자산배분적격TDF2045증권자투자신탁(주식혼합-재간접형)종류C-P2e", 2, "19.23", "36.70", "69.27"),
        # hedge UH 2060 (S5 — must NOT match an (H) query)
        _fund("K55101DR7009", "한국투자적격TDF알아서2060증권자투자신탁UH(주식혼합-재간접형)(C-Re)", 3, "25.43", "47.85", "94.20"),
    ]
    return {"_meta": {"version": "2026-06-01"}, "funds": funds}


@pytest.fixture
def auth_fees():
    fees = {
        "K55223D29737": _fee("K55223D29737", "KB온국민적격TDF2055증권자투자신탁(주식혼합-재간접형)(UH)C-퇴직e", "0.69"),
        "K55105D43299": _fee("K55105D43299", "삼성글로벌EMP적격TDF2055증권자투자신탁[주식혼합-재간접형]_Cpe(퇴직연금)", "0.66"),
        "K55210D57370": _fee("K55210D57370", "신한빠른대응적격TDF2040증권자투자신탁(H)[주식혼합-재간접형](종류C-re)", "0.90"),
        "K55210BR6431": _fee("K55210BR6431", "신한마음편한적격TDF2030증권투자신탁[주식혼합-재간접형](종류C-r)", "0.77"),
        "K55301BU5479": _fee("K55301BU5479", "미래에셋전략배분적격TDF2045혼합자산자투자신탁종류C-P2e", "0.82"),
        "K55301BT5183": _fee("K55301BT5183", "미래에셋ETF로자산배분적격TDF2045증권자투자신탁(주식혼합-재간접형)종류C-P2e", "0.82"),
        "K55101DR7009": _fee("K55101DR7009", "한국투자적격TDF알아서2060증권자투자신탁UH(주식혼합-재간접형)(C-Re)", "1.12"),
    }
    return {"_meta": {"version": "2026-06-01"}, "fees": fees}
