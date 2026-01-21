#!/usr/bin/env python3
"""
CSV to JSON Fund Data Converter

Converts 과학기술공제회 퇴직연금 CSV files to fund_data.json and fund_fees.json

Usage:
    python update_fund_data.py --file <csv_path>
    python update_fund_data.py --file <csv_path> --dry-run
    python update_fund_data.py --file <csv_path> --output-dir <output_dir>
"""

import argparse
import csv
import json
from pathlib import Path
from datetime import datetime
import sys


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Convert 과학기술공제회 퇴직연금 CSV to JSON format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python update_fund_data.py --file resource/25년12월_상품제안서_퇴직연금(DCIRP).csv
  python update_fund_data.py --file resource/25년12월_상품제안서_퇴직연금(DCIRP).csv --dry-run
  python update_fund_data.py --file resource/25년12월_상품제안서_퇴직연금(DCIRP).csv --output-dir funds/
        """
    )
    
    parser.add_argument(
        "--file",
        required=True,
        help="Path to CSV file"
    )
    
    parser.add_argument(
        "--output-dir",
        default="funds",
        help="Output directory for JSON files (default: funds/)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show preview without writing files"
    )
    
    return parser.parse_args()


def detect_header_row(rows):
    """Find header row by searching for '펀드코드' keyword
    
    Args:
        rows: List of CSV rows
        
    Returns:
        tuple: (header_row_index, header_list)
        
    Raises:
        ValueError: If header row not found
    """
    for i, row in enumerate(rows):
        if any("펀드코드" in cell for cell in row):
            return i, row
    
    raise ValueError("Header row with '펀드코드' not found in CSV file")


def extract_metadata(rows):
    """Extract metadata from CSV rows 1-7
    
    Args:
        rows: List of CSV rows
        
    Returns:
        dict: Metadata with keys: provider, systemType, productType, baseDate
    """
    metadata = {}
    
    try:
        # Row 1: 사업자명 (Provider name)
        if len(rows) > 0 and len(rows[0]) > 1:
            metadata["provider"] = rows[0][1].strip()
        else:
            metadata["provider"] = ""
        
        # Row 2: 제도유형 (System type)
        if len(rows) > 1 and len(rows[1]) > 1:
            metadata["systemType"] = rows[1][1].strip()
        else:
            metadata["systemType"] = ""
        
        # Row 3: 상품유형 (Product type)
        if len(rows) > 2 and len(rows[2]) > 1:
            metadata["productType"] = rows[2][1].strip()
        else:
            metadata["productType"] = ""
        
        # Row 4: 기준일 (Base date: "2025-12-01, 제로인")
        if len(rows) > 3 and len(rows[3]) > 1:
            base_date_cell = rows[3][1].strip()
            # Extract date part before comma
            if "," in base_date_cell:
                metadata["baseDate"] = base_date_cell.split(",")[0].strip()
            else:
                metadata["baseDate"] = base_date_cell
        else:
            metadata["baseDate"] = ""
    
    except Exception as e:
        print(f"Warning: Error extracting metadata: {e}")
        metadata = {
            "provider": "",
            "systemType": "",
            "productType": "",
            "baseDate": ""
        }
    
    return metadata


def load_csv(file_path):
    """Load and parse CSV file
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        tuple: (metadata, header, data_rows)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        UnicodeDecodeError: If file encoding is invalid
        ValueError: If CSV structure is invalid
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(
            e.encoding,
            e.object,
            e.start,
            e.end,
            f"Failed to read CSV file with UTF-8 encoding: {e.reason}"
        )
    
    if len(rows) < 9:
        raise ValueError(f"CSV file has only {len(rows)} rows, expected at least 9 rows")
    
    # Extract metadata from rows 1-7
    metadata = extract_metadata(rows)
    
    # Find header row (should be around row 8, but search to be safe)
    header_index, header = detect_header_row(rows)
    
    # Data rows start after header
    data_rows = rows[header_index + 1:]
    
    return metadata, header, data_rows


def parse_fund_data(row, header):
    """Parse a single CSV row into fund data structure (stub)
    
    This will be implemented in Task 3.
    For now, just return a basic dict with fundCode and name.
    
    Args:
        row: CSV row data
        header: CSV header row
        
    Returns:
        dict: Basic fund data structure
    """
    # Create column index mapping
    col_map = {col: i for i, col in enumerate(header)}
    
    # Extract basic fields
    fund_code = row[col_map.get("펀드코드", 0)].strip() if col_map.get("펀드코드") is not None else ""
    fund_name = row[col_map.get("펀드명", 1)].strip() if col_map.get("펀드명") is not None else ""
    
    return {
        "fundCode": fund_code,
        "name": fund_name
    }


def parse_fund_fees(row, header):
    """Parse a single CSV row into fee data structure (stub)
    
    This will be implemented in Task 4.
    For now, just return a basic dict with fundCode and totalFee.
    
    Args:
        row: CSV row data
        header: CSV header row
        
    Returns:
        dict: Basic fee data structure
    """
    # Create column index mapping
    col_map = {col: i for i, col in enumerate(header)}
    
    # Extract basic fields
    fund_code = row[col_map.get("펀드코드", 0)].strip() if col_map.get("펀드코드") is not None else ""
    total_fee = row[col_map.get("비율(%)", -1)].strip() if col_map.get("비율(%)") is not None else ""
    
    return {
        "fundCode": fund_code,
        "totalFee": total_fee
    }


def process_csv(csv_path, output_dir, dry_run):
    """Main processing function
    
    Args:
        csv_path: Path to CSV file
        output_dir: Output directory for JSON files
        dry_run: If True, show preview without writing files
    """
    # Load CSV
    print("=" * 60)
    print("CSV to JSON Fund Data Converter" + (" - DRY RUN" if dry_run else ""))
    print("=" * 60)
    print()
    
    metadata, header, data_rows = load_csv(csv_path)
    
    # Display CSV metadata
    print("CSV Metadata:")
    print(f"  Provider: {metadata['provider']}")
    print(f"  System: {metadata['systemType']}")
    print(f"  Product: {metadata['productType']}")
    print(f"  Base Date: {metadata['baseDate']}")
    print()
    
    # Display CSV structure
    header_index = 0
    for i, row in enumerate(csv.reader(open(csv_path, "r", encoding="utf-8"))):
        if any("펀드코드" in cell for cell in row):
            header_index = i + 1  # 1-based row number
            break
    
    print("CSV Structure:")
    print(f"  Header row: Row {header_index}")
    print(f"  Columns: {len(header)}")
    print(f"  Data rows: {len(data_rows)}")
    print()
    
    # Parse all rows
    fund_data_list = []
    fund_fees_dict = {}
    
    for row in data_rows:
        # Skip empty rows
        if not row or not any(cell.strip() for cell in row):
            continue
        
        # Parse fund data
        fund_data = parse_fund_data(row, header)
        
        # Skip rows without fundCode
        if not fund_data["fundCode"]:
            continue
        
        fund_data_list.append(fund_data)
        
        # Parse fund fees
        fund_fees = parse_fund_fees(row, header)
        fund_fees_dict[fund_fees["fundCode"]] = fund_fees
    
    # Display sample funds
    print("Sample funds:")
    for i, fund in enumerate(fund_data_list[:3], 1):
        print(f"  {i}. {fund['fundCode']}: {fund['name']}")
    print()
    
    if dry_run:
        print("=" * 60)
        print("DRY RUN COMPLETE - No files created")
        print("=" * 60)
        return
    
    # Write JSON files (placeholder for Tasks 3-4)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create fund_data.json (stub)
    fund_data_json = {
        "_meta": {
            "version": metadata["baseDate"],
            "sourceFile": Path(csv_path).name,
            "updatedAt": datetime.now().astimezone().isoformat(),
            "recordCount": len(fund_data_list)
        },
        "funds": fund_data_list
    }
    
    fund_data_path = output_path / "fund_data.json"
    with open(fund_data_path, "w", encoding="utf-8") as f:
        json.dump(fund_data_json, f, ensure_ascii=False, indent=2)
    
    # Create fund_fees.json (stub)
    fund_fees_json = {
        "_meta": {
            "version": metadata["baseDate"],
            "sourceFile": Path(csv_path).name,
            "updatedAt": datetime.now().astimezone().isoformat(),
            "recordCount": len(fund_fees_dict)
        },
        "fees": fund_fees_dict
    }
    
    fund_fees_path = output_path / "fund_fees.json"
    with open(fund_fees_path, "w", encoding="utf-8") as f:
        json.dump(fund_fees_json, f, ensure_ascii=False, indent=2)
    
    print("=" * 60)
    print("CONVERSION COMPLETE")
    print("=" * 60)
    print()
    print(f"Output files:")
    print(f"  {fund_data_path}")
    print(f"  {fund_fees_path}")
    print()
    print(f"Total funds processed: {len(fund_data_list)}")
    print()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Validate file exists
    csv_path = Path(args.file)
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)
    
    # Process
    try:
        process_csv(csv_path, args.output_dir, args.dry_run)
    except ValueError as e:
        print(f"Error: Invalid CSV format - {e}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"Error: File encoding error - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
