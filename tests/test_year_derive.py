"""CURRENT_YEAR derivation: data base date (_meta.version) > system year.

Verifies that the TDF age-band reference year is derived (not hardcoded) and that
recommendedAgeBand shifts deterministically when the reference year changes.
"""
from datetime import date

from update_tdf_data import (
    CURRENT_YEAR,
    _derive_current_year,
    derive_recommended_age_band,
)


def test_derives_year_from_data_version():
    # Priority 1: parse the leading 4 digits of the data base date.
    assert _derive_current_year("2026-06-04") == 2026
    assert _derive_current_year("2030-01-01") == 2030


def test_falls_back_to_system_year_when_version_missing():
    # Priority 2: no usable version -> system year (relative, no hardcoded date).
    assert _derive_current_year(None) == date.today().year
    assert _derive_current_year("") == date.today().year


def test_falls_back_to_system_year_on_malformed_version():
    assert _derive_current_year("garbage") == date.today().year
    assert _derive_current_year("20XX-01-01") == date.today().year


def test_module_current_year_is_not_hardcoded_literal():
    # CURRENT_YEAR must equal the value derived from the active data version,
    # not a frozen 2026 literal.
    from update_tdf_data import TDF_VERSION

    assert CURRENT_YEAR == _derive_current_year(TDF_VERSION)


def test_age_band_uses_derived_reference_year():
    # targetYear 2055, retirement 60 -> birth_year 1995.
    # current_year 2026 -> age 31 -> band [25, 35]; current_year 2030 -> age 35 -> band [30, 40].
    assert derive_recommended_age_band(2055, current_year=2026) == [25, 35]
    assert derive_recommended_age_band(2055, current_year=2030) == [30, 40]
    # Changing only the reference year must change the band.
    assert derive_recommended_age_band(2055, current_year=2026) != derive_recommended_age_band(
        2055, current_year=2030
    )


def test_age_band_default_reference_year_matches_current_year():
    # Default reference year is the derived CURRENT_YEAR.
    assert derive_recommended_age_band(2040) == derive_recommended_age_band(
        2040, current_year=CURRENT_YEAR
    )
