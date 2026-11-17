#!/usr/bin/env python3
"""leadership-analysis.json의 주장을 종류별 출처 기준으로 판정하고 decision_usable을 낸다.

기준(web-search-verifier '주장 종류별 출처 기준'):
- official_fact(현직 인물·직함, 중앙은행 기준금리): 발표 기관 호스트의 1차 출처 1곳(URL·조회 시각·원문)
  으로 확정. 발표 기관 사이트가 열리지 않으면 기존 독립 3출처(원발행자 기준) 규칙. 값이 다른 출처가
  하나라도 있으면 실패.
- interpretation(정책 성향·배분 시사점): 해석 표시 필수, 배분에는 확대·유지·축소 방향만.
- market_number(지수·환율)는 index_status.py의 3출처 규칙 그대로라 여기서 다루지 않는다.
decision_usable은 파일의 자기 신고값이 아니라 7개국 지도자·기준금리가 모두 확정되고 해석 위반이 없을 때 true.
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit

FRESH_DAYS: Final = 7
DIRECTIONS: Final = ("확대", "유지", "축소")
NUMERIC_KEYS: Final = ("weight", "target_weight", "target_pct", "pct", "percent", "allocation_pct")
# 발표 기관 호스트(접미사 일치). 지도자·경제팀은 정부, 기준금리·총재는 중앙은행.
ISSUERS: Final = {
    "미국": {"government": ("whitehouse.gov", "treasury.gov"), "central_bank": ("federalreserve.gov", "newyorkfed.org")},
    "중국": {"government": ("gov.cn",), "central_bank": ("pbc.gov.cn", "chinamoney.com.cn")},
    "한국": {"government": ("president.go.kr", "korea.kr", "moef.go.kr", "mofe.go.kr"), "central_bank": ("bok.or.kr",)},
    "일본": {"government": ("kantei.go.jp", "mof.go.jp"), "central_bank": ("boj.or.jp",)},
    "인도": {"government": ("pmindia.gov.in", "pib.gov.in", "india.gov.in", "finmin.gov.in"), "central_bank": ("rbi.org.in",)},
    "베트남": {"government": ("chinhphu.vn", "baochinhphu.vn", "vietnam.gov.vn", "dangcongsan.vn", "mof.gov.vn"),
             "central_bank": ("sbv.gov.vn",)},
    "인도네시아": {"government": ("presidenri.go.id", "setneg.go.id", "setkab.go.id", "indonesia.go.id", "kemenkeu.go.id"),
              "central_bank": ("bi.go.id",)},
}


def host(url: object) -> str:
    return (urlsplit(url).hostname or "").lower().removeprefix("www.") if isinstance(url, str) else ""


def is_issuer(url: object, hosts: tuple[str, ...]) -> bool:
    name = host(url)
    return any(name == h or name.endswith("." + h) for h in hosts)


def accessed_day(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def norm(value: object) -> str:
    return str(value).replace("%", "").replace(" ", "").replace("~", "-") if value is not None else ""


def quoted(source: dict) -> bool:
    return isinstance(source.get("url"), str) and isinstance(source.get("original_text"), str) \
        and bool(source["original_text"].strip())


def official(claim: object, hosts: tuple[str, ...], today: date, numeric: bool) -> dict:
    if not isinstance(claim, dict):
        return {"status": "MISSING", "basis": None}
    if claim.get("claim_type") != "official_fact":
        return {"status": "CLAIM_TYPE_MISSING", "basis": None}
    sources = claim.get("sources", claim.get("verification_sources"))
    sources = [s for s in sources if isinstance(s, dict)] if isinstance(sources, list) else []
    value = claim.get("value")
    if numeric:
        if value is None or not isinstance(claim.get("decision_date"), str):
            return {"status": "VALUE_OR_DECISION_DATE_MISSING", "basis": None}
        decided = accessed_day(claim["decision_date"])
        if decided is None or decided > today:
            return {"status": "VALUE_OR_DECISION_DATE_MISSING", "basis": None}
        if any("observed_value" in s and norm(s["observed_value"]) != norm(value) for s in sources):
            return {"status": "VALUE_MISMATCH", "basis": None}
    for source in sources:
        day = accessed_day(source.get("accessed_at"))
        if quoted(source) and is_issuer(source["url"], hosts) and day is not None \
                and 0 <= (today - day).days <= FRESH_DAYS:
            return {"status": "VERIFIED", "basis": "issuer_primary", "url": source["url"],
                    "accessed_at": source["accessed_at"]}
    origins = {str(s.get("independent_origin") or host(s.get("url"))) for s in sources
               if quoted(s) and (not numeric or norm(s.get("observed_value")) == norm(value))}
    if len(origins) >= 3:
        return {"status": "VERIFIED", "basis": "independent_3", "origins": sorted(origins)}
    return {"status": "ISSUER_PRIMARY_MISSING", "basis": None}


def interpretation_issues(doc: dict, countries: list[dict]) -> list[str]:
    issues = []
    for row in countries:
        policy = row.get("policy_orientation")
        if isinstance(policy, dict) and policy.get("claim_type") != "interpretation":
            issues.append(f"{row.get('country')}.policy_orientation: 해석 표시(claim_type=interpretation) 없음")
    implications = doc.get("allocation_implications")
    regional = implications.get("regional", []) if isinstance(implications, dict) else []
    for index, item in enumerate(regional if isinstance(regional, list) else []):
        where = f"allocation_implications.regional[{index}]"
        if not isinstance(item, dict):
            issues.append(f"{where}: 객체가 아님")
            continue
        if item.get("claim_type") != "interpretation" or item.get("is_inference") is not True:
            issues.append(f"{where}: 해석 표시(claim_type=interpretation, is_inference=true) 없음")
        if item.get("recommendation") not in DIRECTIONS:
            issues.append(f"{where}: 방향은 확대·유지·축소 중 하나")
        if any(item.get(key) is not None for key in NUMERIC_KEYS):
            issues.append(f"{where}: 해석은 방향(확대·유지·축소)만, 수치 비중 금지")
    return issues


def evaluate(doc: dict, today: date) -> dict:
    rows = [row for row in doc.get("countries", []) if isinstance(row, dict)] \
        if isinstance(doc.get("countries"), list) else []
    by_name = {row.get("country"): row for row in rows}
    report, missing, issues = {}, [], []
    for name, hosts in ISSUERS.items():
        row = by_name.get(name, {})
        bank = row.get("central_bank") if isinstance(row.get("central_bank"), dict) else {}
        leader = official(row.get("leader"), hosts["government"], today, numeric=False)
        rate = official(bank.get("rate_claim"), hosts["central_bank"], today, numeric=True)
        optional = {
            "economic_team": official(row.get("economic_team"), hosts["government"], today, numeric=False),
            "governor": official(bank.get("governor_claim"), hosts["central_bank"], today, numeric=False),
        }
        rate["value"] = bank.get("current_rate")
        report[name] = {"leader": leader, "central_bank_rate": rate,
                        "optional": {k: v["status"] for k, v in optional.items()}}
        for key, result in (("leader", leader), ("central_bank_rate", rate)):
            if result["status"] != "VERIFIED":
                missing.append(f"{name}.{key}")
        if bank.get("current_rate") is not None and rate["status"] != "VERIFIED":
            issues.append(f"{name}.current_rate: 확정되지 않은 수치가 표시됨")
    issues += interpretation_issues(doc, rows)
    return {"as_of": today.isoformat(), "decision_usable": not missing and not issues,
            "missing": missing, "issues": issues, "countries": report}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now().astimezone().date())
    args = parser.parse_args()
    try:
        doc = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ValueError("JSON 객체가 아님")
    except (OSError, UnicodeError, ValueError) as error:
        print(f"입력을 읽을 수 없습니다: {error}", file=sys.stderr)
        return 1
    print(json.dumps(evaluate(doc, args.as_of), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
