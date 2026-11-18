#!/usr/bin/env python3
"""정책 파일로 DC 목표 비중을 계산하고 보유 대비 밴드·포털 거래안을 낸다.

순서: 형 정책 파일(neutral) → 장기 거시 기본 비중(6개월 결정, 검증된 지표만) → 단기 기울이기(검증 통과 시에만)
→ 묶음·펀드 정수 % → dc_limits 검사. rebalance는 보유를 묶음별로 모아 밴드 이탈을 판정하고, 밖이면
dc_limits.portal로 거래안을 만든 뒤 한도를 지키는 정수 매도 방식만 낸다.

묶음은 세 가지다: 위험(risk=true, 70% 산입), 면제(exempt=true, 적격TDF: 위험자산이지만 70% 분자에서 빠지고
스스로 나이에 맞춰 조정되므로 neutral에 고정), 원리금보장(risk=false). 장기 위험 이동은 위험과 원리금보장 사이에서만 움직인다.

외부 접속 없이 Decimal로 계산하고 같은 입력이면 같은 바이트를 낸다. 펀드 과거 수익률 필드는 읽지 않는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dc_limits as dc  # noqa: E402
from dc_limits import InputError, mapping, rows, text  # noqa: E402

ZERO, ONE, HUNDRED = Decimal(0), Decimal(1), Decimal(100)
# 형 결정(2026-11-18, 리드 제안 승인): 단기는 묶음당 ±5%p 안에서만. 장기 기울기·위험 총합 이동도 이 상한을 넘지 않는다.
TILT_CAP_PCT = Decimal(5)
OUTSIDE = "outside"
STATUSES = {"sample", "draft-unapproved", "approved"}
SHORT_KINDS = {"trend", "rate_direction", "valuation_extreme", "credit_spread"}
MATCH_KEYS = {"region", "assetClass", "themes", "principalGuaranteed", "tdfQualified", "riskStatus"}
MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
SOURCE_FIELDS = ("publisher", "url", "accessedAt", "originalText")


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=dc.json_default)


def sha256(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def signed(value: object, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise InputError(f"{label}: 숫자 또는 십진 문자열 필요")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise InputError(f"{label}: 잘못된 숫자") from exc
    if not result.is_finite():
        raise InputError(f"{label}: 유한한 숫자 필요")
    return result


def whole(value: object, label: str, minimum: int = 1) -> int:
    result = dc.number(value, label)
    if result != result.to_integral_value() or result < minimum:
        raise InputError(f"{label}: {minimum} 이상의 정수 필요")
    return int(result)


def clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return max(low, min(high, value))


def month_index(month: object) -> int:
    match = MONTH_RE.match(month) if isinstance(month, str) else None
    if match is None:
        raise InputError(f"월은 YYYY-MM 형식 필요: {month!r}")
    return int(match.group(1)) * 12 + int(match.group(2)) - 1


def month_name(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


@dataclass(frozen=True)
class FundRef:
    key: str
    row: dict
    share: Decimal


@dataclass(frozen=True)
class Sleeve:
    id: str
    label: str
    risk: bool
    neutral: Decimal
    match: dict
    funds: tuple[FundRef, ...]
    exempt: bool = False


@dataclass(frozen=True)
class Indicator:
    id: str
    source_kind: str
    publishers: tuple[str, ...]
    tolerance: Decimal
    minus: tuple[str, str] | None = None
    max_age: int = 1


@dataclass(frozen=True)
class LongRule:
    indicator: str
    neutral: Decimal | None
    scale: Decimal | None
    sleeves: tuple[tuple[str, Decimal], ...]
    risk: Decimal


@dataclass(frozen=True)
class ShortRule:
    id: str
    indicator: str
    kind: str
    window: int
    upper: Decimal | None
    lower: Decimal | None
    sleeves: tuple[tuple[str, Decimal], ...]


@dataclass(frozen=True)
class Policy:
    raw: dict
    sha: str
    status: str
    base_dir: Path
    risk_target: Decimal
    sleeves: tuple[Sleeve, ...]
    band_sleeve: Decimal
    band_near: Decimal
    decide_every: int
    hold: Decimal
    min_verified: int
    long_cap: Decimal
    shift_cap: Decimal
    indicators: dict[str, Indicator]
    long_rules: tuple[LongRule, ...]
    alert_publishers: tuple[str, ...]
    short_enabled: bool
    short_cap: Decimal
    short_rules: tuple[ShortRule, ...]
    validation: dict

    @property
    def risky(self) -> list[Sleeve]:
        return [s for s in self.sleeves if s.risk]

    @property
    def exempt(self) -> list[Sleeve]:
        return [s for s in self.sleeves if s.exempt]

    @property
    def safe(self) -> list[Sleeve]:
        return [s for s in self.sleeves if not s.risk and not s.exempt]

    @property
    def neutral(self) -> dict[str, Decimal]:
        return {s.id: s.neutral for s in self.sleeves}

    @property
    def long_term_sha(self) -> str:
        return sha256({k: self.raw.get(k) for k in ("riskTargetPct", "indicators", "alerts", "longTermMacro", "cadence")}
                      | {"sleeves": [{"id": s.id, "risk": s.risk, "exempt": s.exempt, "neutralPct": s.neutral}
                                     for s in self.sleeves]})

    @property
    def label(self) -> str:
        return "정책 승인됨" if self.status == "approved" else "진단만(정책 미승인)"


def missing_fields(raw: dict) -> list[str]:
    """형이 정할 결정 숫자 가운데 비어 있는 것. 공개 샘플은 전부 비어 있어 계산을 거부한다."""
    paths: list[str] = []

    def need(obj: object, key: str, path: str) -> None:
        if not isinstance(obj, dict) or obj.get(key) is None:
            paths.append(path)

    need(raw, "riskTargetPct", "riskTargetPct")
    sleeves = raw.get("sleeves")
    if not sleeves:
        paths.append("sleeves")
    for i, sleeve in enumerate(sleeves or []):
        need(sleeve, "neutralPct", f"sleeves[{i}].neutralPct")
        funds = sleeve.get("funds") if isinstance(sleeve, dict) else None
        if not funds:
            paths.append(f"sleeves[{i}].funds")
        for j, fund in enumerate(funds or []):
            need(fund, "share", f"sleeves[{i}].funds[{j}].share")
    for section, keys in (("band", ("sleevePct", "nearLimitPct")),
                          ("cadence", ("collectEveryMonths", "decideEveryMonths", "holdThresholdPct",
                                       "minVerifiedMonths")),
                          ("longTermMacro", ("maxSleeveTiltPct", "maxRiskShiftPct")),
                          ("shortTermTilt", ("enabled", "maxTiltPct"))):
        for key in keys:
            need(raw.get(section), key, f"{section}.{key}")
    return paths


def effects(value: object, label: str, risky_ids: set[str]) -> tuple[tuple[tuple[str, Decimal], ...], Decimal]:
    data = mapping(value if value is not None else {}, label)
    sleeves = mapping(data.get("sleeves", {}), label + ".sleeves")
    for sid in sleeves:
        if sid not in risky_ids:
            raise InputError(f"{label}: 위험 묶음이 아닌 {sid}에는 기울기를 줄 수 없음")
    pairs = tuple((sid, signed(sleeves[sid], f"{label}.{sid}")) for sid in sorted(sleeves))
    return pairs, signed(data.get("riskTotal", "0"), label + ".riskTotal")


def optional(value: object, label: str) -> Decimal | None:
    return None if value is None else signed(value, label)


def parse_policy(raw: object, config: dict, base_dir: Path) -> Policy:
    raw = mapping(raw, "정책")
    meta = mapping(raw.get("_meta"), "_meta")
    status = meta.get("status")
    if status not in STATUSES:
        raise InputError("_meta.status는 sample·draft-unapproved·approved 중 하나")
    if status == "approved" and not all(meta.get(k) for k in ("approvedBy", "approvedAt", "approvalSource")):
        raise InputError("approved 정책은 approvedBy·approvedAt·approvalSource(형 원문 링크) 필요")
    missing = missing_fields(raw)
    if missing:
        raise InputError("형이 정할 값이 비어 있어 계산하지 않음: " + ", ".join(missing))
    limit = dc.number(config["riskLimitPct"], "riskLimitPct")
    risk_target = dc.number(raw["riskTargetPct"], "riskTargetPct")
    if risk_target != risk_target.to_integral_value():
        raise InputError("riskTargetPct는 정수 % 필요")
    if risk_target > limit or (risk_target == limit and not config["inclusive"]):
        raise InputError(f"정책 위험자산 목표 {risk_target}%가 한도 {limit}%를 넘음: 정책을 고쳐야 함(재시도·자동 조정 없음)")

    sleeves: list[Sleeve] = []
    seen_funds: dict[str, str] = {}
    for i, item in enumerate(rows(raw["sleeves"], "sleeves")):
        sid = text(item.get("id"), f"sleeves[{i}].id")
        if sid == OUTSIDE or any(s.id == sid for s in sleeves):
            raise InputError(f"묶음 id 중복 또는 예약어: {sid}")
        risk = item.get("risk")
        if not isinstance(risk, bool):
            raise InputError(f"{sid}.risk는 boolean 필요")
        exempt = item.get("exempt", False)
        if not isinstance(exempt, bool):
            raise InputError(f"{sid}.exempt는 boolean 필요")
        if exempt and risk:
            raise InputError(f"{sid}: exempt 묶음(적격TDF, 70% 한도 면제)은 risk=false(70% 비산입)여야 함")
        match = mapping(item.get("match", {}), f"{sid}.match")
        if set(match) - MATCH_KEYS:
            raise InputError(f"{sid}.match: 알 수 없는 키 {sorted(set(match) - MATCH_KEYS)}")
        funds = []
        for j, fund in enumerate(rows(item["funds"], f"{sid}.funds")):
            share = dc.number(fund["share"], f"{sid}.funds[{j}].share")
            if share <= 0:
                raise InputError(f"{sid}.funds[{j}].share는 0보다 커야 함")
            if fund.get("kind") == "principalGuaranteed":
                name = text(fund.get("name"), f"{sid}.funds[{j}].name")
                key, ref = "principal:" + name, {"kind": "principalGuaranteed", "name": name}
            else:
                code = text(fund.get("fundCode"), f"{sid}.funds[{j}].fundCode")
                key, ref = "code:" + code, {"fundCode": code}
                if fund.get("name") is not None:
                    ref["name"] = fund["name"]
            if key in seen_funds:
                raise InputError(f"한 펀드는 한 묶음에만: {key} ({seen_funds[key]}, {sid})")
            seen_funds[key] = sid
            funds.append(FundRef(key, ref, share))
        sleeves.append(Sleeve(sid, str(item.get("label", sid)), risk,
                              dc.number(item["neutralPct"], f"{sid}.neutralPct"), match, tuple(funds), exempt))
    risky_sum = sum((s.neutral for s in sleeves if s.risk), ZERO)
    if risky_sum != risk_target:
        raise InputError(f"위험 묶음 neutralPct 합 {risky_sum} ≠ riskTargetPct {risk_target}")
    if sum((s.neutral for s in sleeves), ZERO) != HUNDRED:
        raise InputError("묶음 neutralPct 합은 정확히 100이어야 함")
    exempt_sum = sum((s.neutral for s in sleeves if s.exempt), ZERO)
    if exempt_sum != exempt_sum.to_integral_value():
        raise InputError(f"면제 묶음 neutralPct 합 {exempt_sum}: 정수 % 필요(면제 묶음은 neutral에 고정)")
    risky_ids = {s.id for s in sleeves if s.risk}

    band = mapping(raw["band"], "band")
    band_sleeve = dc.number(band["sleevePct"], "band.sleevePct")
    band_near = dc.number(band["nearLimitPct"], "band.nearLimitPct")
    if band_sleeve <= 0 or band_near <= 0 or band_near > band_sleeve:
        raise InputError("band: 0 < nearLimitPct ≤ sleevePct 필요")
    cadence = mapping(raw["cadence"], "cadence")
    collect = whole(cadence["collectEveryMonths"], "cadence.collectEveryMonths")
    decide_every = whole(cadence["decideEveryMonths"], "cadence.decideEveryMonths")
    min_verified = whole(cadence["minVerifiedMonths"], "cadence.minVerifiedMonths")
    if decide_every < collect or min_verified > decide_every:
        raise InputError("cadence: collectEveryMonths ≤ decideEveryMonths, minVerifiedMonths ≤ decideEveryMonths 필요")

    indicators: dict[str, Indicator] = {}
    for i, item in enumerate(rows(raw.get("indicators", []), "indicators")):
        iid = text(item.get("id"), f"indicators[{i}].id")
        kind = item.get("sourceKind")
        if iid in indicators or kind not in ("official", "market", "derived"):
            raise InputError(f"지표 {iid}: id 중복이거나 sourceKind가 official·market·derived가 아님")
        if kind == "derived":
            parts = item.get("minus")
            if not (isinstance(parts, list) and len(parts) == 2 and all(p in indicators for p in parts)):
                raise InputError(f"지표 {iid}: derived는 앞에 정의한 지표 두 개 minus [a, b] 필요(a − b)")
            indicators[iid] = Indicator(iid, kind, (), ZERO, (parts[0], parts[1]))
            continue
        publishers = tuple(item.get("officialPublishers") or ())
        if kind == "official" and not publishers:
            raise InputError(f"지표 {iid}: official은 발표 기관(officialPublishers) 필요")
        indicators[iid] = Indicator(iid, kind, publishers, dc.number(item.get("tolerance", "0"), f"{iid}.tolerance"),
                                    max_age=whole(item.get("maxAgeMonths", 1), f"{iid}.maxAgeMonths", 0))

    long_term = mapping(raw["longTermMacro"], "longTermMacro")
    long_cap = dc.number(long_term["maxSleeveTiltPct"], "longTermMacro.maxSleeveTiltPct")
    shift_cap = dc.number(long_term["maxRiskShiftPct"], "longTermMacro.maxRiskShiftPct")
    long_rules = []
    for i, item in enumerate(rows(long_term.get("rules", []), "longTermMacro.rules")):
        iid = text(item.get("indicator"), f"longTermMacro.rules[{i}].indicator")
        if iid not in indicators:
            raise InputError(f"장기 규칙 {iid}: indicators에 없는 지표")
        scale = optional(item.get("scale"), f"{iid}.scale")
        if scale is not None and scale <= 0:
            raise InputError(f"장기 규칙 {iid}: scale은 0보다 커야 함")
        pairs, risk = effects(item.get("effects"), f"장기 규칙 {iid}", risky_ids)
        long_rules.append(LongRule(iid, optional(item.get("neutral"), f"{iid}.neutral"), scale, pairs, risk))

    short = mapping(raw["shortTermTilt"], "shortTermTilt")
    enabled = short["enabled"]
    if not isinstance(enabled, bool):
        raise InputError("shortTermTilt.enabled는 boolean 필요")
    short_cap = dc.number(short["maxTiltPct"], "shortTermTilt.maxTiltPct")
    for label, cap in (("장기 묶음 기울기", long_cap), ("위험 총합 이동", shift_cap), ("단기 기울기", short_cap)):
        if cap > TILT_CAP_PCT:
            raise InputError(f"{label} 상한 {cap}%p가 형이 정한 ±{TILT_CAP_PCT}%p를 넘음")
    short_rules = []
    for i, item in enumerate(rows(short.get("rules", []), "shortTermTilt.rules")):
        rid = text(item.get("id"), f"shortTermTilt.rules[{i}].id")
        iid = text(item.get("indicator"), f"{rid}.indicator")
        kind = item.get("kind")
        if iid not in indicators or kind not in SHORT_KINDS or any(r.id == rid for r in short_rules):
            raise InputError(f"단기 규칙 {rid}: 지표·kind({sorted(SHORT_KINDS)})·id 중복 확인")
        window = 1 if kind == "valuation_extreme" else whole(item.get("window"), f"{rid}.window")
        pairs, risk = effects(item.get("effects"), f"단기 규칙 {rid}", risky_ids)
        if risk:
            raise InputError(f"단기 규칙 {rid}: 위험 총합은 움직일 수 없음(같은 위험자산 비중)")
        short_rules.append(ShortRule(rid, iid, kind, window, optional(item.get("upper"), f"{rid}.upper"),
                                     optional(item.get("lower"), f"{rid}.lower"), pairs))
    alerts = mapping(raw.get("alerts", {}), "alerts")
    return Policy(raw, sha256(raw), status, base_dir, risk_target, tuple(sleeves), band_sleeve, band_near,
                  decide_every, dc.number(cadence["holdThresholdPct"], "cadence.holdThresholdPct"), min_verified,
                  long_cap, shift_cap, indicators, tuple(long_rules), tuple(alerts.get("officialPublishers") or ()),
                  enabled, short_cap, tuple(short_rules), mapping(short.get("validation", {}), "validation"))



GENERIC_SECOND_LEVEL = {"co", "or", "go", "ac", "ne", "re", "pe", "com", "net", "org", "gov", "edu", "mil"}


def site(url: str) -> str:
    """같은 기관의 다른 표기(포트·www·하위 도메인)를 한 출처로 센다: 등록 도메인(예: bok.or.kr, example.com)."""
    labels = [label for label in (urlsplit(url).hostname or "").lower().rstrip(".").split(".") if label]
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in GENERIC_SECOND_LEVEL:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def verify(observation: object, indicator: Indicator | None) -> tuple[Decimal | None, str]:
    """검증되면 (값, 근거), 아니면 (None, 결측 사유). 결측 관측은 비중 계산에 들어가지 않는다."""
    if indicator is None:
        return None, "결측: 정책에 없는 지표"
    if indicator.minus is not None:
        return None, "결측: 계산 지표는 직접 관측을 받지 않음(구성 지표로 계산)"
    if not isinstance(observation, dict):
        return None, "결측: 관측 형식 오류"
    try:
        value = signed(observation.get("value"), "value")
    except InputError:
        return None, "결측: 값 없음"
    if observation.get("sourceKind") != indicator.source_kind:
        return None, f"결측: 출처 종류가 정책({indicator.source_kind})과 다름"
    as_of = observation.get("asOf")
    if not isinstance(as_of, str) or not as_of:
        return None, "결측: 기준일 없음"
    good = []
    for source in observation.get("sources") or []:
        if not isinstance(source, dict) or not all(isinstance(source.get(k), str) and source[k] for k in SOURCE_FIELDS):
            continue
        try:
            source_value = signed(source.get("value"), "source.value")
        except InputError:
            continue
        if source.get("asOf") == as_of and abs(source_value - value) <= indicator.tolerance:
            good.append(source)
    if indicator.source_kind == "official":
        if any(s["publisher"] in indicator.publishers for s in good):
            return value, "검증: 발표 기관 1차 출처"
        return None, "결측: 발표 기관 1차 출처(같은 기준일·같은 값·원문) 없음"
    publishers = {"".join(s["publisher"].split()).lower() for s in good}
    hosts = {site(s["url"]) for s in good}
    if len(publishers) >= 2 and len(hosts) >= 2:
        return value, f"검증: 독립 출처 {min(len(publishers), len(hosts))}곳 같은 기준일·같은 값"
    return None, f"결측: 같은 기준일·같은 값의 독립 출처 {min(len(publishers), len(hosts))}곳(2곳 필요)"


def fresh(value: Decimal, note: str, as_of: str, index: int, max_age: int) -> tuple[Decimal | None, str]:
    try:
        age = index - month_index(as_of[:7])
    except InputError:
        return None, "결측: 기준일 형식 오류(YYYY-MM으로 시작해야 함)"
    if age < 0:
        return None, "결측: 기준일이 기록한 달보다 뒤"
    if age > max_age:
        return None, f"결측: 기준일이 {age}개월 전(허용 {max_age}개월)"
    return value, note


def load_log(path: Path | None) -> dict[int, dict]:
    """매달 한 줄 JSONL: {"month","collectedAt","observations":[...],"alerts":[...]}."""
    if path is None:
        return {}
    log: dict[int, dict] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        entry = mapping(json.loads(line, parse_float=Decimal), f"{path.name}:{number}")
        index = month_index(entry.get("month"))
        if index in log:
            raise InputError(f"{path.name}:{number}: 같은 달 {entry['month']} 줄 중복")
        log[index] = entry
    return log


def verified_series(policy: Policy, log: dict[int, dict], until: int) -> tuple[dict[str, dict[int, Decimal]], list[dict]]:
    series: dict[str, dict[int, Decimal]] = {}
    audit = []
    for index in sorted(log):
        if index > until:
            continue
        seen: set[str] = set()
        for observation in rows(log[index].get("observations", []), "observations"):
            iid = observation.get("indicator")
            if iid in seen:
                raise InputError(f"{month_name(index)}: 지표 {iid} 관측 중복")
            seen.add(iid)
            value, note = verify(observation, policy.indicators.get(iid))
            if value is not None:
                value, note = fresh(value, note, observation.get("asOf"), index, policy.indicators[iid].max_age)
            audit.append({"month": month_name(index), "indicator": iid, "value": observation.get("value"),
                          "asOf": observation.get("asOf"), "verified": value is not None, "note": note})
            if value is not None:
                series.setdefault(iid, {})[index] = value
        for indicator in policy.indicators.values():
            if indicator.minus is None:
                continue
            a, b = (series.get(part, {}).get(index) for part in indicator.minus)
            if a is not None and b is not None:
                series.setdefault(indicator.id, {})[index] = a - b
                audit.append({"month": month_name(index), "indicator": indicator.id, "value": a - b, "asOf": None,
                              "verified": True, "note": f"검증: {indicator.minus[0]} − {indicator.minus[1]} 계산"})
    return series, audit


def verified_alerts(policy: Policy, log: dict[int, dict], after: int, until: int) -> tuple[list[dict], list[dict]]:
    accepted, rejected = [], []
    for index in sorted(log):
        if not after < index <= until:
            continue
        for alert in rows(log[index].get("alerts", []), "alerts"):
            ok = any(isinstance(s, dict) and s.get("publisher") in policy.alert_publishers
                     and all(isinstance(s.get(k), str) and s[k] for k in SOURCE_FIELDS)
                     for s in alert.get("sources") or [])
            record = {"month": month_name(index), "type": alert.get("type"), "summary": alert.get("summary")}
            (accepted if ok else rejected).append(record)
    return accepted, rejected



def zero_sum(tilts: dict[str, Decimal]) -> dict[str, Decimal]:
    """위험 묶음끼리 합 0이 되게 큰 쪽을 비례 축소한다. 한쪽만 있으면 0(위험자산 합 불변)."""
    positive = sum((t for t in tilts.values() if t > 0), ZERO)
    negative = -sum((t for t in tilts.values() if t < 0), ZERO)
    if positive == 0 or negative == 0:
        return {k: ZERO for k in tilts}
    up, down = (negative / positive, ONE) if positive > negative else (ONE, positive / negative)
    return {k: t * up if t > 0 else t * down for k, t in tilts.items()}


def apply_tilt(base: dict[str, Decimal], raw: dict[str, Decimal], cap: Decimal) -> dict[str, Decimal]:
    tilts = {k: max(-base[k], cap * clamp(raw.get(k, ZERO), -ONE, ONE)) for k in base}
    return zero_sum(tilts)


def long_signal(rule: LongRule, mean: Decimal) -> Decimal | None:
    if rule.neutral is None or rule.scale is None:
        return None
    return clamp((mean - rule.neutral) / rule.scale, -ONE, ONE)


def compute_base(policy: Policy, signals: dict[str, Decimal], limit: Decimal) -> tuple[dict[str, Decimal], Decimal]:
    raw = {s.id: ZERO for s in policy.risky}
    raw_risk = ZERO
    for rule in policy.long_rules:
        signal = signals.get(rule.indicator, ZERO)
        for sid, coef in rule.sleeves:
            raw[sid] += coef * signal
        raw_risk += rule.risk * signal
    exempt_total = sum((s.neutral for s in policy.exempt), ZERO)
    safe_neutral = HUNDRED - policy.risk_target - exempt_total
    risk_total = policy.risk_target
    if policy.risk_target > 0 and safe_neutral > 0:
        risk_total = clamp(policy.risk_target + policy.shift_cap * clamp(raw_risk, -ONE, ONE), ZERO,
                           min(limit, HUNDRED - exempt_total))
    risky = {s.id: s.neutral * risk_total / policy.risk_target if policy.risk_target else ZERO for s in policy.risky}
    tilts = apply_tilt(risky, raw, policy.long_cap)
    base = {sid: risky[sid] + tilts[sid] for sid in risky}
    for s in policy.exempt:
        base[s.id] = s.neutral
    for s in policy.safe:
        base[s.id] = s.neutral * (HUNDRED - exempt_total - risk_total) / safe_neutral
    return {s.id: base[s.id] for s in policy.sleeves}, risk_total


def load_decision(previous: object, policy: Policy) -> tuple[dict | None, str | None]:
    if previous is None:
        return None, None
    data = mapping(previous, "이전 결정")
    meta = mapping(data.get("_meta"), "이전 결정 _meta")
    if meta.get("kind") != "base-decision":
        raise InputError("이전 결정 파일의 _meta.kind는 base-decision이어야 함")
    if meta.get("longTermPolicySha256") != policy.long_term_sha:
        return None, "장기 결정에 쓰는 정책 값(위험 목표·묶음 neutral·지표·경보·장기 규칙·주기)이 바뀌어 이전 결정을 쓰지 않고 neutral에서 다시 결정"
    base = mapping(data.get("basePct"), "basePct")
    if set(base) != {s.id for s in policy.sleeves}:
        raise InputError("이전 결정의 묶음이 정책과 다름")
    return data, None


def alert_key(alert: dict) -> tuple:
    return (alert.get("month"), alert.get("type"), alert.get("summary"))


def decide(policy: Policy, log: dict[int, dict], previous: object, month: str, config: dict,
           acknowledge: str | None = None) -> dict:
    """매달 누적한 장기 지표로 decideEveryMonths마다 기본 비중을 정한다.

    창(최근 decideEveryMonths개월) 안 검증 관측이 minVerifiedMonths 이상인 지표만 평균을 새 신호로 쓴다.
    모자라면 결측: 지난 결정의 신호를 그대로 쓰고(자료가 없다고 비중이 움직이지 않음), 지난 신호가 없으면 0.
    묶음별 변화가 모두 holdThresholdPct 미만이면 HOLD. 검증된 체제 변화 경보가 있으면 채택하지 않고 ALERT.
    """
    now = month_index(month)
    limit = dc.number(config["riskLimitPct"], "riskLimitPct")
    prev, note = load_decision(previous, policy)
    prev_index = month_index(mapping(prev["_meta"], "_meta").get("month")) if prev else None
    if prev_index is not None and prev_index > now:
        raise InputError("이전 결정 월이 이번 달보다 뒤")
    series, audit = verified_series(policy, log, now)
    window = range(now - policy.decide_every + 1, now + 1)
    previous_signals = mapping(prev.get("signals", {}), "signals") if prev else {}
    signals: dict[str, Decimal] = {}
    signal_rows = []
    for rule in policy.long_rules:
        values = [series.get(rule.indicator, {}).get(i) for i in window]
        values = [v for v in values if v is not None]
        mean = sum(values, ZERO) / len(values) if len(values) >= policy.min_verified else None
        carried = previous_signals.get(rule.indicator)
        if mean is not None and (signal := long_signal(rule, mean)) is not None:
            state, months_missing = "반영", 0
        elif mean is not None:
            signal, state, months_missing = ZERO, "규칙 미정(기준값 없음): 효과 0", 0
        elif carried is not None:
            signal = signed(carried["signal"], f"{rule.indicator}.signal")
            state = "결측: 지난 결정 신호 유지"
            months_missing = int(carried.get("missingDecisions", 0)) + 1
        else:
            signal, state, months_missing = ZERO, "결측: 효과 0", 0
        signals[rule.indicator] = signal
        signal_rows.append({"indicator": rule.indicator, "verifiedMonths": len(values), "mean": mean,
                            "signal": signal, "state": state, "missingDecisions": months_missing})
    candidate, risk_total = compute_base(policy, signals, limit)
    alerts, rejected_alerts = verified_alerts(policy, log, prev_index if prev_index is not None else now - policy.decide_every, now)
    acknowledged = list(rows(prev.get("acknowledgedAlerts", []), "acknowledgedAlerts")) if prev else []
    seen = {alert_key(a) for a in acknowledged}
    alerts = [a for a in alerts if alert_key(a) not in seen]
    if acknowledge and alerts:
        acknowledged += [{**a, "acknowledgedBy": acknowledge} for a in alerts]
        alerts = []
    prev_base = {k: signed(v, k) for k, v in prev["basePct"].items()} if prev else None
    prev_risk = signed(prev["riskTotalPct"], "riskTotalPct") if prev else None
    change = max((abs(candidate[k] - prev_base[k]) for k in candidate), default=ZERO) if prev_base else None
    if alerts:
        status = "ALERT"
    elif prev_index is not None and now - prev_index < policy.decide_every:
        status = "NOT_DUE"
    elif prev_base is None:
        status = "INITIAL"
    else:
        status = "HOLD" if change < policy.hold else "CHANGE"
    if status in ("INITIAL", "CHANGE"):
        adopted, adopted_risk, adopted_month = candidate, risk_total, now
    elif status == "HOLD":
        adopted, adopted_risk, adopted_month = prev_base, prev_risk, now
    elif prev_base is not None:
        adopted, adopted_risk, adopted_month = prev_base, prev_risk, prev_index
    else:
        adopted, adopted_risk, adopted_month = policy.neutral, policy.risk_target, now
    # 다음 결정이 쓸 신호: 이번에 채택했으면 이번 신호, 아니면 지난 신호를 그대로 둔다.
    kept = ({r["indicator"]: {"signal": r["signal"], "missingDecisions": r["missingDecisions"]} for r in signal_rows}
            if status in ("INITIAL", "CHANGE", "HOLD") else previous_signals)
    messages = [note] if note else []
    messages.append({
        "INITIAL": "첫 결정: 후보를 기본 비중으로 채택",
        "CHANGE": f"묶음 최대 변화 {change}%p ≥ 유지 임계 {policy.hold}%p: 새 기본 비중 채택",
        "HOLD": f"묶음 최대 변화 {change}%p < 유지 임계 {policy.hold}%p: 기존 기본 비중 유지",
        "NOT_DUE": f"결정 주기 {policy.decide_every}개월 전: 기존 기본 비중 유지(지표는 누적만)",
        "ALERT": "검증된 체제 변화 경보: 후보는 보여 주기만 하고 채택하지 않음. 형 확인 필요",
    }[status])
    return {
        "_meta": {"kind": "base-decision", "month": month_name(adopted_month), "status": status,
                  "longTermPolicySha256": policy.long_term_sha, "policySha256": policy.sha,
                  "policyStatus": policy.label, "evaluatedMonth": month},
        "basePct": adopted, "riskTotalPct": adopted_risk, "candidatePct": candidate,
        "candidateRiskTotalPct": risk_total, "maxChangePct": change, "signals": kept,
        "indicatorSignals": signal_rows, "observations": audit, "alerts": alerts,
        "rejectedAlerts": rejected_alerts, "acknowledgedAlerts": acknowledged, "messages": messages,
    }



VALIDATION_META = {"status", "reportPath", "reportSha256", "note"}


def validated_inputs_sha(policy: Policy, base: dict[str, Decimal]) -> str:
    """검증 결과를 바꾸는 입력 전부: 규칙·상한·지표 정의·검증 매개변수(비용 포함)·묶음 구조·기울이기 전 기본 비중."""
    short = mapping(policy.raw["shortTermTilt"], "shortTermTilt")
    return sha256({"rules": short.get("rules", []), "maxTiltPct": short["maxTiltPct"],
                   "indicators": policy.raw.get("indicators", []),
                   "validation": {k: v for k, v in policy.validation.items() if k not in VALIDATION_META},
                   "sleeves": [{"id": s.id, "risk": s.risk, "exempt": s.exempt} for s in policy.sleeves],
                   "basePct": {k: base[k] for k in sorted(base)}})


def code_sha() -> str:
    here = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in ("policy_alloc.py", "tilt_validation.py"):
        digest.update((here / name).read_bytes())
    return digest.hexdigest()


def short_signal(rule: ShortRule, values: list[Decimal | None]) -> tuple[Decimal, str]:
    """values는 결정 시점까지(마지막이 가장 최근) 매달 값. 필요한 칸이 하나라도 비면 결측(0)."""
    need = rule.window + 1 if rule.kind == "rate_direction" else rule.window
    recent = values[-need:]
    if len(recent) < need or any(v is None for v in recent):
        return ZERO, "결측: 효과 0"
    last = recent[-1]
    if rule.kind == "valuation_extreme":
        if rule.upper is None or rule.lower is None:
            return ZERO, "규칙 미정(문턱 없음): 효과 0"
        return (ONE if last >= rule.upper else -ONE if last <= rule.lower else ZERO), "반영"
    if rule.kind == "rate_direction":
        diff = last - recent[0]
    else:
        diff = last - sum(recent, ZERO) / len(recent)
    return (ONE if diff > 0 else -ONE if diff < 0 else ZERO), "반영"


def short_tilts(policy: Policy, base: dict[str, Decimal], signals: dict[str, Decimal]) -> dict[str, Decimal]:
    raw = {s.id: ZERO for s in policy.risky}
    for rule in policy.short_rules:
        for sid, coef in rule.sleeves:
            raw[sid] += coef * signals.get(rule.id, ZERO)
    return apply_tilt({s.id: base[s.id] for s in policy.risky}, raw, policy.short_cap)


def validation_gate(policy: Policy, base: dict[str, Decimal]) -> None:
    """켜려면: status=passed, 보고서 파일 sha256 일치, 보고서 PASS, 검증 입력(기본 비중 포함)·코드 해시가 지금 것과 같음."""
    v = policy.validation
    problems = []
    if v.get("status") != "passed":
        problems.append(f"validation.status={v.get('status')!r}")
    path = policy.base_dir / str(v.get("reportPath", ""))
    if not v.get("reportPath") or not path.is_file():
        problems.append("검증 보고서 파일 없음")
    else:
        if hashlib.sha256(path.read_bytes()).hexdigest() != v.get("reportSha256"):
            problems.append("보고서 sha256 불일치")
        report = mapping(dc.load_json(path), "검증 보고서")
        if report.get("verdict") != "PASS":
            problems.append(f"보고서 verdict={report.get('verdict')!r}")
        if report.get("validatedInputsSha256") != validated_inputs_sha(policy, base):
            problems.append("검증한 설정(규칙·지표·검증 매개변수·기본 비중)과 지금 설정이 다름: 지금 설정으로 다시 검증")
        if report.get("codeSha256") != code_sha():
            problems.append("검증한 계산 코드와 지금 코드가 다름")
    if problems:
        raise InputError("단기 기울이기는 검증 통과 전에는 켤 수 없음: " + "; ".join(problems))



def snapshot(funds_dir: Path) -> dict:
    """데이터 기준일만 기록한다(수익률 같은 다른 필드 변화는 출력에 영향이 없어야 한다)."""
    result = {}
    for name in ("fund_data.json", "tdf_data.json", "deposit_rates.json", "fund_classification.json"):
        path = funds_dir / name
        data = dc.load_json(path) if path.exists() else None
        meta = data.get("_meta") if isinstance(data, dict) else None
        result[name] = meta.get("version") if isinstance(meta, dict) else None
    return result


def allocate(policy: Policy, catalog: dc.Catalog, config: dict, decision: object = None,
             log: dict[int, dict] | None = None, month: str | None = None) -> dict:
    messages = [f"{policy.label}: 형이 승인하기 전에는 실제 운용에 쓰지 않는다"] if policy.status != "approved" else []
    if decision is None:
        base, risk_total, base_source = policy.neutral, policy.risk_target, "정책 neutral(장기 결정 없음)"
    else:
        prev, note = load_decision(decision, policy)
        if prev is None:
            raise InputError(note or "장기 결정 파일 오류")
        base = {k: signed(v, k) for k, v in prev["basePct"].items()}
        risk_total = signed(prev["riskTotalPct"], "riskTotalPct")
        base_source = f"장기 결정 {prev['_meta']['month']} ({prev['_meta']['status']})"
    short_state: dict = {"enabled": policy.short_enabled, "validationStatus": policy.validation.get("status")}
    tilts = {s.id: ZERO for s in policy.risky}
    if policy.short_enabled:
        validation_gate(policy, base)
        if log is None or month is None:
            raise InputError("단기 기울이기가 켜져 있으면 --log와 --month 필요")
        now = month_index(month)
        series, _ = verified_series(policy, log, now)
        signals, signal_rows = {}, []
        for rule in policy.short_rules:
            values = [series.get(rule.indicator, {}).get(i) for i in range(now - rule.window, now + 1)]
            signal, state = short_signal(rule, values)
            signals[rule.id] = signal
            signal_rows.append({"rule": rule.id, "signal": signal, "state": state})
        tilts = short_tilts(policy, base, signals)
        short_state.update({"state": "켜짐(검증 통과)", "signals": signal_rows})
    else:
        short_state["state"] = "꺼짐(검증 대기)" if policy.validation.get("status") != "passed" else "꺼짐(형 결정)"
    final = {sid: base[sid] + tilts.get(sid, ZERO) for sid in base}

    limit = dc.number(config["riskLimitPct"], "riskLimitPct")
    risk_int = int(risk_total.quantize(ONE, rounding=ROUND_HALF_EVEN))
    if risk_int > limit:
        raise InputError("위험 총합이 한도를 넘음")
    exempt_int = int(sum((s.neutral for s in policy.exempt), ZERO))
    sleeve_int: dict[str, int] = {}
    for group, units in ((policy.risky, risk_int), (policy.exempt, exempt_int),
                         (policy.safe, 100 - risk_int - exempt_int)):
        amounts = {s.id: final[s.id] for s in group if final[s.id] > 0}
        if units and not amounts:
            raise InputError("정수화할 묶음 비중이 없음")
        if units:
            sleeve_int.update(dc.largest_remainder(amounts, units))
    values: dc.Positions = {}
    allocation, sleeve_rows = [], []
    for s in policy.sleeves:
        for ref in s.funds:
            fund = catalog.resolve(ref.row)
            if fund.counted != s.risk:
                raise InputError(f"{fund.name}: 70% 산입 여부({fund.counted})가 묶음 {s.id}의 risk({s.risk})와 다름")
            if fund.qualified != s.exempt:
                raise InputError(f"{fund.name}: 적격TDF는 면제 묶음(exempt)에만 넣을 수 있음(안전자산 아님)" if fund.qualified
                                 else f"{fund.name}: 면제 묶음 {s.id}에는 적격TDF만 넣을 수 있음")
        units = sleeve_int.get(s.id, 0)
        split = dc.largest_remainder({r.key: r.share for r in s.funds}, units) if units else {}
        for ref in s.funds:
            weight = split.get(ref.key, 0)
            if weight:
                fund = catalog.resolve(ref.row)
                values[fund] = values.get(fund, ZERO) + Decimal(weight)
                allocation.append({**dc.ref(fund), "name": fund.name, "weight": str(weight), "sleeve": s.id})
        sleeve_rows.append({"id": s.id, "label": s.label, "risk": s.risk, "exempt": s.exempt, "neutralPct": s.neutral,
                            "basePct": base[s.id], "shortTiltPct": tilts.get(s.id, ZERO),
                            "finalPct": final[s.id], "integerPct": units})
    result = dc.check(values, config)
    verdict = result["verdict"]
    if verdict in ("FAIL", "ERROR"):
        verdict = "NO_SOLUTION"
        messages.append("해 없음: dc_limits 판정 " + result["verdict"] + " (" + "; ".join(result["messages"])
                        + "). 정책의 묶음 펀드 나누기·비중을 고쳐야 함. 재시도·자동 조정하지 않음")
    elif Decimal(result["nonExemptRiskWeight"]) != risk_int:
        raise InputError("묶음 위험 총합과 dc_limits 비면제 위험 비중이 다름")
    return {"_meta": {"kind": "target", "policySha256": policy.sha, "policyStatus": policy.label},
            "verdict": verdict, "status": policy.label, "baseSource": base_source,
            "riskTotalPct": risk_int, "shortTermTilt": short_state, "sleeves": sleeve_rows,
            "allocation": allocation, "check": result, "messages": messages}



def matches(match: dict, fund: dc.Fund) -> bool:
    if not match:
        return False
    for key, wanted in match.items():
        if key == "region" and fund.region not in wanted:
            return False
        if key == "assetClass" and fund.asset_class not in wanted:
            return False
        if key == "themes" and not set(fund.themes) & set(wanted):
            return False
        if key == "principalGuaranteed" and fund.principal is not wanted:
            return False
        if key == "tdfQualified" and fund.qualified is not wanted:
            return False
        if key == "riskStatus" and fund.status not in wanted:
            return False
    return True


def sleeve_of(policy: Policy, fund: dc.Fund) -> str:
    """명시한 펀드 목록 먼저, 다음 정책 순서대로 match(70% 산입 여부도 같아야 함), 아니면 정책 밖."""
    key = ("principal:" + fund.name) if fund.principal else ("code:" + str(fund.code))
    for s in policy.sleeves:
        if any(r.key == key for r in s.funds):
            return s.id
    for s in policy.sleeves:
        if fund.counted == s.risk and fund.qualified == s.exempt and matches(s.match, fund):
            return s.id
    return OUTSIDE


def load_rows(path: Path, kinds: set[str], label: str) -> list[dict]:
    """목록 JSON 또는 상태 파일({_meta.kind, positions|allocation}). kind가 다르면 거부(제안을 보유로 쓰는 혼동 방지)."""
    data = dc.load_json(path)
    if isinstance(data, list):
        return data
    data = mapping(data, label)
    kind = mapping(data.get("_meta", {}), f"{label}._meta").get("kind")
    if kind not in kinds:
        raise InputError(f"{label}: _meta.kind={kind!r}는 쓸 수 없음(허용: {', '.join(sorted(kinds))})")
    if data.get("verdict") not in (None, "PASS", "PASS_PENDING_CONFIRMATION"):
        raise InputError(f"{label}: verdict={data.get('verdict')}인 배분은 목표로 쓸 수 없음")
    return rows(data.get("allocation", data.get("positions")), label)


def rebalance(policy: Policy, target_rows: list[dict], holding_rows: list[dict], catalog: dc.Catalog,
              config: dict, contributions: object = None) -> dict:
    target = dc.positions(target_rows, catalog, "weight")
    holdings = dc.positions(holding_rows, catalog, "evalAmount")
    target_check = dc.check(target, config)
    if dc.failed(target_check):
        raise InputError("목표 배분이 dc_limits를 통과하지 못함: " + "; ".join(target_check["messages"]))
    for fund, weight in target.items():
        if weight > 0 and sleeve_of(policy, fund) == OUTSIDE:
            raise InputError(f"목표 펀드가 정책 묶음에 없음: {fund.name}")
    total = sum(holdings.values(), ZERO)
    if total <= 0:
        raise InputError("총평가금액이 0")
    current: dict[str, Decimal] = {}
    wanted: dict[str, Decimal] = {}
    members: dict[str, list[str]] = {}
    for fund, amount in holdings.items():
        sid = sleeve_of(policy, fund)
        current[sid] = current.get(sid, ZERO) + amount * HUNDRED / total
        members.setdefault(sid, []).append(fund.name)
    for fund, weight in target.items():
        sid = sleeve_of(policy, fund)
        wanted[sid] = wanted.get(sid, ZERO) + weight
    ids = [s.id for s in policy.sleeves] + ([OUTSIDE] if OUTSIDE in current or OUTSIDE in wanted else [])
    labels = {s.id: s.label for s in policy.sleeves} | {OUTSIDE: "정책 밖"}
    bands, triggers = [], []
    for sid in ids:
        drift = current.get(sid, ZERO) - wanted.get(sid, ZERO)
        out = abs(drift) > policy.band_sleeve
        bands.append({"id": sid, "label": labels[sid], "currentPct": current.get(sid, ZERO),
                      "targetPct": wanted.get(sid, ZERO), "driftPct": drift, "bandPct": policy.band_sleeve,
                      "outOfBand": out, "heldFunds": sorted(members.get(sid, []))})
        if out:
            triggers.append(f"{labels[sid]} {drift:+.2f}%p (밴드 ±{policy.band_sleeve}%p)")
    holdings_check = dc.check(holdings, config, "holdings", denominator=total)
    limit = dc.number(config["riskLimitPct"], "riskLimitPct")
    current_risk = Decimal(holdings_check["nonExemptRiskWeight"])
    target_risk = Decimal(target_check["nonExemptRiskWeight"])
    near = target_risk + policy.band_sleeve > limit
    risk_band = policy.band_near if near else policy.band_sleeve
    risk_row = {"currentPct": current_risk, "targetPct": target_risk, "driftPct": current_risk - target_risk,
                "bandPct": risk_band, "nearLimit": near, "holdingsVerdict": holdings_check["verdict"],
                "outOfBand": abs(current_risk - target_risk) > risk_band}
    if risk_row["outOfBand"]:
        triggers.append(f"비면제 위험자산 합 {current_risk - target_risk:+.2f}%p (밴드 ±{risk_band}%p"
                        + (", 70% 근처라 좁힘" if near else "") + ")")
    if holdings_check["verdict"] == "MARKET_DRIFT_OVER_LIMIT":
        triggers.append("보유가 시가 변동으로 한도 초과(위반 아님, 다음 변경 시 조정)")
    result = {"_meta": {"kind": "rebalance", "policySha256": policy.sha, "policyStatus": policy.label},
              "status": policy.label, "bands": bands, "riskTotal": risk_row, "triggers": triggers,
              "totalEvalAmount": total}
    if not triggers:
        return {**result, "decision": "HOLD", "plan": None, "messages": ["밴드 안, 바꿀 것 없음"]}
    portal = dc.portal(holdings, target, contributions, catalog, config)
    blocking = [("목표", portal["targetCheck"]), ("정확 매도 시뮬레이션", portal["postTradeCheck"])] + [
        (f"부담금 {name} {key}", column[key]) for name, column in portal["contributions"].items()
        for key in ("inputCheck", "check")]
    failures = [name for name, check in blocking if dc.failed(check)]
    safe = [v for v in ("floor", "ceil") if v not in portal["unsafeIntegerSell"]] if portal["sells"] else []
    if failures or (portal["sells"] and not safe):
        reason = "; ".join(failures) if failures else "내림·올림 정수 매도가 모두 한도 위반"
        return {**result, "decision": "NO_SAFE_PLAN", "plan": None, "portal": portal,
                "messages": [f"거래안을 내지 않음: {reason}. 목표 비중을 고쳐야 함"]}
    variant = None
    if safe:
        def error_sum(name: str) -> Decimal:
            return sum((abs(r["errorKRW"]) for r in portal["integerSellScenarios"][name]["roundingErrors"]), ZERO)
        variant = min(safe, key=lambda name: (error_sum(name), name != "floor"))
    chosen = portal["integerSellScenarios"][variant]["check"] if variant else portal["postTradeCheck"]
    plan = {"integerSellVariant": variant, "excludedVariants": portal["unsafeIntegerSell"],
            "sells": [{"name": r["name"], "sellPct": r[f"{variant}Pct"], "exactPct": r["exactPct"],
                       "sellAmount": r["sellAmount"], "errorKRW": r[f"{variant}ErrorKRW"]} for r in portal["sells"]],
            "buys": portal["buys"], "contributions": {k: v["allocation"] for k, v in portal["contributions"].items()},
            "afterTradeCheck": chosen}
    messages = [f"밴드 밖: {', '.join(triggers)}"]
    if variant:
        messages.append(f"매도는 {'내림' if variant == 'floor' else '올림'} 정수 %로 입력"
                        + (f"({'·'.join(portal['unsafeIntegerSell'])} 방식은 한도 위반이라 제외)" if portal["unsafeIntegerSell"] else ""))
    return {**result, "decision": "REBALANCE", "planVerdict": chosen["verdict"], "plan": plan,
            "portal": portal, "messages": messages}



def dump(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=dc.json_default)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    allocate_cmd = commands.add_parser("allocate", help="정책 → 기본 비중 → (검증 통과 시) 단기 기울이기 → 정수 목표")
    allocate_cmd.add_argument("--decision", type=Path, help="decide 출력(장기 기본 비중). 없으면 정책 neutral")
    allocate_cmd.add_argument("--out", type=Path, help="목표 배분 상태 파일로도 저장")
    decide_cmd = commands.add_parser("decide", help="월 누적 장기 지표로 6개월 기본 비중 결정")
    decide_cmd.add_argument("--previous", type=Path, help="지난 decide 출력")
    decide_cmd.add_argument("--out", type=Path)
    decide_cmd.add_argument("--acknowledge-alerts", metavar="OWNER_SOURCE",
                            help="형이 경보를 확인했다는 원문 링크. 지금 경보를 확인됨으로 기록하고 정상 판정")
    rebalance_cmd = commands.add_parser("rebalance", help="보유 대비 밴드 판정과 포털 정수 거래안")
    rebalance_cmd.add_argument("--target", type=Path, required=True)
    rebalance_cmd.add_argument("--holdings", type=Path, required=True)
    rebalance_cmd.add_argument("--contributions", type=Path)
    for command in (allocate_cmd, decide_cmd, rebalance_cmd):
        command.add_argument("--policy", type=Path, required=True)
        command.add_argument("--funds-dir", type=Path, default=Path("funds"))
    for command in (allocate_cmd, decide_cmd):
        command.add_argument("--log", type=Path, help="월 누적 지표 JSONL")
        command.add_argument("--month", help="결정·계산 기준 월 YYYY-MM")
    args = parser.parse_args(argv)
    code = 0
    try:
        config = mapping(dc.load_json(Path(__file__).with_name("dc_limits_config.json")), "설정")
        policy = parse_policy(dc.load_json(args.policy), config, args.policy.resolve().parent)
        inputs: dict = {"command": args.command, "policy": policy.raw, "config": config,
                        "data": snapshot(args.funds_dir)}
        if args.command == "decide":
            if args.month is None:
                raise InputError("decide에는 --month 필요")
            log = load_log(args.log)
            previous = dc.load_json(args.previous) if args.previous else None
            inputs.update(log={month_name(k): v for k, v in sorted(log.items())}, previous=previous, month=args.month,
                          acknowledge=args.acknowledge_alerts)
            result = decide(policy, log, previous, args.month, config, args.acknowledge_alerts)
        else:
            catalog = dc.Catalog(args.funds_dir)
            if args.command == "allocate":
                log = load_log(args.log) if args.log else None
                decision = dc.load_json(args.decision) if args.decision else None
                inputs.update(decision=decision, month=args.month,
                              log={month_name(k): v for k, v in sorted(log.items())} if log else None)
                result = allocate(policy, catalog, config, decision, log, args.month)
                code = 1 if result["verdict"] == "NO_SOLUTION" else 0
            else:
                target = load_rows(args.target, {"target", "proposal"}, "목표")
                holdings = load_rows(args.holdings, {"holdings"}, "보유")
                contributions = dc.load_json(args.contributions) if args.contributions else None
                inputs.update(target=target, holdings=holdings, contributions=contributions)
                result = rebalance(policy, target, holdings, catalog, config, contributions)
                code = 1 if result["decision"] == "NO_SAFE_PLAN" else 0
        result["inputSha256"] = sha256(inputs)
        if getattr(args, "out", None):
            args.out.write_text(dump(result) + "\n", encoding="utf-8")
    except InputError as exc:
        result = {"verdict": "ERROR", "messages": [str(exc)]}
        if exc.unknown:
            result["unknownFunds"] = list(exc.unknown)
        code = 2 if exc.unknown else 1
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
        result = {"verdict": "ERROR", "messages": [f"입력·데이터 오류: {type(exc).__name__}: {exc}"]}
        code = 1
    print(dump(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
