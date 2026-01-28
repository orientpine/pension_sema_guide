import sys

sys.path.insert(0, "honeypot/plugins/investments-portfolio/scripts")

from classify_funds import RISK_ASSET_CATEGORIES, SAFE_ASSET_CATEGORIES


def test_bond_mixed_not_in_risk():
    """채권혼합형 should NOT be in RISK_ASSET_CATEGORIES"""
    assert "채권혼합형" not in RISK_ASSET_CATEGORIES, (
        "채권혼합형 must be removed from RISK_ASSET_CATEGORIES"
    )


def test_overseas_bond_mixed_not_in_risk():
    """해외채권혼합형 should NOT be in RISK_ASSET_CATEGORIES"""
    assert "해외채권혼합형" not in RISK_ASSET_CATEGORIES, (
        "해외채권혼합형 must be removed from RISK_ASSET_CATEGORIES"
    )


def test_bond_mixed_in_safe():
    """채권혼합형 should be in SAFE_ASSET_CATEGORIES"""
    assert "채권혼합형" in SAFE_ASSET_CATEGORIES, (
        "채권혼합형 must be in SAFE_ASSET_CATEGORIES"
    )


def test_overseas_bond_mixed_in_safe():
    """해외채권혼합형 should be in SAFE_ASSET_CATEGORIES"""
    assert "해외채권혼합형" in SAFE_ASSET_CATEGORIES, (
        "해외채권혼합형 must be in SAFE_ASSET_CATEGORIES"
    )


def test_existing_risk_categories_preserved():
    """Existing risk categories should be preserved"""
    required_risk = ["주식형", "해외주식형", "주식혼합형", "해외주식혼합형"]
    for cat in required_risk:
        assert cat in RISK_ASSET_CATEGORIES, (
            f"{cat} must remain in RISK_ASSET_CATEGORIES"
        )


def test_existing_safe_categories_preserved():
    """Existing safe categories should be preserved"""
    required_safe = ["채권형", "해외채권형", "기타"]
    for cat in required_safe:
        assert cat in SAFE_ASSET_CATEGORIES, (
            f"{cat} must remain in SAFE_ASSET_CATEGORIES"
        )
