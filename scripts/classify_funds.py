#!/usr/bin/env python3
"""
Enhanced Fund Classification Script
Classifies funds into risk/safe assets with improved keyword matching.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, List


def classify_fund(name: str, risk_level: int) -> Tuple[str, bool, str, str, List[str]]:
    """
    Classify a fund based on its name and risk level.
    Returns: (category, is_risk_asset, asset_class, region, themes)
    """
    name_lower = name.lower()

    # Default classification based on risk level
    is_risk_asset = risk_level <= 3  # 1-3등급 = 위험자산
    asset_class = "mixed"
    region = "domestic"
    themes = []
    category = "기타"

    # Priority 1: Specific thematic keywords (highest priority)
    thematic_keywords = {
        # Technology & Semiconductors
        "반도체": ("주식형", True, "equity", "global", ["semiconductor"]),
        "HBM": ("해외주식형", True, "equity", "global", ["semiconductor", "ai"]),
        "SK하이닉스": ("주식형", True, "equity", "domestic", ["semiconductor"]),
        "밸류체인": ("주식형", True, "equity", "domestic", ["technology"]),
        # Defense & Nuclear
        "방산": ("주식형", True, "equity", "domestic", ["defense"]),
        "우주": ("주식형", True, "equity", "domestic", ["defense", "space"]),
        "원자력": ("주식형", True, "equity", "domestic", ["nuclear"]),
        # Energy & Infrastructure
        "전력": ("주식형", True, "equity", "domestic", ["energy"]),
        "태양광": ("주식형", True, "equity", "domestic", ["renewable"]),
        "ESS": ("주식형", True, "equity", "domestic", ["energy"]),
        "신재생": ("주식형", True, "equity", "domestic", ["renewable"]),
        "수소": ("주식형", True, "equity", "domestic", ["hydrogen"]),
        # Other themes
        "금": ("해외주식형", True, "equity", "global", ["gold", "commodity"]),
        "골드": ("해외주식형", True, "equity", "global", ["gold", "commodity"]),
        "로봇": ("주식형", True, "equity", "domestic", ["robotics"]),
        "AI": ("해외주식형", True, "equity", "global", ["ai"]),
    }

    for keyword, (cat, risk, asset, reg, theme) in thematic_keywords.items():
        if keyword in name:
            return cat, risk, asset, reg, theme

    # Priority 2: Broad equity classification
    equity_keywords = {
        # Domestic equity indicators
        "KODEX": ("주식형", True, "equity", "domestic", []),
        "TIGER": ("주식형", True, "equity", "domestic", []),
        "ARIRANG": ("주식형", True, "equity", "domestic", []),
        "KINDEX": ("주식형", True, "equity", "domestic", []),
        "KBSTAR": ("주식형", True, "equity", "domestic", []),
        "RISE": ("주식형", True, "equity", "domestic", []),
        "HANARO": ("주식형", True, "equity", "domestic", []),
        "PLUS": ("주식형", True, "equity", "domestic", []),
        "UNICORN": ("주식형", True, "equity", "domestic", []),
        "SOL": ("주식형", True, "equity", "domestic", []),
        # Domestic indicators in name
        "코리아": ("주식형", True, "equity", "domestic", []),
        "대한민국": ("주식형", True, "equity", "domestic", []),
        "한국": ("주식형", True, "equity", "domestic", []),
        # Index-based
        "KOSPI": ("주식형", True, "equity", "domestic", []),
        "KOSDAQ": ("주식형", True, "equity", "domestic", []),
        "TOP": ("주식형", True, "equity", "domestic", []),
        # Global equity
        "글로벌": ("해외주식형", True, "equity", "global", []),
        "월드": ("해외주식형", True, "equity", "global", []),
        "WORLD": ("해외주식형", True, "equity", "global", []),
        "GLOBAL": ("해외주식형", True, "equity", "global", []),
        # Specific regions
        "미국": ("해외주식형", True, "equity", "global", ["us"]),
        "중국": ("해외주식형", True, "equity", "global", ["china"]),
        "일본": ("해외주식형", True, "equity", "global", ["japan"]),
        "유럽": ("해외주식형", True, "equity", "global", ["europe"]),
        "신흥국": ("해외주식형", True, "equity", "global", ["emerging"]),
        "S&P": ("해외주식형", True, "equity", "global", ["us"]),
        "NASDAQ": ("해외주식형", True, "equity", "global", ["us", "tech"]),
    }

    for keyword, (cat, risk, asset, reg, theme) in equity_keywords.items():
        if keyword in name:
            return cat, risk, asset, reg, theme

    # Priority 2.5: Bond-mixed assets (RISK assets per DC regulation)
    # 과학기술공제회 DC형 규정: 채권혼합형/해외채권혼합형은 위험자산으로 분류
    # 참조: "주식형>주식혼합형>채권혼합형 순서로 위험자산 비중이 높음"
    bond_mixed_keywords = {
        "채권혼합": ("채권혼합형", True, "mixed", "domestic", []),
        "해외채권혼합": ("해외채권혼합형", True, "mixed", "global", []),
    }

    for keyword, (cat, risk, asset, reg, theme) in bond_mixed_keywords.items():
        if keyword in name:
            return cat, risk, asset, reg, theme

    # Priority 3: Safe assets (bonds, MMF)
    safe_keywords = {
        "채권": ("채권형", False, "bond", "domestic", []),
        "국공채": ("채권형", False, "bond", "domestic", ["government"]),
        "회사채": ("채권형", False, "bond", "domestic", ["corporate"]),
        "크레딧": ("채권형", False, "bond", "domestic", ["credit"]),
        "MMF": ("MMF", False, "money_market", "domestic", []),
        "머니마켓": ("MMF", False, "money_market", "domestic", []),
        "단기금융": ("MMF", False, "money_market", "domestic", []),
    }

    for keyword, (cat, risk, asset, reg, theme) in safe_keywords.items():
        if keyword in name:
            return cat, risk, asset, reg, theme

    # Priority 4: Generic patterns
    if "증권상장지수투자신탁" in name and "[주식]" in name:
        # ETF with [주식] tag - likely equity ETF
        if "해외" in name or "Global" in name or "World" in name:
            return "해외주식형", True, "equity", "global", []
        else:
            return "주식형", True, "equity", "domestic", []

    if "증권투자신탁[주식]" in name or "증권자투자신탁(주식" in name:
        # Regular equity fund
        if "해외" in name or "Global" in name or "World" in name:
            return "해외주식형", True, "equity", "global", []
        else:
            return "주식형", True, "equity", "domestic", []

    # Priority 5: Fallback based on risk level
    if risk_level <= 3:
        # High risk, likely equity
        category = "주식형"
        is_risk_asset = True
        asset_class = "equity"
    elif risk_level >= 5:
        # Low risk, likely bond or conservative
        category = "채권형"
        is_risk_asset = False
        asset_class = "bond"
    else:
        # Medium risk, mixed
        category = "혼합형"
        is_risk_asset = True
        asset_class = "mixed"

    return category, is_risk_asset, asset_class, region, themes


def generate_classification(fund_data_path: str, output_path: str) -> Dict[str, Any]:
    """
    Generate enhanced fund classification file.
    """
    with open(fund_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    funds = data.get("funds", [])
    classifications = {}

    for fund in funds:
        name = fund["name"]
        risk_level = fund["riskLevel"]

        category, is_risk_asset, asset_class, region, themes = classify_fund(
            name, risk_level
        )

        # Check if hedged
        hedged = (
            "헤지" in name or "Hedged" in name.lower() or "(H)" in name or "[H]" in name
        )

        classifications[name] = {
            "category": category,
            "riskAsset": is_risk_asset,
            "assetClass": asset_class,
            "region": region,
            "themes": themes,
            "hedged": hedged,
            "riskLevel": risk_level,
            "source": "enhanced keyword classification v2",
            "generatedAt": datetime.now().strftime("%Y-%m-%d"),
        }

    # Write classification file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(classifications, f, ensure_ascii=False, indent=2)

    # Calculate statistics
    risk_count = sum(1 for c in classifications.values() if c["riskAsset"])
    safe_count = len(classifications) - risk_count

    category_stats = {}
    for c in classifications.values():
        cat = c["category"]
        category_stats[cat] = category_stats.get(cat, 0) + 1

    return {
        "total": len(classifications),
        "risk_assets": risk_count,
        "safe_assets": safe_count,
        "categories": category_stats,
        "output_path": output_path,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced fund classification with improved keyword matching"
    )
    parser.add_argument("--fund-data", required=True, help="Path to fund_data.json")
    parser.add_argument(
        "--output",
        help="Output path for classification JSON (default: same dir as fund_data.json)",
    )

    args = parser.parse_args()

    fund_data_path = Path(args.fund_data)
    if not fund_data_path.exists():
        print(f"Error: {fund_data_path} not found", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = fund_data_path.parent / "fund_classification.json"

    print(f"Input: {fund_data_path}")
    print(f"Output: {output_path}")
    print("-" * 60)

    try:
        stats = generate_classification(str(fund_data_path), str(output_path))

        print("\nClassification completed successfully!")
        print(f"Total funds: {stats['total']}")
        print(
            f"Risk assets: {stats['risk_assets']} ({stats['risk_assets'] / stats['total'] * 100:.1f}%)"
        )
        print(
            f"Safe assets: {stats['safe_assets']} ({stats['safe_assets'] / stats['total'] * 100:.1f}%)"
        )
        print(f"\nCategory breakdown:")
        for cat, count in sorted(stats["categories"].items(), key=lambda x: -x[1]):
            pct = count / stats["total"] * 100
            print(f"  {cat}: {count} ({pct:.1f}%)")
        print(f"\nOutput: {stats['output_path']}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
