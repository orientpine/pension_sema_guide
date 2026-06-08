"""RED: canonicalize_name normalization rules (Oracle design A)."""
from update_tdf_data import canonicalize_name


def test_year_and_hedge_uh():
    c = canonicalize_name("KB 온국민 적격TDF 2055 증권 자투자신탁(주식혼합-재간접형)(UH) C-퇴직e")
    assert c["year"] == 2055
    assert c["hedge"] == "UH"


def test_hedge_h_bracket():
    c = canonicalize_name("삼성 글로벌액티브 적격TDF 2055 증권투자신탁H[주식혼합-재간접형]_Cpe(퇴직연금)")
    assert c["hedge"] == "H"


def test_spacing_invariant():
    a = canonicalize_name("삼성 글로벌 EMP 적격 TDF 2055 증권자투자신탁[주식혼합-재간접형]_Cpe(퇴직연금)")
    b = canonicalize_name("삼성글로벌EMP적격TDF2055증권자투자신탁[주식혼합-재간접형]_Cpe(퇴직연금)")
    assert a["key"] == b["key"]


def test_jonglyu_token_stripped():
    a = canonicalize_name("한국투자TDF알아서2015증권투자신탁(채권혼합-재간접형) 종류 C-Re")
    b = canonicalize_name("한국투자TDF알아서2015증권투자신탁(채권혼합-재간접형)(C-Re)")
    assert a["key"] == b["key"]


def test_jeokgyeok_dropped():
    a = canonicalize_name("삼성글로벌EMP적격TDF2030증권자투자신탁[주식혼합-재간접형]_Cpe(퇴직연금)")
    b = canonicalize_name("삼성글로벌EMPTDF2030증권자투자신탁[주식혼합-재간접형]_Cpe(퇴직연금)")
    assert a["key"] == b["key"]


def test_vehicle_collapsed_in_key_strict_preserves():
    a = canonicalize_name("신한빠른대응적격TDF2040증권투자신탁(H)[주식혼합-재간접형](종류C-re)")
    b = canonicalize_name("신한빠른대응적격TDF2040증권자투자신탁(H)[주식혼합-재간접형](종류C-re)")
    assert a["key"] == b["key"], "vehicle token 자 must be collapsed for matching"
    assert a["key_strict"] != b["key_strict"], "strict key must preserve the 자 difference"


def test_distinct_share_class_c_p_vs_c_r():
    cp = canonicalize_name("신한마음편한적격TDF2030증권투자신탁[주식혼합-재간접형](종류C-p)")
    cr = canonicalize_name("신한마음편한적격TDF2030증권투자신탁[주식혼합-재간접형](종류C-r)")
    assert cp["key"] != cr["key"]


def test_distinct_share_class_p2e_vs_pe2():
    a = canonicalize_name("미래에셋ETF로자산배분적격TDF2045증권자투자신탁(주식혼합-재간접형)종류C-P2e")
    b = canonicalize_name("미래에셋ETF로자산배분적격TDF2045증권자투자신탁(주식혼합-재간접형)종류C-Pe2")
    assert a["key"] != b["key"]
