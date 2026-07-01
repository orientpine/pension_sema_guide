---
name: file-save-protocol-tax
description: "세금 상담 결과 파일 저장 프로토콜. confidentialData/tax/ 경로 강제, JSON+MD 동시 저장 필수, 저장 없이 완료 응답 금지."
tools: Write
---

# 파일 저장 프로토콜 (세금 상담용)

## Overview

이 스킬은 세금 상담 에이전트가 결과를 파일로 저장할 때 따라야 하는 규칙을 정의합니다.

**핵심 목표**: 세금 상담 결과의 영속성 보장 및 환각 방지

---

## 1. 핵심 규칙 (CRITICAL)

> **환각 방지의 핵심**: 분석 결과를 **반드시 파일로 저장**해야 합니다.
> 프롬프트로만 반환하면 데이터 손실 및 환각 발생 위험이 있습니다.

### 필수 사항 (MUST)

- coordinator가 제공하는 `output_path`만 사용 (임의 경로 금지)
- JSON과 MD **동시 저장** — 둘 중 하나라도 누락 시 FAIL
- 저장 성공 확인 후에만 완료 보고
- 저장 없이 "완료" 응답 **절대 금지**
- 모든 산출물은 `confidentialData/tax/` 하위에만 저장

### 금지 사항 (NEVER)

- 파일 저장 없이 분석 결과 "완료" 응답
- 저장 실패를 무시하고 진행
- `output_path` 무시하고 임의 경로 사용
- `confidentialData/tax/` 밖에 개인정보 저장
- MD에 JSON에 없는 새 수치 또는 새 출처 추가

---

## 2. 저장 경로 컨벤션

coordinator(tax-consult)가 제공하는 `output_path`를 사용합니다:

```
confidentialData/tax/{YYYY-MM-DD}-{slug}-{6자리}/
├── 00-educator.md          # tax-knowledge-educator 출력
├── 01-strategy.json        # tax-strategy-planner 출력
├── 01-strategy.md          # tax-strategy-planner 출력
├── 02-calc-verify.json     # tax-calc-verifier 출력
├── 02-calc-verify.md       # tax-calc-verifier 출력
├── 03-critic.json          # tax-critic 출력
├── 03-critic.md            # tax-critic 출력
└── 04-summary.md           # tax-consult 최종 요약
```

### 에이전트별 출력 파일

| 에이전트 | 출력 파일 | JSON+MD |
|----------|-----------|:-------:|
| tax-knowledge-educator | `00-educator.md` | MD만 |
| tax-strategy-planner | `01-strategy.json`, `01-strategy.md` | O |
| tax-calc-verifier | `02-calc-verify.json`, `02-calc-verify.md` | O |
| tax-critic | `03-critic.json`, `03-critic.md` | O |
| tax-consult (coordinator) | `04-summary.md` | MD만 |

---

## 3. 저장 프로세스

### Step-by-Step

```
Step 1: coordinator로부터 output_path 수신 확인
        └─ output_path 미전달 → FAIL 반환 (경로 확인 요청)

Step 2: 분석 완료 후 JSON 객체 생성

Step 3: Write 도구로 JSON 저장
        Write(
          file_path="{output_path}/{filename}.json",
          content=JSON.stringify(analysis_result, null, 2)
        )

Step 4: Write 도구로 MD 저장
        Write(
          file_path="{output_path}/{filename}.md",
          content="# {제목}\n\n{JSON 내용 요약}"
        )

Step 5: 양쪽 저장 성공 확인
        └─ 성공: output_path 포함한 완료 응답 반환
        └─ 실패: FAIL 응답 반환 (환각 데이터 생성 금지)
```

### MD 작성 규칙

- JSON 내용을 **요약/정리만** 수행
- 새 수치, 새 출처, 새 해석 추가 **금지**
- 사람이 읽기 쉬운 형태로 구조화

---

## 4. FAIL 응답 형식

저장이 실패하거나 `output_path`가 없으면 **절대 "저장됨"으로 응답하지 않습니다**:

```json
{
  "status": "FAIL",
  "error": "FILE_SAVE_FAILED",
  "detail": "{filename} 저장 실패",
  "attempted_path": "{output_path}/{filename}",
  "action": "재시도 또는 output_path 확인 필요"
}
```

### output_path 미전달 시

```json
{
  "status": "FAIL",
  "error": "OUTPUT_PATH_MISSING",
  "detail": "coordinator로부터 output_path가 전달되지 않음",
  "attempted_path": null,
  "action": "tax-consult coordinator에 output_path 요청"
}
```

### 실패 유형별 대응

| 실패 유형 | 코드 | 대응 |
|:----------|:-----|:-----|
| 경로 없음 | `PATH_NOT_FOUND` | coordinator에 경로 확인 요청 |
| output_path 미전달 | `OUTPUT_PATH_MISSING` | coordinator에 output_path 요청 |
| 권한 오류 | `PERMISSION_DENIED` | 경로 권한 확인 |
| 디스크 공간 | `DISK_FULL` | 공간 확보 후 재시도 |
| 알 수 없음 | `UNKNOWN_ERROR` | 에러 메시지 포함하여 보고 |

---

## 5. 절대 금지

```
❌ 파일 저장 없이 "완료" 응답
❌ output_path 무시하고 임의 경로 사용
❌ confidentialData/tax/ 밖에 개인정보 저장
❌ MD에 새 수치 또는 새 출처 추가 (JSON 내용 요약만)
❌ JSON 저장 없이 MD만 작성 (또는 반대)
❌ 저장 실패를 무시하고 다음 단계 진행
❌ 저장 없이 완료 응답 후 "나중에 저장하겠다" 약속
```

---

## 6. 저장 확인 체크리스트 (MANDATORY)

### 저장 전 확인
- [ ] `output_path`가 coordinator로부터 전달되었는가?
- [ ] 저장할 데이터가 완전한가 (모든 필수 필드 포함)?
- [ ] JSON 형식이 올바른가?
- [ ] 저장 경로가 `confidentialData/tax/` 하위인가?

### 저장 후 확인
- [ ] JSON Write 도구가 에러 없이 완료되었는가?
- [ ] MD Write 도구가 에러 없이 완료되었는가?
- [ ] 저장 경로를 응답에 포함했는가?
- [ ] 저장 실패 시 FAIL 응답을 반환했는가?

---

## 7. 응답 템플릿

### 성공 시 응답

```json
{
  "status": "SUCCESS",
  "output_json": "{output_path}/{filename}.json",
  "output_md": "{output_path}/{filename}.md",
  "summary": {
    "저장된 파일": 2,
    "경로": "{output_path}"
  }
}
```

### 실패 시 응답

```json
{
  "status": "FAIL",
  "error": "FILE_SAVE_FAILED",
  "detail": "02-calc-verify.json 저장 실패",
  "attempted_path": "confidentialData/tax/2026-07-01-pension-tax-abc123/02-calc-verify.json",
  "action": "재시도 또는 output_path 확인 필요"
}
```

---

## 메타 정보

```yaml
version: "1.0"
created: "2026-07-01"
purpose: "세금 상담 결과 파일 저장 프로토콜"
based_on:
  - "investments-portfolio/skills/file-save-protocol"
  - "stock-consultation/skills/file-save-protocol-stock"
consumers:
  - tax-knowledge-educator
  - tax-strategy-planner
  - tax-calc-verifier
  - tax-critic
dependencies:
  - Write
output_path_pattern: "confidentialData/tax/{YYYY-MM-DD}-{slug}-{6자리}/"
```
