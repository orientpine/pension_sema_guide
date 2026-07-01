"""Schema and evidence rule tests for pension_tax_params.json"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
PARAMS_FILE = ROOT / "funds" / "pension_tax_params.json"


def load_params():
    data = json.loads(PARAMS_FILE.read_text(encoding="utf-8"))
    return data


def test_parameters_is_object():
    """parameters must be a dict keyed by id, not an array"""
    data = load_params()
    assert isinstance(data["parameters"], dict), "parameters must be an object (dict), not an array"


def test_meta_freshness_threshold():
    """_meta.freshnessThresholdDays must be 90"""
    data = load_params()
    assert data["_meta"]["freshnessThresholdDays"] == 90


def test_verified_params_have_lawgokr_anchor():
    """Every 'verified' parameter must have at least 1 law.go.kr evidence entry"""
    data = load_params()
    params = data["parameters"]
    for param_id, param in params.items():
        if param["verificationStatus"] == "verified":
            evidence = param.get("evidence", [])
            assert len(evidence) >= 3, f"{param_id}: verified params need ≥3 evidence records"
            has_anchor = any("law.go.kr" in e.get("sourceUrl", "") for e in evidence)
            assert has_anchor, f"{param_id}: verified params need law.go.kr primary anchor"


def test_has_unverified_params():
    """Some parameters must NOT be verified (seed/unverified acceptable)"""
    data = load_params()
    params = data["parameters"]
    has_unverified = any(
        v["verificationStatus"] != "verified" for v in params.values()
    )
    assert has_unverified, "Expected some non-verified (seed/unverified) parameters"


def test_structural_constants_present():
    """Structural constants must be stored as parameters, not literals"""
    data = load_params()
    params = data["parameters"]
    required = [
        "연금수령한도_분모상수",
        "연금수령한도_배수",
        "퇴직소득세_감면율_10년이하",
        "퇴직소득세_감면율_11년_20년",
        "퇴직소득세_감면율_21년이상",
    ]
    for param_id in required:
        assert param_id in params, f"Structural constant {param_id} must be a parameter"


def test_evidence_has_required_fields():
    """Each evidence record must have required fields"""
    data = load_params()
    required_fields = {"sourceUrl", "sourceTier", "original_text", "조문", "시행일", "collectedAt"}
    for param_id, param in data["parameters"].items():
        for i, ev in enumerate(param.get("evidence", [])):
            for field in required_fields:
                assert field in ev, f"{param_id}.evidence[{i}] missing field: {field}"


def test_no_basis_mix_for_same_rate():
    """국세기준 and 지방세포함 rates must be separate parameters"""
    data = load_params()
    params = data["parameters"]
    # Check that we have separate params for both basis types
    national_params = [k for k, v in params.items() if v.get("basis") == "국세기준"]
    inclusive_params = [k for k, v in params.items() if v.get("basis") == "지방세포함"]
    assert len(national_params) >= 2, "Expected ≥2 params with basis=국세기준"
    assert len(inclusive_params) >= 2, "Expected ≥2 params with basis=지방세포함"
