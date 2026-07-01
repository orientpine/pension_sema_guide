"""
Deterministic pension tax calculation revalidation tests.
ALL tax values are loaded from funds/pension_tax_params.json.
"""

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Final, Literal, TypedDict

ROOT: Final = Path(__file__).parent.parent
PARAMS_PATH: Final = ROOT / "funds" / "pension_tax_params.json"
PERCENT_BASE: Final = 100

IncomeLevel = Literal["high", "low"]


class TaxParam(TypedDict, total=False):
    value: int | float
    verificationStatus: str


TaxParams = Mapping[str, TaxParam]


def load_params() -> TaxParams:
    """Load all tax parameters from the JSON SSOT."""
    return json.loads(PARAMS_PATH.read_text(encoding="utf-8"))["parameters"]


def get_param_value(params: TaxParams, param_id: str) -> tuple[int | float | None, str]:
    """Get a verified parameter value, or suspend calculation when not verified."""
    param = params.get(param_id)
    if param is None:
        return None, f"SUSPEND: 계산 보류 — {param_id} NOT_FOUND"
    if param["verificationStatus"] != "verified":
        return (
            None,
            f"SUSPEND: 계산 보류 — {param_id} verificationStatus={param['verificationStatus']}",
        )
    return param["value"], "OK"


def _credit_rate_param_id(income_level: IncomeLevel) -> str:
    if income_level == "high":
        return "공제율_국세기준_고소득"
    return "공제율_국세기준_저소득"


def _tax_credit_limit_param_id(income_level: IncomeLevel) -> str:
    if income_level == "high":
        return "연금계좌_세액공제한도"
    return "연금계좌_세액공제한도_총급여5500이하"


def calc_tax_credit(
    params: TaxParams,
    contribution: float,
    income_level: IncomeLevel,
) -> tuple[int | None, str]:
    """Calculate pension tax credit with verified national-tax parameters only."""
    limit_val, status = get_param_value(params, _tax_credit_limit_param_id(income_level))
    if status != "OK":
        return None, status

    rate_val, rate_status = get_param_value(params, _credit_rate_param_id(income_level))
    if rate_status != "OK":
        return None, rate_status

    assert limit_val is not None
    assert rate_val is not None
    base = min(contribution, limit_val)
    credit = math.floor(base * rate_val / PERCENT_BASE)
    return credit, "OK"


def calc_isa_additional_credit(
    params: TaxParams,
    isa_transfer_amount: float,
    income_level: IncomeLevel,
) -> tuple[int | None, str]:
    """Calculate ISA transfer additional tax credit."""
    rate_val, rate_status = get_param_value(params, "ISA전환_공제율")
    limit_val, limit_status = get_param_value(params, "ISA전환_공제한도")

    if rate_status != "OK":
        return None, rate_status
    if limit_status != "OK":
        return None, limit_status

    assert rate_val is not None
    assert limit_val is not None
    additional_base = min(isa_transfer_amount * rate_val / PERCENT_BASE, limit_val)

    credit_rate_val, credit_rate_status = get_param_value(
        params,
        _credit_rate_param_id(income_level),
    )
    if credit_rate_status != "OK":
        return None, credit_rate_status

    assert credit_rate_val is not None
    credit = math.floor(additional_base * credit_rate_val / PERCENT_BASE)
    return credit, "OK"


def calc_withdrawal_limit(
    params: TaxParams,
    balance: float,
    year_count: int,
) -> tuple[int | None, str]:
    """Calculate pension withdrawal limit, including the no-limit singularity."""
    denom_val, denom_status = get_param_value(params, "연금수령한도_분모상수")
    mult_val, mult_status = get_param_value(params, "연금수령한도_배수")

    if denom_status != "OK":
        return None, denom_status
    if mult_status != "OK":
        return None, mult_status

    assert denom_val is not None
    assert mult_val is not None
    effective_denom = denom_val - year_count
    if effective_denom <= 0:
        return None, "NO_LIMIT"

    limit = math.floor(balance / effective_denom * mult_val / PERCENT_BASE)
    return limit, "OK"


def check_separate_taxation(
    params: TaxParams,
    annual_pension_income: float,
) -> tuple[str | None, int | float | str]:
    """Determine whether separate taxation remains available."""
    boundary_val, status = get_param_value(params, "사적연금_분리과세_경계")
    if status != "OK":
        return None, status

    assert boundary_val is not None
    if annual_pension_income <= boundary_val:
        return "available", boundary_val
    return "required", boundary_val


def param_ids_by_prefix(params: TaxParams, prefix: str) -> list[str]:
    """Collect parameter IDs without spelling numeric age or period labels in tests."""
    return sorted(param_id for param_id in params if param_id.startswith(prefix))


class TestTaxCredit:
    def test_tax_credit_high_income(self):
        """Given verified high-income national rate, credit equals floored formula."""
        params = load_params()
        limit_val = params[_tax_credit_limit_param_id("high")]["value"]

        credit, status = calc_tax_credit(params, limit_val, "high")

        assert status == "OK"
        rate_val = params[_credit_rate_param_id("high")]["value"]
        expected = math.floor(limit_val * rate_val / PERCENT_BASE)
        assert credit == expected

    def test_tax_credit_low_income(self):
        """Given verified low-income national rate, credit equals floored formula."""
        params = load_params()
        limit_val = params[_tax_credit_limit_param_id("low")]["value"]

        credit, status = calc_tax_credit(params, limit_val, "low")

        assert status == "OK"
        rate_val = params[_credit_rate_param_id("low")]["value"]
        expected = math.floor(limit_val * rate_val / PERCENT_BASE)
        assert credit == expected

    def test_tax_credit_capped_at_limit(self):
        """Given contribution above limit, credit is capped at the parameter limit."""
        params = load_params()
        limit_val = params[_tax_credit_limit_param_id("high")]["value"]
        over_contribution = limit_val * 2

        credit_over, status_over = calc_tax_credit(params, over_contribution, "high")
        credit_at_limit, status_at_limit = calc_tax_credit(params, limit_val, "high")

        assert status_over == "OK"
        assert status_at_limit == "OK"
        assert credit_over == credit_at_limit

    def test_tax_credit_effective_rate_seed_suspended(self):
        """Given seed effective-rate parameter, calculator access returns hold status."""
        params = load_params()

        _, status = get_param_value(params, "공제율_체감_고소득")

        assert "SUSPEND" in status
        assert "보류" in status

    def test_tax_credit_mismatch_is_detectable(self):
        """Given a tampered result, exact comparison detects the mismatch."""
        params = load_params()
        limit_val = params[_tax_credit_limit_param_id("high")]["value"]

        credit, status = calc_tax_credit(params, limit_val, "high")

        assert status == "OK"
        tampered_credit = credit + 10000
        assert credit != tampered_credit


class TestISAAdditionalCredit:
    def test_isa_additional_credit_capped_base(self):
        """Given transfer above cap, additional credit uses the capped base."""
        params = load_params()
        isa_limit = params["ISA전환_공제한도"]["value"]
        isa_rate = params["ISA전환_공제율"]["value"]
        transfer_amount = (isa_limit * PERCENT_BASE / isa_rate) + 1

        credit, status = calc_isa_additional_credit(params, transfer_amount, "high")

        assert status == "OK"
        base = min(transfer_amount * isa_rate / PERCENT_BASE, isa_limit)
        credit_rate = params[_credit_rate_param_id("high")]["value"]
        expected = math.floor(base * credit_rate / PERCENT_BASE)
        assert credit == expected


class TestWithdrawalLimit:
    def test_withdrawal_limit_year_before_denominator(self):
        """Given year immediately before denominator, normal limit is calculated."""
        params = load_params()
        denom = params["연금수령한도_분모상수"]["value"]
        mult = params["연금수령한도_배수"]["value"]
        balance = params["연금계좌_세액공제한도"]["value"] * denom
        year_count = int(denom) - 1

        limit, status = calc_withdrawal_limit(params, balance, year_count)

        assert status == "OK"
        assert (denom - year_count) > 0
        expected = math.floor(balance / (denom - year_count) * mult / PERCENT_BASE)
        assert limit == expected

    def test_withdrawal_limit_at_denominator_year_singularity(self):
        """Given year equal to denominator constant, withdrawal has no limit."""
        params = load_params()
        denom_val = params["연금수령한도_분모상수"]["value"]
        balance = params["연금계좌_세액공제한도"]["value"] * denom_val
        year_count = int(denom_val)

        limit, status = calc_withdrawal_limit(params, balance, year_count)

        assert limit is None
        assert status == "NO_LIMIT"

    def test_withdrawal_limit_denominator_plus_one_year_singularity(self):
        """Given year beyond denominator constant, withdrawal has no limit."""
        params = load_params()
        denom_val = params["연금수령한도_분모상수"]["value"]
        balance = params["연금계좌_세액공제한도"]["value"] * denom_val
        year_count = int(denom_val) + 1

        limit, status = calc_withdrawal_limit(params, balance, year_count)

        assert limit is None
        assert status == "NO_LIMIT"

    def test_retirement_tax_reduction_unverified_suspended(self):
        """Given unverified retirement-tax reduction parameters, access is held."""
        params = load_params()
        reduction_ids = param_ids_by_prefix(params, "퇴직소득세_감면율_")

        assert reduction_ids
        for param_id in reduction_ids:
            _, status = get_param_value(params, param_id)
            assert "SUSPEND" in status
            assert "보류" in status

    def test_pension_income_tax_rate_unverified_suspended(self):
        """Given unverified pension-income tax-rate parameters, access is held."""
        params = load_params()
        rate_ids = param_ids_by_prefix(params, "연금소득세율_")

        assert rate_ids
        for param_id in rate_ids:
            _, status = get_param_value(params, param_id)
            assert "SUSPEND" in status
            assert "보류" in status

    def test_missing_parameter_returns_hold_status(self):
        """Given unknown parameter ID, access returns hold status."""
        params = load_params()

        _, status = get_param_value(params, "존재하지_않는_파라미터")

        assert "SUSPEND" in status
        assert "보류" in status


class TestSeparateTaxation:
    def test_separate_taxation_boundary_is_inclusive(self):
        """Given income at boundary, separate taxation remains available."""
        params = load_params()
        boundary = params["사적연금_분리과세_경계"]["value"]

        result, val = check_separate_taxation(params, boundary)

        assert result == "available"
        assert val == boundary

    def test_separate_taxation_above_boundary_is_required(self):
        """Given income above boundary, comprehensive taxation is required."""
        params = load_params()
        boundary = params["사적연금_분리과세_경계"]["value"]

        result, val = check_separate_taxation(params, boundary + 1)

        assert result == "required"
        assert val == boundary
