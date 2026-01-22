#!/usr/bin/env python3
"""
Fund Data Updater Script
Converts CSV pension fund data to JSON format for investments portfolio system.
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import re
import shutil
from typing import Dict, List, Tuple, Any


def find_header_row(csv_path: str) -> Tuple[int, List[str]]:
    """
    Find the row containing the actual header (펀드코드).
    Returns (row_number, header_list).
    """
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if row and '펀드코드' in row:
                return idx, row
    raise ValueError("Header row with '펀드코드' not found in CSV file")


def extract_risk_info(risk_str: str) -> Tuple[int, str]:
    """
    Extract risk level and name from string like "2등급(높은 위험)".
    Returns (risk_level, risk_name).
    """
    if not risk_str:
        return 0, ""

    # Match pattern: "N등급(위험명)"
    match = re.match(r'(\d+)등급\((.+?)\)', risk_str)
    if match:
        level = int(match.group(1))
        name = match.group(2).replace(' 위험', '').replace('위험', '')
        return level, name
    return 0, risk_str


def clean_numeric(value: str) -> str:
    """
    Clean numeric values, removing commas and handling empty strings.
    Returns empty string if value is empty or "-".
    """
    if not value or value.strip() in ['', '-', 'N/A']:
        return ""
    return value.replace(',', '').strip()


def parse_fund_type(fund_name: str, note: str) -> str:
    """
    Determine fund type from name and note column.
    Returns: "ETF", "펀드", or "기타"
    """
    if 'ETF' in note or 'ETF' in fund_name:
        return "ETF"
    elif '증권투자신탁' in fund_name or '펀드' in fund_name:
        return "펀드"
    return "기타"


def is_affiliate(affiliate_str: str) -> bool:
    """Check if fund is from affiliate company (계열사)."""
    return affiliate_str.strip() == '계열사'


def extract_version_from_filename(filename: str) -> str:
    """
    Extract version date from filename like "26년01월_상품제안서_퇴직연금(DCIRP).csv".
    Returns ISO date format like "2026-01-01".
    """
    match = re.search(r'(\d{2})년(\d{2})월', filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        # Assume 20XX for year < 50, 19XX otherwise
        full_year = 2000 + year if year >= 0 else 1900 + year
        return f"{full_year}-{month:02d}-01"
    return datetime.now().strftime("%Y-%m-%d")


def convert_csv_to_json(csv_path: str, output_dir: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Convert CSV fund data to JSON format.

    Args:
        csv_path: Path to input CSV file
        output_dir: Directory to save JSON files
        dry_run: If True, only show preview without saving

    Returns:
        Dictionary with conversion statistics
    """
    csv_path = Path(csv_path)
    output_dir = Path(output_dir)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Find header row
    header_row_idx, headers = find_header_row(str(csv_path))
    print(f"Found header at row {header_row_idx + 1}")
    print(f"Headers: {headers[:5]}...")  # Show first 5 headers

    # Extract version from filename
    version = extract_version_from_filename(csv_path.name)
    source_file = csv_path.name

    # Column mapping
    col_map = {header.strip(): idx for idx, header in enumerate(headers)}

    # Read data
    funds = []
    fees = {}

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for _ in range(header_row_idx + 1):  # Skip to data rows
            next(reader)

        for row in reader:
            if not row or len(row) < 10:  # Skip empty or incomplete rows
                continue

            fund_code = row[col_map.get('펀드코드', 0)].strip()
            if not fund_code:  # Skip rows without fund code
                continue

            # Extract fund data
            fund_name = row[col_map.get('펀드명', 1)].strip()
            company = row[col_map.get('운용회사명', 2)].strip()
            risk_str = row[col_map.get('위험등급', 14)].strip()
            risk_level, risk_name = extract_risk_info(risk_str)

            # Returns
            return_10y = clean_numeric(row[col_map.get('수익률(10Y)', 3)])
            return_7y = clean_numeric(row[col_map.get('수익률(7Y)', 4)])
            return_5y = clean_numeric(row[col_map.get('수익률(5Y)', 5)])
            return_3y = clean_numeric(row[col_map.get('수익률(3Y)', 6)])
            return_1y = clean_numeric(row[col_map.get('수익률(1Y)', 7)])
            return_6m = clean_numeric(row[col_map.get('수익률(6M)', 8)])

            # Assets and fees
            net_assets = clean_numeric(row[col_map.get('순자산총액(억원)', 17)])
            # Convert to actual amount (억원 -> 원, keeping as string to avoid precision loss)
            if net_assets:
                net_assets = str(int(float(net_assets) * 100000000))

            inception_date = clean_numeric(row[col_map.get('설정일', 18)]).replace('-', '')

            total_fee = clean_numeric(row[col_map.get('비율(%)', 15)])
            annual_cost = clean_numeric(row[col_map.get('1년투자비용(원)', 16)])

            # Additional info
            affiliate_str = row[col_map.get('계열사 여부', 19)].strip() if len(row) > 19 else ""
            note = row[col_map.get('비고', 20)].strip() if len(row) > 20 else ""

            fund_type = parse_fund_type(fund_name, note)
            is_aff = is_affiliate(affiliate_str)

            # Build fund object
            fund_obj = {
                "fundCode": fund_code,
                "name": fund_name,
                "company": company,
                "riskLevel": risk_level,
                "riskName": risk_name,
                "return10y": return_10y,
                "return7y": return_7y,
                "return5y": return_5y,
                "return3y": return_3y,
                "return1y": return_1y,
                "return6m": return_6m,
                "netAssets": net_assets,
                "inceptionDate": inception_date,
                "isAffiliate": is_aff,
                "fundType": fund_type
            }

            funds.append(fund_obj)

            # Build fee object
            fees[fund_code] = {
                "fundCode": fund_code,
                "fundName": fund_name,
                "totalFee": total_fee,
                "annualCost": annual_cost
            }

    # Build metadata
    now = datetime.now().astimezone().isoformat()
    meta = {
        "version": version,
        "sourceFile": source_file,
        "updatedAt": now,
        "recordCount": len(funds)
    }

    # Prepare output
    fund_data = {
        "_meta": meta,
        "funds": funds
    }

    fee_data = {
        "_meta": meta,
        "fees": fees
    }

    stats = {
        "total_funds": len(funds),
        "version": version,
        "source_file": source_file,
        "output_dir": str(output_dir)
    }

    if dry_run:
        print("\n=== DRY RUN MODE ===")
        print(f"Total funds: {len(funds)}")
        print(f"Version: {version}")
        print(f"\nSample fund data (first 3):")
        for fund in funds[:3]:
            print(f"  - {fund['fundCode']}: {fund['name'][:50]}")
        print(f"\nSample fee data (first 3):")
        for code in list(fees.keys())[:3]:
            print(f"  - {code}: {fees[code]['totalFee']}% / {fees[code]['annualCost']}원")
        print("\nNo files written (dry run mode)")
        return stats

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_dir = output_dir / "archive"
    archive_dir.mkdir(exist_ok=True)

    # Backup existing files
    fund_data_path = output_dir / "fund_data.json"
    fund_fees_path = output_dir / "fund_fees.json"

    if fund_data_path.exists():
        backup_name = f"fund_data_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        shutil.copy2(fund_data_path, archive_dir / backup_name)
        print(f"Backed up fund_data.json to {backup_name}")

    if fund_fees_path.exists():
        backup_name = f"fund_fees_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        shutil.copy2(fund_fees_path, archive_dir / backup_name)
        print(f"Backed up fund_fees.json to {backup_name}")

    # Write JSON files
    with open(fund_data_path, 'w', encoding='utf-8') as f:
        json.dump(fund_data, f, ensure_ascii=False, indent=2)
    print(f"Created {fund_data_path}")

    with open(fund_fees_path, 'w', encoding='utf-8') as f:
        json.dump(fee_data, f, ensure_ascii=False, indent=2)
    print(f"Created {fund_fees_path}")

    stats['fund_data_path'] = str(fund_data_path)
    stats['fund_fees_path'] = str(fund_fees_path)

    return stats


def classify_funds(fund_data_path: str, output_path: str) -> Dict[str, Any]:
    """
    Generate fund classification file based on fund_data.json.
    Classifies funds into risk/safe assets based on keywords and risk level.
    """
    with open(fund_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    funds = data.get('funds', [])
    classifications = {}

    # Keyword-based classification rules
    risk_keywords = {
        '주식형': ('equity', 'domestic'),
        '해외주식': ('equity', 'global'),
        '반도체': ('equity', 'global', ['semiconductor']),
        'AI': ('equity', 'global', ['ai']),
        '방산': ('equity', 'domestic', ['defense']),
        '원자력': ('equity', 'domestic', ['nuclear']),
        '전력': ('equity', 'domestic', ['energy']),
        'HBM': ('equity', 'global', ['semiconductor', 'ai']),
        'SK하이닉스': ('equity', 'domestic', ['semiconductor']),
        '채권': ('bond', 'domestic'),
        'MMF': ('money_market', 'domestic'),
        '머니마켓': ('money_market', 'domestic'),
    }

    for fund in funds:
        name = fund['name']
        risk_level = fund['riskLevel']

        # Default classification
        asset_class = 'mixed'
        region = 'domestic'
        themes = []
        is_risk_asset = risk_level <= 3  # 1-3등급 = 위험자산

        # Keyword matching
        category = '기타'
        for keyword, rules in risk_keywords.items():
            if keyword in name:
                asset_class = rules[0]
                region = rules[1] if len(rules) > 1 else 'domestic'
                if len(rules) > 2:
                    themes = rules[2]

                if keyword in ['주식형', '해외주식', '반도체', 'AI', '방산', '원자력', '전력', 'HBM', 'SK하이닉스']:
                    category = '주식형' if region == 'domestic' else '해외주식형'
                    is_risk_asset = True
                elif keyword in ['채권']:
                    category = '채권형'
                    is_risk_asset = False
                elif keyword in ['MMF', '머니마켓']:
                    category = 'MMF'
                    is_risk_asset = False
                break

        # Check if hedged
        hedged = '헤지' in name or 'Hedged' in name.lower()

        classifications[name] = {
            "category": category,
            "riskAsset": is_risk_asset,
            "assetClass": asset_class,
            "region": region,
            "themes": themes,
            "hedged": hedged,
            "riskLevel": risk_level,
            "source": "fund_data.json + keyword classification",
            "generatedAt": datetime.now().strftime("%Y-%m-%d")
        }

    # Write classification file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(classifications, f, ensure_ascii=False, indent=2)

    # Calculate statistics
    risk_count = sum(1 for c in classifications.values() if c['riskAsset'])
    safe_count = len(classifications) - risk_count

    category_stats = {}
    for c in classifications.values():
        cat = c['category']
        category_stats[cat] = category_stats.get(cat, 0) + 1

    return {
        'total': len(classifications),
        'risk_assets': risk_count,
        'safe_assets': safe_count,
        'categories': category_stats,
        'output_path': output_path
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert CSV fund data to JSON format for investments portfolio'
    )
    parser.add_argument(
        '--file',
        required=True,
        help='Path to CSV file (e.g., resource/26년01월_상품제안서_퇴직연금(DCIRP).csv)'
    )
    parser.add_argument(
        '--output-dir',
        help='Output directory (default: auto-detect investments/funds/)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview conversion without writing files'
    )

    args = parser.parse_args()

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # Try to auto-detect investments repo
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent
        output_dir = repo_root / 'funds'

        if not repo_root.exists():
            print("Error: Could not auto-detect output directory")
            print("Please specify --output-dir explicitly")
            sys.exit(1)

    print(f"Input CSV: {args.file}")
    print(f"Output directory: {output_dir}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("-" * 60)

    # Convert CSV to JSON
    try:
        stats = convert_csv_to_json(args.file, str(output_dir), dry_run=args.dry_run)

        if not args.dry_run:
            print("\n" + "=" * 60)
            print("Conversion completed successfully!")
            print(f"Total funds: {stats['total_funds']}")
            print(f"Version: {stats['version']}")
            print(f"Files created:")
            print(f"  - {stats['fund_data_path']}")
            print(f"  - {stats['fund_fees_path']}")

            # Generate classification
            print("\nGenerating fund classification...")
            fund_data_path = stats['fund_data_path']
            classification_path = Path(output_dir) / 'fund_classification.json'

            class_stats = classify_funds(fund_data_path, str(classification_path))
            print(f"Created {class_stats['output_path']}")
            print(f"\nClassification statistics:")
            print(f"  Total: {class_stats['total']}")
            print(f"  Risk assets: {class_stats['risk_assets']}")
            print(f"  Safe assets: {class_stats['safe_assets']}")
            print(f"\nCategory breakdown:")
            for cat, count in sorted(class_stats['categories'].items(), key=lambda x: -x[1]):
                print(f"  {cat}: {count}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
