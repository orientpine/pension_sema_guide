#!/usr/bin/env python3
"""형이 따르는 추천안의 지금 비중을 대리 시계열로 추정하고, 정해 둔 규칙이 새로 걸릴 때만 알린다.

실행 기준(안·실행일·선택 납입 기록) → 펀드별 대리(지수·ETF NAV·예금 금리)의 실행일 대비 변화 → 추정 평가액
→ policy_alloc.rebalance(묶음 밴드·70% 근처 좁은 밴드·정수 거래안) + dc_limits.check(70% 초과·단일 40%) + 쏠림(SKILL §4.2)
→ 지난번 알린 이탈과 비교해 새 이탈만 SEND.

check·mark-sent·summary는 외부 접속 없이 Decimal로 계산하고 같은 입력이면 같은 바이트를 낸다(벽시계 시각을 쓰지 않음).
대리 하나라도 비면(기준일 7일 안 값 없음·대응표에 없음·예금 금리 없음) 추정하지 않고 알리지 않는다.
출력에는 금액을 넣지 않는다(비중·정수 %만). fetch만 KRX Open API에 접속한다(키 값은 출력하지 않음).
FRED는 약관이 받은 자료의 저장·캐시를 금지하고, ECOS는 이용 지침 원문을 아직 확인하지 못해 대리로 쓰지 않는다.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dc_limits as dc  # noqa: E402
import policy_alloc as pa  # noqa: E402
from dc_limits import InputError, mapping, rows, text  # noqa: E402

ZERO, HUNDRED = Decimal(0), Decimal(100)
NOTIONAL = Decimal(100_000_000)
STALE_DAYS = 7
PROXY_KINDS = {"index": "인덱스 대리(오차 작음)", "active": "액티브 대리(오차 큼, 참고)"}
# SKILL.md §4.2 섹터 집중 한도. gold는 classify_funds.py가 '퇴직연금'의 '금'을 골드로 잘못 표시해 뺀다.
THEMES = {"semiconductor", "ai", "robot", "healthcare", "energy", "ev", "space", "reits"}
THEME_LIMIT, TECH_AI, TECH_AI_LIMIT = Decimal(30), {"semiconductor", "ai", "robot"}, Decimal(40)
REGION_LIMIT, EM, EM_LIMIT = Decimal(50), {"china", "india", "vietnam", "brazil", "emerging", "asean", "asia"}, Decimal(30)
REGION_NAMES = {"korea": "한국", "us": "미국", "europe": "유럽", "japan": "일본", "china": "중국", "india": "인도",
                "asia": "아시아", "emerging": "신흥국", "vietnam": "베트남", "brazil": "브라질", "asean": "아세안"}
KRX_BASE = "https://data-dbg.krx.co.kr/svc/apis/"
PART_MAX = 1900
SOURCES = {"krx_etf_nav": "etp/etf_bydd_trd", "krx_index": None}


def day(value: object, label: str) -> date:
    try:
        return date.fromisoformat(text(value, label))
    except ValueError as exc:
        raise InputError(f"{label}: YYYY-MM-DD 필요") from exc


def pct(value: Decimal) -> str:
    return f"{value:.1f}"


class Missing(Exception):
    pass


def price(store: dict, series: str, when: date) -> tuple[Decimal, date]:
    values = mapping(store.get(series, {}), f"시계열 {series}")
    seen = [d for d in values if d <= when.isoformat()]
    if not seen:
        raise Missing(f"{series}: {when} 이전 값 없음")
    last = max(seen)
    if (when - date.fromisoformat(last)).days > STALE_DAYS:
        raise Missing(f"{series}: {when} 기준 {STALE_DAYS}일 안 값 없음(마지막 {last})")
    try:
        value = dc.number(values[last], f"{series}.{last}")
    except InputError as exc:
        raise Missing(f"{series}.{last}: 쓸 수 없는 값({exc})") from None
    if value <= 0:
        raise Missing(f"{series}.{last}: 값이 0 이하라 가격 관측으로 쓰지 않음")
    return value, date.fromisoformat(last)


def add_months(when: date, months: int) -> date:
    index = when.year * 12 + when.month - 1 + months
    year, month = divmod(index, 12)
    for day_of_month in range(when.day, 0, -1):
        try:
            return date(year, month + 1, day_of_month)
        except ValueError:
            continue
    raise InputError(f"날짜 계산 오류: {when} + {months}개월")


def load_baseline(path: Path) -> dict:
    data = mapping(dc.load_json(path), "실행 기준")
    meta = mapping(data.get("_meta"), "실행 기준 _meta")
    if meta.get("kind") != "execution-baseline":
        raise InputError("실행 기준 _meta.kind는 execution-baseline이어야 함")
    if meta.get("status") not in ("unset", "set"):
        raise InputError("실행 기준 _meta.status는 unset 또는 set")
    if meta["status"] == "set":
        text(meta.get("source"), "실행 기준 _meta.source(형 원문 링크)")
        text(data.get("plan"), "plan")
        text(data.get("policy"), "policy")
        day(data.get("executedOn"), "executedOn")
        if not data.get("positions"):
            raise InputError("실행 기준 positions 필요: 그날 포털에 넣은 펀드별 정수 비중을 고정해 둔다(정책을 고쳐도 과거가 바뀌지 않게)")
    return data


def load_executions(baseline: dict, base_dir: Path, start: date, until: date) -> list[tuple[date, list[dict]]]:
    """executions.json entries: 형이 포털에 넣어 맞춘 날과 그 뒤 비중. 그날부터 추정을 다시 시작한다."""
    if not baseline.get("executionsLog"):
        return []
    data = mapping(dc.load_json(base_dir / baseline["executionsLog"]), "실행 기록")
    if mapping(data.get("_meta"), "실행 기록 _meta").get("kind") != "executions":
        raise InputError("실행 기록 _meta.kind는 executions여야 함")
    result = []
    for i, entry in enumerate(rows(data.get("entries", []), "entries")):
        when = day(entry.get("date"), f"entries[{i}].date")
        text(entry.get("source"), f"entries[{i}].source(형 원문 링크)")
        if when <= start:
            raise InputError(f"entries[{i}]: 실행일 {when}이 기준 실행일 {start} 이후가 아님")
        if when <= until:
            result.append((when, rows(entry.get("positionsAfter"), f"entries[{i}].positionsAfter")))
    return sorted(result, key=lambda item: item[0])


def load_contributions(baseline: dict, base_dir: Path, start: date, until: date) -> list[dict]:
    if not baseline.get("contributionsLog"):
        return []
    path = base_dir / baseline["contributionsLog"]
    entries = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        entry = mapping(json.loads(line, parse_float=Decimal), f"{path.name}:{number}")
        when = day(entry.get("date"), f"{path.name}:{number}.date")
        if when < start:
            raise InputError(f"{path.name}:{number}: 납입일 {when}이 실행일 {start}보다 앞")
        if when <= until:
            entries.append({**entry, "_date": when, "_amount": pa.whole(entry.get("amount"), f"{path.name}:{number}.amount")})
    return entries


class Proxies:
    def __init__(self, proxy_map: dict, catalog: dc.Catalog, deposits: dict[str, dict]):
        self.series = mapping(proxy_map.get("series", {}), "대응표 series")
        for sid, spec in self.series.items():
            if mapping(spec, f"series {sid}").get("source") not in SOURCES:
                raise InputError(f"series {sid}: source는 {sorted(SOURCES)} 중 하나(FRED 저장 금지, ECOS 약관 미확인)")
        self.by_fund: dict[dc.Fund, dict] = {}
        for i, row in enumerate(rows(proxy_map.get("funds"), "대응표 funds")):
            ref = {k: row[k] for k in ("fundCode", "kind", "name") if k in row}
            fund = catalog.resolve(ref)
            if fund.principal:
                entry = {"deposit": text(row.get("deposit"), f"funds[{i}].deposit"), "proxyKind": "deposit"}
            else:
                sid = text(row.get("series"), f"funds[{i}].series")
                if sid not in self.series:
                    raise InputError(f"대응표 funds[{i}]: series {sid}가 series 목록에 없음")
                if row.get("proxyKind") not in PROXY_KINDS:
                    raise InputError(f"대응표 funds[{i}].proxyKind는 {sorted(PROXY_KINDS)} 중 하나")
                entry = {"series": sid, "proxyKind": row["proxyKind"]}
            self.by_fund[fund] = {**entry, "errorNote": row.get("errorNote")}
        self.cross = rows(proxy_map.get("crossChecks", []), "대응표 crossChecks")
        self.deposits = deposits

    def growth(self, fund: dc.Fund, store: dict, start: date, end: date) -> tuple[Decimal, date]:
        entry = self.by_fund.get(fund)
        if entry is None:
            raise Missing(f"{fund.name}: 대리 대응표에 없음")
        if "deposit" in entry:
            info = self.deposits.get(entry["deposit"])
            if info is None:
                raise Missing(f"{fund.name}: deposit_rates.json에 {entry['deposit']} 금리 없음")
            # 원리금보장은 입금 당시 고시 금리가 만기까지 간다: 그 금리의 적용 기간 안 입금분을 만기 전까지만 추정한다.
            if info["from"] is None or info["term"] is None:
                raise Missing(f"{fund.name}: {entry['deposit']} 금리의 적용 시작일·기간(termMonths)을 모름")
            if start < info["from"] or (info["to"] is not None and start > info["to"]):
                raise Missing(f"{fund.name}: {start} 입금분의 고시 금리를 모름(파일 금리는 {info['from']}~{info['to'] or ''} 입금분)")
            if end > add_months(start, info["term"]):
                raise Missing(f"{fund.name}: {start} 입금분이 만기({info['term']}개월)를 지나 재예치 금리를 모름")
            return 1 + info["rate"] / HUNDRED * (end - start).days / 365, end
        first, _ = price(store, entry["series"], start)
        last, seen = price(store, entry["series"], end)
        return last / first, seen


def deposit_rates(funds_dir: Path) -> dict[str, dict]:
    data = mapping(dc.load_json(funds_dir / "deposit_rates.json"), "deposit_rates.json")
    result = {}
    for r in rows(data.get("rates"), "rates"):
        if not r.get("id") or r.get("rate") is None:
            continue
        period = r.get("bonusPeriod") if isinstance(r.get("bonusPeriod"), dict) else {}
        start, stop = r.get("appliesFrom") or period.get("from"), r.get("appliesTo") or period.get("to")
        result[str(r["id"])] = {"rate": dc.number(r["rate"], f"{r['id']}.rate"),
                                 "from": day(start, f"{r['id']}.appliesFrom") if start else None,
                                 "to": day(stop, f"{r['id']}.appliesTo") if stop else None,
                                 "term": pa.whole(r["termMonths"], f"{r['id']}.termMonths", 0)
                                 if r.get("termMonths") is not None else None}
    return result


def concentration(values: dc.Positions, total: Decimal) -> list[dict]:
    groups: dict[str, tuple[str, Decimal, Decimal]] = {}

    def add(key: str, label: str, limit: Decimal, amount: Decimal) -> None:
        _, _, held = groups.get(key, (label, limit, ZERO))
        groups[key] = (label, limit, held + amount)

    for fund, amount in values.items():
        themes = set(fund.themes) & THEMES
        for theme in themes:
            add(f"theme:{theme}", f"테마 {theme}", THEME_LIMIT, amount)
        if themes & TECH_AI:
            add("group:tech_ai", "Tech/AI 묶음(반도체·AI·로봇)", TECH_AI_LIMIT, amount)
        if fund.region and fund.region != "global":
            add(f"region:{fund.region}", f"{REGION_NAMES.get(fund.region, fund.region)} 지역", REGION_LIMIT, amount)
        if fund.region in EM:
            add("group:em", "신흥국·아시아 합계", EM_LIMIT, amount)
    result = []
    for key in sorted(groups):
        label, limit, held = groups[key]
        weight = held * HUNDRED / total
        result.append({"key": f"conc:{key}", "label": label, "weightPct": weight, "limitPct": limit,
                       "over": weight > limit})
    return result


def estimate(baseline: dict, base_dir: Path, proxies: Proxies, store: dict, catalog: dc.Catalog,
             target: dc.Positions, as_of: date) -> tuple[dict[dc.Fund, Decimal] | None, list[str], dict, date]:
    start = day(baseline["executedOn"], "executedOn")
    if as_of < start:
        raise InputError(f"점검일 {as_of}이 실행일 {start}보다 앞")
    contributions = load_contributions(baseline, base_dir, start, as_of)
    missing: list[str] = []
    if contributions and baseline.get("totalEvalAmount") is None:
        missing.append("납입 기록을 반영하려면 실행 기준에 totalEvalAmount(실행일 총평가액)가 필요")
        return None, missing, {}, start
    total = dc.number(baseline["totalEvalAmount"], "totalEvalAmount") if baseline.get("totalEvalAmount") is not None else NOTIONAL
    # 펀드마다 (입금·매수일, 그날 금액) 분할분을 둔다. 실행 기록 때 줄어든 펀드는 분할분을 같은 비율로 줄이고(입금일 유지),
    # 늘어난 펀드만 그날 새 분할분을 더한다. 그래서 건드리지 않은 예금은 원래 입금일의 금리·만기를 그대로 쓴다.
    tranches: dict[dc.Fund, list[tuple[date, Decimal]]] = {f: [(start, total * w / HUNDRED)] for f, w in target.items() if w}
    executions = [(when, dc.positions(after, catalog, "weight"))
                  for when, after in load_executions(baseline, base_dir, start, as_of)]
    events = sorted([(e["_date"], 1, e) for e in contributions] + [(when, 0, after) for when, after in executions],
                    key=lambda item: (item[0], item[1]))

    def value_at(when: date, seen_dates: dict[str, str] | None) -> dict[dc.Fund, Decimal]:
        values: dict[dc.Fund, Decimal] = {}
        for fund, parts_ in tranches.items():
            for since, base in parts_:
                try:
                    g, seen = proxies.growth(fund, store, since, when)
                except Missing as exc:
                    if str(exc) not in missing:
                        missing.append(str(exc))
                    continue
                values[fund] = values.get(fund, ZERO) + base * g
                if seen_dates is not None:
                    entry = proxies.by_fund[fund]
                    seen_dates[entry.get("series", "deposit:" + entry.get("deposit", ""))] = seen.isoformat()
        return values

    for when, kind, payload in events:
        if kind == 1:
            split = dc.positions(payload["allocation"], catalog, "weight") if payload.get("allocation") else target
            if sum(split.values(), ZERO) != HUNDRED:
                raise InputError(f"납입 {when}: allocation 합계는 100이어야 함")
            for fund, w in split.items():
                if w:
                    tranches.setdefault(fund, []).append((when, payload["_amount"] * w / HUNDRED))
            continue
        if sum(payload.values(), ZERO) != HUNDRED:
            raise InputError(f"실행 기록 {when}: positionsAfter 합계는 100이어야 함")
        before = value_at(when, None)
        if missing:
            return None, missing, {}, start
        whole_value = sum(before.values(), ZERO)
        for fund in set(tranches) | set(payload):
            held, wanted = before.get(fund, ZERO), whole_value * payload.get(fund, ZERO) / HUNDRED
            if wanted == 0:
                tranches.pop(fund, None)
            elif wanted <= held:
                tranches[fund] = [(since, base * wanted / held) for since, base in tranches[fund]]
            else:
                tranches.setdefault(fund, []).append((when, wanted - held))
    seen_dates: dict[str, str] = {}
    values = value_at(as_of, seen_dates)
    if missing:
        return None, missing, {}, start
    return values, [], seen_dates, max([start] + [when for when, _ in executions])


def cross_checks(proxies: Proxies, store: dict, start: date, end: date, catalog: dc.Catalog) -> list[dict]:
    result = []
    for i, row in enumerate(proxies.cross):
        fund = catalog.resolve({"fundCode": text(row.get("fundCode"), f"crossChecks[{i}].fundCode")})
        tolerance = dc.number(row.get("tolerancePct"), f"crossChecks[{i}].tolerancePct")
        try:
            main, _ = proxies.growth(fund, store, start, end)
            other = Decimal(1)
            for sid in row.get("product", []):
                first, _ = price(store, sid, start)
                last, _ = price(store, sid, end)
                other *= last / first
        except Missing as exc:
            result.append({"name": fund.name, "state": "확인 못 함", "note": str(exc)})
            continue
        diff = (main - other) * HUNDRED
        result.append({"name": fund.name, "state": "어긋남" if abs(diff) > tolerance else "일치",
                       "diffPct": diff, "tolerancePct": tolerance, "against": "×".join(row.get("product", []))})
    return result


def breaches(rebalance: dict, holdings_check: dict, conc: list[dict], limit: Decimal) -> list[dict]:
    found = []
    for band in rebalance["bands"]:
        if band["outOfBand"]:
            drift = band["driftPct"]
            found.append({"key": f"band:{band['id']}:{'+' if drift > 0 else '-'}",
                          "text": f"{band['label']} 묶음 {drift:+.1f}%p (목표 {pct(band['targetPct'])}% → 추정 "
                                  f"{pct(band['currentPct'])}%, 밴드 ±{band['bandPct']}%p)"})
    risk = rebalance["riskTotal"]
    if risk["outOfBand"]:
        found.append({"key": f"risk:{'+' if risk['driftPct'] > 0 else '-'}",
                      "text": f"비면제 위험자산 합 {risk['driftPct']:+.1f}%p (목표 {pct(risk['targetPct'])}% → 추정 "
                              f"{pct(risk['currentPct'])}%, 밴드 ±{risk['bandPct']}%p"
                              + (", 70% 근처라 좁힌 밴드)" if risk["nearLimit"] else ")")})
    if Decimal(holdings_check["nonExemptRiskWeight"]) > limit:
        found.append({"key": "limit:over",
                      "text": f"비면제 위험자산 추정 {pct(Decimal(holdings_check['nonExemptRiskWeight']))}%가 한도 {limit}% "
                              "초과(추정치라 포털 화면으로 확인해. 위험자산을 더 사기 전에 줄여야 해)"})
    for row in holdings_check["singleFundChecks"]:
        if row["severity"] == "ERROR":
            found.append({"key": f"conc:fund:{row['name']}",
                          "text": f"한 펀드 쏠림: {row['name']} 추정 {pct(row['weight'])}% (한도 40%)"})
    for row in conc:
        if row["over"]:
            found.append({"key": row["key"], "text": f"쏠림: {row['label']} 추정 {pct(row['weightPct'])}% "
                                                     f"(한도 {row['limitPct']}%)"})
    return found


def plan_lines(rebalance: dict, principal_names: set[str]) -> list[str]:
    if rebalance["decision"] == "HOLD":
        return ["거래안 없음: 묶음 밴드는 안이야(쏠림·한도만 확인)."]
    if rebalance["decision"] == "NO_SAFE_PLAN":
        return ["한도를 지키는 정수 거래안이 없어: 목표 비중을 다시 봐야 해. " + " ".join(rebalance["messages"])]
    plan = rebalance["plan"]
    lines = ["포털에 이렇게 넣어(추정 기준이라 넣기 전에 포털 화면 비중으로 한 번 맞춰 봐):"]
    if plan["sells"]:
        lines.append("- 매도: " + ", ".join(f"{s['name']} {s['sellPct']}%" for s in plan["sells"]))
    if plan["buys"]:
        lines.append("- 매수 비율(매도 대금 나누기): " + ", ".join(f"{b['name']} {b['integerPct']}%" for b in plan["buys"]))
    if plan["integerSellVariant"]:
        lines.append(f"- 매도 %는 {'내림' if plan['integerSellVariant'] == 'floor' else '올림'} 정수로 계산했어"
                     + ("(다른 방식은 한도 위반)." if plan["excludedVariants"] else "."))
    if any(s["name"] in principal_names for s in plan["sells"]):
        lines.append("- 원리금보장(예금)을 만기 전에 팔면 중도해지 이율이 적용돼(deposit_rates.json earlyWithdrawal). "
                     "부담금 투자비율로 천천히 맞추는 방법도 있어.")
    return lines


def slim_rebalance(result: dict) -> dict:
    """금액 필드를 빼고 비중·정수 %만 남긴다."""
    out = {k: result[k] for k in ("decision", "triggers", "messages", "status")}
    out["bands"] = [{k: b[k] for k in ("id", "label", "currentPct", "targetPct", "driftPct", "bandPct", "outOfBand")}
                    for b in result["bands"]]
    out["riskTotal"] = {k: v for k, v in result["riskTotal"].items()}
    if result.get("plan"):
        plan = result["plan"]
        out["planVerdict"] = result["planVerdict"]
        out["plan"] = {"integerSellVariant": plan["integerSellVariant"], "excludedVariants": plan["excludedVariants"],
                       "sells": [{"name": s["name"], "sellPct": s["sellPct"]} for s in plan["sells"]],
                       "buys": [{"name": b["name"], "integerPct": b["integerPct"]} for b in plan["buys"]]}
    return out


def header(baseline: dict, data_date: str) -> str:
    return f"(추정 · 대리 자료 {data_date} 기준 · 안 {baseline['plan']}, {baseline['executedOn']} 실행 기준)"


def summary_text(result: dict) -> str:
    status = result["status"]
    if status == "UNSET":
        return ("포트폴리오 점검: 기준 미정이라 추정·알림이 꺼져 있어. 형이 따른 안(A/B, 예금 %)과 넣은 날짜"
                "(납입했으면 날짜·금액도)를 알려 주면 켜져.")
    if status == "NO_ESTIMATE":
        return (f"포트폴리오 점검: 대리 자료가 모자라 {result['noEstimateSince']}부터 추정하지 못하고 있어"
                "(이 동안 규칙 알림도 멈춤). 이유: " + "; ".join(result["missing"]))
    if status == "ERROR":
        return "포트폴리오 점검: 계산 오류로 추정하지 못했어. " + "; ".join(result["messages"])
    reb, est = result["rebalance"], result["estimate"]
    lines = [f"포트폴리오 점검 {header(result['baseline'], est['dataDate'])}",
             "- 판정: " + ("밴드 안, 걸린 규칙 없음" if not result["breachKeys"] else f"규칙 {len(result['breachKeys'])}개 걸림")]
    for b in reb["bands"]:
        lines.append(f"- {b['label']}: 목표 {pct(b['targetPct'])}% → 추정 {pct(b['currentPct'])}% "
                     f"({b['driftPct']:+.1f}%p, 밴드 ±{b['bandPct']}%p {'밖' if b['outOfBand'] else '안'})")
    risk = reb["riskTotal"]
    lines.append(f"- 비면제 위험자산 합: 목표 {pct(risk['targetPct'])}% → 추정 {pct(risk['currentPct'])}% "
                 f"(밴드 ±{risk['bandPct']}%p{', 70% 근처라 좁힘' if risk['nearLimit'] else ''}, 한도 {result['limitPct']}%)")
    over = [b["text"] for b in result["breaches"] if b["key"].startswith("conc:")]
    lines.append("- 쏠림: " + ("; ".join(over) if over else "한도 넘은 지역·테마·펀드 없음"))
    lines.extend(f"- 걸린 규칙: {b['text']}" for b in result["breaches"] if not b["key"].startswith("conc:"))
    if est["activeProxies"]:
        lines.append("- 대리 오차: 액티브 펀드는 비슷한 지수·ETF로 대신 봐서 오차가 클 수 있어(" + ", ".join(est["activeProxies"]) + ")")
    for row in est["crossChecks"]:
        lines.append(f"- 교차 확인 {row['name']}: {row['state']}"
                     + (f" (차이 {row['diffPct']:+.2f}%p, 허용 ±{row['tolerancePct']}%p)" if "diffPct" in row else f" ({row['note']})"))
    lines.append("※ 대리 지수·ETF로 추정한 값이야. 실제 비중은 포털 화면이 정답이고, 6개월 점검 때 화면으로 맞춰.")
    return "\n".join(lines)


def alert_text(result: dict) -> str:
    new = set(result["newKeys"])
    lines = [f"포트폴리오 규칙 알림 {header(result['baseline'], result['estimate']['dataDate'])}", "새로 걸린 것:"]
    lines += [f"- {b['text']}" for b in result["breaches"] if b["key"] in new]
    rest = [b["text"] for b in result["breaches"] if b["key"] not in new]
    if rest:
        lines += ["이미 알린 것(계속 걸려 있음):"] + [f"- {t}" for t in rest]
    if result["planShown"]:
        lines += plan_lines(result["rebalance"], {f["name"] for f in result["estimate"]["funds"] if f["proxyKind"] == "deposit"})
    else:
        lines += [f"대리 교차 확인 어긋남: {row['name']} 차이 {row['diffPct']:+.2f}%p(허용 ±{row['tolerancePct']}%p)"
                  for row in result["estimate"]["crossChecks"] if row["state"] == "어긋남"]
        lines.append("대리 자료끼리 어긋남서 이번엔 포털 입력 %를 빼. 포털 화면 비중(%만)을 보내 주면 그걸로 다시 계산해 줄게.")
    if result["estimate"]["activeProxies"]:
        lines.append("대리 오차: " + ", ".join(result["estimate"]["activeProxies"]) + "는 액티브 펀드라 추정 오차가 클 수 있어.")
    lines.append("정해 둔 비중으로 되돌리는 규칙 알림이야. 가격 전망이나 최근 성적으로 사고팔라는 뜻은 아니야.")
    return "\n".join(lines)


def parts(message: str) -> list[str]:
    chunks, current = [], ""
    for line in message.split("\n"):
        while len(line) > PART_MAX:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:PART_MAX])
            line = line[PART_MAX:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > PART_MAX:
            chunks.append(current)
            candidate = line
        current = candidate
    return chunks + ([current] if current else [])


def fingerprint(args: argparse.Namespace, baseline: dict, base_dir: Path) -> str:
    """결과를 바꾸는 입력 파일 전부(정책·납입·실행 기록·펀드 분류·예금 금리 포함)의 내용 해시."""
    paths = {"baseline": args.baseline, "map": args.map, "store": args.store}
    for key in ("policy", "contributionsLog", "executionsLog"):
        if baseline.get(key):
            paths[key] = base_dir / baseline[key]
    for name in ("fund_data.json", "tdf_data.json", "fund_classification.json", "deposit_rates.json"):
        paths[name] = args.funds_dir / name
    return pa.sha256({"asOf": args.as_of, **{k: p.read_text(encoding="utf-8") if p.exists() else None
                                             for k, p in sorted(paths.items())}})


def check(args: argparse.Namespace) -> tuple[dict, int]:
    config = mapping(dc.load_json(Path(__file__).with_name("dc_limits_config.json")), "설정")
    limit = dc.number(config["riskLimitPct"], "riskLimitPct")
    baseline = load_baseline(args.baseline)
    base_dir = args.baseline.resolve().parent
    state = mapping(dc.load_json(args.state), "알림 상태") if args.state and args.state.exists() else {"keys": {}}
    if baseline["_meta"]["status"] == "unset":
        result = {"status": "UNSET", "decision": "UNSET", "inputSha256": fingerprint(args, baseline, base_dir)}
        result["summary"] = summary_text(result)
        return result, 0
    policy_path = base_dir / baseline["policy"]
    policy = pa.parse_policy(dc.load_json(policy_path), config, policy_path.parent)
    catalog = dc.Catalog(args.funds_dir)
    target_rows = rows(baseline["positions"], "positions")
    target = dc.positions(target_rows, catalog, "weight")
    proxies = Proxies(mapping(dc.load_json(args.map), "대리 대응표"), catalog, deposit_rates(args.funds_dir))
    store = mapping(mapping(dc.load_json(args.store), "대리 시계열").get("series", {}), "대리 시계열 series")
    as_of = day(args.as_of, "--as-of")
    info = {"plan": baseline["plan"], "executedOn": baseline["executedOn"]}
    values, missing, seen, rebased = estimate(baseline, base_dir, proxies, store, catalog, target, as_of)
    if values is None:
        # 알림 키는 그대로 두고, 결측이 시작된 날만 적는다. 처음 결측이면 opsNotice로 리드에게 한 번 알린다(침묵 = 이상 없음이 아니게).
        result = {"status": "NO_ESTIMATE", "decision": "NO_ESTIMATE", "baseline": info, "asOf": as_of.isoformat(),
                  "missing": missing, "opsNotice": "noEstimateSince" not in state,
                  "noEstimateSince": state.get("noEstimateSince", as_of.isoformat()),
                  "inputSha256": fingerprint(args, baseline, base_dir)}
        if args.state:
            args.state.write_text(pa.dump({**state, "noEstimateSince": result["noEstimateSince"]}) + "\n", encoding="utf-8")
        result["summary"] = summary_text(result)
        return result, 0
    holding_rows = [{**dc.ref(f), "evalAmount": int(v.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))}
                    for f, v in values.items()]
    reb = pa.rebalance(policy, target_rows, holding_rows, catalog, config)
    held = dc.positions(holding_rows, catalog, "evalAmount")
    total = sum(held.values(), ZERO)
    holdings_check = dc.check(held, config, "holdings", denominator=total)
    conc = concentration(held, total)
    found = breaches(reb, holdings_check, conc, limit)
    keys = [b["key"] for b in found]
    previous = mapping(state.get("keys", {}), "알림 상태 keys")
    data_date = min(seen.values()) if seen else as_of.isoformat()
    new_keys = [k for k in keys if k not in previous]
    next_state = {"keys": {k: previous.get(k, {"since": data_date}) for k in keys}}
    decision = "SEND" if new_keys else ("QUIET" if keys else "IN_BAND")
    funds = []
    for fund, value in sorted(values.items(), key=lambda item: item[0].name):
        entry = proxies.by_fund[fund]
        funds.append({**dc.ref(fund), "name": fund.name, "weightPct": value * HUNDRED / sum(values.values(), ZERO),
                      "proxy": entry.get("series") or f"deposit:{entry['deposit']}", "proxyKind": entry["proxyKind"],
                      "proxyLabel": PROXY_KINDS.get(entry["proxyKind"], "예금 금리 단리 일할 추정"),
                      "errorNote": entry.get("errorNote")})
    result = {"status": "ESTIMATED", "decision": decision, "baseline": info, "asOf": as_of.isoformat(),
              "limitPct": limit,
              "estimate": {"dataDate": data_date, "seriesDates": dict(sorted(seen.items())), "funds": funds,
                           "activeProxies": [f["name"] for f in funds if f["proxyKind"] == "active"],
                           "crossChecks": cross_checks(proxies, store, rebased, as_of, catalog),
                           "rebasedOn": rebased.isoformat(),
                           "basis": "totalEvalAmount" if baseline.get("totalEvalAmount") is not None else "notional"},
              "rebalance": slim_rebalance(reb), "concentration": conc, "breaches": found, "breachKeys": keys,
              "newKeys": new_keys, "nextState": next_state, "inputSha256": fingerprint(args, baseline, base_dir)}
    result["planShown"] = not any(row["state"] == "어긋남" for row in result["estimate"]["crossChecks"])
    result["summary"] = summary_text(result)
    if decision == "SEND":
        result["message"] = alert_text(result)
        result["messageParts"] = parts(result["message"])
    if args.state:
        # SEND면 새 키는 보낸 뒤 mark-sent가 더하고, 해소된 키는 지금 뺀다(못 보낸 사이 해소돼도 다음 재발을 새로 알리게).
        kept = {"keys": {k: v for k, v in next_state["keys"].items() if k in previous}} if decision == "SEND" else next_state
        args.state.write_text(pa.dump(kept) + "\n", encoding="utf-8")
    return result, 0


def http_json(url: str, headers: dict[str, str], secrets: tuple[str, ...]) -> object:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, http.client.HTTPException) as exc:
        message = str(exc)
        for secret in secrets:
            message = message.replace(secret, "***")
        raise Missing(f"{urllib.parse.urlsplit(url).hostname}: {type(exc).__name__}: {message}") from None


def fetch(args: argparse.Namespace) -> tuple[dict, int]:
    baseline = load_baseline(args.baseline)
    if baseline["_meta"]["status"] == "unset":
        return {"fetch": "SKIPPED", "reason": "기준 미정"}, 0
    secrets_dir = Path(os.environ.get("DORI_SECRETS_DIR", Path.home() / ".config/dori-secrets"))
    series = mapping(mapping(dc.load_json(args.map), "대리 대응표").get("series"), "대응표 series")
    store_data = mapping(dc.load_json(args.store), "대리 시계열") if args.store.exists() else {}
    store = {k: dict(v) for k, v in mapping(store_data.get("series", {}), "series").items()}
    fetched = {k: set(v) for k, v in mapping(store_data.get("fetched", {}), "fetched").items()}
    as_of = day(args.as_of, "--as-of")
    start = day(baseline["executedOn"], "executedOn")
    base_dir = args.baseline.resolve().parent
    anchors = sorted({start, as_of} | {e["_date"] for e in load_contributions(baseline, base_dir, start, as_of)}
                     | {when for when, _ in load_executions(baseline, base_dir, start, as_of)})
    problems: list[str] = []
    unknown = sorted(sid for sid, s in series.items() if s.get("source") not in SOURCES)
    if unknown:
        raise InputError(f"KRX가 아닌 대리 series {unknown}: FRED 저장 금지, ECOS 약관 미확인")
    key = (secrets_dir / "krx").read_text(encoding="utf-8").strip()
    if not key or any(ch.isspace() for ch in key):
        raise InputError("KRX 키 파일 형식 오류(비었거나 공백·줄바꿈 포함). 키 값은 출력하지 않음")
    endpoint_of = {sid: SOURCES[s["source"]] or text(s.get("endpoint"), f"{sid}.endpoint") for sid, s in series.items()}
    if series:
        for endpoint in sorted(set(endpoint_of.values())):
            wanted = {sid: s for sid, s in series.items() if endpoint_of[sid] == endpoint}
            for anchor in anchors:
                for back in range(STALE_DAYS + 1):
                    when = anchor - timedelta(days=back)
                    iso = when.isoformat()
                    if all(iso in store.get(sid, {}) for sid in wanted):
                        break
                    if when.weekday() >= 5 or iso in fetched.get(endpoint, set()):
                        continue
                    try:
                        data = http_json(f"{KRX_BASE}{endpoint}?basDd={when:%Y%m%d}", {"AUTH_KEY": key}, (key,))
                    except Missing as exc:
                        problems.append(str(exc))
                        break
                    block = rows(mapping(data, "KRX 응답").get("OutBlock_1", []), "OutBlock_1")
                    hits = 0
                    for sid, spec in wanted.items():
                        match = [r for r in block if (r.get("ISU_CD") == spec.get("code") if spec["source"] == "krx_etf_nav"
                                                      else r.get("IDX_NM") == spec.get("name"))]
                        field = "NAV" if spec["source"] == "krx_etf_nav" else "CLSPRC_IDX"
                        if match and str(match[0].get(field, "")).replace(",", "").strip():
                            store.setdefault(sid, {})[iso] = str(match[0][field]).replace(",", "").strip()
                            hits += 1
                    if not block and (as_of - when).days >= 3:
                        fetched.setdefault(endpoint, set()).add(iso)
                    if hits == len(wanted):
                        break
    out = {"_meta": {"kind": "proxy-series", "note": "KRX Open API 원시 값(제3자 제공 금지·공개 저장소 금지). drift_watch.py fetch가 쓴다",
                     "lastFetchAsOf": as_of.isoformat()},
           "series": {k: dict(sorted(v.items())) for k, v in sorted(store.items())},
           "fetched": {k: sorted(v) for k, v in sorted(fetched.items())}}
    args.store.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    counts = {sid: len(store.get(sid, {})) for sid in sorted(series)}
    return {"fetch": "PARTIAL" if problems else "OK", "problems": problems, "seriesPoints": counts}, (1 if problems else 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check_cmd = commands.add_parser("check", help="추정 비중 → 밴드·70%·쏠림 판정 → 새 이탈만 SEND")
    fetch_cmd = commands.add_parser("fetch", help="필요한 날짜(실행일·납입일·점검일)의 대리 시계열을 KRX Open API에서 받아 저장")
    for command in (check_cmd, fetch_cmd):
        command.add_argument("--baseline", type=Path, required=True)
        command.add_argument("--map", type=Path, required=True)
        command.add_argument("--store", type=Path, required=True)
        command.add_argument("--as-of", default=date.today().isoformat())
    check_cmd.add_argument("--funds-dir", type=Path, default=Path("funds"))
    check_cmd.add_argument("--state", type=Path, help="지난번 알린 이탈. SEND가 아니면 여기에 바로 쓰고, SEND는 mark-sent가 쓴다")
    check_cmd.add_argument("--latest", type=Path, help="결과 JSON도 저장(mark-sent·summary가 읽음)")
    sent_cmd = commands.add_parser("mark-sent", help="보낸 뒤 latest의 nextState를 상태 파일에 쓴다")
    summary_cmd = commands.add_parser("summary", help="latest의 비중 요약(금액 없음)을 출력")
    for command in (sent_cmd, summary_cmd):
        command.add_argument("--latest", type=Path, required=True)
    sent_cmd.add_argument("--state", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "mark-sent":
            latest = mapping(dc.load_json(args.latest), "latest")
            if latest.get("decision") != "SEND":
                raise InputError(f"latest decision={latest.get('decision')!r}: 보낼 알림이 아님")
            args.state.write_text(pa.dump(latest["nextState"]) + "\n", encoding="utf-8")
            print("MARKED " + " ".join(latest["newKeys"]))
            return 0
        if args.command == "summary":
            print(mapping(dc.load_json(args.latest), "latest")["summary"])
            return 0
        result, code = check(args) if args.command == "check" else fetch(args)
    except InputError as exc:
        result, code = {"status": "ERROR", "decision": "ERROR", "messages": [str(exc)]}, 1
        result["summary"] = summary_text(result)
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
        result, code = {"status": "ERROR", "decision": "ERROR", "messages": [f"입력·데이터 오류: {type(exc).__name__}: {exc}"]}, 1
        result["summary"] = summary_text(result)
    output = pa.dump(result)
    if args.command == "check" and args.latest:
        args.latest.write_text(output + "\n", encoding="utf-8")
    print(output)
    return code


if __name__ == "__main__":
    sys.exit(main())
