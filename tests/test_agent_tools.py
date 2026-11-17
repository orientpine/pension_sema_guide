"""플러그인 에이전트·스킬 frontmatter의 tools는 실행 환경에 실제로 있는 도구 이름만 쓴다(거시 실패 원인 H1)."""

import re
from pathlib import Path

PLUGINS = Path(__file__).resolve().parents[1] / ".claude/plugins"
KNOWN_TOOLS = {"Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebSearch", "WebFetch", "AskUserQuestion", "Task"}


def frontmatter_tools(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---", text, re.S)
    if not match:
        return []
    line = re.search(r"^tools:\s*(.+)$", match.group(1), re.M)
    return [name.strip() for name in line.group(1).split(",") if name.strip()] if line else []


def test_every_declared_tool_exists() -> None:
    unknown = {
        str(path.relative_to(PLUGINS)): sorted(set(frontmatter_tools(path)) - KNOWN_TOOLS)
        for path in sorted(PLUGINS.rglob("*.md"))
        if set(frontmatter_tools(path)) - KNOWN_TOOLS
    }
    assert unknown == {}


def test_body_does_not_call_undeclared_search_tools() -> None:
    pattern = re.compile(r"\b(?:mcp_)?(?:websearch_|exa_)?web_search_exa\b|\bmcp_question\b")
    hits = {
        str(path.relative_to(PLUGINS)): sorted(set(pattern.findall(path.read_text(encoding="utf-8"))))
        for path in sorted(PLUGINS.rglob("*.md"))
        if pattern.search(path.read_text(encoding="utf-8"))
    }
    assert hits == {}
