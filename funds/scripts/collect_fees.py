#!/usr/bin/env python3
"""
Fund Fee Template Generator

Creates a template JSON file for manual fund fee data entry.
Run this script to generate fund_fees_template.json, then manually fill in the fee data.

Usage:
    python collect_fees.py

Output:
    funds/fund_fees_template.json
"""

import json
from pathlib import Path
from datetime import datetime


def load_fund_data():
    """Load fund data from fund_data.json"""
    fund_data_path = Path(__file__).parent.parent / "fund_data.json"
    with open(fund_data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_existing_fees():
    """Load existing fee data if available"""
    fees_path = Path(__file__).parent.parent / "fund_fees.json"
    if fees_path.exists():
        with open(fees_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def create_fee_template():
    """Create fee template for all funds"""
    funds = load_fund_data()
    existing_fees = load_existing_fees()

    fee_template = {}

    for fund in funds:
        fund_name = fund["name"]

        # If we already have fee data, preserve it
        if fund_name in existing_fees:
            fee_template[fund_name] = existing_fees[fund_name]
            fee_template[fund_name]["_status"] = "confirmed"
        else:
            # Create empty template for manual entry
            fee_template[fund_name] = {
                "totalFee": None,  # Total Expense Ratio (%)
                "managementFee": None,  # 운용보수 (%)
                "trustFee": None,  # 신탁보수 (%)
                "sellingFee": None,  # 판매보수 (%)
                "otherFee": None,  # 기타보수 (%)
                "frontLoad": "0.000",  # 선취수수료 (%)
                "redemptionFee": "없음",  # 환매수수료
                "source": "투자설명서",
                "updatedAt": None,
                "_status": "pending",  # pending, confirmed
                "_index": fund["index"],
            }

    return fee_template


def get_priority_funds():
    """Return list of priority funds (current portfolio + popular funds)"""
    # 현재 포트폴리오 펀드들
    current_portfolio = [
        "삼성글로벌반도체증권자투자신탁UH[주식]_Cpe(퇴직)",
        "삼성글로벌반도체증권자투자신탁H[주식]_Cpe(퇴직)",
        "삼성미국S&P500인덱스증권자투자신탁UH[주식] Cpe(퇴직)",
        "미래에셋코어테크증권자투자신탁(주식) 종류C-P2E",
        "삼성글로벌휴머노이드로봇증권자투자신탁UH[주식]_Cpe(퇴직연금)",
        "삼성글로벌휴머노이드로봇증권자투자신탁H[주식]_Cpe(퇴직연금)",
        "미래에셋퇴직연금배당커버드콜액티브증권자투자신탁1호(주식혼합) 종류C-P2e",
        "미래에셋솔로몬중장기국공채증권자투자신탁1호(채권)C-P2E(퇴직)",
        "미래에셋솔로몬장기국공채증권자투자신탁1호(채권) 종류 C-P2e",
    ]

    # 인기 펀드 (순자산 큰 펀드들)
    popular_funds = [
        "키움더드림단기채증권투자신탁[채권] Cla  C-P2e(퇴직연금)",
        "유진챔피언단기채증권자투자신탁(채권) Cla  C-Pe2",
        "피델리티글로벌배당인컴증권자투자신탁(주식-재간접형)CP-e",
        "AB미국그로스증권투자신탁(주식-재간접형)종류형Ce-P2",
        "마이다스 우량채권 증권 자투자신탁 제1호(채권) C-Pe2클래스",
        "한국투자글로벌전기차&자율주행증권투자신탁(주식) 종류 C-Re",
        "KB스타 미국 나스닥 100 인덱스 증권 자투자신탁(주식-파생형)(H) C-퇴직e",
        "KB퇴직연금배당40증권자투자신탁(채권혼합)CE",
    ]

    return list(set(current_portfolio + popular_funds))


def main():
    print("=" * 60)
    print("Fund Fee Template Generator")
    print("=" * 60)

    # Generate template
    fee_template = create_fee_template()

    # Save template
    output_path = Path(__file__).parent.parent / "fund_fees_template.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(fee_template, f, ensure_ascii=False, indent=2)

    # Statistics
    total = len(fee_template)
    confirmed = sum(1 for f in fee_template.values() if f.get("_status") == "confirmed")
    pending = total - confirmed

    print(f"\nTemplate generated: {output_path}")
    print(f"\nStatistics:")
    print(f"  Total funds: {total}")
    print(f"  Confirmed:   {confirmed}")
    print(f"  Pending:     {pending}")

    # Priority funds list
    priority_funds = get_priority_funds()
    print(f"\n⚠️  Priority funds to fill (current portfolio + popular):")
    for i, fund in enumerate(priority_funds, 1):
        status = fee_template.get(fund, {}).get("_status", "unknown")
        icon = "✅" if status == "confirmed" else "❌"
        print(f"  {i}. {icon} {fund}")

    print(f"\n" + "=" * 60)
    print("How to fill fee data:")
    print("=" * 60)
    print("""
1. Open fund_fees_template.json
2. For each fund, fill in:
   - totalFee: 총보수 (e.g., "1.230")
   - managementFee: 운용보수
   - trustFee: 신탁보수
   - sellingFee: 판매보수
   - updatedAt: 입력 날짜 (e.g., "2026-01-05")
   - _status: Change to "confirmed"
   
3. Find fee info in:
   - 과학기술인공제회 퇴직연금 포털
   - 각 펀드 투자설명서 (PDF)
   - 금융투자협회 전자공시시스템

4. After filling, copy confirmed entries to fund_fees.json
""")


if __name__ == "__main__":
    main()
