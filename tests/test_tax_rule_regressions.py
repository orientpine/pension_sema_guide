"""01~03 회귀: 산문 대신 SSOT 규칙과 실제 계산 결과를 검사한다.

공식 근거·확인 시각은 pension_tax_params.json의 해당 evidence에 기록한다.
아래 금액은 개인정보가 아닌 독립 산술 검산용 합성 입력이다.
"""

import json
import math
from collections.abc import Mapping
from copy import deepcopy
from datetime import date
from fractions import Fraction
from typing import TypedDict

import pytest

import test_tax_calc as calc


class TaxRule(TypedDict):
    value: list[str]
    includedSources: list[str]
    excludedSources: list[str]
    aboveBoundary: str
    rateParam: str
    verificationStatus: str
    effectiveDate: str
    refreshStatus: str


class TaxComparison(TypedDict):
    eligibleIncome: int
    regime: str
    separatePensionTax: int
    separateTotalTax: int
    comprehensiveTotalTax: int
    preferred: str


def rule_status(rule: TaxRule, as_of: date) -> str:
    """기계 판독 규칙에도 수치 파라미터와 같은 보류 조건을 적용한다."""
    if (rule["verificationStatus"] != "verified"
            or rule["refreshStatus"] == "disproven"
            or date.fromisoformat(rule["effectiveDate"]) > as_of):
        return "SUSPEND: 공식 확인 필요, 계산 보류"
    return "OK"


def allocate_withdrawal(
    rule: TaxRule, amount: int, balances: Mapping[str, int],
) -> tuple[Mapping[str, int] | None, str]:
    """SSOT 순서대로 일부 인출의 재원을 배분한다."""
    status = rule_status(rule, date.today())
    if status != "OK":
        return None, status
    remaining = amount
    allocation = {}
    for source in rule["value"]:
        allocation[source] = min(remaining, balances[source])
        remaining -= allocation[source]
    return allocation, "OK"


def compare_pension_tax(
    params: calc.TaxParams, rule: TaxRule, sources: Mapping[str, int],
    comprehensive_total: int, other_comprehensive_total: int,
) -> tuple[TaxComparison | None, str]:
    """국세 결정세액 전체를 같은 기준으로 비교한다(종합세액은 별도 검증 입력)."""
    status = rule_status(rule, date.today())
    if status != "OK":
        return None, status
    if sources.keys() - set(rule["includedSources"]) - set(rule["excludedSources"]):
        return None, "SUSPEND: 재원 분류 확인 필요"
    eligible = sum(sources.get(source, 0) for source in rule["includedSources"])
    regime, boundary = calc.check_separate_taxation(params, eligible)
    if regime is None:
        return None, str(boundary)
    if regime == "available":
        return None, "SUSPEND: 경계 이하 연령·계약별 세율 검증 필요"
    rate, status = calc.get_param_value(params, rule["rateParam"])
    if status != "OK":
        return None, status
    rate_param = params[rule["rateParam"]]
    if (date.fromisoformat(rate_param["effectiveDate"]) > date.today()
            or rate_param["refreshStatus"] == "disproven"):
        return None, "SUSPEND: 분리과세율 시행·검증 확인 필요"
    assert rate is not None
    pension_tax = math.floor(eligible * Fraction(str(rate)) / calc.PERCENT_BASE)
    separate_total = pension_tax + other_comprehensive_total
    preferred = "separate" if separate_total < comprehensive_total else "comprehensive"
    if separate_total == comprehensive_total:
        preferred = "equal"
    return {"eligibleIncome": eligible, "regime": rule["aboveBoundary"],
            "separatePensionTax": pension_tax, "separateTotalTax": separate_total,
            "comprehensiveTotalTax": comprehensive_total, "preferred": preferred}, "OK"


def calc_retirement_withholding(
    params: calc.TaxParams, receipt: int, deferred_income: int, deferred_tax: int,
    actual_receipt_year: int, receipt_date: date,
) -> tuple[int | None, str]:
    """이연세액/이연소득 × 수령액 × 적용비율을 마지막에만 절사한다."""
    for param_id in calc.param_ids_by_prefix(params, "퇴직소득세_원천징수적용비율_"):
        param = params[param_id]
        upper = param["yearThrough"]
        if actual_receipt_year < param["yearFrom"] or (upper is not None and actual_receipt_year > upper):
            continue
        ratio, status = calc.get_param_value(params, param_id)
        if status != "OK":
            return None, status
        if (date.fromisoformat(param["effectiveDate"]) > receipt_date
                or param["refreshStatus"] == "disproven"
                or param["semantics"] != "withholding_multiplier"):
            return None, "SUSPEND: 원천징수 적용비율의 시행·의미 확인 필요"
        assert ratio is not None
        return math.floor(Fraction(receipt * deferred_tax, deferred_income)
                          * Fraction(str(ratio)) / calc.PERCENT_BASE), "OK"
    return None, "SUSPEND: 실제 수령연차 구간 확인 필요"


def test_review01_tax_exempt_funds_are_withdrawn_first() -> None:
    data = json.loads(calc.PARAMS_PATH.read_text(encoding="utf-8"))
    order = data.get("rules", {}).get("withdrawalOrder", {}).get("value")
    assert order == ["과세제외금액", "이연퇴직소득", "그밖의과세금액"]
    # 800 중 과세제외 300을 먼저 빼고, 남은 500은 이연퇴직소득에서 인출.
    allocation, status = allocate_withdrawal(
        data["rules"]["withdrawalOrder"], 800,
        {"과세제외금액": 300, "이연퇴직소득": 900, "그밖의과세금액": 600},
    )
    assert status == "OK"
    assert allocation == {"과세제외금액": 300, "이연퇴직소득": 500, "그밖의과세금액": 0}


@pytest.mark.parametrize("income,expected", [(14_999_999, "available"), (15_000_000, "available"), (15_000_001, "choice")])
def test_review02_boundary_choice(income: int, expected: str) -> None:
    assert calc.check_separate_taxation(calc.load_params(), income) == (expected, 15_000_000)


def test_review02_excludes_separately_taxed_sources_and_compares_total_tax() -> None:
    data = json.loads(calc.PARAMS_PATH.read_text(encoding="utf-8"))
    rule = data.get("rules", {}).get("separateTaxation", {})
    assert rule.get("excludedSources") == [
        "과세제외금액", "이연퇴직소득", "의료목적등", "공적연금", "연금외수령기타소득",
    ]
    # 대상 9백만 + 7백만 = 1천6백만. 별도분리과세/비과세 재원은 합산하지 않음.
    # 특례 세액 = 대상 전체 16,000,000 × 15/100 + 다른 종합소득 결정세액 800,000
    #             = 2,400,000 + 800,000 = 3,200,000 (초과분만 과세하지 않음).
    sources = {"공제받은납입액": 9_000_000, "운용수익": 7_000_000,
               "과세제외금액": 100_000_000, "이연퇴직소득": 40_000_000,
               "의료목적등": 30_000_000, "공적연금": 20_000_000,
               "연금외수령기타소득": 10_000_000}
    result, status = compare_pension_tax(
        data["parameters"], rule, sources, 3_600_000, 800_000,
    )
    assert status == "OK"
    assert result == {"eligibleIncome": 16_000_000, "regime": "choice",
                      "separatePensionTax": 2_400_000, "separateTotalTax": 3_200_000,
                      "comprehensiveTotalTax": 3_600_000, "preferred": "separate"}


@pytest.mark.parametrize("year,expected", [(1, 700_000), (10, 700_000), (11, 600_000), (20, 600_000), (21, 500_000)])
def test_review03_multiplies_withholding_ratio(year: int, expected: int) -> None:
    data = json.loads(calc.PARAMS_PATH.read_text(encoding="utf-8"))
    ratios = {key: value for key, value in data["parameters"].items()
              if key.startswith("퇴직소득세_원천징수적용비율_")}
    assert len(ratios) == 3
    assert all(p["semantics"] == "withholding_multiplier" for p in ratios.values())
    # 실데이터의 보류는 유지. 산식만 분리 검증하기 위해 복사본을 검증완료로 가정.
    params = deepcopy(data["parameters"])
    for key in ratios:
        params[key]["verificationStatus"] = "verified"
    # 이연퇴직소득 10,000,000 중 2,000,000 수령, 이연세액 5,000,000:
    # 배분 세액 1,000,000 × 70/100 = 700,000; ×60/100 =600,000; ×50/100 =500,000.
    amount, status = calc_retirement_withholding(
        params, 2_000_000, 10_000_000, 5_000_000, year, date(2026, 1, 1),
    )
    assert status == "OK"
    assert amount == expected


def test_review03_unverified_and_pre_effective_receipts_suspend() -> None:
    params = calc.load_params()
    ratio_ids = calc.param_ids_by_prefix(params, "퇴직소득세_원천징수적용비율_")
    assert len(ratio_ids) == 3
    amount, status = calc_retirement_withholding(
        params, 2_000_000, 10_000_000, 5_000_000, 21, date(2026, 1, 1),
    )
    assert amount is None
    assert status.startswith("SUSPEND")
    verified = deepcopy(params)
    for key in ratio_ids:
        verified[key]["verificationStatus"] = "verified"
    amount, status = calc_retirement_withholding(
        verified, 2_000_000, 10_000_000, 5_000_000, 21, date(2025, 12, 31),
    )
    assert amount is None
    assert status.startswith("SUSPEND")
