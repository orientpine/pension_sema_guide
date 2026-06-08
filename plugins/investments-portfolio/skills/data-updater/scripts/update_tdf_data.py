#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast


TDF_VERSION = "2026-06-04"
TDF_SOURCE = "펀드평가사 제로인"
BASE_DATE_NOTE = "fund_data.json 기준일 2026-03-01과 상이. 직접 교차비교 금지"
CURRENT_YEAR = 2026
RETIREMENT_AGE = 60
FRESHNESS_THRESHOLD_DAYS = 30
FEE_AGREEMENT_TOLERANCE = 0.01

ROW_RE = re.compile(r"^\s*(\d+)\.\s*(.+)$")
RISK_RE = re.compile(r"^(.+?)([1-6])$")
TARGET_YEAR_RE = re.compile(r"(?<!\d)(20(?:1[5-9]|[2-5]\d|60))(?!\d)")


@dataclass(frozen=True)
class CliArgs:
    input: str
    output: str
    fees: bool


JsonValue = str | int | bool | None | list[int]
FundRecord = dict[str, JsonValue]
JsonObject = dict[str, object]


def parse_args() -> CliArgs:
    parser = argparse.ArgumentParser(
        description="Convert pasted SEMA TDF markdown table to tdf_data.json"
    )
    _ = parser.add_argument("--input", required=True, help="Path to tdf-raw-table.md")
    _ = parser.add_argument(
        "--output",
        default="funds/tdf_data.json",
        help="Output JSON path (default: funds/tdf_data.json)",
    )
    _ = parser.add_argument(
        "--fees",
        action="store_true",
        help="Enrich fee data after 3-source verification",
    )
    namespace = parser.parse_args()
    parsed = cast(dict[str, object], vars(namespace))
    return CliArgs(
        input=str(parsed["input"]),
        output=str(parsed["output"]),
        fees=bool(parsed["fees"]),
    )


def clean_cell(value: str) -> str:
    return value.strip()


def parse_risk(value: str) -> tuple[str, int]:
    compact = re.sub(r"\s+", "", value.strip())
    match = RISK_RE.match(compact)
    if not match:
        raise ValueError(f"Invalid risk value: {value}")
    return match.group(1), int(match.group(2))


def derive_target_year(name: str) -> int | None:
    match = TARGET_YEAR_RE.search(name)
    if match:
        return int(match.group(1))
    return None


def derive_hedge(name: str) -> str | None:
    upper_name = name.upper()
    if "(UH)" in upper_name or re.search(r"(?<![A-Z])UH(?![A-Z])", upper_name):
        return "UH"
    if "(H)" in upper_name or "H[" in upper_name:
        return "H"
    return None


def round_to_nearest_five(value: int) -> int:
    return int((value + 2) // 5 * 5)


def derive_recommended_age_band(targetYear: int, retirement_age: int = RETIREMENT_AGE) -> list[int]:
    birth_year = targetYear - retirement_age
    current_age = CURRENT_YEAR - birth_year
    return [round_to_nearest_five(current_age - 5), round_to_nearest_five(current_age + 5)]


def derive_tdf_qualified(name: str) -> dict[str, bool]:
    has_qualified_token = "적격" in name
    return {"qualified": True, "needsReview": not has_qualified_token}


def reconcile_fee(values: list[float]) -> JsonObject:
    numeric_values = [float(value) for value in values]
    result: JsonObject = {
        "values": numeric_values,
        "agree": False,
        "needs_review": True,
    }
    if len(numeric_values) < 3:
        return result

    agree = max(numeric_values) - min(numeric_values) <= FEE_AGREEMENT_TOLERANCE
    result["agree"] = agree
    if agree:
        return {"agree": True, "value": sum(numeric_values) / len(numeric_values)}
    return result


def parse_tdf_table(text: str) -> list[FundRecord]:
    funds: list[FundRecord] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        row_match = ROW_RE.match(stripped)
        if not row_match:
            continue

        row_number = int(row_match.group(1))
        cells = [clean_cell(cell) for cell in row_match.group(2).split("|")]
        if len(cells) != 11:
            raise ValueError(
                f"Row {row_number} has {len(cells)} columns; expected 11: {stripped}"
            )

        (
            name,
            risk_value,
            return1m,
            return3m,
            return6m,
            return1y,
            return2y,
            return3y,
            return_since_inception,
            net_assets,
            company,
        ) = cells

        risk_name, risk_level = parse_risk(risk_value)
        target_year = derive_target_year(name)
        tdf_qualified = derive_tdf_qualified(name)

        fund: FundRecord = {
            "fundCode": "",
            "name": name,
            "company": company,
            "targetYear": target_year,
            "recommendedAgeBand": derive_recommended_age_band(target_year) if target_year else [],
            "hedge": derive_hedge(name),
            "tdfQualified": tdf_qualified["qualified"],
            "riskName": risk_name,
            "riskLevel": risk_level,
            "return1m": return1m,
            "return3m": return3m,
            "return6m": return6m,
            "return1y": return1y,
            "return2y": return2y,
            "return3y": return3y,
            "returnSinceInception": return_since_inception,
            "netAssets": net_assets,
        }
        funds.append(fund)

    return funds


def write_json(
    funds: list[FundRecord],
    output_path: str | Path,
    meta_override: dict[str, object] | None = None,
) -> JsonObject:
    meta: JsonObject = {
        "version": TDF_VERSION,
        "source": TDF_SOURCE,
        "updatedAt": datetime.now().astimezone().isoformat(),
        "recordCount": len(funds),
        "freshnessThresholdDays": FRESHNESS_THRESHOLD_DAYS,
        "baseDateNote": BASE_DATE_NOTE,
    }
    if meta_override:
        meta.update(meta_override)

    data: JsonObject = {"_meta": meta, "funds": funds}
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        _ = f.write("\n")
    return data


def main() -> int:
    args = parse_args()
    if args.fees:
        print(
            "Error: --fees requires external 3-source fee verification; offline enrichment is unavailable.",
            file=sys.stderr,
        )
        return 2
    text = Path(args.input).read_text(encoding="utf-8")
    funds = parse_tdf_table(text)
    _ = write_json(funds, args.output)
    print(f"Parsed {len(funds)} TDF funds")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
