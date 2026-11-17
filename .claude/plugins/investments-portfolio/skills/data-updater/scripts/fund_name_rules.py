#!/usr/bin/env python3
"""펀드명 표기에서 환헤지 여부와 DC 위험자산 한도 상태를 정하는 공용 규칙.

classify_funds.py(일반 펀드)와 update_tdf_data.py(TDF)가 같이 쓴다. stdlib만 쓴다.

위험자산 판정 기준 (퇴직연금감독규정 [시행 2023. 11. 16.] 금융위원회고시 제2023-56호):
- 근로자퇴직급여 보장법 시행령 제26조: 원리금보장 운용방법과 "투자위험을 낮춘 운용방법"만
  적립금의 100%까지, 그 밖의 운용방법은 70%까지.
- 감독규정 제11조 제1항: "투자위험을 낮춘 운용방법"의 목록. 펀드에 해당하는 것은
  5호 약관상 주식 투자한도 50% 미만 증권형 집합투자증권(투자부적격 채무증권 한도 30% 초과 제외),
  6호 MMF, 9호 감독원장 기준을 충족한 TDF(적격TDF), 10호 승인받은 사전지정운용방법.
- 금융위 2023-11-16 보도자료(fsc.go.kr/no010101/81085): 채권혼합형펀드의 주식 편입 한도를
  40% 이내 → 50% 미만으로 상향해 100% 투자 가능 상품에 넣었다.
  (원문 발췌: reviews/evidence/sema-fix-p0/law/, 2026-11-17 KST 확인)

펀드명의 유형 표기(예: "[주식]", "(주식-재간접형)", "[채권혼합]")는 금융투자협회 유형 분류로,
약관상 주식 편입 한도를 나타낸다. 투자부적격 채권 한도(30%)는 이름으로 알 수 없으므로
5호로 본 펀드는 needsConfirmation=True로 표시하고, 하이일드처럼 이름에 투자부적격 위주가
드러나면 unverified(한도 산입)로 둔다. 판단할 수 없는 것은 unverified이고, unverified는
70% 한도 계산에 위험자산으로 넣는다.
"""

from __future__ import annotations

import re

RISK = "risk"
NON_RISK = "nonRisk"
UNVERIFIED = "unverified"

BASIS_RISK_EQUITY = (
    "주식 편입 한도 50% 이상 유형(약관) → 감독규정 제11조① 각 호 비해당, 시행령 제26조 70% 한도 산입"
)
BASIS_RISK_NON_SECURITIES = (
    "증권형이 아닌 집합투자기구(혼합자산·특별자산·부동산) → 감독규정 제11조①5호 비해당, 70% 한도 산입"
)
BASIS_NONRISK_SEC5 = (
    "감독규정 제11조①5호: 약관상 주식 한도 50% 미만 증권형 → 100% 가능 "
    "(투자부적격 채권 한도 30% 이하 조건은 펀드명으로 확인 불가 — 포털 표시·규약 확인 필요)"
)
BASIS_NONRISK_MMF = "감독규정 제11조①6호: 단기금융집합투자기구(MMF) → 100% 가능"
BASIS_UNVERIFIED_HIGH_YIELD = (
    "투자부적격 채권 위주(하이일드) 표기 → 감독규정 제11조①5호 괄호 제외 대상일 수 있음, 미확인으로 70% 한도 산입"
)
BASIS_UNVERIFIED_UNKNOWN = "유형 표기로 주식 편입 한도를 알 수 없음 → 미확인으로 70% 한도 산입"

_TYPE_TAG_RE = re.compile(
    r"[\(\[]([^\(\)\[\]]*(?:주식|채권|혼합|재간접|자산|부동산|파생|금-|금_|MMF|단기금융|리츠|REITs)[^\(\)\[\]]*)[\)\]]"
)
_BODY_TYPE_RE = re.compile(r"(혼합자산|특별자산|부동산|단기금융|MMF)")
_HIGH_YIELD_RE = re.compile(r"하이일드|하이 일드|high\s*yield|투자부적격", re.IGNORECASE)


def derive_hedge(name: str) -> str | None:
    """펀드명의 환헤지 표기: "UH"(환노출), "H"(환헤지), None(표기 없음).

    UH를 먼저 본다. "(UH)" 안의 "H)"를 헤지로 잡던 오류(classify_funds 구판)를 막는다.
    """
    upper_name = name.upper()
    if "(UH)" in upper_name or re.search(r"(?<![A-Z])UH(?![A-Z])", upper_name) or "환노출" in name:
        return "UH"
    if "(H)" in upper_name or "H[" in upper_name or "[H]" in upper_name or "환헤지" in name:
        return "H"
    return None


def extract_type_tag(name: str) -> str | None:
    match = _TYPE_TAG_RE.search(name)
    if match:
        return match.group(1).strip().replace("_", "-")
    body = _BODY_TYPE_RE.search(name)
    if body:
        return body.group(1)
    return None


def classify_risk(name: str) -> dict[str, object]:
    """DC 70% 한도 상태. riskStatus는 risk / nonRisk / unverified, unverified는 한도 산입.

    적격TDF 면제(제11조①9호)는 여기서 다루지 않는다 — tdf_data.json의 tdfQualified로 따로 본다.
    """
    tag = extract_type_tag(name)
    status = UNVERIFIED
    basis = BASIS_UNVERIFIED_UNKNOWN
    needs_confirmation = False

    if tag is None:
        pass
    elif tag in ("혼합자산", "특별자산", "부동산") or tag.startswith(("금-", "리츠", "REITs")):
        status, basis = RISK, BASIS_RISK_NON_SECURITIES
    elif tag in ("단기금융", "MMF"):
        status, basis = NON_RISK, BASIS_NONRISK_MMF
    elif tag.startswith("주식"):
        status, basis = RISK, BASIS_RISK_EQUITY
    elif tag.startswith("채권") and "파생" not in tag:
        status, basis, needs_confirmation = NON_RISK, BASIS_NONRISK_SEC5, True

    if status == NON_RISK and needs_confirmation and _HIGH_YIELD_RE.search(name):
        status, basis, needs_confirmation = UNVERIFIED, BASIS_UNVERIFIED_HIGH_YIELD, False

    return {
        "typeTag": tag,
        "riskStatus": status,
        "riskBasis": basis,
        "needsConfirmation": needs_confirmation,
    }
