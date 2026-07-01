# PLUGIN: pension-tax-advisor

퇴직연금·연금계좌 세금 상담 멀티에이전트. 납입→운용→수령 단계별 절세 최적화, law.go.kr 출처 등급제, 3중 검증(calc-verifier→critic→devil-advocate), 미검증 파라미터 자동 보류로 정확한 절세 상담 제공.

## STRUCTURE

```
pension-tax-advisor/
├── .claude-plugin/plugin.json    # name/version 1.0.0
├── commands/tax-consult.md       # 오케스트레이터 (Task 전용 진입점)
├── agents/                       # 5 agents
└── skills/                       # 3 skills
    └── pension-tax-rules/SKILL.md # §9 계산식 스펙 포함
```

## ORCHESTRATION (tax-consult.md)

> 오케스트레이터는 **반드시 Task 도구로만** 하위 에이전트 호출. 직접 분석·계산·검증 금지.

```
0  read-time 신선도 체크 (pension_tax_params.json 90일 초과 시 tax-law-updater BLOCKING)
1  tax-knowledge-educator (BLOCKING) → 00-educator.md
2  tax-strategy-planner (BLOCKING)   → 01-strategy.md
C4 tax-calc-verifier → tax-critic (calc consume) → devil-advocate (BLOCKING 3중 게이팅)
   재시도 최대 3회, 미통과 시 "제공 보류"
3  04-summary 재검증(calc-verifier→critic 재실행) → 04-summary.md
```

## AGENTS (5)

| Agent | tools | skills |
|-------|-------|--------|
| tax-knowledge-educator | Read,Write | pension-tax-rules, file-save-protocol-tax |
| tax-strategy-planner | Read,Write | pension-tax-rules, file-save-protocol-tax, devil-advocate |
| tax-calc-verifier | Read,Bash,Write | file-save-protocol-tax |
| tax-critic | Read,Bash,Grep,Write | file-save-protocol-tax, devil-advocate |
| tax-law-updater | Read,WebSearch,WebFetch,Write | tax-law-verifier, file-save-protocol-tax |

## SKILLS (3)

| Skill | 역할 |
|-------|------|
| pension-tax-rules | 납입/운용/수령 3단계 규칙 + §9 계산식 스펙 (parameter_id 참조만) |
| tax-law-verifier | 출처 등급제 (law-primary-anchor/law-text/corroborating) + EXACT 검증 |
| file-save-protocol-tax | confidentialData/tax/ 경로, JSON+MD 동시 저장 강제 |

## DATA SSOT

- **파라미터**: `funds/pension_tax_params.json` (19개, law.go.kr 앵커 기반 verified, 90일 신선도)
- **계산**: pension-tax-rules §9 (모든 수치 parameter_id 참조)
- **검증**: tax-calc-verifier python3 재계산 + tax-critic A~F 채점

## ANTI-PATTERNS (절대 금지)

- 오케스트레이터: Task 없이 분석·계산·검증 직접 수행
- 거시경제 분석 엔진 참조 (세제 상담에 불필요)
- 세금 수치·구조상수를 agent/skill/command/test 코드에 하드코딩 (반드시 parameter_id 참조)
- corroborating/단일 출처로 `verified` 표기
- 유효한 verified 값을 pending 재확인 실패로 보류 처리
- 04-summary에 새 숫자 생성 (검증 부록 1:1 매핑만)
- 자동 커밋 (커밋은 제안만)
