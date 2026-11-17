#!/usr/bin/env python3
"""지수 검증·신선도 상태를 JSON으로 반환한다. 결측은 정상적인 결과다."""

import argparse
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Final, TypeAlias, TypedDict
from urllib.parse import urlsplit

Json: TypeAlias = dict[str, "Json"] | list["Json"] | str | int | float | bool | None
SERIES: Final = ("KOSPI", "KOSDAQ", "S&P 500", "NASDAQ", "USD/KRW", "EUR/KRW", "JPY/KRW")


class SeriesStatus(TypedDict):
    status: str
    age_days: int | None


def rows(value: Json, key: str = "") -> list[dict[str, Json]]:
    """배열, 이름별 객체, stock_indices/currencies 그룹을 같은 행으로 읽는다."""
    match value:
        case list():
            return [row for item in value for row in rows(item)]
        case dict():
            if "value" in value or "verified" in value:
                return [{**value, "name": value.get("name", key)}]
            return [row for name, item in value.items() for row in rows(item, name)]
        case _:
            return []


def data_date(value: Json) -> date | None:
    match value:
        case str():
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        case _:
            return None


def finite_number(value: Json) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def classify(row: dict[str, Json], fallback: Json, today: date) -> SeriesStatus:
    """verified 표시만 믿지 않고 출처·원문·동일 기준일·편차를 검사한다."""
    missing: SeriesStatus = {"status": "missing", "age_days": None}
    value = row.get("value")
    sources = row.get("sources")
    if row.get("verified") is not True or not finite_number(value) or value <= 0:
        return missing
    if not isinstance(sources, list) or len(sources) < 3:
        return missing
    domains: set[str] = set()
    dates: set[date] = set()
    for source in sources:
        if not isinstance(source, dict):
            return missing
        url = source.get("url")
        quote = source.get("original_text")
        observed = source.get("observed_value")
        if not isinstance(url, str) or not isinstance(quote, str) or not quote.strip():
            return missing
        host = urlsplit(url).hostname
        if not host or not finite_number(observed) or abs(observed - value) / value > 0.01:
            return missing
        domains.add(host.lower().removeprefix("www."))
        day = data_date(source.get("date") or source.get("reference_date")
                        or row.get("date") or row.get("data_date")
                        or row.get("reference_date") or fallback)
        if day is None or day > today:
            return missing
        dates.add(day)
    if len(domains) < 3 or len(dates) != 1:
        return missing
    age = (today - next(iter(dates))).days
    return {"status": "stale" if age > 7 else "verified", "age_days": age}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now().astimezone().date())
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print("입력은 JSON 객체여야 합니다.", file=sys.stderr)
            return 1
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"입력을 읽을 수 없습니다: {error}", file=sys.stderr)
        return 1
    aliases = {name.replace(" ", "").replace("/", "").upper(): name for name in SERIES}
    found = {}
    fallback = payload.get("data_date") or payload.get("reference_date") or payload.get("timestamp")
    for row in rows(payload.get("indices")):
        name = str(row.get("name", "")).replace(" ", "").replace("/", "").upper()
        if name in aliases:
            found[aliases[name]] = classify(row, fallback, args.as_of)
    statuses = {name: found.get(name, {"status": "missing", "age_days": None}) for name in SERIES}
    usable = [name for name in SERIES if statuses[name]["status"] == "verified"]
    missing = [name for name in SERIES if name not in usable]
    mode = "full" if not missing else "partial" if usable else "none"
    print(json.dumps({"mode": mode, "as_of": args.as_of.isoformat(), "series": statuses,
                      "usable": usable, "missing": missing}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
