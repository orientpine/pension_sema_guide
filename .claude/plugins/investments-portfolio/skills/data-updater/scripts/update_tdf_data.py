#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import TextIO, cast


TDF_VERSION = "2026-06-04"
TDF_SOURCE = "펀드평가사 제로인"
BASE_DATE_NOTE = (
    "all_fund_data.json 기준일과 상이할 수 있음(기준일 drift). "
    "단위 주의: all_fund_data는 3Y/5Y/7Y/10Y=연환산·6M/1Y=누적, tdf는 전 구간 누적. "
    "단위 정규화 없이 직접 교차비교 금지"
)
RETIREMENT_AGE = 60
FRESHNESS_THRESHOLD_DAYS = 30


def _derive_current_year(data_version: str | None = None) -> int:
    """Age-band reference year. Priority: data base date (_meta.version) > system year."""
    if data_version:
        try:
            return int(data_version[:4])
        except (ValueError, TypeError):
            pass
    from datetime import date

    return date.today().year


CURRENT_YEAR = _derive_current_year(TDF_VERSION)

ROW_RE = re.compile(r"^\s*(\d+)\.\s*(.+)$")
RISK_RE = re.compile(r"^(.+?)([1-6])$")
TARGET_YEAR_RE = re.compile(r"(?<!\d)(20(?:1[5-9]|[2-5]\d|60))(?!\d)")


@dataclass(frozen=True)
class CliArgs:
    input: str
    output: str
    fees: bool
    all_dir: str
    allow_unresolved: bool


JsonValue = str | int | bool | None | list[int]
FundRecord = dict[str, JsonValue]
JsonObject = dict[str, object]


def parse_args() -> CliArgs:
    parser = argparse.ArgumentParser(
        description="Convert pasted SEMA TDF markdown table to tdf_data.json"
    )
    _ = parser.add_argument(
        "--input", required=False, default="", help="Path to tdf-raw-table.md (table-parse mode)"
    )
    _ = parser.add_argument(
        "--output",
        default="funds/tdf_data.json",
        help="Output JSON path (default: funds/tdf_data.json)",
    )
    _ = parser.add_argument(
        "--fees",
        action="store_true",
        help="Deterministic local enrichment: resolve fundCode + totalFee from funds/all/*",
    )
    _ = parser.add_argument(
        "--all-dir",
        default="",
        help="Directory holding all_fund_data.json/all_fund_fees.json (default: <output_dir>/all)",
    )
    _ = parser.add_argument(
        "--allow-unresolved",
        action="store_true",
        help="Exit 0 (warn only) even when unresolved/missing rows remain",
    )
    namespace = parser.parse_args()
    parsed = cast(dict[str, object], vars(namespace))
    return CliArgs(
        input=str(parsed["input"]),
        output=str(parsed["output"]),
        fees=bool(parsed["fees"]),
        all_dir=str(parsed["all_dir"]),
        allow_unresolved=bool(parsed["allow_unresolved"]),
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


def derive_recommended_age_band(
    targetYear: int,
    current_year: int = CURRENT_YEAR,
    retirement_age: int = RETIREMENT_AGE,
) -> list[int]:
    birth_year = targetYear - retirement_age
    current_age = current_year - birth_year
    return [round_to_nearest_five(current_age - 5), round_to_nearest_five(current_age + 5)]


def derive_tdf_qualified(name: str) -> dict[str, bool]:
    has_qualified_token = "적격" in name
    return {"qualified": True, "needsReview": not has_qualified_token}


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


_STRIP_TOKENS = ("적격", "종류", "CLASS", "클래스")
_SEP_RE = re.compile(r"[\s_/\[\]\(\)\{\}\.,·\-]")
_SHARE_CLASS_RE = re.compile(r"C[-]?[A-Z0-9]+")

# Return-unit contract (the two sources express returns differently):
#   all_fund_data.json (제로인 상품제안서 CSV): 6M/1Y = 누적(cumulative),
#                                              3Y/5Y/7Y/10Y = 연환산(annualized).
#   tdf_data.json (pasted 제로인 web/HTS):      ALL horizons = 누적(cumulative).
# Cross-validation MUST normalize to one basis before thresholding; comparing
# 누적(~100%) against 연환산(~25%) directly trips a false warning on every TDF.
# Maps an authoritative annualized field to its compounding horizon (years).
ANNUALIZED_HORIZON_YEARS: dict[str, int] = {
    "return3y": 3,
    "return5y": 5,
    "return7y": 7,
    "return10y": 10,
}

# Soft drift threshold (percentage points). Raised from 0.20 to absorb base-date
# drift between the TDF paste date and the all_fund_data 기준일 (관측 최대 ~3.7%p
# @1Y across 75 TDFs). After unit normalization genuine paste/code errors remain
# far larger (단위 혼동 시 수십 %p), so 5.0%p suppresses noise without masking errors.
RETURN_TOLERANCE_PP = 5.0
SIMILARITY_THRESHOLD = 0.92


def _normalize_strict(name: str) -> str:
    s = unicodedata.normalize("NFKC", name).upper()
    for tok in _STRIP_TOKENS:
        s = s.replace(tok.upper(), "")
    s = _SEP_RE.sub("", s)
    return s


def canonicalize_name(name: str) -> dict[str, object]:
    """Canonicalize a Korean fund name for deterministic matching.

    Returns `key` (vehicle-token collapsed, used for exact match), `key_strict`
    (preserves the 증권자투자신탁 vs 증권투자신탁 difference, used for needsReview
    detection), plus extracted `year` and `hedge`. Share class, target year and
    hedge are preserved inside the key and never collapsed.
    """
    strict = _normalize_strict(name)
    key = strict.replace("증권자투자신탁", "증권투자신탁")
    return {
        "key": key,
        "key_strict": strict,
        "year": derive_target_year(name),
        "hedge": derive_hedge(name),
    }


def _share_class_hint(name: str) -> str:
    match = _SHARE_CLASS_RE.search(unicodedata.normalize("NFKC", name).upper())
    return match.group(0) if match else ""


def build_authoritative_index(all_fund_data: JsonObject, all_fund_fees: JsonObject) -> JsonObject:
    """Index the authoritative TDF universe by canonical key (fundCode-joined fee)."""
    fees = cast(dict[str, JsonObject], all_fund_fees.get("fees", {}))
    by_key: dict[str, JsonObject] = {}
    ambiguous: set[str] = set()
    records: list[JsonObject] = []
    for fund in cast(list[JsonObject], all_fund_data.get("funds", [])):
        name = str(fund.get("name", ""))
        if "TDF" not in name.upper():
            continue
        canon = canonicalize_name(name)
        code = str(fund.get("fundCode", ""))
        rec: JsonObject = {
            "fundCode": code,
            "fundName": name,
            "totalFee": str(fees.get(code, {}).get("totalFee", "")),
            "return6m": fund.get("return6m", ""),
            "return1y": fund.get("return1y", ""),
            "return3y": fund.get("return3y", ""),
            "riskLevel": fund.get("riskLevel"),
            "key": canon["key"],
            "key_strict": canon["key_strict"],
            "year": canon["year"],
            "hedge": canon["hedge"],
        }
        records.append(rec)
        key = cast(str, canon["key"])
        if key in by_key:
            ambiguous.add(key)
        else:
            by_key[key] = rec
    return {"by_key": by_key, "ambiguous": ambiguous, "records": records}


def resolve_tdf_row(row: JsonObject, _index: int, auth_index: JsonObject) -> JsonObject:
    """Resolve one TDF row to an authoritative fundCode via canonical-exact match.

    Auto-resolve only when the canonical key is unique AND target year + hedge agree.
    Similarity (>=0.92) is used solely to populate candidateCodes, never to resolve.
    """
    name = str(row.get("name", ""))
    canon = canonicalize_name(name)
    by_key = cast(dict[str, JsonObject], auth_index["by_key"])
    ambiguous = cast(set[str], auth_index["ambiguous"])
    result: JsonObject = {
        "status": "unresolved",
        "fundCode": None,
        "needsReview": False,
        "differences": [],
        "candidateCodes": [],
        "reason": None,
    }
    key = cast(str, canon["key"])
    if key in by_key and key not in ambiguous:
        rec = by_key[key]
        if rec["year"] == canon["year"] and rec["hedge"] == canon["hedge"]:
            result["status"] = "resolved"
            result["fundCode"] = rec["fundCode"]
            if canon["key_strict"] != rec["key_strict"]:
                result["needsReview"] = True
                cast(list[str], result["differences"]).append("vehicle")
            return result

    candidates: list[tuple[float, JsonObject]] = []
    for rec in cast(list[JsonObject], auth_index["records"]):
        ratio = SequenceMatcher(None, cast(str, canon["key_strict"]), cast(str, rec["key_strict"])).ratio()
        if ratio >= SIMILARITY_THRESHOLD:
            candidates.append((ratio, rec))
    candidates.sort(key=lambda pair: -pair[0])
    for _ratio, rec in candidates[:5]:
        reason = "shareClass mismatch" if rec["year"] == canon["year"] else "year/class mismatch"
        cast(list[JsonObject], result["candidateCodes"]).append({
            "fundCode": rec["fundCode"],
            "fundName": rec["fundName"],
            "shareClass": _share_class_hint(cast(str, rec["fundName"])),
            "totalFee": rec["totalFee"],
            "reason": reason,
        })
    result["reason"] = "no canonical-exact match in authoritative index"
    return result


def reconcile_fee(fund_code: str, all_fund_fees: JsonObject) -> JsonObject:
    """Return the authoritative totalFee (string) for a fundCode, or missing.

    A code present with an empty/blank totalFee is treated as missing, not verified,
    so it is surfaced (never silently blessed with an empty fee).
    """
    fees = cast(dict[str, JsonObject], all_fund_fees.get("fees", {}))
    if fund_code in fees:
        value = str(fees[fund_code].get("totalFee", "")).strip()
        if value:
            return {"status": "verified", "value": value}
    return {"status": "missing", "value": ""}


def _to_float(value: object) -> float | None:
    try:
        return float(cast(str, value))
    except (TypeError, ValueError):
        return None


def _cumulative_to_annualized(cumulative_pct: float, years: int) -> float:
    return ((1.0 + cumulative_pct / 100.0) ** (1.0 / years) - 1.0) * 100.0


def cross_validate_tdf_row(tdf_row: JsonObject, auth_row: JsonObject) -> list[JsonObject]:
    """Soft-validate overlapping returns + riskLevel against the authoritative row.

    Returns are unit-normalized before thresholding: tdf_data is 누적(cumulative)
    for every horizon, while all_fund_data is 연환산(annualized) for 3Y/5Y/7Y/10Y
    and 누적 for 6M/1Y. For the annualized horizons the tdf cumulative value is
    converted to annualized so both sides share one basis (avoids the false ~80%p
    mismatch that 누적 vs 연환산 직접 비교 produced on every TDF). Remaining diffs
    are soft (base-date drift); riskLevel mismatch is escalated to needsReview.
    """
    warnings: list[JsonObject] = []
    for field in ("return6m", "return1y", "return3y"):
        a = _to_float(tdf_row.get(field))
        b = _to_float(auth_row.get(field))
        if a is None or b is None:
            continue
        years = ANNUALIZED_HORIZON_YEARS.get(field)
        if years is not None:
            a_cmp = _cumulative_to_annualized(a, years)
            basis = "annualized"
            note = "기준일 drift 가능 · tdf 누적→연환산 정규화 후 비교"
        else:
            a_cmp = a
            basis = "cumulative"
            note = "기준일 drift 가능 · 누적 기준 비교"
        if abs(a_cmp - b) > RETURN_TOLERANCE_PP:
            warnings.append({
                "field": field,
                "tdf": tdf_row.get(field),
                "auth": auth_row.get(field),
                "basis": basis,
                "normalizedDelta": round(a_cmp - b, 2),
                "severity": "soft",
                "note": note,
            })
    rt = tdf_row.get("riskLevel")
    ra = auth_row.get("riskLevel")
    if rt is not None and ra is not None and rt != ra:
        warnings.append({"field": "riskLevel", "tdf": rt, "auth": ra, "severity": "needsReview"})
    return warnings


def _verified_fee_record(
    code: str,
    name: str,
    orig_ter: str,
    value: str,
    all_fund_fees: JsonObject,
    checked_at: str,
) -> JsonObject:
    meta = cast(JsonObject, all_fund_fees.get("_meta", {}))
    src_csv = str(meta.get("sourceFile", ""))
    return {
        "fundCode": code,
        "fundName": name,
        "totalFee": value,
        "ter": orig_ter,
        "feeVerification": {
            "status": "verified",
            "authority": "official-csv",
            "value": value,
            "agree": True,
            "checkedAt": checked_at,
            "sources": [{
                "name": "SEMA monthly product proposal CSV",
                "type": "local-authoritative-csv",
                "path": ("resource/" + src_csv) if src_csv else "",
                "derivedFrom": "funds/all/all_fund_fees.json",
                "fundCode": code,
                "value": value,
                "baseDate": str(meta.get("version", "")),
                "note": "totalFee copied from all_fund_fees[fundCode].totalFee",
            }],
        },
    }


def _missing_fee_record(code: str, name: str, orig_ter: str, checked_at: str) -> JsonObject:
    return {
        "fundCode": code,
        "fundName": name,
        "totalFee": "",
        "ter": orig_ter,
        "feeVerification": {
            "status": "missing", "authority": "none", "value": "", "agree": False,
            "checkedAt": checked_at, "sources": [],
            "note": "fundCode not present in all_fund_fees",
        },
    }


def _unresolved_fee_record(code: str, name: str, orig_ter: str, checked_at: str) -> JsonObject:
    return {
        "fundCode": code,
        "fundName": name,
        "totalFee": "",
        "ter": orig_ter,
        "feeVerification": {
            "status": "unresolved", "authority": "none", "value": "", "agree": False,
            "checkedAt": checked_at, "sources": [],
            "note": "no authoritative CSV fee because no exact code resolution",
        },
    }


def enrich_tdf_rows(
    tdf_data: JsonObject,
    tdf_fees: JsonObject,
    all_fund_data: JsonObject,
    all_fund_fees: JsonObject,
    checked_at: str | None = None,
) -> JsonObject:
    """Deterministically enrich TDF data/fees from the authoritative all_fund universe.

    - Already-coded rows: reconcile totalFee by EXISTING fundCode (no name match).
    - UNKNOWN_* rows: resolve fundCode by canonical-exact name match (guard-railed).
    - Unresolved/missing rows are surfaced in additive `_meta`, never silently dropped.
    """
    checked_at = checked_at or datetime.now().astimezone().date().isoformat()
    auth_index = build_authoritative_index(all_fund_data, all_fund_fees)
    auth_by_code: dict[str, JsonObject] = {
        str(f.get("fundCode", "")): f for f in cast(list[JsonObject], all_fund_data.get("funds", []))
    }
    fees_in = cast(dict[str, JsonObject], tdf_fees.get("fees", {}))

    out_data = copy.deepcopy(tdf_data)
    new_fees: dict[str, JsonObject] = {}
    seen_codes: set[str] = set()
    unresolved: list[JsonObject] = []
    needs_review: list[JsonObject] = []
    missing: list[str] = []
    validation_warnings: list[JsonObject] = []
    code_name_mismatch: list[JsonObject] = []
    resolved_unknown = 0

    def put_fee(code: str, rec: JsonObject) -> None:
        if code in seen_codes:
            raise ValueError(f"duplicate resolved fundCode during enrichment: {code}")
        seen_codes.add(code)
        new_fees[code] = rec

    def record_cross_validation(code: str, name: str, idx: int, fund: JsonObject) -> None:
        auth_row = auth_by_code.get(code)
        if not auth_row:
            return
        for warn in cross_validate_tdf_row(fund, auth_row):
            if warn["severity"] == "needsReview":
                needs_review.append({
                    "index": idx, "fundCode": code, "fundName": name,
                    "reason": f"{warn['field']} mismatch tdf={warn['tdf']} auth={warn['auth']}",
                    "differences": [warn["field"]], "accepted": True,
                })
            else:
                validation_warnings.append({"index": idx, "fundCode": code, **warn})

    for idx, fund in enumerate(cast(list[JsonObject], out_data.get("funds", []))):
        orig_code = str(fund.get("fundCode", ""))
        name = str(fund.get("name", ""))
        orig_ter = str(fees_in.get(orig_code, {}).get("ter", ""))

        if orig_code.startswith("UNKNOWN"):
            res = resolve_tdf_row(fund, idx, auth_index)
            if res["status"] == "resolved":
                resolved_unknown += 1
                new_code = cast(str, res["fundCode"])
                fund["fundCode"] = new_code
                if res["needsReview"]:
                    matched = cast(dict[str, JsonObject], auth_index["by_key"])[cast(str, canonicalize_name(name)["key"])]
                    needs_review.append({
                        "index": idx, "fundCode": new_code, "fundName": name,
                        "matchedFundName": matched["fundName"],
                        "reason": "resolved after safe vehicle-token normalization",
                        "differences": res["differences"], "accepted": True,
                    })
                fee = reconcile_fee(new_code, all_fund_fees)
                if fee["status"] == "verified":
                    put_fee(new_code, _verified_fee_record(new_code, name, orig_ter, cast(str, fee["value"]), all_fund_fees, checked_at))
                    record_cross_validation(new_code, name, idx, fund)
                else:
                    if new_code not in missing:
                        missing.append(new_code)
                    put_fee(new_code, _missing_fee_record(new_code, name, orig_ter, checked_at))
            else:
                unresolved.append({
                    "index": idx, "placeholderCode": orig_code, "fundName": name,
                    "company": fund.get("company", ""), "targetYear": fund.get("targetYear"),
                    "shareClass": _share_class_hint(name), "hedge": fund.get("hedge"),
                    "reason": res["reason"], "candidateCodes": res["candidateCodes"],
                })
                put_fee(orig_code, _unresolved_fee_record(orig_code, name, orig_ter, checked_at))
        else:
            auth_row = auth_by_code.get(orig_code)
            if auth_row is not None:
                row_canon = canonicalize_name(name)
                auth_canon = canonicalize_name(str(auth_row.get("name", "")))
                if row_canon["key"] != auth_canon["key"]:
                    code_name_mismatch.append({
                        "index": idx, "fundCode": orig_code, "fundName": name,
                        "authoritativeName": auth_row.get("name", ""),
                        "reason": "row name does not canonically match the authoritative name for this fundCode",
                    })
                elif row_canon["key_strict"] != auth_canon["key_strict"]:
                    needs_review.append({
                        "index": idx, "fundCode": orig_code, "fundName": name,
                        "matchedFundName": auth_row.get("name", ""),
                        "reason": "resolved after safe vehicle-token normalization",
                        "differences": ["vehicle"], "accepted": True,
                    })
            fee = reconcile_fee(orig_code, all_fund_fees)
            if fee["status"] == "verified":
                put_fee(orig_code, _verified_fee_record(orig_code, name, orig_ter, cast(str, fee["value"]), all_fund_fees, checked_at))
                record_cross_validation(orig_code, name, idx, fund)
            else:
                if orig_code not in missing:
                    missing.append(orig_code)
                put_fee(orig_code, _missing_fee_record(orig_code, name, orig_ter, checked_at))

    enrichment_meta: JsonObject = {
        "method": "canonical-name-exact",
        "authoritativeFundData": "funds/all/all_fund_data.json",
        "authoritativeFeeData": "funds/all/all_fund_fees.json",
        "sourceCsv": str(cast(JsonObject, all_fund_fees.get("_meta", {})).get("sourceFile", "")),
        "checkedAt": checked_at,
        "resolvedUnknownCount": resolved_unknown,
        "unresolvedCount": len(unresolved),
        "missingCount": len(missing),
        "needsReviewCount": len(needs_review),
        "codeNameMismatchCount": len(code_name_mismatch),
    }
    resolved_total = sum(
        1 for f in cast(list[JsonObject], out_data.get("funds", []))
        if not str(f.get("fundCode", "")).startswith("UNKNOWN")
    )

    def attach_meta(target: JsonObject, *, with_record_count: int | None = None) -> None:
        meta = cast(JsonObject, target.setdefault("_meta", {}))
        meta["enrichment"] = enrichment_meta
        meta["missing"] = missing
        meta["unresolved"] = unresolved
        meta["needsReview"] = needs_review
        meta["validationWarnings"] = validation_warnings
        meta["codeNameMismatch"] = code_name_mismatch
        meta["resolvedFundCodeCount"] = resolved_total
        meta["unresolvedFundCodeCount"] = len(unresolved)
        if with_record_count is not None:
            meta["recordCount"] = with_record_count

    attach_meta(out_data)

    out_fees = copy.deepcopy(tdf_fees)
    out_fees["fees"] = new_fees
    attach_meta(out_fees, with_record_count=len(new_fees))

    return {
        "tdf_data": out_data,
        "tdf_fees": out_fees,
        "exit_code": 2 if (unresolved or missing) else 0,
        "summary": enrichment_meta,
    }


def _print_enrichment_report(result: JsonObject, stream: TextIO) -> None:
    summary = cast(JsonObject, result["summary"])
    meta = cast(JsonObject, cast(JsonObject, result["tdf_data"])["_meta"])
    unresolved = cast(list[JsonObject], meta.get("unresolved", []))
    missing = cast(list[str], meta.get("missing", []))
    code_name_mismatch = cast(list[JsonObject], meta.get("codeNameMismatch", []))
    has_gap = bool(unresolved or missing)
    header = "WARNING: TDF enrichment completed with gaps" if has_gap else "INFO: TDF enrichment completed"
    print("=" * 64, file=stream)
    print(header, file=stream)
    print(f"- resolved UNKNOWN: {summary['resolvedUnknownCount']}", file=stream)
    print(f"- unresolved:       {summary['unresolvedCount']}", file=stream)
    print(f"- missing fees:     {summary['missingCount']}", file=stream)
    print(f"- needsReview:      {summary['needsReviewCount']}", file=stream)
    print(f"- codeNameMismatch: {summary['codeNameMismatchCount']}", file=stream)
    if unresolved:
        print("\nUnresolved (human action required):", file=stream)
        for item in unresolved:
            print(f"  [{item['index']}] {item['placeholderCode']} {item['fundName']}", file=stream)
            print(f"      reason: {item['reason']}", file=stream)
            for cand in cast(list[JsonObject], item.get("candidateCodes", [])):
                print(f"      candidate: {cand['fundCode']} ({cand['reason']}) fee={cand['totalFee']}", file=stream)
    if missing:
        print(f"\nMissing authoritative fees for codes: {missing}", file=stream)
    if code_name_mismatch:
        print("\nName advisory (fundCode kept; row name differs from authoritative name):", file=stream)
        for item in code_name_mismatch:
            print(f"  [{item['index']}] {item['fundCode']} row='{item['fundName']}' auth='{item['authoritativeName']}'", file=stream)
    if has_gap:
        print("\nRe-run with --allow-unresolved to accept these known gaps.", file=stream)
    print("=" * 64, file=stream)


def run_enrichment(args: CliArgs) -> int:
    out_path = Path(args.output)
    funds_dir = out_path.parent
    all_dir = Path(args.all_dir) if args.all_dir else funds_dir / "all"
    fees_path = funds_dir / "tdf_fees.json"

    tdf_data = cast(JsonObject, json.loads(out_path.read_text(encoding="utf-8")))
    tdf_fees = cast(JsonObject, json.loads(fees_path.read_text(encoding="utf-8")))
    all_fund_data = cast(JsonObject, json.loads((all_dir / "all_fund_data.json").read_text(encoding="utf-8")))
    all_fund_fees = cast(JsonObject, json.loads((all_dir / "all_fund_fees.json").read_text(encoding="utf-8")))

    result = enrich_tdf_rows(tdf_data, tdf_fees, all_fund_data, all_fund_fees)

    _ = out_path.write_text(json.dumps(result["tdf_data"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _ = fees_path.write_text(json.dumps(result["tdf_fees"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _print_enrichment_report(result, sys.stderr)
    print(f"Wrote {out_path}")
    print(f"Wrote {fees_path}")

    if result["exit_code"] == 2 and not args.allow_unresolved:
        return 2
    return 0


def main() -> int:
    args = parse_args()
    if args.fees:
        return run_enrichment(args)
    if not args.input:
        print("Error: --input is required in table-parse mode (or use --fees).", file=sys.stderr)
        return 2
    text = Path(args.input).read_text(encoding="utf-8")
    funds = parse_tdf_table(text)
    _ = write_json(funds, args.output)
    print(f"Parsed {len(funds)} TDF funds")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    exit_code = main()
    if exit_code == 0:
        from _consistency_gate import run_consistency_gate

        run_consistency_gate()
    raise SystemExit(exit_code)
