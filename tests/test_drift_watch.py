"""drift_watch.py: 실행 기준 + 대리 시계열 → 추정 비중 → policy_alloc.rebalance 밴드·70%·쏠림 → 새 이탈만 알림."""
from __future__ import annotations

import json
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


def write(path: Path, value) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def world(tmp_path):
    funds = tmp_path / "funds"
    shutil.copytree(FIXTURES / "dc_limits", funds)
    deposits = json.loads((funds / "deposit_rates.json").read_text(encoding="utf-8"))
    deposits["rates"][0]["rate"] = 3.0
    write(funds / "deposit_rates.json", deposits)
    write(tmp_path / "policy.json", POLICY)
    baseline = {"_meta": {"kind": "execution-baseline", "status": "set", "source": "https://example.invalid/owner"},
                "plan": "A", "policy": "policy.json", "executedOn": START}
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
    assert first == second


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
    state = write(tmp_path / "state.json", {"keys": {}})
    rc, result, _ = run(world, state=state)
    assert (rc, result["status"], result["decision"]) == (0, "NO_ESTIMATE", "NO_ESTIMATE")
    assert result.get("estimate") is None and result.get("message") is None and result["missing"]
    assert json.loads(state.read_text(encoding="utf-8")) == {"keys": {}}


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
    assert result["status"] == "ESTIMATED" and Decimal(kr["currentPct"]) > 27
