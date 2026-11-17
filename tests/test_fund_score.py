"""소유자 지침 no-performance-chasing(2026-11-18): 최근·과거 성적으로 펀드를 고르지 않는다.

같은 지수를 따르는 펀드라면 과거 수익률이 좋았던 비싼 펀드가 싼 펀드를 이기면 안 된다.
"""

import importlib.util
import sys
from decimal import Decimal as D
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[1]
          / ".claude/plugins/investments-portfolio/skills/fund-selection-criteria/scripts/fund_score.py")
spec = importlib.util.spec_from_file_location("fund_score", SCRIPT)
fund_score = importlib.util.module_from_spec(spec)
sys.modules["fund_score"] = fund_score
spec.loader.exec_module(fund_score)

CLASSIFICATION = {"region": "europe", "themes": []}


def fund(name: str, return3y: str, net_assets: str = "60000000") -> dict:
    return {"name": name, "return3y": return3y, "return1y": return3y, "return6m": return3y,
            "netAssets": net_assets, "riskLevel": 2, "inceptionDate": "20150101"}


def total(row: dict, fee: str) -> int:
    return fund_score.score(row, CLASSIFICATION, D(fee), 2)["total"]


def test_strong_past_returns_do_not_beat_a_cheaper_fund_on_the_same_index() -> None:
    expensive_hot = total(fund("A유럽인덱스", "35"), "1.06")
    cheap_cold = total(fund("B유럽인덱스", "-3"), "0.63")
    assert cheap_cold > expensive_hot


def test_score_does_not_move_with_past_returns() -> None:
    assert total(fund("C유럽인덱스", "80"), "0.9") == total(fund("C유럽인덱스", "-40"), "0.9")


def test_no_weight_is_given_to_returns() -> None:
    assert sum(fund_score.WEIGHTS.values()) == 100
    assert not [key for key in fund_score.WEIGHTS if "return" in key]


def test_index_or_general_labels_are_not_treated_as_sector_concentration() -> None:
    row = fund("D유럽인덱스", "0")
    broad = fund_score.score(row, {"region": "europe", "themes": ["index", "general"]}, D("1.0"), 2)
    sector = fund_score.score(row, {"region": "europe", "themes": ["semiconductor"]}, D("1.0"), 2)
    single = fund_score.score(row, {"region": "vietnam", "themes": ["index"]}, D("1.0"), 2)
    assert broad["parts"]["diversification"] > single["parts"]["diversification"] > sector["parts"]["diversification"]
