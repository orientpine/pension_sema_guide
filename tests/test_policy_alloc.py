"""policy_alloc.py·tilt_validation.py: 정책 → 장기 기본 비중 → 단기 기울이기 관문 → 정수 목표 → 밴드 거래안 계약."""
from __future__ import annotations

import copy
import hashlib
import json
import random
import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude/plugins/investments-portfolio/skills/dc-pension-rules"
SCRIPT = SKILL / "scripts/policy_alloc.py"
VALIDATOR = SKILL / "scripts/tilt_validation.py"
FUNDS = Path(__file__).parent / "fixtures/dc_limits"
POLICY = json.loads((Path(__file__).parent / "fixtures/policy/policy.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(SKILL / "scripts"))

import policy_alloc as pa  # noqa: E402

CONFIG = json.loads((SKILL / "scripts/dc_limits_config.json").read_text(encoding="utf-8"))


def write(path: Path, value) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def cli(tmp_path, *args, policy=None, script=SCRIPT, funds=FUNDS):
    command = [sys.executable, str(script), *args]
    if script is SCRIPT:
        command += ["--funds-dir", str(funds)]
    command += ["--policy", str(write(tmp_path / "policy.json", policy or POLICY))]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    assert done.stdout, done.stderr
    return done.returncode, json.loads(done.stdout), done.stdout


def policy_with(**changes):
    policy = copy.deepcopy(POLICY)
    for path, value in changes.items():
        target = policy
        keys = path.split("__")
        for key in keys[:-1]:
            target = target[int(key)] if isinstance(target, list) else target[key]
        target[keys[-1]] = value
    return policy


def source(publisher, host, value, as_of="2026-10-31"):
    return {"publisher": publisher, "url": f"https://{host}/series", "accessedAt": "2026-11-01T09:00+09:00",
            "originalText": f"value {value}", "value": str(value), "asOf": as_of}


def market(indicator, value, sources=2, as_of="2026-10-31"):
    hosts = [("가짜거래소", "exchange.example"), ("가짜통계", "stats.example"), ("가짜신문", "news.example")]
    return {"indicator": indicator, "value": str(value), "asOf": as_of, "sourceKind": "market",
            "sources": [source(p, h, value, as_of) for p, h in hosts[:sources]]}


def official(indicator, value, publisher="가짜중앙은행"):
    return {"indicator": indicator, "value": str(value), "asOf": "2026-10-31", "sourceKind": "official",
            "sources": [source(publisher, "bank.example", value)]}


def dated(observation: dict, month: str) -> dict:
    if observation["asOf"] != "2026-10-31":
        return observation
    day = f"{month}-28"
    return {**observation, "asOf": day, "sources": [{**s, "asOf": day} for s in observation["sources"]]}


def log_file(tmp_path, months: dict[str, list[dict]], alerts: dict[str, list[dict]] | None = None) -> Path:
    lines = [json.dumps({"month": m, "observations": [dated(o, m) for o in obs], "alerts": (alerts or {}).get(m, [])},
                        ensure_ascii=False) for m, obs in months.items()]
    path = tmp_path / "macro-log.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def months_between(first: str, count: int) -> list[str]:
    start = pa.month_index(first)
    return [pa.month_name(start + i) for i in range(count)]


def decide(tmp_path, month, log, previous=None, policy=None, extra=()):
    args = ["decide", "--month", month, "--log", str(log), *extra]
    if previous is not None:
        args += ["--previous", str(write(tmp_path / f"previous-{month}.json", previous))]
    command = [sys.executable, str(SCRIPT), *args, "--policy", str(write(tmp_path / "policy.json", policy or POLICY))]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    return done.returncode, json.loads(done.stdout)



def test_allocate_neutral_policy_gives_integer_target_that_passes_dc_limits(tmp_path):
    rc, result, _ = cli(tmp_path, "allocate")
    assert (rc, result["verdict"], result["riskTotalPct"]) == (0, "PASS", 70)
    assert {r["name"]: r["weight"] for r in result["allocation"]} == {
        "국내지수": "20", "위험가": "15", "위험나": "15", "해외지수미상": "20", "예금": "30"}
    assert result["check"]["nonExemptRiskWeight"] == "70"
    assert result["status"] == "진단만(정책 미승인)"


def test_allocate_same_input_gives_same_bytes(tmp_path):
    first = cli(tmp_path, "allocate")[2]
    second = cli(tmp_path, "allocate")[2]
    assert hashlib.sha256(first.encode()).hexdigest() == hashlib.sha256(second.encode()).hexdigest()


def test_allocate_ignores_past_fund_returns(tmp_path):
    funds = tmp_path / "funds"
    shutil.copytree(FUNDS, funds)
    data = json.loads((funds / "fund_data.json").read_text(encoding="utf-8"))
    for i, fund in enumerate(data["funds"]):
        fund.update(return6m=str(i * 7), return1y=str(-i * 13), return3y=str(i * 3))
    write(funds / "fund_data.json", data)
    assert cli(tmp_path, "allocate", funds=funds)[2] == cli(tmp_path, "allocate")[2]


def test_allocate_refuses_risk_target_over_legal_limit(tmp_path):
    policy = policy_with(riskTargetPct="71", sleeves__0__neutralPct="21", sleeves__3__neutralPct="29")
    rc, result, _ = cli(tmp_path, "allocate", policy=policy)
    assert (rc, result["verdict"]) == (1, "ERROR")
    assert "한도 70%를 넘음" in result["messages"][0]


def test_allocate_single_fund_over_40_is_no_solution_not_retried(tmp_path):
    policy = policy_with(sleeves__1__funds=[{"fundCode": "R1", "share": "1"}],
                         sleeves__1__neutralPct="45", sleeves__0__neutralPct="5")
    rc, result, _ = cli(tmp_path, "allocate", policy=policy)
    assert (rc, result["verdict"]) == (1, "NO_SOLUTION")
    assert result["check"]["verdict"] == "ERROR"


def test_allocate_rejects_fund_whose_risk_class_differs_from_sleeve(tmp_path):
    policy = policy_with(sleeves__0__funds=[{"fundCode": "S", "share": "1"}])
    rc, result, _ = cli(tmp_path, "allocate", policy=policy)
    assert (rc, result["verdict"]) == (1, "ERROR")
    assert "확정채권" in result["messages"][0]


def test_allocate_fractional_neutral_keeps_risk_total_exact(tmp_path):
    policy = policy_with(sleeves__0__neutralPct="23.3", sleeves__1__neutralPct="23.3", sleeves__2__neutralPct="23.4")
    rc, result, _ = cli(tmp_path, "allocate", policy=policy)
    weights = {r["sleeve"]: int(r["weight"]) for r in result["allocation"] if r["sleeve"] != "global"}
    assert rc == 0 and result["check"]["nonExemptRiskWeight"] == "70"
    assert sum(int(r["weight"]) for r in result["allocation"]) == 100
    assert weights["kr"] + weights["europe"] + sum(
        int(r["weight"]) for r in result["allocation"] if r["sleeve"] == "global") == 70


def test_public_sample_policy_has_no_numbers_and_is_refused(tmp_path):
    sample = json.loads((SKILL / "policy.sample.json").read_text(encoding="utf-8"))

    def numbers(value):
        if isinstance(value, dict):
            return [n for v in value.values() for n in numbers(v)]
        if isinstance(value, list):
            return [n for v in value for n in numbers(v)]
        return [value] if isinstance(value, (int, float)) and not isinstance(value, bool) else []

    assert numbers({k: v for k, v in sample.items() if k != "_meta"}) == []
    rc, result, _ = cli(tmp_path, "allocate", policy=sample)
    assert (rc, result["verdict"]) == (1, "ERROR")
    assert "riskTargetPct" in result["messages"][0] and "sleeves[0].funds" in result["messages"][0]



INDICATORS = {"europe_val_pct": pa.Indicator("europe_val_pct", "market", (), Decimal(0)),
              "real_rate": pa.Indicator("real_rate", "official", ("가짜중앙은행",), Decimal(0))}


@pytest.mark.parametrize("observation,verified", [
    (market("europe_val_pct", 80), True),
    (market("europe_val_pct", 80, sources=1), False),
    ({**market("europe_val_pct", 80), "sources": [source("가짜거래소", "exchange.example", 80)] * 2}, False),
    ({**market("europe_val_pct", 80), "sources": [source("가짜거래소", "exchange.example", 80),
                                                  source("가짜통계", "stats.example", 81)]}, False),
    ({**market("europe_val_pct", 80), "sources": [source("가짜거래소", "exchange.example", 80),
                                                  source("가짜통계", "stats.example", 80, as_of="2026-09-30")]}, False),
    ({**market("europe_val_pct", 80), "sources": [{**source("가짜거래소", "exchange.example", 80), "originalText": ""},
                                                  source("가짜통계", "stats.example", 80)]}, False),
    ({**market("europe_val_pct", 80), "sourceKind": "official"}, False),
    ({**market("europe_val_pct", 80), "sources": [source("가짜거래소", "same.example", 80),
                                                  source("가짜거래소 영문", "same.example:443", 80)]}, False),
    ({**market("europe_val_pct", 80), "sources": [source("가짜은행통계", "ecos.bank.or.kr", 80),
                                                  source("가짜은행", "www.bank.or.kr", 80)]}, False),
    (official("real_rate", "1.5"), True),
    (official("real_rate", "1.5", publisher="가짜신문"), False),
])
def test_observation_is_used_only_when_source_rule_holds(observation, verified):
    value, note = pa.verify(observation, INDICATORS[observation["indicator"]])
    assert (value is not None) is verified
    assert note.startswith("검증") if verified else note.startswith("결측")



def test_decide_unverified_indicators_have_zero_effect(tmp_path):
    months = {m: [market("europe_val_pct", 100, sources=1)] for m in months_between("2026-06", 6)}
    rc, result = decide(tmp_path, "2026-11", log_file(tmp_path, months))
    assert (rc, result["_meta"]["status"]) == (0, "INITIAL")
    assert result["basePct"] == {"kr": "20", "global": "30", "europe": "20", "safe": "30"}
    assert {r["indicator"]: r["state"] for r in result["indicatorSignals"]} == {
        "europe_val_pct": "결측: 효과 0", "real_rate": "결측: 효과 0"}


def test_decide_long_tilt_is_capped_and_keeps_risk_total(tmp_path):
    months = {m: [market("europe_val_pct", 100), official("real_rate", "1")] for m in months_between("2026-06", 6)}
    rc, result = decide(tmp_path, "2026-11", log_file(tmp_path, months))
    base = {k: Decimal(v) for k, v in result["basePct"].items()}
    assert rc == 0
    assert (base["europe"], base["kr"], base["global"], base["safe"]) == (15, 25, 30, 30)
    assert base["kr"] + base["global"] + base["europe"] == 70


@pytest.mark.parametrize("real_rate,risk_total,safe", [("-9", "70", "30"), ("9", "65", "35")])
def test_decide_risk_shift_is_bounded_by_cap_and_legal_limit(tmp_path, real_rate, risk_total, safe):
    months = {m: [official("real_rate", real_rate)] for m in months_between("2026-06", 6)}
    rc, result = decide(tmp_path, "2026-11", log_file(tmp_path, months))
    assert (Decimal(result["riskTotalPct"]), Decimal(result["basePct"]["safe"])) == (Decimal(risk_total), Decimal(safe))


@pytest.mark.parametrize("with_cpi,risk_total", [(True, "65"), (False, "70")])
def test_decide_derived_real_rate_needs_both_verified_components(tmp_path, with_cpi, risk_total):
    policy = copy.deepcopy(POLICY)
    policy["indicators"] = [i for i in policy["indicators"] if i["id"] != "real_rate"] + [
        {"id": "base_rate", "sourceKind": "official", "officialPublishers": ["가짜중앙은행"]},
        {"id": "cpi", "sourceKind": "official", "officialPublishers": ["가짜통계청"]},
        {"id": "real_rate", "sourceKind": "derived", "minus": ["base_rate", "cpi"]}]
    observations = [official("base_rate", "12")] + ([official("cpi", "1", publisher="가짜통계청")] if with_cpi else [])
    months = {m: observations for m in months_between("2026-06", 6)}
    rc, result = decide(tmp_path, "2026-11", log_file(tmp_path, months), policy=policy)
    assert (rc, Decimal(result["riskTotalPct"])) == (0, Decimal(risk_total))


def test_decide_needs_min_verified_months(tmp_path):
    months = {m: ([market("europe_val_pct", 100)] if i < 2 else []) for i, m in enumerate(months_between("2026-06", 6))}
    rc, result = decide(tmp_path, "2026-11", log_file(tmp_path, months))
    row = next(r for r in result["indicatorSignals"] if r["indicator"] == "europe_val_pct")
    assert (row["verifiedMonths"], row["state"], result["basePct"]["europe"]) == (2, "결측: 효과 0", "20")


def first_decision(tmp_path, value=100):
    months = {m: [market("europe_val_pct", value)] for m in months_between("2026-06", 6)}
    return decide(tmp_path, "2026-11", log_file(tmp_path, months))[1]


@pytest.mark.parametrize("month,value,status,europe", [
    ("2027-02", 0, "NOT_DUE", "15"),
    ("2027-05", 90, "HOLD", "15"),
    ("2027-05", 0, "CHANGE", "25"),
])
def test_decide_six_month_cycle_and_two_point_hold(tmp_path, month, value, status, europe):
    previous = first_decision(tmp_path)
    months = {m: [market("europe_val_pct", value)] for m in months_between("2026-12", 6)}
    rc, result = decide(tmp_path, month, log_file(tmp_path, months), previous)
    assert (rc, result["_meta"]["status"], result["basePct"]["europe"]) == (0, status, europe)


def test_decide_missing_data_keeps_last_signal_instead_of_reverting(tmp_path):
    previous = first_decision(tmp_path)
    months = {m: [] for m in months_between("2026-12", 6)}
    rc, result = decide(tmp_path, "2027-05", log_file(tmp_path, months), previous)
    row = next(r for r in result["indicatorSignals"] if r["indicator"] == "europe_val_pct")
    assert (result["_meta"]["status"], result["basePct"]["europe"]) == ("HOLD", "15")
    assert (row["state"], row["missingDecisions"]) == ("결측: 지난 결정 신호 유지", 1)


@pytest.mark.parametrize("publisher,status", [("가짜감독기관", "ALERT"), ("가짜블로그", "CHANGE")])
def test_decide_verified_regime_alert_blocks_adoption(tmp_path, publisher, status):
    previous = first_decision(tmp_path)
    months = {m: [market("europe_val_pct", 0)] for m in months_between("2026-12", 6)}
    alert = {"type": "금리 체계", "summary": "가짜 정책금리 체계 변경",
             "sources": [source(publisher, "regulator.example", 0)]}
    rc, result = decide(tmp_path, "2027-05", log_file(tmp_path, months, {"2027-03": [alert]}), previous)
    assert (result["_meta"]["status"], result["basePct"]["europe"]) == (status, "15" if status == "ALERT" else "25")


def test_decide_stale_observation_is_missing(tmp_path):
    months = {m: [market("europe_val_pct", 100, as_of="2025-12-31")] for m in months_between("2026-06", 6)}
    rc, result = decide(tmp_path, "2026-11", log_file(tmp_path, months))
    assert result["basePct"]["europe"] == "20"
    assert {o["note"] for o in result["observations"]} == {"결측: 기준일이 6개월 전(허용 1개월)", "결측: 기준일이 7개월 전(허용 1개월)",
                                                          "결측: 기준일이 8개월 전(허용 1개월)", "결측: 기준일이 9개월 전(허용 1개월)",
                                                          "결측: 기준일이 10개월 전(허용 1개월)", "결측: 기준일이 11개월 전(허용 1개월)"}


def test_decide_acknowledged_alert_stops_blocking_and_is_remembered(tmp_path):
    previous = first_decision(tmp_path)
    months = {m: [market("europe_val_pct", 0)] for m in months_between("2026-12", 6)}
    alert = {"type": "금리 체계", "summary": "가짜 정책금리 체계 변경", "sources": [source("가짜감독기관", "regulator.example", 0)]}
    log = log_file(tmp_path, months, {"2027-03": [alert]})
    blocked = decide(tmp_path, "2027-04", log, previous)[1]
    acknowledged = decide(tmp_path, "2027-04", log, previous, extra=("--acknowledge-alerts", "https://discord.example/형확인"))[1]
    later = decide(tmp_path, "2027-05", log, acknowledged)[1]
    assert (blocked["_meta"]["status"], acknowledged["_meta"]["status"], later["_meta"]["status"]) == ("ALERT", "NOT_DUE", "CHANGE")
    assert later["acknowledgedAlerts"][0]["acknowledgedBy"] == "https://discord.example/형확인"


def test_decide_previous_survives_unrelated_policy_change(tmp_path):
    previous = first_decision(tmp_path)
    months = {m: [] for m in months_between("2026-12", 6)}
    policy = policy_with(band__sleevePct="4", shortTermTilt__enabled=False, shortTermTilt__maxTiltPct="4")
    rc, result = decide(tmp_path, "2027-05", log_file(tmp_path, months), previous, policy=policy)
    assert (result["_meta"]["status"], result["basePct"]["europe"]) == ("HOLD", "15")


def test_decide_previous_from_other_policy_is_not_reused(tmp_path):
    previous = first_decision(tmp_path)
    policy = policy_with(longTermMacro__maxSleeveTiltPct="4")
    months = {m: [] for m in months_between("2026-12", 6)}
    rc, result = decide(tmp_path, "2027-05", log_file(tmp_path, months), previous, policy=policy)
    assert (result["_meta"]["status"], result["basePct"]["europe"]) == ("INITIAL", "20")


def test_allocate_uses_decision_base(tmp_path):
    decision = write(tmp_path / "decision.json", first_decision(tmp_path))
    rc, result, _ = cli(tmp_path, "allocate", "--decision", str(decision))
    assert {r["name"]: r["weight"] for r in result["allocation"]}["해외지수미상"] == "15"
    assert result["check"]["nonExemptRiskWeight"] == "70"



def history(signal_leads: bool, months=150, revised=False):
    rng = random.Random(11)
    signs = [rng.choice((-1, 1)) for _ in range(months)]
    kr, glob = [], []
    for t in range(months):
        driver = signs[t - 1] if signal_leads and t else signs[t]
        noise = Decimal(rng.randint(-20, 20)) / 10
        kr.append(str(Decimal(driver) * 2 + noise))
        glob.append(str(Decimal(-driver) * 2 + noise))
    return {"_meta": {"sources": [{"publisher": "가짜", "url": "https://data.example", "accessedAt": "2026-11-18"}]},
            "months": months_between("2010-01", months),
            "sleeveReturnsPct": {"kr": kr, "global": glob, "europe": ["0.5"] * months, "safe": ["0.3"] * months},
            "indicators": {"kr_signal": {"values": [str(s) for s in signs], "releaseLagMonths": 0,
                                         "vintage": "revised" if revised else "revisionFree"}}}


def validate(tmp_path, data, policy=None, out=None, extra=()):
    args = [sys.executable, str(VALIDATOR), *extra, "--history", str(write(tmp_path / "history.json", data)),
            "--policy", str(write(tmp_path / "policy.json", policy or POLICY))]
    if out:
        args += ["--out", str(out)]
    done = subprocess.run(args, capture_output=True, text=True, check=False)
    return done.returncode, json.loads(done.stdout)


def test_validation_passes_rule_that_helps_out_of_sample(tmp_path):
    rc, report = validate(tmp_path, history(signal_leads=True))
    assert (rc, report["verdict"], report["outOfSampleMonths"]) == (0, "PASS", 149)


def test_validation_does_not_see_same_month_data(tmp_path):
    rc, report = validate(tmp_path, history(signal_leads=False))
    assert rc == 1 and report["verdict"] == "FAIL"
    assert abs(Decimal(report["meanDiffPctPerMonth"])) < Decimal("0.1")


@pytest.mark.parametrize("data,verdict", [
    (history(signal_leads=True, months=100), "INSUFFICIENT_DATA"),
    (history(signal_leads=True, revised=True), "INVALID_DATA"),
])
def test_validation_refuses_short_or_revised_history(tmp_path, data, verdict):
    assert validate(tmp_path, data)[1]["verdict"] == verdict


def test_validation_does_not_count_months_without_indicator_data(tmp_path):
    data = history(signal_leads=True)
    data["indicators"]["kr_signal"]["values"] = [None] * len(data["months"])
    rc, report = validate(tmp_path, data)
    assert (rc, report["verdict"], report["outOfSampleMonths"], report["skippedMonthsMissingData"]) == (
        1, "INSUFFICIENT_DATA", 0, 149)


def test_validation_refuses_rule_without_thresholds(tmp_path):
    policy = copy.deepcopy(POLICY)
    policy["shortTermTilt"]["rules"][0]["upper"] = None
    assert validate(tmp_path, history(signal_leads=True), policy=policy)[1]["verdict"] == "INVALID_RULES"


def test_short_tilt_needs_validation_at_the_decided_base(tmp_path):
    decision = write(tmp_path / "decision.json", first_decision(tmp_path))
    report = tmp_path / "report.json"
    validate(tmp_path, history(signal_leads=True), out=report)
    log = log_file(tmp_path, {"2026-11": [market("kr_signal", 1)]})
    args = ("allocate", "--decision", str(decision), "--log", str(log), "--month", "2026-11")
    refused = cli(tmp_path, *args, policy=enabled_policy(tmp_path, report))
    validate(tmp_path, history(signal_leads=True), out=report, extra=("--decision", str(decision)))
    accepted = cli(tmp_path, *args, policy=enabled_policy(tmp_path, report))
    assert (refused[0], accepted[0], accepted[1]["shortTermTilt"]["state"]) == (1, 0, "켜짐(검증 통과)")


def test_short_tilt_is_off_by_default(tmp_path):
    rc, result, _ = cli(tmp_path, "allocate")
    assert result["shortTermTilt"]["state"] == "꺼짐(검증 대기)"
    assert all(Decimal(s["shortTiltPct"]) == 0 for s in result["sleeves"])


def enabled_policy(tmp_path, report_path: Path) -> dict:
    policy = policy_with(shortTermTilt__enabled=True)
    policy["shortTermTilt"]["validation"].update(
        status="passed", reportPath=report_path.name,
        reportSha256=hashlib.sha256(report_path.read_bytes()).hexdigest())
    return policy


def test_short_tilt_cannot_be_enabled_without_passed_report(tmp_path):
    rc, result, _ = cli(tmp_path, "allocate", policy=policy_with(shortTermTilt__enabled=True))
    assert (rc, result["verdict"]) == (1, "ERROR")
    assert "검증 통과 전에는 켤 수 없음" in result["messages"][0]


def test_short_tilt_enabled_after_validation_stays_within_cap(tmp_path):
    report = tmp_path / "report.json"
    validate(tmp_path, history(signal_leads=True), out=report)
    log = log_file(tmp_path, {"2026-11": [market("kr_signal", 1)]})
    rc, result, _ = cli(tmp_path, "allocate", "--log", str(log), "--month", "2026-11",
                        policy=enabled_policy(tmp_path, report))
    tilts = {s["id"]: Decimal(s["shortTiltPct"]) for s in result["sleeves"]}
    assert (rc, result["shortTermTilt"]["state"]) == (0, "켜짐(검증 통과)")
    assert (tilts["kr"], tilts["global"], sum(tilts.values())) == (5, -5, 0)
    assert result["check"]["nonExemptRiskWeight"] == "70"


@pytest.mark.parametrize("tamper", ["report", "rules", "cost", "neutral"])
def test_short_tilt_validation_is_bound_to_report_and_rules(tmp_path, tamper):
    report = tmp_path / "report.json"
    validate(tmp_path, history(signal_leads=True), out=report)
    policy = enabled_policy(tmp_path, report)
    if tamper == "report":
        report.write_text(report.read_text(encoding="utf-8").replace('"PASS"', '"PASS" '), encoding="utf-8")
    elif tamper == "rules":
        policy["shortTermTilt"]["rules"][0]["effects"]["sleeves"] = {"kr": "-1", "global": "1"}
    elif tamper == "cost":
        policy["shortTermTilt"]["validation"]["switchCostPct"] = "10"
    else:
        policy["sleeves"][0]["neutralPct"], policy["sleeves"][1]["neutralPct"] = "25", "25"
    log = log_file(tmp_path, {"2026-11": [market("kr_signal", 1)]})
    rc, result, _ = cli(tmp_path, "allocate", "--log", str(log), "--month", "2026-11", policy=policy)
    assert (rc, result["verdict"]) == (1, "ERROR")



TARGET = [{"fundCode": "KR", "weight": "20"}, {"fundCode": "R1", "weight": "15"}, {"fundCode": "R2", "weight": "15"},
          {"fundCode": "EU", "weight": "20"}, {"kind": "principalGuaranteed", "name": "예금", "weight": "30"}]


def holdings(kr, r1, r2, eu, deposit, **extra):
    rows = [{"fundCode": "KR", "evalAmount": kr * 1000}, {"fundCode": "R1", "evalAmount": r1 * 1000},
            {"fundCode": "R2", "evalAmount": r2 * 1000}, {"fundCode": "EU", "evalAmount": eu * 1000},
            {"kind": "principalGuaranteed", "name": "예금", "evalAmount": deposit * 1000}]
    return rows + [{"fundCode": code, "evalAmount": amount * 1000} for code, amount in extra.items()]


def rebalance(tmp_path, target, held, policy=None):
    return cli(tmp_path, "rebalance", "--target", str(write(tmp_path / "target.json", target)),
               "--holdings", str(write(tmp_path / "holdings.json", held)), policy=policy)


def test_rebalance_inside_band_holds_with_no_trades(tmp_path):
    rc, result, _ = rebalance(tmp_path, TARGET, holdings(22, 16, 15, 17, 30))
    assert (rc, result["decision"], result["plan"], result["messages"]) == (0, "HOLD", None, ["밴드 안, 바꿀 것 없음"])


def test_rebalance_outside_band_uses_only_safe_integer_sell(tmp_path):
    rc, result, _ = rebalance(tmp_path, [{"fundCode": "R1", "weight": "40"}, {"fundCode": "R2", "weight": "30"},
                                         {"kind": "principalGuaranteed", "name": "예금", "weight": "30"}],
                              [{"fundCode": "R1", "evalAmount": 60000},
                               {"kind": "principalGuaranteed", "name": "예금", "evalAmount": 40000}])
    plan = result["plan"]
    assert (rc, result["decision"], result["planVerdict"]) == (0, "REBALANCE", "PASS")
    assert (plan["integerSellVariant"], plan["excludedVariants"]) == ("ceil", ["floor"])
    assert {r["name"]: r["sellPct"] for r in plan["sells"]}["위험가"] == 34
    assert result["portal"]["verdict"] == "FAIL"


@pytest.mark.parametrize("held,decision", [
    (holdings(19, 14, 14, 20, 33), "REBALANCE"),
    (holdings(20, 14.5, 14.5, 20, 31), "HOLD"),
])
def test_rebalance_risk_total_band_is_narrow_near_limit(tmp_path, held, decision):
    rc, result, _ = rebalance(tmp_path, TARGET, held)
    assert all(not b["outOfBand"] for b in result["bands"])
    assert (result["riskTotal"]["bandPct"], result["decision"]) == ("2", decision)


def test_rebalance_market_drift_over_limit_triggers(tmp_path):
    rc, result, _ = rebalance(tmp_path, TARGET, holdings(21, 16, 16, 20, 27))
    assert result["riskTotal"]["holdingsVerdict"] == "MARKET_DRIFT_OVER_LIMIT"
    assert (rc, result["decision"], result["planVerdict"]) == (0, "REBALANCE", "PASS")


def test_rebalance_counts_unlisted_fund_as_outside_policy(tmp_path):
    rc, result, _ = rebalance(tmp_path, TARGET, holdings(18, 13, 13, 18, 28, Q=10))
    outside = next(b for b in result["bands"] if b["id"] == "outside")
    assert (outside["heldFunds"], outside["outOfBand"], result["decision"]) == (["적격TDF"], True, "REBALANCE")


def test_rebalance_refuses_proposal_given_as_holdings(tmp_path):
    proposal = {"_meta": {"kind": "proposal"}, "positions": TARGET}
    rc, result, _ = cli(tmp_path, "rebalance", "--target", str(write(tmp_path / "target.json", TARGET)),
                        "--holdings", str(write(tmp_path / "holdings.json", proposal)))
    assert (rc, result["verdict"]) == (1, "ERROR")
    assert "_meta.kind='proposal'" in result["messages"][0]


def test_rebalance_refuses_target_fund_outside_policy(tmp_path):
    target = [{"fundCode": "S", "weight": "30"}, {"fundCode": "KR", "weight": "40"}, {"fundCode": "R1", "weight": "30"}]
    rc, result, _ = rebalance(tmp_path, target, holdings(20, 15, 15, 20, 30))
    assert (rc, result["verdict"]) == (1, "ERROR")
    assert "정책 묶음에 없음" in result["messages"][0]
