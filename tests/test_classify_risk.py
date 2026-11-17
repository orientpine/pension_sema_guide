"""classify_funds.py: DC 70% 한도 위험자산·환헤지 분류 (R01·R02·R28).

기준: 퇴직연금감독규정 제11조 제1항(시행 2023-11-16) — 5호 주식 한도 50% 미만 증권형(투자부적격 30% 초과 제외),
6호 MMF만 100% 가능하고 나머지 펀드는 70% 한도에 산입한다. 펀드명은 상품제안서의 공개 펀드명이다.
"""
import json

import pytest

import classify_funds

GOLD_MINER_UH = "iM에셋월드골드증권자투자신탁(주식-재간접형)(UH)(C-Rpe)"
EQUITY_EMP = "KB글로벌테크놀로지EMP증권자투자신탁(주식-재간접형)C-퇴직e"
EQUITY_INCOME = "피델리티글로벌배당인컴증권자투자신탁(주식-재간접형)종류CP-e"
GOLD_SPECIAL = "미래에셋골드특별자산자투자신탁(금-재간접형)종류C-P2e"
MIXED_ASSET = "미래에셋평생소득TIF혼합자산자투자신탁종류C-P2e"
REIT_FOF = "하나글로벌리츠부동산자투자신탁[재간접형]ClassC-P2E"
BOND_MIXED = "트러스톤장기성장40퇴직연금증권자투자신탁[채권혼합]Ce클래스"
BOND_MIXED_HIGH_YIELD = "웰컴공모주하이일드증권투자신탁제3호[채권혼합]C-P2E"
BOND = "키움단기국공채증권자투자신탁 1[채권]C-P2e(퇴직연금)"
EQUITY_MIXED = "미래에셋퇴직연금배당커버드콜액티브증권자투자신탁 1(주식혼합)종류C-P2e"
SEMI_UH_BRACKET = "삼성글로벌반도체증권자투자신탁UH[주식]_Cpe(퇴직)"
SEMI_H_BRACKET = "삼성글로벌반도체증권자투자신탁H[주식]_Cpe(퇴직)"
ENERGY_H = "iM에셋월드에너지증권자투자신탁(주식-재간접형)(H)(C-Rpe)"
NO_HEDGE_MARK = "하나IT코리아증권자투자신탁 1[주식]ClassC-P2E"

ALL_NAMES = [
    GOLD_MINER_UH, EQUITY_EMP, EQUITY_INCOME, GOLD_SPECIAL, MIXED_ASSET, REIT_FOF, BOND_MIXED,
    BOND_MIXED_HIGH_YIELD, BOND, EQUITY_MIXED, SEMI_UH_BRACKET, SEMI_H_BRACKET, ENERGY_H, NO_HEDGE_MARK,
]


def _classify(tmp_path):
    funds = [{"fundCode": f"K{i:011d}", "name": n, "riskLevel": 3} for i, n in enumerate(ALL_NAMES)]
    (tmp_path / "fund_data.json").write_text(
        json.dumps({"_meta": {"version": "2026-10-30"}, "funds": funds}, ensure_ascii=False), encoding="utf-8"
    )
    classify_funds.main(str(tmp_path))
    return json.loads((tmp_path / "fund_classification.json").read_text(encoding="utf-8"))


def test_r01_equity_typed_funds_count_toward_70pct_limit(tmp_path):
    out = _classify(tmp_path)
    for name in (GOLD_MINER_UH, EQUITY_EMP, EQUITY_INCOME, EQUITY_MIXED):
        assert out[name]["riskAsset"] is True, name
        assert out[name].get("riskStatus") == "risk", name


def test_r01_non_securities_and_unknown_types_count_toward_limit(tmp_path):
    out = _classify(tmp_path)
    for name in (GOLD_SPECIAL, MIXED_ASSET):
        assert out[name]["riskAsset"] is True, name
        assert out[name].get("riskStatus") == "risk", name
    assert out[REIT_FOF]["riskAsset"] is True
    assert out[REIT_FOF].get("riskStatus") == "unverified"


def test_r02_uh_marks_are_unhedged_and_h_marks_hedged(tmp_path):
    out = _classify(tmp_path)
    assert out[GOLD_MINER_UH]["hedged"] is False
    assert out[SEMI_UH_BRACKET]["hedged"] is False
    assert out[SEMI_H_BRACKET]["hedged"] is True
    assert out[ENERGY_H]["hedged"] is True
    assert out[NO_HEDGE_MARK]["hedged"] is None


def test_r28_bond_mixed_is_reg11_5_non_risk_pending_confirmation(tmp_path):
    out = _classify(tmp_path)
    for name in (BOND_MIXED, BOND):
        assert out[name]["riskAsset"] is False, name
        assert out[name].get("riskStatus") == "nonRisk", name
        assert out[name].get("needsConfirmation") is True, name
        assert "제11조①5호" in out[name].get("riskBasis", ""), name


def test_r28_high_yield_bond_mixed_stays_in_limit_as_unverified(tmp_path):
    out = _classify(tmp_path)
    assert out[BOND_MIXED_HIGH_YIELD]["riskAsset"] is True
    assert out[BOND_MIXED_HIGH_YIELD].get("riskStatus") == "unverified"


@pytest.mark.parametrize("name,region", [
    ("유리필라델피아반도체인덱스증권자투자신탁UH[주식]ClassC-P1e", "us"),
    ("베어링독일증권자투자신탁[H](주식-재간접형)ClassC-P2e", "europe"),
    ("미래에셋연금선진시장증권자투자신탁 1(주식-재간접형)종류C-P2e", "global"),
    ("삼성퇴직연금KOSPI200증권자투자신탁 1[주식]_Ce", "korea"),
])
def test_region_foreign_names_are_not_defaulted_to_korea(name, region):
    assert classify_funds.extract_region(name) == region
