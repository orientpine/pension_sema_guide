"""주장 종류별 출처 기준: 공식 사실은 발표 기관 1차 출처로 확정, 해석은 해석으로만 쓴다.

leadership-analyst가 기준금리·현직 인물까지 '독립 3출처'를 요구해 7개국 금리가 모두 비고
decision_usable=false가 된 회귀(2026-11-17)를 막는다. 기준을 낮추지 않는 쪽(재게시 3건,
발표 기관이 아닌 단일 출처, 오래된 조회, 값 충돌)도 함께 잡는다.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / ".claude/plugins/macro-analysis/scripts/claim_status.py"
AS_OF = "2026-11-17"
ISSUERS = {
    "미국": ("https://www.whitehouse.gov/administration/", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm"),
    "중국": ("https://english.www.gov.cn/state_council/", "https://www.pbc.gov.cn/en/3688229/index.html"),
    "한국": ("https://www.president.go.kr/", "https://www.bok.or.kr/portal/singl/baseRate/list.do"),
    "일본": ("https://japan.kantei.go.jp/", "https://www.boj.or.jp/en/mopo/mpmdeci/index.htm"),
    "인도": ("https://www.pmindia.gov.in/en/", "https://www.rbi.org.in/"),
    "베트남": ("https://en.baochinhphu.vn/", "https://www.sbv.gov.vn/"),
    "인도네시아": ("https://www.presidenri.go.id/", "https://www.bi.go.id/en/"),
}


def source(url: str, origin: str, value: str | None = None, accessed: str = "2026-11-17T20:00:00+09:00") -> dict:
    row = {"url": url, "independent_origin": origin, "accessed_at": accessed,
           "original_text": f"{origin} says {value or 'the incumbent'}"}
    if value is not None:
        row["observed_value"] = value
    return row


def country(name: str, rate_sources: list[dict] | None = None, leader_sources: list[dict] | None = None,
            rate: str | None = "4.00") -> dict:
    leader_url, bank_url = ISSUERS[name]
    return {
        "country": name,
        "leader": {"name": "현직", "title": "정상", "claim_type": "official_fact",
                   "sources": leader_sources if leader_sources is not None else [source(leader_url, "정부")]},
        "policy_orientation": {"claim_type": "interpretation", "monetary": "중립(해석)",
                               "original_text": "data dependent", "sources": [source(bank_url, "중앙은행")]},
        "central_bank": {
            "name": "중앙은행", "current_rate": None if rate is None else f"{rate}%",
            "rate_claim": None if rate is None else {
                "claim_type": "official_fact", "value": rate, "unit": "%", "decision_date": "2026-10-28",
                "sources": rate_sources if rate_sources is not None else [source(bank_url, "중앙은행", rate)],
            },
        },
    }


def document(countries: list[dict] | None = None, regional: list[dict] | None = None) -> dict:
    return {
        "analysis_date": AS_OF,
        "countries": countries if countries is not None else [country(name) for name in ISSUERS],
        "allocation_implications": {"regional": regional if regional is not None else [
            {"region": "중국", "recommendation": "유지", "claim_type": "interpretation", "is_inference": True}]},
    }


def run(tmp_path: Path, payload: dict) -> dict:
    path = tmp_path / "leadership-analysis.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    done = subprocess.run([sys.executable, str(SCRIPT), str(path), "--as-of", AS_OF],
                          capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_issuer_primary_source_alone_confirms_official_facts(tmp_path: Path) -> None:
    report = run(tmp_path, document())
    assert report["decision_usable"] is True
    assert report["missing"] == []
    assert {c["central_bank_rate"]["basis"] for c in report["countries"].values()} == {"issuer_primary"}


@pytest.mark.parametrize("defect,reason", [
    ("reposts", "ISSUER_PRIMARY_MISSING"),
    ("non_issuer", "ISSUER_PRIMARY_MISSING"),
    ("stale", "ISSUER_PRIMARY_MISSING"),
    ("conflict", "VALUE_MISMATCH"),
    ("no_quote", "ISSUER_PRIMARY_MISSING"),
])
def test_official_fact_is_not_loosened(tmp_path: Path, defect: str, reason: str) -> None:
    bank = ISSUERS["중국"][1]
    wire = "https://apnews.com/article/pboc"
    rate_sources = {
        "reposts": [source(wire, "AP", "3.00"), source("https://finance.yahoo.com/news/pboc", "AP", "3.00"),
                    source("https://www.usnews.com/news/pboc", "AP", "3.00")],
        "non_issuer": [source("https://www.reuters.com/markets/pboc", "Reuters", "3.00")],
        "stale": [source(bank, "PBOC", "3.00", accessed="2026-11-01T09:00:00+09:00")],
        "conflict": [source(bank, "PBOC", "3.00"), source(wire, "AP", "2.90")],
        "no_quote": [{**source(bank, "PBOC", "3.00"), "original_text": " "}],
    }[defect]
    rows = [country(name) for name in ISSUERS if name != "중국"]
    rows.append(country("중국", rate_sources=rate_sources, rate="3.00"))
    report = run(tmp_path, document(rows))
    assert report["decision_usable"] is False
    assert report["countries"]["중국"]["central_bank_rate"]["status"] == reason
    assert "중국.central_bank_rate" in report["missing"]


def test_three_independent_origins_still_confirm_when_issuer_site_is_closed(tmp_path: Path) -> None:
    rate_sources = [source("https://apnews.com/a", "AP", "5.50"), source("https://www.reuters.com/b", "Reuters", "5.50"),
                    source("https://www.bloomberg.com/c", "Bloomberg", "5.50")]
    rows = [country(name) for name in ISSUERS if name != "인도"]
    rows.append(country("인도", rate_sources=rate_sources, rate="5.50"))
    report = run(tmp_path, document(rows))
    assert report["countries"]["인도"]["central_bank_rate"]["basis"] == "independent_3"
    assert report["decision_usable"] is True


def test_missing_rate_or_unverified_displayed_rate_blocks_decision(tmp_path: Path) -> None:
    rows = [country(name) for name in ISSUERS if name not in ("베트남", "일본")]
    rows.append(country("베트남", rate=None))
    japan = country("일본", rate_sources=[source("https://www.reuters.com/boj", "Reuters", "0.75")], rate="0.75")
    rows.append(japan)
    report = run(tmp_path, document(rows))
    assert report["decision_usable"] is False
    assert {"베트남.central_bank_rate", "일본.central_bank_rate"} <= set(report["missing"])
    assert "일본.current_rate: 확정되지 않은 수치가 표시됨" in report["issues"]


@pytest.mark.parametrize("regional,issue", [
    ([{"region": "중국", "recommendation": "확대", "claim_type": "interpretation", "is_inference": True,
       "target_weight": 7}], "allocation_implications.regional[0]: 해석은 방향(확대·유지·축소)만, 수치 비중 금지"),
    ([{"region": "중국", "recommendation": "대폭 확대", "claim_type": "interpretation", "is_inference": True}],
     "allocation_implications.regional[0]: 방향은 확대·유지·축소 중 하나"),
    ([{"region": "중국", "recommendation": "확대"}],
     "allocation_implications.regional[0]: 해석 표시(claim_type=interpretation, is_inference=true) 없음"),
])
def test_interpretation_gives_direction_only(tmp_path: Path, regional: list[dict], issue: str) -> None:
    report = run(tmp_path, document(regional=regional))
    assert report["decision_usable"] is False
    assert issue in report["issues"]


def test_policy_orientation_must_be_labeled_interpretation(tmp_path: Path) -> None:
    rows = [country(name) for name in ISSUERS]
    rows[0]["policy_orientation"].pop("claim_type")
    report = run(tmp_path, document(rows))
    assert report["decision_usable"] is False
    assert "미국.policy_orientation: 해석 표시(claim_type=interpretation) 없음" in report["issues"]


def test_missing_country_is_reported(tmp_path: Path) -> None:
    report = run(tmp_path, document([country(name) for name in ISSUERS if name != "인도네시아"]))
    assert report["decision_usable"] is False
    assert {"인도네시아.leader", "인도네시아.central_bank_rate"} <= set(report["missing"])


def test_unreadable_input_is_nonzero(tmp_path: Path) -> None:
    path = tmp_path / "leadership-analysis.json"
    path.write_text("[", encoding="utf-8")
    done = subprocess.run([sys.executable, str(SCRIPT), str(path), "--as-of", AS_OF],
                          capture_output=True, text=True, check=False)
    assert done.returncode == 1


@pytest.mark.parametrize("display,usable", [("99%", False), ("3.00% (1년 LPR)", True), (None, False)])
def test_displayed_rate_must_match_verified_claim(tmp_path: Path, display: str | None, usable: bool) -> None:
    rows = [country(name) for name in ISSUERS if name != "중국"]
    china = country("중국", rate="3.00")
    china["central_bank"]["current_rate"] = display
    rows.append(china)
    report = run(tmp_path, document(rows))
    assert report["decision_usable"] is usable
    if display == "99%":
        assert "중국.current_rate: 표시값이 검증된 rate_claim.value와 다름" in report["issues"]
