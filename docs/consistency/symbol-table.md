# 플러그인 심볼 테이블 및 참조 추출 규칙

기준 경로: `.claude/plugins/`  
스캔 범위: 마켓플레이스 1개 + 플러그인 4개(`investments-portfolio`, `macro-analysis`, `stock-consultation`, `equity-research`)

## 1. 선언 이름 레지스트리

선언 이름 집합은 `agents/*.md` 및 `skills/*/SKILL.md`의 frontmatter `name:`과 `commands/*.md` 명령 파일명을 기준으로 한다. 현재 2개 command 파일에는 frontmatter `name:`이 없으므로 파일 stem을 명령 이름으로 사용한다.

### 1.1 마켓플레이스/플러그인 컨텍스트

| plugin | type | name | file |
|---|---|---|---|
| marketplace | marketplace | pension-sema-guide | `.claude/plugins/.claude-plugin/marketplace.json` |
| investments-portfolio | plugin | investments-portfolio | `.claude/plugins/investments-portfolio/.claude-plugin/plugin.json` |
| macro-analysis | plugin | macro-analysis | `.claude/plugins/macro-analysis/.claude-plugin/plugin.json` |
| stock-consultation | plugin | stock-consultation | `.claude/plugins/stock-consultation/.claude-plugin/plugin.json` |
| equity-research | plugin | equity-research | `.claude/plugins/equity-research/.claude-plugin/plugin.json` |

### 1.2 Agent 선언

| plugin | type | name | file |
|---|---|---|---|
| investments-portfolio | agent | compliance-checker | `.claude/plugins/investments-portfolio/agents/compliance-checker.md` |
| investments-portfolio | agent | fund-portfolio | `.claude/plugins/investments-portfolio/agents/fund-portfolio.md` |
| investments-portfolio | agent | output-critic | `.claude/plugins/investments-portfolio/agents/output-critic.md` |
| macro-analysis | agent | index-fetcher | `.claude/plugins/macro-analysis/agents/index-fetcher.md` |
| macro-analysis | agent | leadership-analyst | `.claude/plugins/macro-analysis/agents/leadership-analyst.md` |
| macro-analysis | agent | macro-critic | `.claude/plugins/macro-analysis/agents/macro-critic.md` |
| macro-analysis | agent | macro-synthesizer | `.claude/plugins/macro-analysis/agents/macro-synthesizer.md` |
| macro-analysis | agent | rate-analyst | `.claude/plugins/macro-analysis/agents/rate-analyst.md` |
| macro-analysis | agent | risk-analyst | `.claude/plugins/macro-analysis/agents/risk-analyst.md` |
| macro-analysis | agent | sector-analyst | `.claude/plugins/macro-analysis/agents/sector-analyst.md` |
| stock-consultation | agent | bear-case-critic | `.claude/plugins/stock-consultation/agents/bear-case-critic.md` |
| stock-consultation | agent | materials-organizer | `.claude/plugins/stock-consultation/agents/materials-organizer.md` |
| stock-consultation | agent | stock-critic | `.claude/plugins/stock-consultation/agents/stock-critic.md` |
| stock-consultation | agent | stock-screener | `.claude/plugins/stock-consultation/agents/stock-screener.md` |
| stock-consultation | agent | stock-valuation | `.claude/plugins/stock-consultation/agents/stock-valuation.md` |
| equity-research | agent | equity-research-analyst | `.claude/plugins/equity-research/agents/equity-research-analyst.md` |

### 1.3 Skill 선언

| plugin | type | name | file |
|---|---|---|---|
| investments-portfolio | skill | analyst-common | `.claude/plugins/investments-portfolio/skills/analyst-common/SKILL.md` |
| investments-portfolio | skill | bogle-principles | `.claude/plugins/investments-portfolio/skills/bogle-principles/SKILL.md` |
| investments-portfolio | skill | data-updater | `.claude/plugins/investments-portfolio/skills/data-updater/SKILL.md` |
| investments-portfolio | skill | dc-pension-rules | `.claude/plugins/investments-portfolio/skills/dc-pension-rules/SKILL.md` |
| investments-portfolio | skill | devil-advocate | `.claude/plugins/investments-portfolio/skills/devil-advocate/SKILL.md` |
| investments-portfolio | skill | file-save-protocol | `.claude/plugins/investments-portfolio/skills/file-save-protocol/SKILL.md` |
| investments-portfolio | skill | fund-output-template | `.claude/plugins/investments-portfolio/skills/fund-output-template/SKILL.md` |
| investments-portfolio | skill | fund-selection-criteria | `.claude/plugins/investments-portfolio/skills/fund-selection-criteria/SKILL.md` |
| investments-portfolio | skill | macro-output-template | `.claude/plugins/investments-portfolio/skills/macro-output-template/SKILL.md` |
| investments-portfolio | skill | perspective-balance | `.claude/plugins/investments-portfolio/skills/perspective-balance/SKILL.md` |
| investments-portfolio | skill | web-search-verifier | `.claude/plugins/investments-portfolio/skills/web-search-verifier/SKILL.md` |
| stock-consultation | skill | analyst-common-stock | `.claude/plugins/stock-consultation/skills/analyst-common-stock/SKILL.md` |
| stock-consultation | skill | file-save-protocol-stock | `.claude/plugins/stock-consultation/skills/file-save-protocol-stock/SKILL.md` |
| stock-consultation | skill | stock-data-verifier | `.claude/plugins/stock-consultation/skills/stock-data-verifier/SKILL.md` |

### 1.4 Command 선언

| plugin | type | name | file |
|---|---|---|---|
| investments-portfolio | command | portfolio-analyze | `.claude/plugins/investments-portfolio/commands/portfolio-analyze.md` |
| stock-consultation | command | stock-consult | `.claude/plugins/stock-consultation/commands/stock-consult.md` |

## 2. 참조 추출 문법

기본 이름 토큰은 `[A-Za-z0-9][A-Za-z0-9_-]{2,}`로 제한한다. 즉 최소 3자 이상, 공백 없음, 영문/숫자/하이픈/언더스코어만 허용한다.

| pattern | regex/condition | example | false-positive guard |
|---|---|---|---|
| `subagent_type="<name>"` | `subagent_type\s*=\s*["'](?:(?<plugin>[A-Za-z0-9_-]+):)?(?<name>[A-Za-z0-9][A-Za-z0-9_-]{2,})["']` | `subagent_type="macro-analysis:index-fetcher"` | `plugin:` prefix는 네임스페이스로 분리하고 `name`만 선언 집합과 대조한다. `Task(subagent_type=...)`처럼 값이 생략된 예시는 제외한다. |
| `@<name>` | <code>(?&lt;![\w.+-])@(?&lt;name&gt;[A-Za-z0-9][A-Za-z0-9_-]{2,})(?=[\s\]\\),.;:!?&#96;]&#124;$)</code> | `@equity-research-analyst` | 이메일 오탐 방지: 앞 문자가 단어/`.`/`+`/`-`이면 제외한다. 뒤에는 공백 또는 문장부호가 와야 한다. |
| `/<plugin>:<command>` | <code>(?&lt;!\S)/(?&lt;plugin&gt;[A-Za-z0-9_-]+):(?&lt;command&gt;[A-Za-z0-9][A-Za-z0-9_-]{2,})(?=[\s\]\\),.;:!?&#96;]&#124;$)</code> | `/investments-portfolio:portfolio-analyze` | markdown 링크 URL path와 일반 파일 경로 오탐 방지: 토큰 시작 전은 공백/행 시작이어야 하며 반드시 `plugin:command` 콜론 형태여야 한다. |
| `skills_reference:` | `^\s*skills_reference:\s*["'](?<names>[^"']+)["']` 후 comma split | `skills_reference: "portfolio-orchestrator, file-save-protocol"` | YAML/frontmatter형 키에서만 추출한다. 각 comma 항목은 trim 후 기본 이름 토큰과 일치해야 한다. |
| backtick 이름 | `` `(?<name>[A-Za-z0-9][A-Za-z0-9_-]{2,})` `` + 같은 문장/행에 symbol context 필요 | `` `file-save-protocol` 스킬 `` | 같은 행 또는 인접 문장에 `agent`, `skill`, `command`, `에이전트`, `스킬`, `명령`, `호출`, `참조`, `Task`, `subagent_type` 중 하나가 있어야 한다. 코드 변수/필드/파일명/상수 오탐은 제외한다. |
| legacy prose identifier 후보 | 기본 이름 토큰이 symbol context와 함께 반복 출현 | `portfolio-orchestrator에서 호출` | 고신뢰 문법은 아니므로 자동 판정이 아니라 후보로만 둔다. 동일 이름이 3회 이상 또는 2개 파일 이상에서 나타나고, 주변에 `orchestrator`, `coordinator`, `호출`, `스킬`, `에이전트`, `command` 등이 있을 때만 후보화한다. |

오탐 방지 공통 규칙:

- 영어 일반 단어 단독 출현은 참조로 보지 않는다. `the`, `risk`, `report` 같은 산문 단어는 기본 이름 토큰에 맞더라도 위 패턴/컨텍스트 없이는 제외한다.
- snake_case 변수(`original_text`, `materials_path`, `totalFee`), ALL_CAPS 상수(`DC_RISK_LIMIT_70`), 파일명/출력명(`macro-outlook.json`)은 선언 집합에 없는 한 dangling 후보에서 제외한다.
- MCP/tool 네임스페이스(`mcp_*`, `websearch_*`, `exa_*`)는 플러그인 agent/skill/command 심볼이 아니므로 제외한다.
- markdown 링크 `[text](url)`의 URL/path 부분은 `/plugin:command` 패턴 대상에서 제외한다.
- 최종 dangling 판정은 `참조 name ∉ {agent names ∪ skill names ∪ command names}`일 때만 한다. 플러그인 prefix는 별도 namespace로 확인하고, local name만 선언 집합과 대조한다.

## 3. 댕글링 후보 목록

| referenced name | count | files | disposition |
|---|---:|---|---|
| portfolio-orchestrator | 16 | 9 files: `.claude/plugins/macro-analysis/agents/macro-synthesizer.md`, `.claude/plugins/macro-analysis/agents/leadership-analyst.md`, `.claude/plugins/investments-portfolio/agents/compliance-checker.md`, `.claude/plugins/investments-portfolio/agents/fund-portfolio.md`, `.claude/plugins/investments-portfolio/agents/output-critic.md`, `.claude/plugins/investments-portfolio/skills/fund-output-template/SKILL.md`, `.claude/plugins/investments-portfolio/skills/data-updater/SKILL.md`, `.claude/plugins/investments-portfolio/skills/file-save-protocol/SKILL.md`, `.claude/plugins/investments-portfolio/commands/portfolio-analyze.md` | 선언 집합에 없음. 현재 실제 진입점은 command `portfolio-analyze`이며, `commands/portfolio-analyze.md:681`의 `skills_reference: "portfolio-orchestrator, file-save-protocol"`은 선언이 아니라 참조다. Evidence: `.omo/evidence/task-4-dangling.txt` (`wc -l` = 16). |

현재 스캔에서 `portfolio-orchestrator`는 요청된 기준(16곳/9파일)을 만족하는 댕글링 후보로 확인되었다. 자동 수정은 수행하지 않았다.
