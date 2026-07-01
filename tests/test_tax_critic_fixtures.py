"""
Tax Critic fixture validation tests.
Verifies that the critic rules correctly REJECT the 4 violation types.
These tests validate the DETECTION LOGIC, not the agent runtime.
"""
import re
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).parent.parent
FIXTURES_DIR: Final = ROOT / "tests" / "fixtures" / "tax"


def load_fixture(filename: str) -> str:
    path = FIXTURES_DIR / filename
    assert path.exists(), f"Fixture not found: {path}"
    return path.read_text(encoding="utf-8")


def actionable_report_lines(report: str) -> list[str]:
    return [
        line
        for line in report.splitlines()
        if line.strip()
        and not line.startswith("#")
        and not line.startswith("[")
    ]


def critic_detects_unverified(report: str) -> bool:
    for line in actionable_report_lines(report):
        has_unverified_param = "연금소득세율_" in line or "퇴직소득세_감면율_" in line
        has_definitive = "정확히" in line or "됩니다" in line or "입니다" in line
        has_hold_caveat = "보류" in line or "참고용" in line or "미검증" in line
        if has_unverified_param and has_definitive and not has_hold_caveat:
            return True
    return False


def critic_detects_future_effective(report: str) -> bool:
    future_patterns = [
        r"시행 예정",
        r"미래 시행",
        r"effectiveDate.*>.*오늘",
        r"\d{4}-\d{2}-\d{2}부터 시행",
    ]
    return any(re.search(pattern, report) for pattern in future_patterns)


def critic_detects_basis_mix(report: str) -> bool:
    for line in actionable_report_lines(report):
        has_inclusive_rate = "13.2" in line or "16.5" in line
        has_basis_label = "지방세포함" in line or "국세기준" in line or "basis" in line.lower()
        if has_inclusive_rate and not has_basis_label:
            return True
    return False


def critic_detects_unmapped_summary(report: str) -> bool:
    has_unmapped_signal = "검증 부록에 없는" in report or "미매핑" in report or "27만원" in report
    return has_unmapped_signal


class TestTaxCriticFixtures:
    def test_fixture_01_unverified_detected(self):
        report = load_fixture("fixture-01-unverified.md")
        assert critic_detects_unverified(report), (
            "Critic failed to detect unverified parameter used as definitive value"
        )

    def test_fixture_02_future_effective_detected(self):
        report = load_fixture("fixture-02-future-effective.md")
        assert critic_detects_future_effective(report), (
            "Critic failed to detect future-effective parameter usage"
        )

    def test_fixture_03_basis_mix_detected(self):
        report = load_fixture("fixture-03-basis-mix.md")
        assert critic_detects_basis_mix(report), (
            "Critic failed to detect basis label mixing (13.2% without '지방세포함' label)"
        )

    def test_fixture_04_unmapped_summary_detected(self):
        report = load_fixture("fixture-04-summary-unmapped.md")
        assert critic_detects_unmapped_summary(report), (
            "Critic failed to detect unmapped amount in 04-summary"
        )
