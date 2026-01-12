# Paper Style Generator Architecture Refactoring

## Context

### Original Request
현재 `honeypot/plugins/paper-style-generator/` 플러그인이 10개의 독립 Skills를 생성하는 구조에서, 9개 Agents + 1개 Skill (하이브리드 구조)로 전환하는 아키텍처 설계 문서 작성.

### Interview Summary
**Key Discussions**:
- Skills vs Agents: Skill은 메인 컨텍스트 내에서 로드되는 지침, Agent는 독립 컨텍스트에서 실행되는 자율적 작업자
- 사용 패턴: 전체 논문 자동 생성 후 개별 섹션 편집 (Full Auto → Section Edit)
- 컨텍스트 보존: Agent 간 격리된 컨텍스트 선호 (토큰 절약 + 명확한 책임)
- Single Source of Truth: Style Guide를 Skill로 구현하여 모든 Agent가 참조

**Research Findings**:
- `agents_build_manual.md`: Agent는 별도 컨텍스트에서 실행, 복잡한 다단계 작업에 적합
- `agent_skills_best_practices.md`: Skill은 점진적 공개 패턴으로 토큰 효율성 확보
- 현재 구조: orchestrator → pdf-converter → style-analyzer → skill-generator (4 Agents)

### Metis Review
**Identified Gaps** (addressed):
- Editor Agent 범위: C 선택 - Writer가 작성+수정 모두 담당 (Editor 불필요)
- Style Guide 범위: C 선택 - 완전체 (패턴 + 측정단위 + 인용 + 섹션 템플릿)
- Cascade 관리: C 선택 - Orchestrator가 전파 결정 관리 (Verify는 보고만)
- Alias 검증: A 선택 - 규칙 적용 (소문자, 하이픈, 3-20자)
- 하위호환: B 선택 - 새 구조만 문서화

---

## Work Objectives

### Core Objective
Paper Style Generator의 출력 구조를 Skills 기반에서 Agents + Skill 하이브리드 구조로 전환하여, 논문 작성 시 섹션 간 컨텍스트 격리와 일관성 검증을 동시에 달성.

### Concrete Deliverables
1. 9개 Agent 명세 문서 (역할, 입출력, 의존성)
2. Style Guide Skill 구조 명세
3. Alias 검증 규칙 정의
4. 워크플로우 다이어그램

### Definition of Done
- [x] 모든 9개 Agent의 역할과 책임이 명확히 정의됨
- [x] Style Guide Skill의 파일 구조와 내용 범위가 정의됨
- [x] Orchestrator의 전파 관리 로직이 명세됨
- [x] Writer의 작성/수정 모드 구분이 명세됨

### Must Have
- 9개 Agent 명세 (orchestrator, 7 writers, verify)
- Style Guide Skill 완전체 구조
- Alias 검증 규칙
- 워크플로우 다이어그램

### Must NOT Have (Guardrails)
- 실제 구현 코드 작성 (설계 문서만)
- 기존 `honeypot/plugins/paper-style-generator/` 파일 수정
- 마이그레이션 가이드 (Q5: B 선택)
- Editor Agent 정의 (Q1: C 선택으로 불필요)
- Verify Agent에 실행 권한 부여 (Q3: C - 보고만)

---

## Architecture Design

### 1. Output Directory Structure

```
~/.claude/skills/{alias}-paper-skills/
├── agents/                              # 9 Agents
│   ├── {alias}-paper-orchestrator.md    # 전체 논문 자동 생성 + 전파 관리
│   ├── {alias}-title-writer.md          # Title 작성 + 수정
│   ├── {alias}-abstract-writer.md       # Abstract 작성 + 수정
│   ├── {alias}-introduction-writer.md   # Introduction 작성 + 수정
│   ├── {alias}-methodology-writer.md    # Methodology 작성 + 수정
│   ├── {alias}-results-writer.md        # Results 작성 + 수정
│   ├── {alias}-discussion-writer.md     # Discussion 작성 + 수정
│   ├── {alias}-caption-writer.md        # Figure/Table Caption 작성 + 수정
│   └── {alias}-verify.md                # 일관성 검증 + 보고
│
├── skills/
│   └── {alias}-style-guide/             # Single Source of Truth
│       ├── SKILL.md                     # 메인 스타일 가이드 (진입점)
│       └── references/
│           ├── voice-tense-patterns.md
│           ├── vocabulary-patterns.md
│           ├── measurement-formats.md
│           ├── citation-style.md
│           └── section-templates/
│               ├── title-template.md
│               ├── abstract-template.md
│               ├── introduction-template.md
│               ├── methodology-template.md
│               ├── results-template.md
│               ├── discussion-template.md
│               └── caption-template.md
│
├── .claude-plugin/
│   └── marketplace.json                 # 플러그인 등록
│
└── README.md                            # 사용 가이드
```

### 2. Alias Validation Rules

| Rule | Specification | Example |
|------|---------------|---------|
| Characters | 소문자 영문 + 숫자 + 하이픈만 허용 | `hakho-lee`, `nature-methods` |
| Length | 3-20자 | `ai` (X), `my-super-long-alias-name` (X) |
| Format | 하이픈으로 시작/끝 불가, 연속 하이픈 불가 | `-hakho` (X), `hakho--lee` (X) |
| Reserved | `anthropic`, `claude`, `paper`, `style` 포함 불가 | `claude-style` (X) |

**Validation Regex**: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` (length 3-20)

---

## Agent Specifications

### 3.1 {alias}-paper-orchestrator

**Purpose**: 전체 논문 자동 생성 및 섹션 간 전파 관리

**Frontmatter**:
```yaml
---
name: {alias}-paper-orchestrator
description: "{alias} 스타일로 전체 논문을 자동 생성하고, 섹션 수정 시 관련 섹션으로 변경사항을 전파합니다. 논문 작성을 시작하거나 섹션 간 일관성을 유지해야 할 때 사용합니다."
tools: Read, Write, Edit, Glob, Grep, Task
model: opus
skills: {alias}-style-guide
---
```

**Responsibilities**:
1. **Full Auto Mode**: 순차적으로 모든 섹션 생성
   - 순서: Title → Abstract → Introduction → Methodology → Results → Discussion → Captions
   - 각 Writer Agent를 Task로 호출
   - 완료 후 Verify Agent로 최종 검증

2. **Propagation Management Mode**: 섹션 수정 후 전파 관리
   - Verify Agent 호출하여 불일치 목록 수신
   - 사용자에게 전파 대상 확인 요청
   - 승인된 섹션의 Writer Agent 순차 호출

**Input Schema**:
```yaml
mode: "full_auto" | "propagate"
paper_topic: string  # 논문 주제 (full_auto 시)
modified_section: string  # 수정된 섹션 (propagate 시)
output_dir: string  # 출력 디렉토리
```

**Output**:
- `{output_dir}/manuscript_complete.md` (전체 논문)
- `{output_dir}/sections/` (개별 섹션 파일)

**Workflow (Full Auto)**:
```
                    ┌─────────────────┐
                    │  사용자 입력     │
                    │  (주제, 연구내용)│
                    └────────┬────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│                    Orchestrator                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  1. Title Writer 호출                                 │ │
│  │  2. Abstract Writer 호출                              │ │
│  │  3. Introduction Writer 호출                          │ │
│  │  4. Methodology Writer 호출                           │ │
│  │  5. Results Writer 호출                               │ │
│  │  6. Discussion Writer 호출                            │ │
│  │  7. Caption Writer 호출                               │ │
│  │  8. Verify Agent 호출 → 불일치 보고                   │ │
│  │  9. 불일치 있으면 해당 Writer 재호출                   │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  manuscript     │
                    │  _complete.md   │
                    └─────────────────┘
```

**Workflow (Propagation)**:
```
┌─────────────────┐
│ 섹션 수정 감지   │
│ (예: Abstract)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Orchestrator: Propagation Mode         │
│  ┌───────────────────────────────────┐  │
│  │ 1. Verify Agent 호출               │  │
│  │    → 불일치 목록 수신              │  │
│  │    (예: Introduction, Discussion) │  │
│  │                                    │  │
│  │ 2. 사용자에게 확인 요청            │  │
│  │    "다음 섹션을 업데이트할까요?   │  │
│  │     - Introduction               │  │
│  │     - Discussion                 │  │
│  │    [Y/N/선택]"                    │  │
│  │                                    │  │
│  │ 3. 승인된 섹션 Writer 호출         │  │
│  │    (컨텍스트: 수정된 내용 전달)    │  │
│  │                                    │  │
│  │ 4. 재검증 (Verify Agent)          │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

### 3.2 {alias}-title-writer

**Purpose**: 논문 제목 작성 및 수정

**Frontmatter**:
```yaml
---
name: {alias}-title-writer
description: "{alias} 스타일로 논문 제목을 생성하거나 수정합니다. 제목 작성, 제목 수정, 제목 개선이 필요할 때 사용합니다."
tools: Read, Write, Edit
model: sonnet
skills: {alias}-style-guide
---
```

**Execution Modes**:

| Mode | Trigger | Input | Output |
|------|---------|-------|--------|
| **Create** | `mode: "create"` | 연구 주제, 핵심 결과 | 새 제목 |
| **Edit** | `mode: "edit"` | 기존 제목, 수정 지시 | 수정된 제목 |

**Input Schema**:
```yaml
mode: "create" | "edit"
# Create mode
research_topic: string
key_findings: string[]
# Edit mode
current_title: string
edit_instruction: string
```

**Process (Create)**:
1. Style Guide에서 `section-templates/title-template.md` 로드
2. `voice-tense-patterns.md`에서 Title 패턴 참조
3. 연구 주제와 핵심 결과를 반영한 제목 생성
4. 길이, 구조 패턴 검증

**Process (Edit)**:
1. 기존 제목 분석
2. 수정 지시 반영
3. Style Guide 준수 확인
4. 수정된 제목 반환

---

### 3.3 {alias}-abstract-writer

**Purpose**: Abstract 작성 및 수정

**Frontmatter**:
```yaml
---
name: {alias}-abstract-writer
description: "{alias} 스타일로 논문 초록(Abstract)을 생성하거나 수정합니다. 초록 작성, 초록 수정, 초록 요약이 필요할 때 사용합니다."
tools: Read, Write, Edit
model: sonnet
skills: {alias}-style-guide
---
```

**Execution Modes**:

| Mode | Trigger | Input | Output |
|------|---------|-------|--------|
| **Create** | `mode: "create"` | 전체 연구 요약 | 새 Abstract |
| **Edit** | `mode: "edit"` | 기존 Abstract, 수정 지시 | 수정된 Abstract |

**Input Schema**:
```yaml
mode: "create" | "edit"
# Create mode
research_summary:
  background: string
  methods: string
  results: string
  conclusions: string
# Edit mode
current_abstract: string
edit_instruction: string
```

**Style Guide References**:
- `section-templates/abstract-template.md`: 구조 및 길이
- `voice-tense-patterns.md`: Voice/Tense 비율
- `vocabulary-patterns.md`: 핵심 동사, 전환어

---

### 3.4 {alias}-introduction-writer

**Purpose**: Introduction 작성 및 수정

**Frontmatter**:
```yaml
---
name: {alias}-introduction-writer
description: "{alias} 스타일로 논문 서론(Introduction)을 생성하거나 수정합니다. 서론 작성, 서론 수정, 배경 설명이 필요할 때 사용합니다."
tools: Read, Write, Edit
model: sonnet
skills: {alias}-style-guide
---
```

**Input Schema**:
```yaml
mode: "create" | "edit"
# Create mode
research_context:
  field_overview: string
  existing_challenges: string
  research_gap: string
  proposed_solution: string
  paper_organization: string
# Edit mode
current_introduction: string
edit_instruction: string
```

**Style Guide References**:
- `section-templates/introduction-template.md`: 서사 흐름, 통계 인용
- `voice-tense-patterns.md`: Introduction 특화 패턴
- `vocabulary-patterns.md`: 전환어, hedging 표현

---

### 3.5 {alias}-methodology-writer

**Purpose**: Methodology/Methods 작성 및 수정

**Frontmatter**:
```yaml
---
name: {alias}-methodology-writer
description: "{alias} 스타일로 논문 방법론(Methodology/Methods)을 생성하거나 수정합니다. 방법론 작성, 실험 방법 기술이 필요할 때 사용합니다."
tools: Read, Write, Edit
model: sonnet
skills: {alias}-style-guide
---
```

**Input Schema**:
```yaml
mode: "create" | "edit"
# Create mode
methodology:
  study_design: string
  materials: string[]
  procedures: string[]
  data_analysis: string
# Edit mode
current_methodology: string
edit_instruction: string
```

**Style Guide References**:
- `section-templates/methodology-template.md`: 소제목 스타일
- `voice-tense-patterns.md`: Passive voice 비율 (Methods 특화)
- `measurement-formats.md`: 단위, 농도, 시간 표기법

---

### 3.6 {alias}-results-writer

**Purpose**: Results 작성 및 수정

**Frontmatter**:
```yaml
---
name: {alias}-results-writer
description: "{alias} 스타일로 논문 결과(Results)를 생성하거나 수정합니다. 결과 작성, 데이터 기술, Figure 참조가 필요할 때 사용합니다."
tools: Read, Write, Edit
model: sonnet
skills: {alias}-style-guide
---
```

**Input Schema**:
```yaml
mode: "create" | "edit"
# Create mode
results:
  findings: 
    - description: string
      data: string
      figure_ref: string
  statistical_analysis: string
# Edit mode
current_results: string
edit_instruction: string
```

**Style Guide References**:
- `section-templates/results-template.md`: 테마/실험 구조
- `voice-tense-patterns.md`: "We" 사용 비율 (목표: ≤30%)
- `measurement-formats.md`: 통계 표기, p-value 형식

---

### 3.7 {alias}-discussion-writer

**Purpose**: Discussion 작성 및 수정

**Frontmatter**:
```yaml
---
name: {alias}-discussion-writer
description: "{alias} 스타일로 논문 토론/결론(Discussion/Conclusions)을 생성하거나 수정합니다. 토론 작성, 결론 도출, 한계점 기술이 필요할 때 사용합니다."
tools: Read, Write, Edit
model: sonnet
skills: {alias}-style-guide
---
```

**Input Schema**:
```yaml
mode: "create" | "edit"
# Create mode
discussion:
  key_findings_interpretation: string
  comparison_with_literature: string
  limitations: string[]
  future_directions: string[]
  conclusions: string
# Edit mode
current_discussion: string
edit_instruction: string
```

**Style Guide References**:
- `section-templates/discussion-template.md`: 한계 인정, 미래 방향, 임팩트 진술
- `voice-tense-patterns.md`: Discussion 특화 패턴
- `vocabulary-patterns.md`: hedging, emphasis 표현

---

### 3.8 {alias}-caption-writer

**Purpose**: Figure/Table Caption 작성 및 수정

**Frontmatter**:
```yaml
---
name: {alias}-caption-writer
description: "{alias} 스타일로 Figure 및 Table 캡션을 생성하거나 수정합니다. 캡션 작성, 캡션 수정, 패널 레이블링이 필요할 때 사용합니다."
tools: Read, Write, Edit
model: sonnet
skills: {alias}-style-guide
---
```

**Input Schema**:
```yaml
mode: "create" | "edit"
# Create mode
figure:
  type: "figure" | "table"
  number: integer
  panels: 
    - label: string
      description: string
  main_message: string
# Edit mode
current_caption: string
edit_instruction: string
```

**Style Guide References**:
- `section-templates/caption-template.md`: 제목 포맷, 패널 레이블링
- `measurement-formats.md`: 통계 표기, 축 레이블

---

### 3.9 {alias}-verify

**Purpose**: 섹션 간 일관성 검증 및 불일치 보고 (실행 권한 없음)

**Frontmatter**:
```yaml
---
name: {alias}-verify
description: "{alias} 스타일 논문의 섹션 간 일관성을 검증하고 불일치를 보고합니다. 논문 검증, 일관성 확인이 필요할 때 사용합니다. 직접 수정하지 않고 보고만 합니다."
tools: Read, Glob, Grep
model: sonnet
skills: {alias}-style-guide
---
```

**CRITICAL: This agent REPORTS ONLY. It does NOT modify any files.**

**Verification Checklist**:

| Category | Check Items |
|----------|-------------|
| **Cross-Section Consistency** | Sample sizes match across sections |
| | Key metrics/biomarkers consistent |
| | Figure/Table references valid |
| | Terminology consistent |
| **Style Compliance** | Voice/Tense ratios within target |
| | "We" usage in Results ≤30% |
| | Citation style consistent |
| | Measurement format consistent |
| **Structural** | All required sections present |
| | Section lengths within typical range |
| | Logical flow maintained |

**Output Schema**:
```yaml
verification_result:
  status: "PASS" | "FAIL"
  inconsistencies:
    - type: "cross_section" | "style" | "structural"
      severity: "critical" | "warning" | "suggestion"
      location:
        section: string
        line: integer
      description: string
      affected_sections: string[]  # 전파 대상
      suggested_fix: string
  summary:
    total_issues: integer
    critical: integer
    warnings: integer
    suggestions: integer
```

**Propagation Detection Logic**:
```
IF Abstract 수정됨:
  → 영향받는 섹션: Introduction (배경 요약), Discussion (결론)

IF Methodology 수정됨:
  → 영향받는 섹션: Results (참조), Discussion (한계점)

IF Results 수정됨:
  → 영향받는 섹션: Abstract (핵심 결과), Discussion (해석)

IF 핵심 수치/용어 변경됨:
  → 모든 섹션에서 해당 수치/용어 사용 위치 보고
```

---

## Style Guide Skill Specification

### 4.1 SKILL.md Structure

```yaml
---
name: {alias}-style-guide
description: "{alias} 논문 작성 스타일 가이드. Voice/Tense 패턴, 어휘 패턴, 측정 단위 형식, 인용 스타일, 섹션별 템플릿을 제공합니다. 모든 {alias} Writer Agent가 참조합니다."
---
```

**SKILL.md Content (Overview)**:
```markdown
# {Alias} Paper Style Guide

## Overview
이 스킬은 {source_papers}편의 논문 분석을 통해 추출된 {alias} 스타일 가이드입니다.

## Quick Reference

### Voice/Tense Summary
| Section | Active:Passive | Past:Present |
|---------|----------------|--------------|
| Abstract | 70:30 | 60:40 |
| Introduction | 60:40 | 40:60 |
| Methods | 20:80 | 90:10 |
| Results | 70:30 | 80:20 |
| Discussion | 50:50 | 50:50 |

### High-Frequency Verbs
demonstrated, achieved, validated, revealed, exhibited...

## Detailed References

**Voice/Tense Patterns**: [references/voice-tense-patterns.md](references/voice-tense-patterns.md)
**Vocabulary Patterns**: [references/vocabulary-patterns.md](references/vocabulary-patterns.md)
**Measurement Formats**: [references/measurement-formats.md](references/measurement-formats.md)
**Citation Style**: [references/citation-style.md](references/citation-style.md)
**Section Templates**: [references/section-templates/](references/section-templates/)
```

### 4.2 Reference Files

#### voice-tense-patterns.md
```markdown
# Voice and Tense Patterns

## Section-Specific Patterns

### Abstract
- **Target Ratio**: Active 70%, Passive 30%
- **Tense**: Past (results) + Present (conclusions)
- **Examples**:
  - Active: "We developed a novel approach..."
  - Passive: "A significant improvement was observed..."

### Methods
- **Target Ratio**: Active 20%, Passive 80%
- **Tense**: Past 90%
- **Examples**:
  - "Samples were collected..."
  - "Data were analyzed using..."

[... 각 섹션별 상세 패턴 ...]
```

#### vocabulary-patterns.md
```markdown
# Vocabulary Patterns

## High-Frequency Verbs
| Category | Verbs | Usage Context |
|----------|-------|---------------|
| Achievement | demonstrated, achieved, validated | Results, Discussion |
| Discovery | revealed, identified, discovered | Results |
| Comparison | outperformed, exceeded, compared to | Results, Discussion |

## Transition Phrases
| Type | Phrases |
|------|---------|
| Introduction | Here we present, To address this challenge |
| Addition | Furthermore, Additionally, Moreover |
| Contrast | However, In contrast, Nevertheless |
| Conclusion | In summary, Taken together, Overall |

## Hedging Expressions
may, could, suggests, indicates, appears to...

[... 상세 어휘 패턴 ...]
```

#### measurement-formats.md
```markdown
# Measurement Formats

## Temperature
- Format: `XX °C` (space before degree symbol)
- Range: `XX-YY °C`

## Concentration
- Molar: `X mM`, `X μM`, `X nM`
- Percentage: `X%` (no space)
- Weight/Volume: `X mg/mL`

## Time
- Hours: `X h`
- Minutes: `X min`
- Seconds: `X s`

## Statistical
- P-value: `P < 0.05`, `P = 0.001`
- Mean ± SD: `X ± Y`
- Confidence Interval: `95% CI: X-Y`

[... 상세 측정 형식 ...]
```

#### citation-style.md
```markdown
# Citation Style

## Detected Style: [Numeric/Author-Year/Superscript]

## In-Text Citations
- Single: [1] or (Smith et al., 2024) or ^1
- Multiple: [1-3] or [1, 5, 7]
- With text: Smith et al. [1] demonstrated...

## Reference List Format
[Journal-specific format extracted from papers]

[... 상세 인용 스타일 ...]
```

#### section-templates/{section}-template.md
각 섹션별 템플릿:
```markdown
# {Section} Template

## Structure
1. [First element]
2. [Second element]
3. [Third element]

## Length
- Typical: XXX-YYY words
- Paragraphs: N-M

## Key Components
- [Component 1]: [Description]
- [Component 2]: [Description]

## Example Patterns
[Extracted patterns from analyzed papers]
```

---

## Jinja2 Template Updates

### 5.1 Templates to Modify

현재 템플릿 (`templates/` 디렉토리):
```
skill_common.md.j2      → {alias}-style-guide/SKILL.md
skill_abstract.md.j2    → agents/{alias}-abstract-writer.md
skill_introduction.md.j2 → agents/{alias}-introduction-writer.md
skill_methodology.md.j2 → agents/{alias}-methodology-writer.md
skill_results.md.j2     → agents/{alias}-results-writer.md
skill_discussion.md.j2  → agents/{alias}-discussion-writer.md
skill_caption.md.j2     → agents/{alias}-caption-writer.md
skill_title.md.j2       → agents/{alias}-title-writer.md
skill_verify.md.j2      → agents/{alias}-verify.md
skill_orchestrator.md.j2 → agents/{alias}-paper-orchestrator.md
marketplace.json.j2     → .claude-plugin/marketplace.json
```

### 5.2 New Templates Required

| Template | Output | Purpose |
|----------|--------|---------|
| `agent_orchestrator.md.j2` | `agents/{alias}-paper-orchestrator.md` | Full auto + propagation |
| `agent_writer.md.j2` | `agents/{alias}-{section}-writer.md` | Create + edit modes |
| `agent_verify.md.j2` | `agents/{alias}-verify.md` | Read-only verification |
| `skill_style_guide.md.j2` | `skills/{alias}-style-guide/SKILL.md` | Style guide entry point |
| `ref_voice_tense.md.j2` | `skills/.../voice-tense-patterns.md` | Voice/tense reference |
| `ref_vocabulary.md.j2` | `skills/.../vocabulary-patterns.md` | Vocabulary reference |
| `ref_measurement.md.j2` | `skills/.../measurement-formats.md` | Measurement reference |
| `ref_citation.md.j2` | `skills/.../citation-style.md` | Citation reference |
| `ref_section_template.md.j2` | `skills/.../section-templates/{section}.md` | Section templates |
| `marketplace_hybrid.json.j2` | `.claude-plugin/marketplace.json` | Plugin registration |

### 5.3 Template Variable Schema

```python
template_context = {
    "alias": str,  # 사용자 입력 (validated)
    "style_name": str,  # Display name
    "source_papers_count": int,
    "analysis": {
        "voice_tense": {
            "abstract": {"active_ratio": float, "past_ratio": float},
            "introduction": {...},
            "methods": {...},
            "results": {...},
            "discussion": {...}
        },
        "vocabulary": {
            "high_freq_verbs": List[str],
            "transition_phrases": Dict[str, List[str]],
            "hedging_expressions": List[str]
        },
        "measurement": {
            "temperature": str,
            "concentration": str,
            "time": str,
            "statistical": str
        },
        "citation": {
            "style": str,  # "numeric" | "author-year" | "superscript"
            "examples": List[str]
        },
        "sections": {
            "abstract": {"structure": List[str], "length": Dict},
            "introduction": {...},
            ...
        }
    }
}
```

---

## marketplace.json Structure

### 6.1 Hybrid Registration

```json
{
  "name": "{alias}-paper-skills",
  "description": "PDF 논문 분석 기반 {alias} 스타일 논문 작성 에이전트 세트",
  "version": "2.0.0",
  "category": "documentation",
  "strict": true,
  "agents": [
    "./agents/{alias}-paper-orchestrator.md",
    "./agents/{alias}-title-writer.md",
    "./agents/{alias}-abstract-writer.md",
    "./agents/{alias}-introduction-writer.md",
    "./agents/{alias}-methodology-writer.md",
    "./agents/{alias}-results-writer.md",
    "./agents/{alias}-discussion-writer.md",
    "./agents/{alias}-caption-writer.md",
    "./agents/{alias}-verify.md"
  ],
  "skills": [
    "./skills/{alias}-style-guide"
  ]
}
```

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (Jinja2 template rendering)
- **User wants tests**: Manual verification
- **QA approach**: Manual verification with checklists

### Manual Verification Procedures

**For Each Generated Agent**:
- [x] Frontmatter fields valid (name, description, tools, model, skills)
- [x] Skill reference `{alias}-style-guide` correct
- [x] Both create and edit modes documented
- [x] Input schema complete
- [x] Process steps clear

**For Style Guide Skill**:
- [x] SKILL.md under 500 lines
- [x] All references one level deep
- [x] Table of contents in long files
- [x] Progressive disclosure pattern followed

**For marketplace.json**:
- [x] All 9 agents listed
- [x] Skill directory listed
- [x] Paths use forward slashes
- [x] strict: true set

---

## TODOs

> 설계 문서 작성 작업 목록. 구현 작업은 포함하지 않음.

- [x] 1. Agent 명세 상세화

  **What to do**:
  - 각 Agent의 frontmatter 완성
  - Input/Output schema JSON 예시 추가
  - Process workflow 다이어그램 작성

  **Must NOT do**:
  - 실제 .md 파일 생성
  - 코드 작성

  **Parallelizable**: YES (각 Agent 독립)

  **References**:
  - `honeypot/resource/agents_build_manual.md` - Agent 파일 형식
  - `honeypot/plugins/paper-style-generator/agents/orchestrator.md` - 기존 구조 참조

  **Acceptance Criteria**:
  - [x] 9개 Agent 모두 frontmatter 완성
  - [x] Input schema에 모든 필드 문서화
  - [x] 각 Agent의 Style Guide 참조 경로 명시

  **Commit**: NO (설계 문서 내 작업)

---

- [x] 2. Style Guide Skill 구조 상세화

  **What to do**:
  - SKILL.md 목차 및 내용 범위 정의
  - references/ 하위 파일별 내용 범위 정의
  - 점진적 공개 패턴 적용 확인

  **Must NOT do**:
  - 실제 파일 생성
  - 분석 결과 하드코딩

  **Parallelizable**: YES (Agent 명세와 병렬)

  **References**:
  - `honeypot/resource/agent_skills_best_practices.md` - Skill 작성 모범 사례
  - `honeypot/plugins/paper-style-generator/references/analysis_schema.md` - 분석 스키마

  **Acceptance Criteria**:
  - [x] SKILL.md 구조 500줄 이하 설계
  - [x] references/ 파일 목록 및 역할 명세
  - [x] 점진적 공개 경로 문서화

  **Commit**: NO (설계 문서 내 작업)

---

- [x] 3. Jinja2 템플릿 명세 작성

  **What to do**:
  - 새 템플릿 파일 목록 확정
  - 템플릿 변수 스키마 정의
  - 기존 템플릿과의 매핑 문서화

  **Must NOT do**:
  - 실제 .j2 파일 작성
  - 기존 템플릿 수정

  **Parallelizable**: NO (Agent/Skill 명세 완료 후)

  **References**:
  - `honeypot/plugins/paper-style-generator/templates/` - 기존 템플릿
  - `honeypot/plugins/paper-style-generator/references/output_structure.md` - 출력 구조

  **Acceptance Criteria**:
  - [x] 10+ 신규 템플릿 명세 완료
  - [x] 템플릿 변수 스키마 완전 정의
  - [x] 기존→신규 템플릿 매핑 테이블 작성

  **Commit**: NO (설계 문서 내 작업)

---

- [x] 4. Workflow 다이어그램 완성

  **What to do**:
  - Full Auto 워크플로우 다이어그램 상세화
  - Propagation 워크플로우 다이어그램 상세화
  - 섹션 간 의존성 그래프 작성

  **Must NOT do**:
  - 실제 구현
  - 이미지 파일 생성 (ASCII art로 대체)

  **Parallelizable**: YES (명세 작업과 병렬)

  **References**:
  - 이 문서 내 기존 다이어그램
  - `honeypot/plugins/paper-style-generator/agents/orchestrator.md` - 기존 워크플로우

  **Acceptance Criteria**:
  - [x] Full Auto 9단계 워크플로우 완성
  - [x] Propagation 4단계 워크플로우 완성
  - [x] 섹션 의존성 그래프 완성 (어떤 섹션이 어떤 섹션에 영향)

  **Commit**: NO (설계 문서 내 작업)

---

- [x] 5. 설계 문서 최종 검토

  **What to do**:
  - 전체 문서 일관성 검토
  - Guardrails 준수 확인
  - 누락 항목 보완

  **Must NOT do**:
  - 구현 작업 시작

  **Parallelizable**: NO (모든 작업 완료 후)

  **References**:
  - 이 문서 전체
  - Metis 갭 분석 결과

  **Acceptance Criteria**:
  - [x] 모든 Must Have 항목 포함 확인
  - [x] 모든 Must NOT Have 항목 미포함 확인
  - [x] 용어 일관성 확인

  **Commit**: YES
  - Message: `docs(paper-style-generator): add architecture design for Agent+Skill hybrid structure`
  - Files: `.sisyphus/plans/paper-style-generator-architecture.md`

---

## Success Criteria

### Verification Commands
```bash
# 설계 문서 존재 확인
ls -la .sisyphus/plans/paper-style-generator-architecture.md

# 필수 섹션 존재 확인
grep -c "## Agent Specifications" .sisyphus/plans/paper-style-generator-architecture.md
grep -c "## Style Guide Skill" .sisyphus/plans/paper-style-generator-architecture.md
grep -c "## Alias Validation" .sisyphus/plans/paper-style-generator-architecture.md
```

### Final Checklist
- [x] 9개 Agent 명세 완료 (orchestrator, 7 writers, verify)
- [x] Style Guide Skill 구조 정의 완료
- [x] Alias 검증 규칙 정의 완료
- [x] Jinja2 템플릿 명세 완료
- [x] 워크플로우 다이어그램 완료
- [x] Guardrails 모두 준수
- [x] 실제 구현 코드 없음 (설계 문서만)

---

## Appendix

### A. Comparison: Current vs New Structure

| Aspect | Current (Skills) | New (Agents + Skill) |
|--------|------------------|----------------------|
| Context | 메인 컨텍스트 공유 | Agent별 격리 |
| Execution | 지침 제공 | 자율 실행 |
| Consistency | 수동 확인 | Verify Agent 자동 검증 |
| Propagation | 없음 | Orchestrator 관리 |
| Token Usage | 모든 Skill 로드 시 누적 | Agent별 필요 시 로드 |
| Edit Mode | 불명확 | 명시적 create/edit 모드 |

### B. Section Dependency Graph

```
                    Title
                      │
                      ▼
                   Abstract ◄──────────────────┐
                      │                        │
                      ▼                        │
                Introduction ◄─────────┐       │
                      │                │       │
                      ▼                │       │
                 Methodology           │       │
                      │                │       │
                      ▼                │       │
                   Results ────────────┴───────┘
                      │
                      ▼
                  Discussion
                      │
                      ▼
                   Captions
```

**Legend**:
- `│` : 순차 의존성 (위 섹션 완료 후 작성)
- `◄──` : 역참조 (아래 섹션 변경 시 위 섹션 영향)

### C. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 템플릿 복잡도 증가 | High | Medium | 템플릿 모듈화, 공통 매크로 추출 |
| Agent 간 컨텍스트 전달 오류 | Medium | High | 명확한 Input/Output 스키마 정의 |
| Style Guide 토큰 초과 | Low | Medium | 점진적 공개 패턴 적용 |
| Propagation 무한 루프 | Low | High | 최대 전파 깊이 제한 (2단계) |

---

*Document Version: 1.0.0*
*Created: 2026-01-12*
*Author: Prometheus (Planning Consultant)*
