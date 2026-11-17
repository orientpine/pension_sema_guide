"""R03/R04: 실제 CLI 계약과 독립적인 손계산 예시의 회귀 검사."""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude/plugins/investments-portfolio/skills/dc-pension-rules/scripts"
SCRIPT = SCRIPTS / "dc_limits.py"
FIXTURES = Path(__file__).parent / "fixtures/dc_limits"
sys.path.insert(0, str(SCRIPTS))


def deposit(weight):
    return {"kind": "principalGuaranteed", "name": "예금", "weight": str(weight)}


def allocation(risk="70", other=None):
    weight = Decimal(risk)
    return [
        {"fundCode": "R1", "weight": str(weight / 2)},
        {"fundCode": "R2", "weight": str(weight / 2)},
        other or deposit(100 - weight),
    ]


def invoke(tmp_path, command, **inputs):
    args = [sys.executable, str(SCRIPT), command, "--funds-dir", str(FIXTURES), "--json"]
    for key, value in inputs.items():
        if key == "mode":
            args.extend(["--mode", value])
        else:
            path = tmp_path / f"{key}.json"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            args.extend(["--" + key, str(path)])
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    assert completed.stdout, completed.stderr
    return completed.returncode, json.loads(completed.stdout)


@pytest.mark.parametrize("risk,verdict,code", [("70.00", "PASS", 0), ("70.01", "FAIL", 1)])
def test_check_boundary(tmp_path, risk, verdict, code):
    rc, result = invoke(tmp_path, "check", allocation=allocation(risk))
    assert (rc, result["verdict"]) == (code, verdict)
    assert Decimal(result["nonExemptRiskWeight"]) == Decimal(risk)


def test_check_qualified_tdf_exemption_and_warning(tmp_path):
    rc, result = invoke(tmp_path, "check", allocation=[{"fundCode": "Q", "weight": 100}])
    assert (rc, result["verdict"], result["nonExemptRiskWeight"]) == (0, "PASS", "0")
    assert result["singleFundChecks"][0]["severity"] == "WARNING"
    assert result["funds"][0]["status"] == "risk"
    assert result["funds"][0]["hedge"] == "UH"


def test_check_nonqualified_tdf_judged_by_type_not_exempted(tmp_path):
    rc, result = invoke(tmp_path, "check", allocation=[
        {"fundCode": "N", "weight": 40}, {"fundCode": "R1", "weight": 35}, deposit(25)
    ])
    assert (rc, result["verdict"], result["nonExemptRiskWeight"]) == (0, "PASS", "35")
    assert next(f for f in result["funds"] if f["fundCode"] == "N")["tdfQualified"] is False


@pytest.mark.parametrize("code,status", [("U", "unverified"), ("T", "unverified")])
def test_check_unverified_and_nonqualified_tdf_counted(tmp_path, code, status):
    rc, result = invoke(tmp_path, "check", allocation=[
        {"fundCode": code, "weight": 40}, {"fundCode": "R1", "weight": 35}, deposit(25)
    ])
    assert (rc, result["verdict"], result["nonExemptRiskWeight"]) == (1, "FAIL", "75")
    assert next(f for f in result["funds"] if f["fundCode"] == code)["status"] == status


@pytest.mark.parametrize("code", ["B", "OLD"])
def test_check_pending_confirmation_including_legacy(tmp_path, code):
    rc, result = invoke(tmp_path, "check", allocation=allocation(
        "70", {"fundCode": code, "weight": 30}
    ))
    assert (rc, result["verdict"], result["conservativeRiskWeight"]) == (0, "PASS_PENDING_CONFIRMATION", "100")
    assert result["confirmationFunds"] == ["확인채권" if code == "B" else "구분류채권"]


def test_check_legacy_risk_and_exact_name(tmp_path):
    rc, result = invoke(tmp_path, "check", allocation=[
        {"name": "구분류주식", "weight": 40}, deposit(60)
    ])
    assert (rc, result["nonExemptRiskWeight"]) == (0, "40")


def test_check_total_error(tmp_path):
    rc, result = invoke(tmp_path, "check", allocation=[deposit("99.999")])
    assert (rc, result["verdict"], result["totalWeight"]) == (1, "ERROR", "99.999")


def test_check_unknown_names_exit_two(tmp_path):
    rc, result = invoke(tmp_path, "check", allocation=[
        {"name": "없는펀드", "weight": 50}, {"fundCode": "MISSING", "weight": 50}
    ])
    assert (rc, result["unknownFunds"]) == (2, ["MISSING", "없는펀드"])


def test_check_holdings_market_drift(tmp_path):
    rc, result = invoke(tmp_path, "check", allocation=allocation("80"), mode="holdings")
    assert (rc, result["verdict"]) == (0, "MARKET_DRIFT_OVER_LIMIT")
    assert "위반 아님, 다음 변경 시 조정" in result["messages"][0]


def test_check_single_fund_error_and_principal_exemption(tmp_path):
    rc, result = invoke(tmp_path, "check", allocation=[{"fundCode": "S", "weight": 41}, deposit(59)])
    assert (rc, result["verdict"]) == (1, "ERROR")
    assert {row["name"]: row["severity"] for row in result["singleFundChecks"]} == {
        "확정채권": "ERROR", "예금": "EXEMPT"
    }


def test_check_duplicate_code_name_cannot_bypass_concentration(tmp_path):
    rc, result = invoke(tmp_path, "check", allocation=[
        {"fundCode": "R1", "weight": 25}, {"name": "위험가", "weight": 25}, deposit(50)
    ])
    assert (rc, result["verdict"]) == (1, "ERROR")
    assert len(result["funds"]) == 2


@pytest.mark.parametrize("value", [-1, "NaN", "Infinity", True])
def test_check_rejects_invalid_weight(tmp_path, value):
    rc, result = invoke(tmp_path, "check", allocation=[deposit(value)])
    assert (rc, result["verdict"]) == (1, "ERROR")


def test_portal_largest_remainder_ties():
    module = importlib.import_module("dc_limits")
    assert module.largest_remainder({"다": Decimal(1), "가": Decimal(1), "나": Decimal(1)}) == {
        "가": 34, "나": 33, "다": 33
    }
    # 같은 소수부 0.5에서 부족액 60.5가 39.5보다 먼저 1%를 받는다.
    assert module.largest_remainder({"가": Decimal("39.5"), "나": Decimal("60.5")}) == {"가": 39, "나": 61}


def test_portal_sell_math_and_new_target(tmp_path):
    holdings = json.loads((FIXTURES / "holdings.json").read_text())
    target = json.loads((FIXTURES / "target.json").read_text())
    rc, result = invoke(tmp_path, "portal", holdings=holdings, target=target)
    # 총 100,000원. 위험가 60,000 -> 40,000: 20,000 매도 = 100/3%.
    # 내림 33% -> 19,800(-200), 올림 34% -> 20,400(+400).
    # 예금 40,000 -> 30,000: 10,000 매도. 30,000 전액 위험나 신규 매수.
    sell = next(row for row in result["sells"] if row["name"] == "위험가")
    # 내림 33% 매도면 위험가가 40.2%가 되어 단일 펀드 한도 위반 -> 전체 판정도 FAIL(입력 금지 방식 표시)
    assert (rc, result["verdict"], result["unsafeIntegerSell"]) == (1, "FAIL", ["floor"])
    assert Decimal(sell["exactPct"]) == Decimal(100) / 3
    assert (sell["floorPct"], sell["ceilPct"], sell["floorErrorKRW"], sell["ceilErrorKRW"]) == (33, 34, "-200", "400")
    assert result["buys"] == [{"name": "위험나", "shortfall": "30000", "integerPct": 100}]
    assert result["newTargetFunds"] == ["위험나"]
    assert result["postTradeCheck"]["verdict"] == "PASS"
    assert all(Decimal(row["errorKRW"]) == 0 for row in result["roundingErrors"])
    assert result["integerSellScenarios"]["floor"]["check"]["verdict"] == "ERROR"


@pytest.mark.parametrize("name", ["위험가", "목록에없는예금"])
def test_check_principal_guaranteed_must_be_listed_deposit(tmp_path, name):
    rc, result = invoke(tmp_path, "check", allocation=[
        {"kind": "principalGuaranteed", "name": name, "weight": 100}
    ])
    assert (rc, result["verdict"], result["unknownFunds"]) == (2, "ERROR", [name])


def test_portal_integer_buy_rounding_is_rechecked(tmp_path):
    rc, result = invoke(tmp_path, "portal",
        holdings=[{"fundCode": "R1", "evalAmount": 3540},
                  {"kind": "principalGuaranteed", "name": "예금", "evalAmount": 6460}],
        target=[{"fundCode": "R1", "weight": "35.4"}, {"fundCode": "R2", "weight": "34.6"},
                {"fundCode": "S", "weight": 30}])
    assert rc == 1
    assert sum(row["integerPct"] for row in result["buys"]) == 100
    assert result["targetCheck"]["verdict"] == "PASS"
    assert result["postTradeCheck"]["verdict"] == "FAIL"
    assert {r["name"]: r["errorKRW"] for r in result["roundingErrors"]} == {
        "예금": "0", "위험가": "0", "위험나": "28.4", "확정채권": "-28.4"
    }


def test_portal_contributions_three_columns_checked_before_and_after_rounding(tmp_path):
    rc, result = invoke(tmp_path, "portal",
        holdings=json.loads((FIXTURES / "holdings.json").read_text()),
        target=json.loads((FIXTURES / "target.json").read_text()),
        contributions=json.loads((FIXTURES / "contributions.json").read_text()))
    assert rc == 1
    columns = result["contributions"]
    assert set(columns) == {"기본", "일시전환", "경영성과"}
    assert all(sum(r["integerPct"] for r in c["allocation"]) == 100 for c in columns.values())
    assert [columns[k]["inputCheck"]["verdict"] for k in ("기본", "일시전환", "경영성과")] == ["PASS", "FAIL", "PASS"]
    assert all(c["check"]["verdict"] == "PASS" for c in columns.values())


@pytest.mark.parametrize("holdings,target,message", [
    ([{"fundCode": "Q", "evalAmount": 0}], [{"fundCode": "Q", "weight": 100}], "총평가금액이 0"),
    ([{"fundCode": "Q", "evalAmount": -1}], [{"fundCode": "Q", "weight": 100}], "음수"),
    ([{"fundCode": "Q", "evalAmount": "1.5"}], [{"fundCode": "Q", "weight": 100}], "정수"),
    ([{"fundCode": "Q", "evalAmount": 100}], [{"fundCode": "Q", "weight": -1}, deposit(101)], "음수"),
])
def test_portal_invalid_values(tmp_path, holdings, target, message):
    rc, result = invoke(tmp_path, "portal", holdings=holdings, target=target)
    assert (rc, result["verdict"]) == (1, "ERROR")
    assert message in " ".join(result["messages"])


def test_portal_nothing_to_sell(tmp_path):
    rc, result = invoke(tmp_path, "portal",
        holdings=[{"fundCode": "Q", "evalAmount": 100}], target=[{"fundCode": "Q", "weight": 100}])
    assert (rc, result["sellProceeds"], result["buys"]) == (0, "0", [])
    assert "매도할 금액 없음" in result["messages"]


def test_portal_missing_contribution_column(tmp_path):
    rc, result = invoke(tmp_path, "portal",
        holdings=[{"fundCode": "Q", "evalAmount": 100}], target=[{"fundCode": "Q", "weight": 100}],
        contributions={"기본": [{"fundCode": "Q", "weight": 100}]})
    assert (rc, result["verdict"]) == (1, "ERROR")

HEDGE_ALLOCATION = [{"fundCode": "R1", "weight": "20"}, {"fundCode": "R2", "weight": "10"},
                    {"fundCode": "EU", "weight": "20"}, {"fundCode": "KR", "weight": "20"}, deposit(30)]


@pytest.mark.parametrize("target,tolerance,status", [
    (None, None, "INFO"), ("60", "15", "UNCERTAIN"), ("0", "5", "OUTSIDE_REFERENCE"), ("40", "25", "WITHIN_REFERENCE")])
def test_check_hedge_mix_is_reference_only(tmp_path, target, tolerance, status):
    args = [sys.executable, str(SCRIPT), "check", "--funds-dir", str(FIXTURES), "--json"]
    path = tmp_path / "allocation.json"
    path.write_text(json.dumps(HEDGE_ALLOCATION, ensure_ascii=False), encoding="utf-8")
    args += ["--allocation", str(path)]
    if target is not None:
        args += ["--hedge-target", target, "--hedge-tolerance", tolerance]
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    mix = result["hedgeMix"]
    assert (completed.returncode, result["verdict"]) == (0, "PASS")
    assert (Decimal(mix["foreignWeight"]), Decimal(mix["hedged"]), Decimal(mix["unhedged"]),
            Decimal(mix["unknown"])) == (50, 10, 20, 20)
    assert (Decimal(mix["hedgedShareMin"]), Decimal(mix["hedgedShareMax"])) == (20, 60)
    assert mix["status"] == status
