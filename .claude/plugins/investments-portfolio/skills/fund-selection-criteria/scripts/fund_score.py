#!/usr/bin/env python3
"""fund-selection-criteria §4.1 펀드 선택 점수. 과거 수익률은 점수에 넣지 않고 맥락으로만 함께 보여 준다.

python3 fund_score.py --codes K55301C83862 K55235BW6849 --profile-risk 2 [--funds-dir funds]
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal as D
from pathlib import Path

WEIGHTS = {"cost": 45, "index": 15, "diversification": 15, "size": 15, "risk_fit": 5, "track": 5}
SINGLE_COUNTRY = {"korea", "us", "japan", "china", "india", "vietnam", "brazil"}
SECTOR_THEMES = {"semiconductor", "ai", "robot", "energy", "healthcare", "ev", "space", "reits"}
RETURN_FIELDS = ("return6m", "return1y", "return3y", "return5y")


def cost_points(fee: D) -> int:
    return max(0, int((D(45) * (1 - fee / 2)).to_integral_value()))


def index_points(name: str) -> int:
    return 15 if "인덱스" in name or "index" in name.lower() else 0


def diversification_points(classification: dict) -> int:
    if SECTOR_THEMES & set(classification.get("themes") or []):
        return 4
    return 8 if classification.get("region") in SINGLE_COUNTRY else 15


def size_points(net_assets_thousand_krw: D) -> int:
    return 15 if net_assets_thousand_krw / 100_000 >= 100 else 0


def risk_points(fund_risk: int, profile_risk: int) -> int:
    gap = abs(fund_risk - profile_risk)
    return 5 if gap == 0 else 2 if gap == 1 else 0


def track_points(inception: str, as_of: date) -> int:
    started = date(int(inception[:4]), int(inception[4:6]), int(inception[6:8]))
    return 5 if (as_of - started).days >= 3 * 365 else 2


def score(fund: dict, classification: dict, fee: D, profile_risk: int, as_of: date | None = None) -> dict:
    parts = {
        "cost": cost_points(fee),
        "index": index_points(fund["name"]),
        "diversification": diversification_points(classification),
        "size": size_points(D(fund["netAssets"])),
        "risk_fit": risk_points(int(fund["riskLevel"]), profile_risk),
        "track": track_points(fund["inceptionDate"], as_of or date.today()),
    }
    context = {k: fund.get(k) for k in RETURN_FIELDS if fund.get(k) not in (None, "")}
    return {"total": sum(parts.values()), "parts": parts,
            "pastReturnsContextOnly": context}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codes", nargs="+", required=True)
    parser.add_argument("--profile-risk", type=int, required=True)
    parser.add_argument("--funds-dir", type=Path, default=Path("funds"))
    args = parser.parse_args()
    data = json.loads((args.funds_dir / "fund_data.json").read_text(encoding="utf-8"))
    fees = json.loads((args.funds_dir / "fund_fees.json").read_text(encoding="utf-8"))["fees"]
    classes = json.loads((args.funds_dir / "fund_classification.json").read_text(encoding="utf-8"))
    as_of = date.fromisoformat(data["_meta"]["version"])
    by_code = {f["fundCode"]: f for f in data["funds"]}
    rows = []
    for code in args.codes:
        fund = by_code[code]
        result = score(fund, classes[fund["name"]], D(fees[code]["totalFee"]), args.profile_risk, as_of)
        rows.append({"fundCode": code, "name": fund["name"], **result})
    print(json.dumps({"asOf": as_of.isoformat(), "weights": WEIGHTS, "rows": rows}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
