# 정책 파일 → 코드 배분 (새 경로) 설계와 사용법

형 말(2026-11-18 21:44 KST): "장기 거시 6개월마다 하는건어때? 3개월은 너무 짧나? 3개월을 누적해가면 좋을거같은데, 아니면 1개월? 2번도 좋네. 3번도 좋아 4번도 좋아. 그렇게 해봐. 검토 꼼꼼히 하고!"

형이 승인한 네 가지(리드 제안): 1) 기본 비중 = 장기 거시 정책, 형 승인 2) 단기는 정해 둔 지표 신호로 묶음당 ±5%p 안에서만 3) 안 기울인 것보다 표본 밖 성과가 나쁘지 않을 때만 켬 4) 비중은 코드, AI는 수집·설명. 주기: 장기 지표는 매달 수집·누적, 기본 비중 결정은 6개월마다(누적 평균), 묶음당 변화 2%p 미만이면 유지, 사이에 체제 변화(금리 체계·규제)가 있으면 즉시 경보.

기존 경로(`/portfolio-analyze`: 거시 에이전트 → fund-portfolio LLM 배분 → dc_limits 검사)는 **그대로 둔다**. 새 경로는 옆에 있고, 형이 두 결과를 나란히 비교해 승인한 뒤에만 기본으로 바꾼다(reviews/sema-arch-review.md M4·M5).

## 1. 흐름

```
형 정책 파일(neutral 묶음 비중·밴드·주기·규칙, 형 승인)          보유 상태(confidentialData, _meta.kind=holdings)
        │                                                              │
매달: LLM이 지표를 모아 macro-log.jsonl에 한 줄 추가(출처·원문·기준일) │
        │                                                              │
policy_alloc.py decide  ── 6개월마다 누적 평균 → 장기 기본 비중(코드)    │
        │                                                              │
policy_alloc.py allocate ── (검증 통과 시) 단기 기울이기 → 묶음·펀드 정수 % → dc_limits.check
        │                                                              │
policy_alloc.py rebalance ── 묶음 밴드 판정 → 안이면 "바꿀 것 없음" / 밖이면 dc_limits.portal 정수 거래안
        │
LLM: 결과 설명만(숫자는 JSON에서 렌더)
```

스크립트: `.claude/plugins/investments-portfolio/skills/dc-pension-rules/scripts/`

```bash
S=.claude/plugins/investments-portfolio/skills/dc-pension-rules/scripts
python3 $S/policy_alloc.py decide   --policy <정책.json> --log <macro-log.jsonl> --month 2026-11 [--previous <지난 결정.json>] --out <결정.json>
python3 $S/policy_alloc.py allocate --policy <정책.json> [--decision <결정.json>] [--log ... --month ...] --out <목표.json>
python3 $S/policy_alloc.py rebalance --policy <정책.json> --target <목표.json> --holdings <보유.json> [--contributions <부담금.json>]
python3 $S/tilt_validation.py --policy <정책.json> --history <월별 원자료.json> --out <보고서.json>
```

모든 출력은 정렬된 JSON이고 `inputSha256`(입력 해시)를 단다. 같은 입력이면 같은 바이트가 나온다(`tests/test_policy_alloc.py`). 펀드 과거 수익률 필드는 읽지 않는다(수익률을 바꿔도 출력이 같다는 테스트가 있다).

## 2. 정책 파일

공개 스키마 샘플: `dc-pension-rules/policy.sample.json`. 결정 숫자가 모두 `null`이라 스크립트가 계산을 거부하고 빈 칸 목록을 낸다. 형 정책은 `confidentialData/` 안에만 둔다.

| 필드 | 뜻 | 검사 |
|---|---|---|
| `_meta.status` | `sample` / `draft-unapproved` / `approved` | approved는 `approvedBy`·`approvedAt`·`approvalSource`(형 원문 링크) 필수. 미승인 정책 출력은 모두 "진단만(정책 미승인)" |
| `riskTargetPct` | 비면제 위험자산 목표(정수) | 법정 한도(`dc_limits_config.json`, 70) 초과면 오류(재시도·자동 조정 없음) |
| `sleeves[]` | 묶음: `id`, `label`, `risk`, `exempt`(선택, 기본 false), `neutralPct`, `match`, `funds[{fundCode 또는 kind+name, share}]` | 위험 묶음 neutral 합 = riskTargetPct, 전체 100. 한 펀드는 한 묶음에만. 펀드의 70% 산입 여부가 묶음 `risk`와 다르면 오류. `share`는 묶음 안 상대 비율. `exempt: true`는 적격TDF 면제 묶음(`risk: false` 필수, 적격TDF만 넣을 수 있고 적격TDF는 면제 묶음에만, neutral 합은 정수): 위험 이동·기울이기에서 빠지고 neutral에 고정 |
| `match` | 목록에 없는 보유 펀드를 묶음에 넣는 규칙(`region`·`assetClass`·`themes`·`principalGuaranteed`·`tdfQualified`·`riskStatus`) | 정책 순서대로 첫 일치. 아무 데도 안 맞으면 "정책 밖"(목표 0) |
| `band` | `sleevePct`(묶음 밴드), `nearLimitPct`(위험 목표 + 묶음 밴드가 한도를 넘을 때 위험자산 합에 쓰는 좁은 밴드) | 0 < nearLimitPct ≤ sleevePct |
| `cadence` | `collectEveryMonths`, `decideEveryMonths`, `holdThresholdPct`, `minVerifiedMonths` | 형 승인값 1·6·2. minVerifiedMonths(창 안 검증 월수 최소)는 제안값 3 |
| `indicators[]` | 지표: `sourceKind` = `official`(발표 기관 `officialPublishers`) / `market` / `derived`(`minus: [a, b]` = a − b), `tolerance`, `maxAgeMonths`(기준일이 기록한 달보다 몇 달 전까지 받는지, 기본 1) | — |
| `alerts.officialPublishers` | 체제 변화 경보로 인정할 발표 기관 | — |
| `longTermMacro` | `maxSleeveTiltPct`, `maxRiskShiftPct`, `rules[{indicator, neutral, scale, effects{sleeves, riskTotal}}]` | 상한은 5 이하. neutral·scale이 null이면 "규칙 미정", 효과 0 |
| `shortTermTilt` | `enabled`(기본 false), `maxTiltPct`(≤5), `validation`, `rules[{id, indicator, kind, window, upper, lower, effects}]` | 위험 총합은 못 움직임 |

## 3. 장기 거시 → 기본 비중

**지표 검증(코드, `policy_alloc.verify`).** 관측마다 값·기준일(`asOf`)·출처 종류·출처 목록(`publisher`, `url`, `accessedAt`, `originalText`, 출처별 `value`·`asOf`)을 적는다.

- `official`: 정책이 정한 발표 기관 출처가 1곳 이상, 같은 기준일·같은 값·원문이 있어야 검증.
- `market`: 서로 다른 발행처 **그리고** 서로 다른 등록 도메인(포트·www·하위 도메인은 같은 곳으로 셈, 예: `ecos.bok.or.kr`와 `www.bok.or.kr:443`은 한 곳)이 2곳 이상, 같은 기준일, 값 차이가 `tolerance` 이하.
- `derived`: 직접 관측을 받지 않는다. 같은 달 두 구성 지표가 모두 검증됐을 때만 a − b로 계산한다(예: 실질금리 = 기준금리 − 소비자물가 상승률).
- 기준일(`asOf`, YYYY-MM…)이 기록한 달보다 뒤이거나 `maxAgeMonths`보다 오래되면 결측이다(옛 값을 이번 달 값으로 쓰지 않게).
- 위 조건을 못 맞추면 그 관측은 **결측**이고 비중 계산에 들어가지 않는다. 관측마다 판정 사유가 출력 `observations`에 남는다.

**월 누적 형식(`macro-log.jsonl`).** 한 달에 한 줄: `{"month":"YYYY-MM","collectedAt":...,"observations":[...],"alerts":[...]}`. 같은 달 두 줄, 같은 달 같은 지표 두 번은 오류.

**6개월 결정(`decide`).**
1. 창 = 이번 달까지 `decideEveryMonths`개월. 지표별로 창 안 검증 관측이 `minVerifiedMonths` 이상이면 평균을 낸다.
2. 신호 s = clamp((평균 − neutral) / scale, −1, 1). 규칙의 neutral·scale이 비어 있으면 0.
3. 평균이 없으면(결측) **지난 결정의 신호를 그대로 쓴다**. 자료를 못 구했다고 비중이 움직이지 않게 하기 위해서다(다른 family 반박 2). 지난 신호가 없으면 0. 결측이 이어진 결정 횟수는 `missingDecisions`로 센다.
4. 위험 묶음 기울기 = `maxSleeveTiltPct` × clamp(Σ 계수·s, −1, 1), 묶음 비중 아래로는 0까지. 그다음 위험 묶음끼리 합이 0이 되게 큰 쪽을 비례로 줄인다. 그래서 장기 기울기는 위험자산 합을 바꾸지 않고, 모든 묶음이 같은 방향이면 0이다.
5. 위험 총합 이동(`riskTotal` 계수, 예: 실질금리) = `maxRiskShiftPct` × clamp(Σ, −1, 1). 위로는 법정 한도에서 멈춘다. 안전(원리금보장) 묶음이 neutral 비율대로 흡수한다. 면제(적격TDF) 묶음은 운용사가 나이에 맞춰 조정하므로 움직이지 않는다(TDF는 안전자산이 아니다).
6. 판정: 처음이면 `INITIAL`. 지난 결정에서 `decideEveryMonths`가 안 지났으면 `NOT_DUE`(유지, 지표는 누적만). 지났으면 모든 묶음의 변화가 `holdThresholdPct` 미만일 때 `HOLD`(유지), 아니면 `CHANGE`. 지난 결정 뒤 **검증된** 체제 변화 경보(정책이 정한 발표 기관 출처)가 있으면 `ALERT`: 후보는 보여 주기만 하고 채택하지 않는다. 형이 정한다. 형이 확인하면 `decide --acknowledge-alerts <형 원문 링크>`로 다시 돌린다. 지금 경보가 `acknowledgedAlerts`에 링크와 함께 기록되고 정상 판정(NOT_DUE·HOLD·CHANGE)으로 넘어가며, 다음 결정에서도 같은 경보로 다시 막히지 않는다.
7. 장기 결정에 쓰는 정책 값(위험 목표·묶음 neutral·지표·경보·장기 규칙·주기)이 바뀌면 지난 결정을 쓰지 않고 다시 시작한다. 밴드·단기 기울이기 설정만 바뀌면 지난 결정을 그대로 쓴다(`longTermPolicySha256`).

**기울기 상한과 근거.**

| 상한 | 값 | 근거 |
|---|---|---|
| 단기 기울기 | 묶음당 ±5%p, 위험 총합 불변 | 형 결정(리드 제안 2번 승인). 코드 상수 `TILT_CAP_PCT`로 정책이 더 크게 못 잡는다 |
| 장기 묶음 기울기 | 묶음당 ±5%p, 위험 총합 불변 | 장기 결과는 대부분 정책 배분이 정한다(Brinson·Hood·Beebower 1986, reviews/sema-arch-review.md §8). 전망에 따른 타이밍의 우위는 입증되기 어렵다(연준 IFDP 855). 그래서 기울기를 묶음 밴드(±5%p)보다 크게 두지 않아 정책이 주된 결정 요인으로 남게 한다. 더 크게 바꾸려면 neutral 자체를 바꾸는 정책 결정(형)이다 |
| 위험 총합 이동 | ±5%p, 위로는 70% 한도 | 퇴직연금감독규정 제11조①의 70% 한도. 위험 목표가 70이면 위로는 못 간다 |
| 한 묶음의 neutral 대비 최대 이탈 | 장기 5 + 단기 5 = 10%p | 위 둘의 합. 묶음 비중은 0 아래로 못 간다 |
| 유지 임계 | 2%p 미만 변화는 유지 | 형 승인 주기. 작은 변화로 거래하지 않게 한다 |

## 4. 단기 기울이기 (기본 꺼짐)

- 규칙 종류: `trend`(최근 값 − 창 평균의 부호), `rate_direction`(창 길이 전 대비 변화의 부호), `credit_spread`(최근 값 − 창 평균의 부호), `valuation_extreme`(`upper` 이상 +1, `lower` 이하 −1). 신호 −1/0/1 × 계수 → 묶음 기울기, 묶음당 `maxTiltPct`(≤5) 안, 위험 묶음끼리 합 0. 창 안에 빈 달이 있으면 결측(0).
- **켜는 관문(`validation_gate`).** `enabled: true`이려면 `validation.status = "passed"`, `reportPath` 파일의 sha256 = `reportSha256`, 보고서 `verdict = PASS`, 보고서의 `validatedInputsSha256` = 지금 검증 입력(규칙·상한·지표 정의·검증 매개변수와 전환 비용·묶음 구조·**기울이기 전 기본 비중**)의 해시, 보고서의 `codeSha256` = 지금 `policy_alloc.py`+`tilt_validation.py`의 해시. 하나라도 틀리면 오류로 멈춘다(켜지 않음). 규칙의 방향, 비용, 검증 기준, 기본 비중 가운데 무엇을 바꿔도, 계산 코드를 고쳐도 다시 검증해야 한다(다른 family 반박 3, 게이트 리뷰 B1). 장기 결정이 CHANGE로 기본 비중을 바꾸면 그 결정 파일로 `tilt_validation.py --decision <결정.json>`을 다시 돌려야 켜진 상태를 유지한다(HOLD·NOT_DUE는 기본 비중이 그대로라 유지).

**검증 절차(`tilt_validation.py`).**

1. 자료(`--history`): 이어진 월 목록, 묶음별 월 총수익률 %(원화 기준 권장), 규칙이 쓰는 지표의 월 값. 지표마다 `releaseLagMonths`(그 달 값이 몇 달 뒤에 공개되는지)와 `vintage`(`pointInTime` 당시 공개본 / `revisionFree` 수정 안 되는 값: 시장 가격·정책금리 / `revised` 사후 수정본)를 적는다. `_meta.sources`에 발행처·URL·조회 시각을 적는다.
2. 워크포워드: 달 t의 신호는 t − 1 − `releaseLagMonths`까지의 값만 쓴다. 규칙 매개변수는 검증 전에 정책 파일에 고정하고 자료에 맞춰 고르지 않는다(맞춰 고르면 그 자체가 표본 안 최적화다).
3. 같은 위험자산 비중: 기울인 안과 안 기울인 안은 neutral 위에서 위험 묶음끼리만 옮긴다. 월 차이 = 기울인 안 − 안 기울인 안 − 전환 비용(회전율 × `switchCostPct`).
4. 원형 블록 부트스트랩(블록 `bootstrapBlockMonths`, `bootstrapDraws`회, 고정 `seed`)으로 평균 차이의 단측 하한(`alpha`)을 낸다.
5. 어느 규칙이든 창 안에 빈 값이 있는 달은 표본에서 뺀다(`skippedMonthsMissingData`). 자료가 없어 신호가 0인 달을 "기울여도 손해 없음"으로 세지 않기 위해서다(게이트 리뷰 B3). 문턱이 비어 있는 규칙이 있으면 `INVALID_RULES`.
6. **PASS** = 표본 밖 월수 ≥ `minOutOfSampleMonths` **그리고** 평균 차이 ≥ 0 **그리고** 하한 ≥ `nonInferiorityMarginPctPerMonth` **그리고** 최대낙폭·월 변동성이 안 기울인 안보다 크지 않음(sema-quant-research §7 단계 4). `revised` 자료를 쓰면 `INVALID_DATA`, 월수가 모자라면 `INSUFFICIENT_DATA`.
7. 보고서를 형에게 보이고, 형이 승인하면 정책 `validation`에 `status=passed`·`reportPath`·`reportSha256`을 넣고 `enabled=true`로 바꾼다.

비열등 한계(−0.1%p/월)는 sema-quant-research의 제안값이고, 형이 승인해야 하는 손실 허용폭이다. "평균 차이 ≥ 0" 조건 때문에 매달 조금씩 지는 규칙은 하한이 한계 위에 있어도 통과하지 못한다(다른 family 반박 4).

### 필요한 데이터 (지금 상태: 검증 대기)

KRX Open API 키는 2026-11-18에 들어왔다(`~/.config/dori-secrets/krx`, 지수·ETF 일별 NAV·채권지수·금시장 승인, 2026-11-21 호출 확인). 단기 규칙 검증은 아직 돌리지 않았고, 정책의 `validation.status`는 `pending`이다. 필요한 것은 아래와 같다(출처별 약관 확인은 reviews/sema-redesign-review.md "데이터 출처" 표).

| 용도 | 자료 | 조건 |
|---|---|---|
| 묶음 월 수익률 | 국내주식·미국주식·선진국(미국 제외)·신흥국·섹터 묶음을 대표하는 지수 또는 펀드 기준가 월말값, 원화 환산용 환율 | 120개월 이상, 자동 수집이 약관상 허용, 재배포 안 함(로컬 보관) |
| 추세 | KOSPI200·S&P500 등 월말 지수 | 같음, `revisionFree` |
| 금리 방향 | 한국은행 기준금리 | 공식 1차 출처, `revisionFree` |
| 신용 스프레드 | 회사채(AA-) 3년 − 국고채 3년 | 공식 통계 또는 독립 2곳 |
| 밸류에이션 | 지역별 PER·CAPE 등의 자기 역사 백분위 | 독립 2곳 이상 또는 공식 통계. 단일 발행처 지수(예: 한 대학의 CAPE)는 `market` 2곳 조건을 못 맞춰 결측이 된다 |
| 실질금리 | 기준금리(한국은행) − 소비자물가 상승률(통계청) | `derived`. 물가는 수정될 수 있어 검증 자료에서는 `pointInTime`이거나 공표 지연을 적어야 한다 |

Yahoo Finance처럼 약관이 자동 수집을 금지하는 출처는 쓰지 않는다. 시계열은 공개 저장소에 올리지 않는다.

**출처 조사 결과(2026-11-18 조회, 약관 원문 인용은 reviews/sema-redesign-review.md).**

| 지표 | 허용된 출처 | 상태 |
|---|---|---|
| 한국 기준금리 | 한국은행 통화정책 결정 공표(공식 1차) | 수집 가능(공식 사실). ECOS API 약관은 원문 미확인 |
| 소비자물가 상승률 | KOSIS OpenAPI(약관이 프로그램 이용 허용, 출처 표시) | 수집 가능 → 실질금리(`derived`) 계산 가능 |
| 미국 10년 실질금리(TIPS) | 미 재무부 Daily Treasury Interest Rate XML Feed(GET 허용, 2003년부터) | 수집 가능 |
| 지역별 밸류에이션(CAPE·PER 백분위) | 없음. MSCI·FTSE Russell은 라이선스 필요, Shiller(미국만) 자동 수집 허가 문구 미확인, KRX Open API는 PER 이력 미확인·제3자 제공 금지 | **결측 유지.** 형 결정: 라이선스 구매 / 다른 지표로 대체 / 사람이 공식 공표를 매달 확인 |
| 국내 지수 월말값 | KRX Open API(인증키, 2010년부터, 제3자 제공 금지) | 키가 들어오면 로컬 사용 가능 |
| 해외 지역 지수 총수익률 | 없음(MSCI 등 라이선스) | 단기 검증 자료가 모자람 → 검증 대기 |
| 신용 스프레드 | 미국 Baa(Moody's)는 재배포 금지, ICE HY OAS는 FRED에서 최근 3년만, 한국 회사채는 ECOS 시계열 권리 미확인 | 결측 |

## 5. 밴드와 거래안 (`rebalance`)

1. 보유(평가금액)와 목표를 묶음으로 모은다(명시한 펀드 → `match` → 정책 밖).
2. 묶음마다 |지금 − 목표| > `sleevePct`면 밴드 밖.
3. 비면제 위험자산 합: 위험 목표 + `sleevePct`가 법정 한도를 넘으면(예: 목표 70) 밴드를 `nearLimitPct`로 좁힌다. 보유가 시가 변동으로 한도를 넘었으면(`MARKET_DRIFT_OVER_LIMIT`, 위반 아님) 항상 밖이다.
4. 모두 안이면 `HOLD`, "밴드 안, 바꿀 것 없음", 거래 0.
5. 밖이면 `dc_limits.portal`로 거래안을 만들고 이렇게 판정한다. 목표·부담금 3칸 검사 가운데 하나라도 FAIL이면 `NO_SAFE_PLAN`(거래안 없음, 종료 코드 1). 정확 매도 시뮬레이션은 매도가 없을 때만 막는다. 매도가 있으면 포털에 넣는 것은 정수 매도라 정확 매도는 참고값이고, 아래 정수 방식 검사가 판정한다. 내림·올림 정수 매도 가운데 한도를 지키는 방식만 고르고, 둘 다 안전하면 반올림 오차 합이 작은 쪽(같으면 내림)을 고른다. 고른 방식의 거래 뒤 검사 결과가 `planVerdict`다.
6. 상태 파일은 `_meta.kind`로 구분한다(`proposal` 제안, `holdings` 보유, `executions` 실행, `target` allocate 출력). 제안을 보유로 넣으면 거부한다.

## 5.1 매일·매주 점검: 추정 비중 규칙 알림 (`drift_watch.py`)

형 말(2026-11-21): "세마 화면을 붙이는게 아니라 나는 네가 추천해준 포트폴리오 대로 갈거니까 그거 기준으로 하자." 화면 없이 추천안을 넣은 날의 비중에서 출발해 대리 시계열로 지금 비중을 추정하고, 위 `rebalance`와 `dc_limits`로 판정해 새로 걸린 규칙만 알린다.

1. **실행 기준(비공개, `execution-baseline.json`).** `_meta.status`가 `unset`이면 "기준 미정": 추정·알림을 하지 않는다. `set`이면 `source`(형 원문 링크)·`plan`(A/B)·`policy`(정책 파일)·`executedOn`·`positions`(그날 넣은 펀드별 정수 비중, 목표이자 출발 비중)가 필요하다. `positions`를 고정해 두므로 정책 파일을 나중에 고쳐도 과거 보유가 바뀌지 않는다(다른 family 반박·게이트 B1). 형이 리밸런싱을 넣으면 `executionsLog`(기존 `executions.json`, entries `{date, positionsAfter, source}`)에 적고, 그날 줄어든 펀드는 분할분을 같은 비율로 줄이고(원래 입금·매수일 유지) 늘어난 펀드만 그날 새 분할분을 더한다. 그래서 건드리지 않은 예금은 원래 입금일의 금리·만기를 그대로 쓴다(그날 총액은 앞 구간 추정치, 게이트 2차 N2). 납입 기록(`contributionsLog`, 한 줄 `{date, amount, allocation?, source}`)을 반영하려면 `totalEvalAmount`(실행일 총평가액)가 필요하고, 없으면 추정하지 않는다.
2. **대리 대응표(비공개, `proxy-map.json`).** 펀드마다 시계열 하나와 `proxyKind`: `index`(같은 지수·같은 환헤지, 오차 작음) / `active`(액티브이거나 기준·환헤지가 달라 오차 큼, 출력에 따로 표시)와 `errorNote`. 원리금보장은 `deposit_rates.json`의 금리로 단리 일할 추정하되, 입금일이 그 금리의 적용 기간(`appliesFrom~appliesTo` 또는 `bonusPeriod`) 안이고 만기(`termMonths`) 전일 때만 쓴다. 아니면 그 입금분의 금리를 모르므로 결측(게이트 B2: 입금 당시 고시 금리가 만기까지 간다). 시계열은 KRX Open API(`etp/etf_bydd_trd` NAV, `idx/*_dd_trd` 종가)만 쓴다. FRED는 약관이 받은 자료의 저장·캐시를 금지하고, ECOS는 이용 지침 원문을 아직 확인하지 못해 쓰지 않는다(코드가 거부). `crossChecks`는 같은 펀드를 다른 대리로 다시 계산해 차이를 보인다(예: S&P 500 UH ETF 두 개).
3. **추정.** 펀드 i의 지금 값 = 출발 금액 × (대리 점검일 값 / 대리 실행일 값) + Σ 납입 × (점검일 값 / 납입일 값). 날짜마다 그 날 이전 7일 안의 마지막 값을 쓴다. 대응표에 없는 펀드, 7일 안 값이 없거나 0 이하인 대리, 금리를 모르는 예금이 하나라도 있으면 `NO_ESTIMATE`(규칙 알림 없음, 알린 키는 그대로). 결측이 시작된 날을 `noEstimateSince`에 적고 처음 한 번 리드 창에 알린다(침묵이 ‘이상 없음’으로 읽히지 않게, 다른 family 반박). 주간 요약에도 그 날과 이유가 나온다. 금액 기준이 없으면 명목 1억 원으로 비중만 계산한다. 펀드마다 (입금·매수일, 금액) 분할분으로 계산하고 금액 0인 분할분은 만들지 않는다(보유하지 않은 예금의 금리를 요구하지 않게, 게이트 3차 N3). 펀드는 이름순으로 돌아 결측 사유 순서도 늘 같다(N4, 사유 순서는 예전 납입 흐름 순에서 펀드 이름순으로 바뀜). 실행 기준 비중 합이 100이 아니면 결측보다 먼저 오류다.
4. **규칙.** 추정 평가액을 보유로 `rebalance`에 넣는다: 묶음 밴드(`band:<묶음>:±`), 비면제 위험자산 합 밴드(70% 근처면 좁힘, `risk:±`). `dc_limits.check` 보유 모드로 70% 초과(`limit:over`, 추정치라 원인은 단정하지 않고 포털 확인 요청)와 한 펀드 40% 초과(`conc:fund:<펀드>`). 쏠림은 dc-pension-rules SKILL.md §4.2: 테마 하나 30%, Tech/AI(반도체·AI·로봇) 40%, 지역 하나 50%(global 제외), 신흥국·아시아 합계 30%(`conc:...`). gold 테마는 분류 오류(아래 한계) 때문에 빼다.
5. **알림.** 지난번 알린 키(`alert-state.json`)에 없는 키가 생기면 `SEND`, 다 아는 키면 `QUIET`, 없으면 `IN_BAND`. SEND면 새 키는 보낸 뒤 `mark-sent`가 더하므로 보내기가 실패하면 다음 번에 다시 보낸다. 해소된 키는 매번 바로 빼므로(SEND 때도) 밴드 안 복귀·방향 전환 뒤 재발은 다시 알린다(게이트 B5). 같은 펀드를 다른 대리로 본 `crossChecks`(마지막 실행 기록일부터, 추정과 같은 구간)가 어긋나면 포털 입력 %는 빼고 포털 화면 비중을 달라고 한다(`planShown=false`). Discord 2000자 한도 때문에 글은 줄 단위 1900자 안 조각(`messageParts`)으로 보내고, 모두 성공해야 상태를 남긴다. 글에는 비중·정수 매도 %·매수 비율만 있고 금액은 없다. 예금 매도가 들어 있으면 중도해지 이율을 알린다.
6. **돌리기.** `~/.geumdori/bin/sema-alert.sh`(systemd `geumdori-sema-alert.timer`, 평일 18:30 KST): `fetch`(실행일·납입일·점검일의 KRX 값만 받아 비공개 `proxy-series.json`에) → `check` → SEND면 #geumdori에 한 번 → `mark-sent`. `--dry-run`은 보낼 글만 출력, `--report`는(둘 다 상태·latest·시계열을 임시 사본에만 쓴다) 주간 경제 보고서 "포트폴리오 점검" 절이 읽는 요약. 저널에는 판정 한 줄만 남는다.
7. 대리 추정은 실제 포털 비중과 다르다(보수·배당·환헤지·기준가 시차, 액티브 펀드). 6개월 점검 때 포털 화면으로 실행 기준을 다시 맞춘다(새 `executedOn`·`positions`).

## 6. 보고서 권고 → 반영 대응표

| 보고서 권고 | 반영 | 이유 |
|---|---|---|
| arch M0 상태 셋 분리(제안·실제 보유·실행) | 반영 | `_meta.kind` 상태 파일과 kind 검사. 형 폴더에 세 파일 |
| arch M1 검산·리밸런싱을 코드로(밴드 → 정수 거래안) | 반영 | `rebalance` |
| arch M2 정책 파일 스키마(공개 샘플) + 형 정책(비공개) | 반영 | `policy.sample.json`(숫자 없음), 형 초안은 confidentialData `policy-draft.json`(미승인) |
| arch M3 정책 → 묶음 → 펀드 → 정수 %, dc_limits 제약 | 부분 | 묶음 → 펀드는 정책에 적은 펀드·비율로 한다. fund_score로 역할별 후보를 자동으로 고르는 부분은 만들지 않았다. 펀드 선택은 형 승인 항목으로 두는 편이 이번 범위(형 돈에 적용 안 함)에 맞다. 40% 초과는 자동 분할 대신 `NO_SOLUTION`으로 멈춘다 |
| arch M4 그림자 실행·나란히 비교 | 반영 | 형 폴더 `11-redesign-compare.md`. 기존 경로 파일은 바꾸지 않았다 |
| arch M5 거시를 비중에서 뗀다 | 형이 바꿈 | 형 결정(2026-11-18): 장기 거시는 기본 비중 입력, 단기는 검증된 규칙 기울이기. 이 문서가 그 구현이다 |
| arch M6 설명 층(위험 기여도) | 안 함 | 이번 범위 밖 |
| arch Q1 결정성 | 반영 | 해시 테스트 |
| arch Q2 거시 독립 | 바뀜 | 거시는 이제 입력이다. 대신 미검증 입력 = 결측, 결측은 비중을 움직이지 않음, 효과는 상한 안 |
| arch Q3 한도를 제약으로 | 반영 | 71 → 오류, 70 → PASS |
| arch Q4 밴드와 안전한 정수 거래안 | 반영(정의 바뀜, 아래) | — |
| arch Q5 렌더 변조 검사 | 부분 | 형 폴더 `render_11.py --check`(다시 렌더해 한 글자라도 다르면 FAIL). 공용 렌더·검산 일반화는 후속 |
| arch Q8 과거 성적 무관 | 반영 | 수익률을 바꿔도 출력 바이트가 같다는 테스트 |
| arch Q9 40% 분할·해 없음 | 부분 | 해 없음(`NO_SOLUTION`, 종료 1)은 반영. 자동 분할은 안 함(펀드 선택은 정책 결정) |
| arch Q10 기준선 고정 | 반영 | 기존 경로 파일 해시를 1fc55b2와 대조(리뷰 문서) |
| quant §7 단계 4 비교 기준(같은 위험자산 비중, 워크포워드, 블록 부트스트랩, 비열등) | 반영 | `tilt_validation.py`. 낙폭·변동성 조건과 "평균 ≥ 0"을 더했다 |
| quant §7 단계 5 밴드 ±5%p, 70% 근처 좁게, 주문 시점과 시장 변동 구분 | 반영 | `rebalance`(MARKET_DRIFT_OVER_LIMIT은 위반이 아니라 밴드 밖 사유) |
| quant §7 단계 1~3·6~8 | 안 함 | 시계열·라이선스 문제가 먼저다(단계 0) |

### 결과 본 뒤 바꾼 정의

- 단기 검증의 "표본 밖 월수" 옛 정의(4f2d57d): 준비 기간 뒤 모든 달을 셈(자료가 빈 규칙은 신호 0). 게이트 리뷰가 지표가 전부 비어도 129개월 PASS가 나는 것을 보인 뒤 바꿨다. 새 정의: 모든 규칙의 자료가 있는 달만 셈. 옛 정의로는 그 합성 자료가 PASS, 새 정의로는 INSUFFICIENT_DATA(0개월).
- arch Q4의 옛 정의: "밴드 밖: 종료 코드 0, `verdict`=PASS, `unsafeIntegerSell`가 빈 목록". 저장된 fixture 출력(`postTradeCheck` PASS, `unsafeIntegerSell=["floor"]`, ceil PASS, 전체 FAIL)을 다른 family 반박이 지적한 뒤 바꿨다. 새 정의: 고른 정수 매도 방식의 거래 뒤 검사가 통과하고, 목표·정확 시뮬레이션·부담금 검사가 모두 통과하면 `REBALANCE`. 옛 정의로는 같은 fixture가 "거래안 없음"이었고, 새 정의로는 "올림 정수로 입력, 내림은 제외"다.

- `rebalance`의 "정확 매도 시뮬레이션" 옛 정의(870c38d~5d067a5): FAIL이면 항상 `NO_SAFE_PLAN`. sema-rule-alerts에서 목표 70%(안 A처럼) 보유가 매수 비율 정수화 때문에 정확 매도 70.01%로 FAIL인데 실제 입력할 올림 정수 매도는 69.97% PASS인 경우를 본 뒤 바꿨다. 새 정의: 매도가 있으면 정확 매도는 참고값, 판정은 정수 방식 검사. 옛 정의로는 그 보유(테스트 `test_rebalance_exact_sell_over_limit_still_gives_the_safe_integer_plan`)가 "거래안 없음", 새 정의로는 "올림 정수로 입력, 거래 뒤 PASS"다.

## 7. 한계

- 형 정책 초안은 미승인이다. 형 돈에는 아무것도 적용하지 않았다.
- 장기 지표는 아직 하나도 검증되지 않았다(첫 달 수집 전). 그래서 형 폴더의 새 경로 비중은 정책 neutral(= 11-17 제안의 묶음 비중)과 같다.
- 단기 규칙은 검증 대기다(자료 없음).
- 펀드를 역할별 점수로 자동 선택하는 기능은 없다.
- `classify_funds.py`의 테마 정규식 `골드|금`이 '퇴직연금'의 '금'에도 걸려, 많은 펀드에 `gold` 테마가 붙는다. 형 정책 초안은 `match`에 gold를 쓰지 않는다(후속 수리 대상).
