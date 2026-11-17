#!/usr/bin/env python3
"""DC 한도 검사와 SEMA 입력 환산. 외부 접속 없이 Decimal로 계산한다."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path


@dataclass(frozen=True)
class InputError(Exception):
    message: str
    unknown: tuple[str, ...] = ()

    def __str__(self) -> str:
        return self.message


def number(value: object, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise InputError(f"{label}: 숫자 또는 십진 문자열 필요")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise InputError(f"{label}: 잘못된 숫자") from exc
    if not result.is_finite():
        raise InputError(f"{label}: 유한한 숫자 필요")
    if result < 0:
        raise InputError(f"{label}: 음수 불가")
    return result


def text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise InputError(f"{label}: 빈 문자열 불가")
    return value


def mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise InputError(f"{label}: JSON 객체 필요")
    return value


def rows(value: object, label: str) -> list[dict]:
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise InputError(f"{label}: JSON 객체 배열 필요")
    return value


def load_json(path: Path) -> object:
    def reject_constant(value: str) -> None:
        raise InputError(f"{path}: 유한하지 않은 JSON 숫자 {value}")

    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal,
                      parse_constant=reject_constant)


@dataclass(frozen=True, slots=True)
class Fund:
    key: str
    code: str | None
    name: str
    status: str
    basis: str
    confirmation: bool
    hedge: str | bool | None
    qualified: bool = False
    principal: bool = False

    @property
    def counted(self) -> bool:
        return not self.principal and not self.qualified and self.status != "nonRisk"


class Catalog:
    def __init__(self, directory: Path):
        classification = mapping(load_json(directory / "fund_classification.json"), "분류 자료")
        self.by_code: dict[str, Fund] = {}
        self.by_name: dict[str, list[Fund]] = {}
        # TDF 자료가 같은 코드의 일반 자료보다 구체적인 적격성 정보를 가진다.
        for filename, is_tdf in (("fund_data.json", False), ("tdf_data.json", True)):
            data = mapping(load_json(directory / filename), filename)
            for row in rows(data.get("funds"), filename):
                name = text(row.get("name"), "펀드명")
                code = text(row.get("fundCode"), "fundCode")
                source = row if is_tdf else mapping(classification.get(name, {}), name)
                status = source.get("riskStatus")
                legacy_nonrisk = status is None and source.get("riskAsset") is False
                if status is None:
                    status = ("risk" if source.get("riskAsset") is True else
                              "nonRisk" if legacy_nonrisk else "unverified")
                if status not in {"risk", "nonRisk", "unverified"}:
                    raise InputError(f"{name}: 알 수 없는 riskStatus")
                confirmation = source.get("needsConfirmation", status == "nonRisk")
                if not isinstance(confirmation, bool):
                    raise InputError(f"{name}: needsConfirmation은 boolean 필요")
                basis = source.get("riskBasis", "구분류 riskAsset 기준, 법적 분류 확인 필요"
                                   if status != "unverified" else "위험 분류 근거 미확인")
                self.by_code[code] = Fund(
                    code, code, name, status, text(basis, "riskBasis"),
                    legacy_nonrisk or confirmation,
                    source.get("hedge", source.get("hedged")),
                    is_tdf and row.get("tdfQualified") is True,
                )
        for fund in self.by_code.values():
            self.by_name.setdefault(fund.name, []).append(fund)

    def resolve(self, row: dict) -> Fund:
        if row.get("kind") == "principalGuaranteed":
            name = text(row.get("name"), "원리금보장 상품명")
            if row.get("fundCode") is not None:
                raise InputError("원리금보장 상품은 fundCode 대신 kind와 name으로 지정")
            return Fund("principal:" + name, None, name, "nonRisk",
                        "근로자퇴직급여보장법 시행령 제25조① 원리금보장", False, None,
                        principal=True)
        if "kind" in row:
            raise InputError("kind는 principalGuaranteed만 지원")
        code, name = row.get("fundCode"), row.get("name")
        if code is not None:
            code = text(code, "fundCode")
            fund = self.by_code.get(code)
            if fund is None:
                raise InputError(f"알 수 없는 펀드: {code}", (code,))
            if name is not None and name != fund.name:
                raise InputError(f"{code}: fundCode와 정확한 name이 일치하지 않음")
            return fund
        name = text(name, "name 또는 fundCode")
        matches = self.by_name.get(name, [])
        if len(matches) != 1:
            raise InputError(f"알 수 없거나 이름이 중복된 펀드: {name}", (name,))
        return matches[0]


Positions = dict[Fund, Decimal]


def positions(value: object, catalog: Catalog, field: str) -> Positions:
    result: Positions = {}
    unknown: set[str] = set()
    for row in rows(value, field):
        try:
            fund = catalog.resolve(row)
        except InputError as exc:
            if not exc.unknown:
                raise
            unknown.update(exc.unknown)
            continue
        amount = number(row.get(field), f"{fund.name}.{field}")
        if field == "evalAmount" and amount != amount.to_integral_value():
            raise InputError(f"{fund.name}: evalAmount는 원 단위 정수 필요")
        result[fund] = result.get(fund, Decimal(0)) + amount
    if unknown:
        raise InputError("알 수 없는 펀드: " + ", ".join(sorted(unknown)), tuple(sorted(unknown)))
    return dict(sorted(result.items(), key=lambda item: (item[0].name, item[0].key)))


def check(values: Positions, config: dict, mode: str = "proposal",
          denominator: Decimal = Decimal(100)) -> dict:
    """배분은 % 단위, 거래 시뮬레이션은 원 단위로 동일한 교차곱 검사를 한다."""
    total = sum(values.values(), Decimal(0))
    limit = number(config["riskLimitPct"], "riskLimitPct")
    single_limit = number(config["singleFundLimitPct"], "singleFundLimitPct")
    inclusive = config["inclusive"]
    if not isinstance(inclusive, bool):
        raise InputError("설정 inclusive는 boolean 필요")
    if denominator <= 0:
        raise InputError("총평가금액이 0")

    def over(amount: Decimal) -> bool:
        left, right = amount * 100, denominator * limit
        return left > right if inclusive else left >= right

    risk = sum((v for f, v in values.items() if f.counted), Decimal(0))
    pending = [f for f, v in values.items()
               if v > 0 and not f.counted and not f.qualified and f.status == "nonRisk" and f.confirmation]
    conservative = risk + sum((values[f] for f in pending), Decimal(0))
    table, singles = [], []
    for fund, amount in values.items():
        weight = amount * 100 / denominator
        table.append({"fundCode": fund.code, "name": fund.name, "weight": weight,
                      "status": fund.status, "basis": fund.basis, "hedge": fund.hedge,
                      "needsConfirmation": fund.confirmation, "tdfQualified": fund.qualified,
                      "nonExempt": fund.counted})
        severity = ("EXEMPT" if fund.principal else
                    "WARNING" if fund.qualified and amount * 100 > denominator * single_limit else
                    "ERROR" if amount * 100 > denominator * single_limit else "PASS")
        singles.append({"name": fund.name, "weight": weight, "severity": severity})
    concentration = any(row["severity"] == "ERROR" for row in singles)
    messages = []
    if total != denominator:
        verdict = "ERROR"
        messages.append("비중 합계는 정확히 100이어야 함")
    elif (over(risk) or concentration) and mode == "holdings":
        verdict = "MARKET_DRIFT_OVER_LIMIT"
        messages.append("위반 아님, 다음 변경 시 조정: 평가액 변동만으로 초과한 보유분에 한함. 운용관리기관 통보 필요")
    elif concentration:
        verdict = "ERROR"
        messages.append("단일 펀드 한도 초과")
    elif over(risk):
        verdict = "FAIL"
        messages.append("위험자산 한도 초과")
    elif over(conservative):
        verdict = "PASS_PENDING_CONFIRMATION"
        messages.append("포털·규약에서 비위험 분류 조건 확인 필요")
    else:
        verdict = "PASS"
    return {"verdict": verdict, "mode": mode, "totalWeight": total * 100 / denominator,
            "nonExemptRiskWeight": risk * 100 / denominator,
            "conservativeRiskWeight": conservative * 100 / denominator,
            "confirmationFunds": [f.name for f in pending],
            "funds": table, "singleFundChecks": singles, "messages": messages,
            "config": config}


def largest_remainder(amounts: dict[str, Decimal], units: int = 100) -> dict[str, int]:
    """소수부, 부족금액 내림차순, 이름 오름차순으로 잔여 단위를 배분한다."""
    if not amounts or sum(amounts.values()) <= 0 or any(v < 0 for v in amounts.values()):
        raise InputError("최대잉여 배분에는 양수 합계와 음수 없는 금액 필요")
    total = sum(amounts.values())
    # 나눗셈으로 소수부를 먼저 반올림하지 않고 나머지의 교차 단위를 사용한다.
    scaled = {name: amount * units for name, amount in amounts.items()}
    result = {name: int(value // total) for name, value in scaled.items()}
    order = sorted(amounts, key=lambda name: (
        -(scaled[name] - result[name] * total), -amounts[name], name))
    for name in order[:units - sum(result.values())]:
        result[name] += 1
    assert sum(result.values()) == units
    return dict(sorted(result.items()))


def ref(fund: Fund) -> dict:
    return ({"kind": "principalGuaranteed", "name": fund.name} if fund.principal else
            {"fundCode": fund.code})


def failed(result: dict) -> bool:
    return result["verdict"] in {"FAIL", "ERROR"}


def portal(holdings: Positions, target: Positions, contributions: object,
           catalog: Catalog, config: dict) -> dict:
    total = sum(holdings.values(), Decimal(0))
    if total == 0:
        raise InputError("총평가금액이 0: 환산 불가")
    target_check = check(target, config)
    if target_check["totalWeight"] != 100:
        raise InputError("목표 비중 합계는 정확히 100이어야 함")
    universe = sorted(holdings.keys() | target.keys(), key=lambda f: (f.name, f.key))
    if len({f.name for f in universe}) != len(universe):
        raise InputError("동일 이름의 서로 다른 상품은 포털 환산에서 구분할 수 없음")
    desired = {f: total * target.get(f, Decimal(0)) / 100 for f in universe}
    sells, shorts = [], {}
    sale_amounts: Positions = {}
    for fund in universe:
        held = holdings.get(fund, Decimal(0))
        sell = max(Decimal(0), held - desired[fund])
        if sell:
            exact = sell / held * 100
            floor = int(exact.to_integral_value(rounding=ROUND_FLOOR))
            ceil = int(exact.to_integral_value(rounding=ROUND_CEILING))
            sells.append({"name": fund.name, "evalAmount": held, "targetAmount": desired[fund],
                          "sellAmount": sell, "exactPct": exact, "floorPct": floor, "ceilPct": ceil,
                          "floorErrorKRW": held * floor / 100 - sell,
                          "ceilErrorKRW": held * ceil / 100 - sell})
            sale_amounts[fund] = sell
        shortfall = max(Decimal(0), desired[fund] - held)
        if shortfall:
            shorts[fund.name] = shortfall
    proceeds = sum(sale_amounts.values(), Decimal(0))
    ratios = largest_remainder(shorts) if shorts else {}
    buys = [{"name": name, "shortfall": shorts[name], "integerPct": pct} for name, pct in ratios.items()]

    def simulate(sales: Positions) -> tuple[list[dict], dict]:
        cash = sum(sales.values(), Decimal(0))
        amounts = {f: holdings.get(f, Decimal(0)) - sales.get(f, Decimal(0)) +
                   cash * ratios.get(f.name, 0) / 100 for f in universe}
        errors = [{"name": f.name, "targetAmount": desired[f], "simulatedAmount": amounts[f],
                   "errorKRW": amounts[f] - desired[f], "weight": amounts[f] * 100 / total}
                  for f in universe]
        return errors, check(amounts, config, denominator=total)

    errors, post_check = simulate(sale_amounts)
    scenarios = {}
    for variant in ("floor", "ceil"):
        rounded_sales = {f: holdings[f] * next(row[variant + "Pct"] for row in sells if row["name"] == f.name) / 100
                         for f in sale_amounts}
        scenario_errors, scenario_check = simulate(rounded_sales)
        scenarios[variant] = {"roundingErrors": scenario_errors, "check": scenario_check}
    columns = {}
    if contributions is not None:
        source = mapping(contributions, "부담금")
        if set(source) != {"기본", "일시전환", "경영성과"}:
            raise InputError("부담금은 기본·일시전환·경영성과 3칸이 모두 필요")
        for name in ("기본", "일시전환", "경영성과"):
            weights = positions(source[name], catalog, "weight")
            input_check = check(weights, config)
            if input_check["totalWeight"] != 100:
                raise InputError(f"부담금 {name}: 합계는 정확히 100이어야 함")
            if len({f.name for f in weights}) != len(weights):
                raise InputError(f"부담금 {name}: 상품명 중복")
            integers = largest_remainder({f.name: w for f, w in weights.items()})
            rounded = {f: Decimal(integers[f.name]) for f in weights}
            columns[name] = {
                "allocation": [{**ref(f), "name": f.name, "integerPct": integers[f.name]} for f in weights],
                "inputCheck": input_check, "check": check(rounded, config)}
    checks = [target_check, post_check] + [
        c[k] for c in columns.values() for k in ("inputCheck", "check")]
    verdict = ("FAIL" if any(failed(c) for c in checks) else
               "PASS_PENDING_CONFIRMATION" if any(c["verdict"] == "PASS_PENDING_CONFIRMATION" for c in checks)
               else "PASS")
    new_funds = [f.name for f in target if f not in holdings and target[f] > 0]
    messages = ["평가금액 고정·수수료 없음 가정. 원 미만 계산값을 유지하며 실제 결제금액·좌수는 포털 확인 필요",
                "주 시뮬레이션은 정확한 매도비율 기준. 정수 매도는 floor/ceil 결과를 별도 확인"]
    if not proceeds:
        messages.append("매도할 금액 없음")
    if new_funds:
        messages.append("목표 펀드가 현재 보유에 없음: 신규 매수 목록 확인 — " + ", ".join(new_funds))
    return {"verdict": verdict, "totalEvalAmount": total, "targetCheck": target_check,
            "sellProceeds": proceeds, "sells": sells, "buys": buys,
            "newTargetFunds": new_funds, "roundingErrors": errors, "postTradeCheck": post_check,
            "integerSellScenarios": scenarios, "contributions": columns, "messages": messages}


def json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else format(value, "f")
    raise TypeError(f"JSON 출력 불가: {type(value).__name__}")


def human(result: dict) -> None:
    print("판정:", result["verdict"])
    for message in result.get("messages", []):
        print(message)
    if "nonExemptRiskWeight" in result:
        print("합계 / 한도 산입 / 보수적 위험 비중:",
              *(json_default(result[k]) + "%" for k in
                ("totalWeight", "nonExemptRiskWeight", "conservativeRiskWeight")))
        print("펀드명 | 비중(%) | 분류 | 근거 | 환헤지 | 단일 펀드")
        for row, single in zip(result["funds"], result["singleFundChecks"]):
            print(f'{row["name"]} | {json_default(row["weight"])} | {row["status"]} | '
                  f'{row["basis"]} | {row["hedge"]} | {single["severity"]}')
        if result["confirmationFunds"]:
            print("포털 확인 대상:", ", ".join(result["confirmationFunds"]))
    if "sells" in result:
        print("매도: 상품 | 매도금액(원) | 정확 비율(%) | 내림% / 오차(원) | 올림% / 오차(원)")
        for r in result["sells"]:
            print(f'{r["name"]} | {r["sellAmount"]} | {r["exactPct"]} | '
                  f'{r["floorPct"]} / {r["floorErrorKRW"]} | {r["ceilPct"]} / {r["ceilErrorKRW"]}')
        print("매수: 상품 | 부족액(원) | 정수 비율(%)")
        for r in result["buys"]:
            print(f'{r["name"]} | {r["shortfall"]} | {r["integerPct"]}')
        print("목표 검사:", result["targetCheck"]["verdict"])
        print("거래 후 검사:")
        human(result["postTradeCheck"])
        print("반올림 오차: 상품 | 목표(원) | 예상(원) | 오차(원)")
        for r in result["roundingErrors"]:
            print(f'{r["name"]} | {r["targetAmount"]} | {r["simulatedAmount"]} | {r["errorKRW"]}')
        for variant, scenario in result["integerSellScenarios"].items():
            print("정수 매도", variant, "검사:")
            human(scenario["check"])
            for r in scenario["roundingErrors"]:
                print(f'{r["name"]} | 예상 {r["simulatedAmount"]}원 | 오차 {r["errorKRW"]}원')
        for column, data in result["contributions"].items():
            print(f'부담금 {column}: 원안 {data["inputCheck"]["verdict"]} / 정수화 {data["check"]["verdict"]}')
            for r in data["allocation"]:
                print(f'{r["name"]} | {r["integerPct"]}%')
            human(data["check"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    checker = commands.add_parser("check", help="목표 배분 또는 평가액 변동 보유분 검사")
    checker.add_argument("--allocation", type=Path, required=True)
    checker.add_argument("--mode", choices=("proposal", "holdings"), default="proposal")
    converter = commands.add_parser("portal", help="SEMA 매도·매수·부담금 환산")
    converter.add_argument("--holdings", type=Path, required=True)
    converter.add_argument("--target", type=Path, required=True)
    converter.add_argument("--contributions", type=Path)
    for command in (checker, converter):
        command.add_argument("--funds-dir", type=Path, default=Path("funds"))
        command.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    exit_code = 0
    try:
        config = mapping(load_json(Path(__file__).with_name("dc_limits_config.json")), "설정")
        catalog = Catalog(args.funds_dir)
        if args.command == "check":
            result = check(positions(load_json(args.allocation), catalog, "weight"), config, args.mode)
        else:
            result = portal(
                positions(load_json(args.holdings), catalog, "evalAmount"),
                positions(load_json(args.target), catalog, "weight"),
                load_json(args.contributions) if args.contributions else None, catalog, config)
        exit_code = 1 if failed(result) else 0
    except InputError as exc:
        result = {"verdict": "ERROR", "messages": [str(exc)]}
        if exc.unknown:
            result["unknownFunds"] = list(exc.unknown)
        exit_code = 2 if exc.unknown else 1
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
        result = {"verdict": "ERROR", "messages": [f"입력·데이터 오류: {exc}"]}
        exit_code = 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=json_default))
    else:
        human(result)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
