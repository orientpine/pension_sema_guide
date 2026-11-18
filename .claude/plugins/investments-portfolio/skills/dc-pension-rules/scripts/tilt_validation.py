#!/usr/bin/env python3
"""단기 기울이기 규칙의 워크포워드 비열등 검증. 통과 보고서가 있어야 policy_alloc가 기울이기를 켠다.

매달 t의 신호는 t-1-releaseLagMonths까지 공개된 값만 쓴다(규칙 매개변수는 검증 전에 정책 파일에 고정).
기울인 안과 안 기울인 안은 같은 위험자산 비중이다(위험 묶음끼리 합 0). 월 차이(기울임-안 기울임, 전환 비용 차감)를
원형 블록 부트스트랩(고정 시드)으로 재표집해 평균의 단측 하한을 구한다.
PASS = 표본 밖 월수 ≥ minOutOfSampleMonths, 평균 차이 ≥ 0, 하한 ≥ 비열등 한계, 최대낙폭·월 변동성이 안 기울인 안보다 크지 않음.
사후 수정된 자료(vintage=revised)를 쓰는 규칙이 있으면 INVALID_DATA.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dc_limits as dc  # noqa: E402
import policy_alloc as pa  # noqa: E402
from dc_limits import InputError, mapping, rows  # noqa: E402

ZERO, ONE, HUNDRED = Decimal(0), Decimal(1), Decimal(100)
VINTAGES = {"pointInTime", "revisionFree", "revised"}
PARAMS = ("nonInferiorityMarginPctPerMonth", "minOutOfSampleMonths", "bootstrapBlockMonths", "bootstrapDraws",
          "seed", "alpha")


def parameters(policy: pa.Policy) -> dict:
    v = policy.validation
    missing = [k for k in PARAMS if v.get(k) is None]
    if missing:
        raise InputError("검증 매개변수가 비어 있음(형 승인 대상): " + ", ".join(missing))
    alpha = dc.number(v["alpha"], "alpha")
    if not ZERO < alpha < ONE:
        raise InputError("alpha는 0과 1 사이")
    return {"margin": pa.signed(v["nonInferiorityMarginPctPerMonth"], "nonInferiorityMarginPctPerMonth"),
            "minMonths": pa.whole(v["minOutOfSampleMonths"], "minOutOfSampleMonths"),
            "block": pa.whole(v["bootstrapBlockMonths"], "bootstrapBlockMonths"),
            "draws": pa.whole(v["bootstrapDraws"], "bootstrapDraws"),
            "seed": pa.whole(v["seed"], "seed", minimum=0), "alpha": alpha,
            "switchCostPct": dc.number(v.get("switchCostPct", "0"), "switchCostPct")}


def load_history(data: object, policy: pa.Policy) -> tuple[list[str], dict[str, list[Decimal]], dict[str, dict]]:
    data = mapping(data, "검증 자료")
    meta = mapping(data.get("_meta"), "_meta")
    sources = rows(meta.get("sources"), "_meta.sources")
    if not sources or not all(all(isinstance(s.get(k), str) and s[k] for k in ("publisher", "url", "accessedAt"))
                              for s in sources):
        raise InputError("검증 자료 _meta.sources에 publisher·url·accessedAt 필요")
    months = data.get("months")
    if not isinstance(months, list) or not months:
        raise InputError("months 필요")
    indexes = [pa.month_index(m) for m in months]
    if any(b - a != 1 for a, b in zip(indexes, indexes[1:])):
        raise InputError("months는 빠짐없이 이어진 월이어야 함")
    returns = mapping(data.get("sleeveReturnsPct"), "sleeveReturnsPct")
    series = {}
    for sleeve in policy.sleeves:
        values = returns.get(sleeve.id)
        if not isinstance(values, list) or len(values) != len(months):
            raise InputError(f"sleeveReturnsPct.{sleeve.id}: months와 같은 길이 필요")
        series[sleeve.id] = [pa.signed(v, f"{sleeve.id} 수익률") for v in values]
    indicators = mapping(data.get("indicators"), "indicators")
    used = {}
    for rule in policy.short_rules:
        item = mapping(indicators.get(rule.indicator), f"indicators.{rule.indicator}")
        values = item.get("values")
        if not isinstance(values, list) or len(values) != len(months):
            raise InputError(f"indicators.{rule.indicator}.values: months와 같은 길이 필요")
        if item.get("vintage") not in VINTAGES:
            raise InputError(f"indicators.{rule.indicator}.vintage는 {sorted(VINTAGES)} 중 하나")
        used[rule.indicator] = {"values": [None if v is None else pa.signed(v, rule.indicator) for v in values],
                                "lag": pa.whole(item.get("releaseLagMonths"), f"{rule.indicator}.releaseLagMonths", 0),
                                "vintage": item["vintage"]}
    return months, series, used


def max_drawdown(returns: list[Decimal]) -> Decimal:
    wealth, peak, worst = ONE, ONE, ZERO
    for r in returns:
        wealth *= ONE + r / HUNDRED
        peak = max(peak, wealth)
        worst = max(worst, (peak - wealth) / peak * HUNDRED)
    return worst


def stdev(values: list[Decimal]) -> Decimal:
    mean = sum(values, ZERO) / len(values)
    return (sum(((v - mean) ** 2 for v in values), ZERO) / len(values)).sqrt()


def block_bootstrap_lower(diffs: list[Decimal], block: int, draws: int, seed: int, alpha: Decimal) -> Decimal:
    rng = random.Random(seed)
    n = len(diffs)
    means = []
    for _ in range(draws):
        sample: list[Decimal] = []
        while len(sample) < n:
            start = rng.randrange(n)
            sample.extend(diffs[(start + i) % n] for i in range(block))
        means.append(sum(sample[:n], ZERO) / n)
    means.sort()
    return means[int(alpha * draws)]


def validate(policy: pa.Policy, history: object) -> dict:
    p = parameters(policy)
    months, returns, indicators = load_history(history, policy)
    base = {s.id: s.neutral for s in policy.sleeves}
    risky = {s.id: s.neutral for s in policy.risky}
    diffs, tilted, untilted, turnovers = [], [], [], []
    previous = {k: ZERO for k in risky}
    first = None
    for t in range(len(months)):
        signals = {}
        ready = True
        for rule in policy.short_rules:
            data = indicators[rule.indicator]
            known = data["values"][: max(0, t - data["lag"])]
            need = rule.window + 1 if rule.kind == "rate_direction" else rule.window
            if len(known) < need:
                ready = False
                break
            signals[rule.id], _ = pa.short_signal(rule, known)
        if not ready:
            continue
        first = months[t] if first is None else first
        tilt = pa.short_tilts(policy, risky, signals)
        plain = sum((base[k] * returns[k][t] for k in base), ZERO) / HUNDRED
        turnover = sum((abs(tilt[k] - previous[k]) for k in risky), ZERO) / 2
        previous = tilt
        moved = plain + sum((tilt[k] * returns[k][t] for k in risky), ZERO) / HUNDRED - turnover * p["switchCostPct"] / HUNDRED
        tilted.append(moved)
        untilted.append(plain)
        turnovers.append(turnover)
        diffs.append(moved - plain)
    revised = sorted(i for i, d in indicators.items() if d["vintage"] == "revised")
    result = {"_meta": {"kind": "tilt-validation", "policySha256": policy.sha},
              "rulesSha256": pa.short_rules_sha(policy), "codeSha256": pa.code_sha(),
              "dataSha256": pa.sha256(history), "parameters": p, "python": f"{sys.version_info[0]}.{sys.version_info[1]}",
              "outOfSampleMonths": len(diffs), "firstMonth": first, "lastMonth": months[-1] if diffs else None,
              "reasons": []}
    if revised:
        result["verdict"] = "INVALID_DATA"
        result["reasons"].append("사후 수정 자료(vintage=revised): " + ", ".join(revised))
        return result
    if len(diffs) < p["minMonths"]:
        result["verdict"] = "INSUFFICIENT_DATA"
        result["reasons"].append(f"표본 밖 {len(diffs)}개월 < {p['minMonths']}개월")
        return result
    mean = sum(diffs, ZERO) / len(diffs)
    lower = block_bootstrap_lower(diffs, p["block"], p["draws"], p["seed"], p["alpha"])
    mdd = {"tilted": max_drawdown(tilted), "untilted": max_drawdown(untilted)}
    vol = {"tilted": stdev(tilted), "untilted": stdev(untilted)}
    checks = [(mean >= 0, f"평균 월 차이 {mean:.6f}%p < 0"),
              (lower >= p["margin"], f"하한 {lower:.6f}%p < 비열등 한계 {p['margin']}%p"),
              (mdd["tilted"] <= mdd["untilted"], "최대낙폭이 안 기울인 안보다 큼"),
              (vol["tilted"] <= vol["untilted"], "월 변동성이 안 기울인 안보다 큼")]
    result["reasons"] = [message for ok, message in checks if not ok]
    result.update(verdict="FAIL" if result["reasons"] else "PASS", meanDiffPctPerMonth=mean,
                  lowerBoundPctPerMonth=lower, maxDrawdownPct=mdd, monthlyVolatilityPct=vol,
                  averageTurnoverPct=sum(turnovers, ZERO) / len(turnovers))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="보고서 저장(정책 validation.reportPath·reportSha256에 넣을 파일)")
    args = parser.parse_args(argv)
    try:
        config = mapping(dc.load_json(Path(__file__).with_name("dc_limits_config.json")), "설정")
        policy = pa.parse_policy(dc.load_json(args.policy), config, args.policy.resolve().parent)
        result = validate(policy, dc.load_json(args.history))
    except InputError as exc:
        result = {"verdict": "ERROR", "messages": [str(exc)]}
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
        result = {"verdict": "ERROR", "messages": [f"입력·데이터 오류: {type(exc).__name__}: {exc}"]}
    text = pa.dump(result) + "\n"
    if args.out and result.get("verdict") != "ERROR":
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
