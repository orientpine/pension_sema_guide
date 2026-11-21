"""drift_watch.py: 실행 기준 + 대리 시계열 → 추정 비중 → policy_alloc.rebalance 밴드·70%·쏠림 → 새 이탈만 알림."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude/plugins/investments-portfolio/skills/dc-pension-rules/scripts/drift_watch.py"
FIXTURES = Path(__file__).parent / "fixtures"
POLICY = json.loads((FIXTURES / "policy/policy.json").read_text(encoding="utf-8"))
START, END = "2026-11-02", "2026-11-20"
SERIES = {"KR": "s:kr", "R1": "s:r1", "R2": "s:r2", "EU": "s:eu"}
TARGET = [{"fundCode": "KR", "weight": "20"}, {"fundCode": "R1", "weight": "15"}, {"fundCode": "R2", "weight": "15"},
          {"fundCode": "EU", "weight": "20"}, {"kind": "principalGuaranteed", "name": "예금", "weight": "30"}]


def write(path: Path, value) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def world(tmp_path):
    funds = tmp_path / "funds"
    shutil.copytree(FIXTURES / "dc_limits", funds)
    deposits = json.loads((funds / "deposit_rates.json").read_text(encoding="utf-8"))
    deposits["rates"][0].update(rate=3.0, appliesFrom="2026-10-01", termMonths=12)
    write(funds / "deposit_rates.json", deposits)
    write(tmp_path / "policy.json", POLICY)
    baseline = {"_meta": {"kind": "execution-baseline", "status": "set", "source": "https://example.invalid/owner"},
                "plan": "A", "policy": "policy.json", "executedOn": START, "positions": TARGET}
    proxy_map = {"_meta": {"kind": "proxy-map"},
                 "series": {sid: {"source": "krx_etf_nav", "code": sid[2:]} for sid in SERIES.values()},
                 "funds": [{"fundCode": "KR", "series": "s:kr", "proxyKind": "index"},
                           {"fundCode": "R1", "series": "s:r1", "proxyKind": "index"},
                           {"fundCode": "R2", "series": "s:r2", "proxyKind": "index"},
                           {"fundCode": "EU", "series": "s:eu", "proxyKind": "active", "errorNote": "액티브 대리"},
                           {"kind": "principalGuaranteed", "name": "예금", "deposit": "dep-1y"}]}
    return {"dir": tmp_path, "funds": funds, "baseline": baseline, "map": proxy_map,
            "prices": {sid: {START: "100", END: "100"} for sid in SERIES.values()}}


def run(world, *extra, state: Path | None = None, as_of=END):
    d = world["dir"]
    args = [sys.executable, str(SCRIPT), "check", "--baseline", str(write(d / "baseline.json", world["baseline"])),
            "--map", str(write(d / "map.json", world["map"])),
            "--store", str(write(d / "store.json", {"_meta": {"kind": "proxy-series"}, "series": world["prices"]})),
            "--funds-dir", str(world["funds"]), "--as-of", as_of, "--latest", str(d / "latest.json"), *extra]
    if state is not None:
        args += ["--state", str(state)]
    done = subprocess.run(args, capture_output=True, text=True, check=False)
    assert done.stdout, done.stderr
    return done.returncode, json.loads(done.stdout), done.stdout


def mark_sent(world, state: Path):
    done = subprocess.run([sys.executable, str(SCRIPT), "mark-sent", "--latest", str(world["dir"] / "latest.json"),
                           "--state", str(state)], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr


def grow(world, code: str, end_price: str):
    world["prices"][SERIES[code]][END] = end_price


def test_same_input_gives_same_bytes(world):
    grow(world, "R1", "150")
    first, second = run(world)[2], run(world)[2]
    assert first == second and json.loads(first)["status"] == "ESTIMATED"


def test_estimated_weights_follow_proxy_growth_and_deposit_interest(world):
    grow(world, "KR", "150")
    rc, result, _ = run(world)
    deposit = Decimal(30) * (1 + Decimal("0.03") * 18 / 365)
    total = Decimal(30) + 15 + 15 + 20 + deposit
    kr = next(b for b in result["rebalance"]["bands"] if b["id"] == "kr")
    assert (rc, result["status"]) == (0, "ESTIMATED")
    assert Decimal(kr["currentPct"]).quantize(Decimal("0.01")) == (30 * 100 / total).quantize(Decimal("0.01"))
    assert result["rebalance"]["decision"] == "REBALANCE"
    sells = result["rebalance"]["plan"]["sells"]
    assert sells and all(isinstance(s["sellPct"], int) for s in sells)
    assert result["rebalance"]["planVerdict"] == "PASS"


@pytest.mark.parametrize("breakage", ["series_gap", "unmapped_fund", "no_deposit_rate", "stale_series"])
def test_missing_proxy_gives_no_estimate_and_no_alert(world, tmp_path, breakage):
    grow(world, "R1", "300")
    if breakage == "series_gap":
        del world["prices"]["s:eu"][END]
    elif breakage == "unmapped_fund":
        world["map"]["funds"] = [f for f in world["map"]["funds"] if f.get("fundCode") != "R2"]
    elif breakage == "no_deposit_rate":
        deposits = json.loads((world["funds"] / "deposit_rates.json").read_text(encoding="utf-8"))
        del deposits["rates"][0]["rate"]
        write(world["funds"] / "deposit_rates.json", deposits)
    else:
        world["prices"]["s:kr"] = {START: "100", "2026-11-10": "100"}
    state = write(tmp_path / "state.json", {"keys": {"band:kr:+": {"since": START}}})
    rc, result, _ = run(world, state=state)
    assert (rc, result["status"], result["decision"]) == (0, "NO_ESTIMATE", "NO_ESTIMATE")
    assert result.get("estimate") is None and result.get("message") is None and result["missing"]
    assert result["opsNotice"] is True and json.loads(state.read_text(encoding="utf-8"))["keys"] == {"band:kr:+": {"since": START}}
    assert run(world, state=state)[1]["opsNotice"] is False


def test_same_breach_is_not_alerted_twice_and_comes_back_after_return(world, tmp_path):
    state = tmp_path / "state.json"
    grow(world, "R1", "200")
    first = run(world, state=state)[1]
    assert first["decision"] == "SEND" and "band:global:+" in first["newKeys"] and first["message"]
    mark_sent(world, state)
    second = run(world, state=state)[1]
    assert (second["decision"], second["newKeys"], second.get("message")) == ("QUIET", [], None)
    grow(world, "R1", "100")
    back = run(world, state=state)[1]
    assert back["decision"] == "IN_BAND" and json.loads(state.read_text(encoding="utf-8"))["keys"] == {}
    grow(world, "R1", "200")
    again = run(world, state=state)[1]
    assert again["decision"] == "SEND" and "band:global:+" in again["newKeys"]


def test_long_alert_is_split_on_lines_within_discord_limit():
    sys.path.insert(0, str(SCRIPT.parent))
    import drift_watch

    message = "\n".join(f"- 펀드{i} " + "가" * 150 for i in range(30)) + "\n" + "나" * 2500
    parts = drift_watch.parts(message)
    assert len(parts) > 1 and all(len(p) <= 1900 for p in parts)
    assert "".join(parts).replace("\n", "") == message.replace("\n", "")


def test_unsent_alert_is_sent_again_next_run(world, tmp_path):
    state = tmp_path / "state.json"
    grow(world, "R1", "200")
    assert run(world, state=state)[1]["decision"] == "SEND"
    assert run(world, state=state)[1]["decision"] == "SEND"


def test_unset_baseline_turns_alerts_off(world, tmp_path):
    world["baseline"] = {"_meta": {"kind": "execution-baseline", "status": "unset"}}
    state = tmp_path / "state.json"
    rc, result, _ = run(world, state=state)
    assert (rc, result["status"], result["decision"], result.get("message")) == (0, "UNSET", "UNSET", None)
    assert not state.exists()


def test_limit_and_concentration_rules_raise_their_own_keys(world):
    grow(world, "KR", "500")
    keys = run(world)[1]["breachKeys"]
    assert {"band:kr:+", "conc:region:korea", "limit:over"} <= set(keys)


def test_active_proxy_is_marked_with_its_error(world):
    grow(world, "EU", "200")
    result = run(world)[1]
    eu = next(f for f in result["estimate"]["funds"] if f.get("fundCode") == "EU")
    assert (eu["proxyKind"], eu["errorNote"]) == ("active", "액티브 대리")
    assert result["estimate"]["activeProxies"] == ["해외지수미상"]


def test_contribution_needs_base_total_and_moves_weights(world, tmp_path):
    log = tmp_path / "contributions.jsonl"
    log.write_text(json.dumps({"date": "2026-11-10", "amount": 10000000,
                               "allocation": [{"fundCode": "KR", "weight": "100"}]}) + "\n", encoding="utf-8")
    world["baseline"]["contributionsLog"] = str(log)
    world["prices"]["s:kr"]["2026-11-10"] = "100"
    rc, result, _ = run(world)
    assert (rc, result["status"]) == (0, "NO_ESTIMATE") and "totalEvalAmount" in result["missing"][0]
    world["baseline"]["totalEvalAmount"] = 100000000
    rc, result, _ = run(world)
    kr = next(b for b in result["rebalance"]["bands"] if b["id"] == "kr")
    deposit = Decimal(30000000) * (1 + Decimal("0.03") * 18 / 365)
    expected = Decimal(30000000) * 100 / (Decimal(80000000) + deposit)
    assert result["status"] == "ESTIMATED"
    assert Decimal(kr["currentPct"]).quantize(Decimal("0.01")) == expected.quantize(Decimal("0.01"))


def test_baseline_positions_are_frozen_against_policy_edits(world):
    before = run(world)[1]
    policy = json.loads(json.dumps(POLICY))
    next(s for s in policy["sleeves"] if s["id"] == "global")["funds"][0]["share"] = "2"
    write(world["dir"] / "policy.json", policy)
    after = run(world)[1]
    assert before["estimate"]["funds"] == after["estimate"]["funds"]
    assert before["inputSha256"] != after["inputSha256"]
    del world["baseline"]["positions"]
    assert run(world)[1]["status"] == "ERROR"


def test_recorded_execution_rebases_the_estimate(world, tmp_path):
    world["prices"]["s:r1"].update({"2026-11-13": "200", END: "200"})
    for sid in ("s:kr", "s:r2", "s:eu"):
        world["prices"][sid]["2026-11-13"] = "100"
    assert run(world)[1]["decision"] == "SEND"
    log = write(tmp_path / "executions.json", {"_meta": {"kind": "executions"}, "entries": [
        {"date": "2026-11-13", "positionsAfter": TARGET, "source": "https://example.invalid/owner-done"}]})
    world["baseline"]["executionsLog"] = str(log)
    result = run(world)[1]
    assert (result["decision"], result["breachKeys"]) == ("IN_BAND", [])


def test_cross_check_disagreement_withholds_the_trade_plan(world):
    world["map"]["series"]["s:alt"] = {"source": "krx_etf_nav", "code": "alt"}
    world["map"]["crossChecks"] = [{"fundCode": "R1", "product": ["s:alt"], "tolerancePct": "1"}]
    world["prices"]["s:alt"] = {START: "100", END: "100"}
    grow(world, "R1", "200")
    result = run(world)[1]
    assert result["decision"] == "SEND" and result["rebalance"]["plan"] is not None
    assert (result["estimate"]["crossChecks"][0]["state"], result["planShown"]) == ("어긋남", False)
    world["prices"]["s:alt"][END] = "200"
    assert run(world)[1]["planShown"] is True


@pytest.mark.parametrize("change", ["before_rate_window", "past_maturity"])
def test_deposit_rate_is_used_only_for_deposits_it_applies_to(world, change):
    rate = json.loads((world["funds"] / "deposit_rates.json").read_text(encoding="utf-8"))
    if change == "before_rate_window":
        rate["rates"][0]["appliesFrom"] = "2026-11-05"
    else:
        rate["rates"][0]["termMonths"] = 0
    write(world["funds"] / "deposit_rates.json", rate)
    result = run(world)[1]
    assert result["status"] == "NO_ESTIMATE" and any("예금" in m for m in result["missing"])


@pytest.mark.parametrize("day", [START, END])
def test_non_positive_proxy_value_is_missing_not_a_total_loss(world, day):
    world["prices"]["s:kr"][day] = "0"
    rc, result, _ = run(world)
    assert (rc, result["status"], result["decision"]) == (0, "NO_ESTIMATE", "NO_ESTIMATE")


def test_breach_that_resolved_while_an_alert_was_unsent_is_alerted_again(world, tmp_path):
    state = tmp_path / "state.json"
    grow(world, "R1", "200")
    assert run(world, state=state)[1]["decision"] == "SEND"
    mark_sent(world, state)
    grow(world, "R1", "50")
    flipped = run(world, state=state)[1]
    assert flipped["decision"] == "SEND" and "band:global:-" in flipped["newKeys"]
    grow(world, "R1", "200")
    again = run(world, state=state)[1]
    assert again["decision"] == "SEND" and "band:global:+" in again["newKeys"]


def test_malformed_key_is_refused_without_printing_it(world, tmp_path):
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "krx").write_text("DUMMY-KEY-PART\nSECOND-PART", encoding="utf-8")
    d = world["dir"]
    args = [sys.executable, str(SCRIPT), "fetch", "--baseline", str(write(d / "baseline.json", world["baseline"])),
            "--map", str(write(d / "map.json", world["map"])), "--store", str(d / "fetched.json"), "--as-of", END]
    done = subprocess.run(args, capture_output=True, text=True, check=False,
                          env={**os.environ, "DORI_SECRETS_DIR": str(secrets)})
    assert done.returncode == 1 and json.loads(done.stdout)["status"] == "ERROR"
    assert "DUMMY-KEY-PART" not in done.stdout + done.stderr and "SECOND-PART" not in done.stdout + done.stderr


def test_cross_check_after_an_execution_covers_the_window_the_estimate_uses(world, tmp_path):
    middle = "2026-11-13"
    for prices in world["prices"].values():
        prices[middle] = "100"
    world["map"]["series"]["s:alt"] = {"source": "krx_etf_nav", "code": "alt"}
    world["map"]["crossChecks"] = [{"fundCode": "R1", "product": ["s:alt"], "tolerancePct": "1"}]
    world["prices"]["s:alt"] = {START: "100", middle: "100", END: "100"}
    world["prices"]["s:r1"].update({middle: "50", END: "100"})
    log = write(tmp_path / "executions.json", {"_meta": {"kind": "executions"}, "entries": [
        {"date": middle, "positionsAfter": TARGET, "source": "https://example.invalid/owner-done"}]})
    world["baseline"]["executionsLog"] = str(log)
    result = run(world)[1]
    assert result["decision"] == "SEND"
    assert (result["estimate"]["crossChecks"][0]["state"], result["planShown"]) == ("어긋남", False)


def test_execution_that_leaves_the_deposit_alone_keeps_its_deposit_date(world, tmp_path):
    rates = json.loads((world["funds"] / "deposit_rates.json").read_text(encoding="utf-8"))
    rates["rates"][0].update(rate=0, termMonths=1)
    write(world["funds"] / "deposit_rates.json", rates)
    swap, end = "2026-11-25", "2026-12-03"
    for prices in world["prices"].values():
        prices.update({swap: "100", end: "100"})
    assert run(world, as_of=end)[1]["status"] == "NO_ESTIMATE"
    after = [dict(row) for row in TARGET]
    after[0]["weight"], after[1]["weight"] = "25", "10"
    log = write(tmp_path / "executions.json", {"_meta": {"kind": "executions"}, "entries": [
        {"date": swap, "positionsAfter": after, "source": "https://example.invalid/owner-done"}]})
    world["baseline"]["executionsLog"] = str(log)
    result = run(world, as_of=end)[1]
    assert result["status"] == "NO_ESTIMATE" and any("만기" in m for m in result["missing"])
