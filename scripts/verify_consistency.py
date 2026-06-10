#!/usr/bin/env python3
import argparse
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast


@dataclass(frozen=True)
class Violation:
    file: str
    line: int
    ssot: str
    message_ko: str


CheckResult = list[Violation]


@dataclass(frozen=True)
class Args:
    root: Path
    only: str | None


_PLUGINS_REL = ".claude/plugins"

_RE_SUBAGENT = re.compile(
    r"""subagent_type\s*=\s*["'](?:(?P<plugin>[A-Za-z0-9_-]+):)?(?P<name>[A-Za-z0-9][A-Za-z0-9_-]{2,})["']"""
)
_RE_AT = re.compile(
    r"(?<![\w.+\-])@(?P<name>[A-Za-z0-9][A-Za-z0-9_-]{2,})(?=[\s\]\\),.;:!?`]|$)"
)
_RE_SLASH_CMD = re.compile(
    r"(?<!\S)/(?P<plugin>[A-Za-z0-9_-]+):(?P<command>[A-Za-z0-9][A-Za-z0-9_-]{2,})"
    r"(?=[\s\]\\),.;:!?`]|$)"
)
_RE_SKILLS_REF = re.compile(r"""^\s*skills_reference:\s*["'](?P<names>[^"']+)["']""")

# ASCII 경계 lookaround(한글은 \w라 제외 불가) + 하이픈 1개 이상 kebab만 매치
_RE_KEBAB = re.compile(
    r"(?<![A-Za-z0-9_./+\-])(?P<name>[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+)(?![A-Za-z0-9_-])"
)

_ROLE_WORDS = ("orchestrator", "coordinator")

_RE_FRONTMATTER_NAME = re.compile(
    r'^name:\s*["\']?(?P<name>[A-Za-z0-9][A-Za-z0-9_-]+)', re.MULTILINE
)

_TOOL_PREFIXES = ("mcp-", "mcp_", "websearch-", "websearch_", "exa-", "exa_")


def _dangling_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _frontmatter_name(path: Path) -> str | None:
    head = _dangling_read_text(path)[:2000]
    match = _RE_FRONTMATTER_NAME.search(head)
    return match.group("name") if match else None


def _build_declared(root: Path) -> set[str]:
    declared: set[str] = set()
    plugins_dir = root / _PLUGINS_REL

    marketplace = plugins_dir / ".claude-plugin" / "marketplace.json"
    if marketplace.is_file():
        try:
            data = json.loads(_dangling_read_text(marketplace))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            if isinstance(data.get("name"), str):
                declared.add(data["name"])
            for plugin in data.get("plugins", []) or []:
                if isinstance(plugin, dict) and isinstance(plugin.get("name"), str):
                    declared.add(plugin["name"])

    for plugin_json in plugins_dir.glob("*/.claude-plugin/plugin.json"):
        try:
            data = json.loads(_dangling_read_text(plugin_json))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict) and isinstance(data.get("name"), str):
            declared.add(data["name"])

    for agent_md in plugins_dir.glob("*/agents/*.md"):
        name = _frontmatter_name(agent_md)
        declared.add(name if name else agent_md.stem)

    for skill_md in plugins_dir.glob("*/skills/*/SKILL.md"):
        name = _frontmatter_name(skill_md)
        declared.add(name if name else skill_md.parent.name)

    for command_md in plugins_dir.glob("*/commands/*.md"):
        declared.add(command_md.stem)
        name = _frontmatter_name(command_md)
        if name:
            declared.add(name)

    fund_data = root / "funds" / "fund_data.json"
    if fund_data.is_file():
        try:
            meta = json.loads(_dangling_read_text(fund_data)).get("_meta", {})
        except (json.JSONDecodeError, AttributeError):
            meta = {}
        for code in meta.get("missing", []) or []:
            if isinstance(code, str):
                declared.add(code)

    return declared


def _is_filename_token(text: str, end: int) -> bool:
    return text[end : end + 1] == "." and text[end + 1 : end + 2].isalnum()


def _is_role_identifier(name: str) -> bool:
    return any(role in name for role in _ROLE_WORDS)


def check_dangling(root: Path) -> CheckResult:
    plugins_dir = root / _PLUGINS_REL
    if not plugins_dir.is_dir():
        return []

    declared = _build_declared(root)
    violations: list[Violation] = []
    seen: set[tuple[str, int, str]] = set()

    prose_hits: list[tuple[str, int, str]] = []
    prose_files: dict[str, set[str]] = {}
    prose_count: dict[str, int] = {}

    def add(rel: str, line_no: int, name: str) -> None:
        key = (rel, line_no, name)
        if key in seen:
            return
        seen.add(key)
        violations.append(
            Violation(
                file=rel,
                line=line_no,
                ssot="symbol-table",
                message_ko=f"선언 없는 참조: {name}",
            )
        )

    def is_dangling(name: str) -> bool:
        if name in declared:
            return False
        return not any(name.startswith(prefix) for prefix in _TOOL_PREFIXES)

    for md_file in sorted(plugins_dir.glob("**/*.md")):
        rel = md_file.relative_to(root).as_posix()
        text = _dangling_read_text(md_file)
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in _RE_SUBAGENT.finditer(line):
                name = match.group("name")
                if is_dangling(name):
                    add(rel, line_no, name)
            for match in _RE_AT.finditer(line):
                name = match.group("name")
                if is_dangling(name):
                    add(rel, line_no, name)
            for match in _RE_SLASH_CMD.finditer(line):
                name = match.group("command")
                if is_dangling(name):
                    add(rel, line_no, name)
            ref_match = _RE_SKILLS_REF.match(line)
            if ref_match:
                for raw in ref_match.group("names").split(","):
                    name = raw.strip()
                    if name and is_dangling(name):
                        add(rel, line_no, name)
            for match in _RE_KEBAB.finditer(line):
                name = match.group("name")
                if not is_dangling(name):
                    continue
                if _is_filename_token(line, match.end()):
                    continue
                if not _is_role_identifier(name):
                    continue
                prose_hits.append((rel, line_no, name))
                prose_files.setdefault(name, set()).add(rel)
                prose_count[name] = prose_count.get(name, 0) + 1

    # prose 빈도 게이트: 동일 이름이 ≥2 파일 또는 ≥3 회일 때만 승격
    for rel, line_no, name in prose_hits:
        if len(prose_files.get(name, set())) >= 2 or prose_count.get(name, 0) >= 3:
            add(rel, line_no, name)

    violations.sort(key=lambda v: (v.file, v.line, v.message_ko))
    return violations


DATE_RE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
PATH_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}-[A-Z]")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
FRONTMATTER_DATE_RE = re.compile(r"^\s*(created|updated):\s*\d{4}-\d{2}-\d{2}")
SEMANTIC_MARKER_RE = re.compile(r"<!--\s*semantic-date:([^\s>]+)\s*-->")
ILLUSTRATIVE_MARKER_RE = re.compile(r"<!--\s*illustrative-date\s*-->")
SEMANTIC_KEYWORDS = ("기준일", "version", "baseDate", "_meta", "as of", "기준")


def _logic_markdown_files(root: Path) -> list[Path]:
    plugins_root = root / _PLUGINS_REL
    paths: set[Path] = set()

    paths.update(plugins_root.glob("**/agents/*.md"))
    paths.update(plugins_root.glob("**/skills/**/SKILL.md"))
    paths.update(plugins_root.glob("**/commands/*.md"))

    return sorted(path for path in paths if path.is_file())


def _read_ssot_value(root: Path, pointer: str) -> object:
    if "#" not in pointer:
        raise ValueError("포인터에 # 구분자가 없습니다")

    file_name, accessor = pointer.split("#", 1)
    if not file_name or not accessor:
        raise ValueError("포인터의 파일 경로 또는 접근자가 비어 있습니다")

    data = cast(object, json.loads((root / file_name).read_text(encoding="utf-8")))
    parts = [part for chunk in accessor.split("/") for part in chunk.split(".") if part]

    for part in parts:
        if isinstance(data, dict):
            data = data[part]
        elif isinstance(data, list):
            data = data[int(part)]
        else:
            raise KeyError(part)

    return data


def _has_semantic_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in SEMANTIC_KEYWORDS)


def _marker_text(lines: list[str], index: int) -> str:
    previous = lines[index - 1] if index > 0 else ""
    return f"{previous}\n{lines[index]}"


def _guard_text(lines: list[str], index: int) -> str:
    start = max(0, index - 1)
    end = min(len(lines), index + 2)
    return "\n".join(lines[start:end])


def _is_path_date(line: str, start: int) -> bool:
    return PATH_DATE_RE.match(line, start) is not None


def _semantic_violation(
    root: Path,
    relative: str,
    line_number: int,
    pointer: str,
    literal: str,
) -> Violation | None:
    try:
        actual = str(_read_ssot_value(root, pointer))
    except Exception as e:
        return Violation(
            file=relative,
            line=line_number,
            ssot=pointer,
            message_ko=f"semantic-date 포인터 해석 실패: {pointer} ({e})",
        )

    if actual == literal:
        return None

    return Violation(
        file=relative,
        line=line_number,
        ssot=pointer,
        message_ko=f"날짜 불일치: 문서 {literal}, SSOT {actual}",
    )


def _check_tdf_base_date_note(root: Path) -> CheckResult:
    relative = "funds/tdf_data.json"
    path = root / relative
    if not path.is_file():
        return []

    pointer = "funds/fund_data.json#_meta.version"
    violations: CheckResult = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        raw = cast(dict[str, object], json.loads(text))
        meta = raw.get("_meta", {})
        if not isinstance(meta, dict):
            return []
        note = str(cast(dict[str, object], meta).get("baseDateNote", ""))
    except json.JSONDecodeError:
        return []
    if not note or "fund_data.json" not in note:
        return []

    line_number = 1
    for index, line in enumerate(lines):
        if '"baseDateNote"' in line:
            line_number = index + 1
            break

    for match in DATE_RE.finditer(note):
        violation = _semantic_violation(root, relative, line_number, pointer, match.group(0))
        if violation is not None:
            violations.append(
                Violation(
                    file=violation.file,
                    line=violation.line,
                    ssot=violation.ssot,
                    message_ko=f"tdf baseDateNote 날짜 불일치/미주석: {violation.message_ko}",
                )
            )

    return violations


def check_date_sync(root: Path) -> CheckResult:
    violations: CheckResult = []

    for path in _logic_markdown_files(root):
        relative = path.relative_to(root).as_posix()
        lines = path.read_text(encoding="utf-8").splitlines()
        in_fence = False
        fence_token = ""
        in_frontmatter = False
        frontmatter_done = False

        for index, line in enumerate(lines):
            line_number = index + 1

            if line_number == 1 and line.strip() == "---":
                in_frontmatter = True
                continue

            if in_frontmatter and line.strip() == "---":
                in_frontmatter = False
                frontmatter_done = True
                continue

            if not in_frontmatter and not frontmatter_done and line_number != 1:
                frontmatter_done = True

            fence_match = FENCE_RE.match(line)
            if fence_match is not None:
                token = fence_match.group(1)
                if in_fence and token == fence_token:
                    in_fence = False
                    fence_token = ""
                elif not in_fence:
                    in_fence = True
                    fence_token = token
                continue

            if in_fence and not _has_semantic_keyword(line):
                continue

            for match in DATE_RE.finditer(line):
                if in_frontmatter and FRONTMATTER_DATE_RE.match(line):
                    continue
                if _is_path_date(line, match.start()):
                    continue

                marker_text = _marker_text(lines, index)
                semantic_match = SEMANTIC_MARKER_RE.search(marker_text)
                if semantic_match is not None:
                    violation = _semantic_violation(
                        root,
                        relative,
                        line_number,
                        semantic_match.group(1),
                        match.group(0),
                    )
                    if violation is not None:
                        violations.append(violation)
                    continue

                if ILLUSTRATIVE_MARKER_RE.search(marker_text) is not None:
                    if _has_semantic_keyword(_guard_text(lines, index)):
                        violations.append(
                            Violation(
                                file=relative,
                                line=line_number,
                                ssot="illustrative-date",
                                message_ko="illustrative 오분류 가능 — 재분류 필요",
                            )
                        )
                    continue

                violations.append(
                    Violation(
                        file=relative,
                        line=line_number,
                        ssot="date_sync",
                        message_ko=(
                            f"미주석 날짜 리터럴({match.group(0)}) — 주석 필요: "
                            "<!-- semantic-date:PTR --> 또는 <!-- illustrative-date -->"
                        ),
                    )
                )

    violations.extend(_check_tdf_base_date_note(root))
    return violations


def check_freshness(root: Path) -> CheckResult:
    relative = "funds/deposit_rates.json"
    raw: object = json.loads((root / relative).read_text(encoding="utf-8"))
    meta = cast(dict[str, object], cast(dict[str, object], raw)["_meta"])

    parsed = datetime.fromisoformat(cast(str, meta["updatedAt"]))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    threshold = int(cast(int, meta.get("freshnessThresholdDays", 30)))
    now = datetime.now(timezone.utc)
    age = (now - parsed).days

    if age > threshold:
        return [
            Violation(
                file=relative,
                line=1,
                ssot=f"{relative}#_meta.updatedAt",
                message_ko=f"deposit_rates.json 신선도 만료: {age}일 경과 (임계: {threshold}일) — 수동 갱신 필요",
            )
        ]

    return []


def check_dup_test(root: Path) -> CheckResult:
    import ast

    tests_dir = root / "tests"
    if not tests_dir.is_dir():
        return []

    violations: CheckResult = []

    for path in sorted(tests_dir.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue

        names: dict[str, list[int]] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    names.setdefault(node.name, []).append(node.lineno)

        for name, lines in names.items():
            if len(lines) <= 1:
                continue
            lines.sort()
            line1, line2 = lines[0], lines[1]
            line_str = ", ".join(str(line) for line in lines)
            violations.append(
                Violation(
                    file=relative,
                    line=line1,
                    ssot="",
                    message_ko=f"중복 테스트 함수명: {name} (라인 {line_str})",
                )
            )
            violations.append(
                Violation(
                    file=relative,
                    line=line2,
                    ssot="",
                    message_ko=f"중복 테스트 함수명: {name} (중복 — 라인 {line1}과 동일)",
                )
            )

    return violations


def check_manifest(root: Path) -> CheckResult:
    market_rel = ".claude/plugins/.claude-plugin/marketplace.json"
    market_path = root / market_rel
    violations: CheckResult = []

    market = json.loads(market_path.read_text(encoding="utf-8"))
    plugins = market.get("plugins", [])

    settings_rel = ".claude/settings.json"
    settings_path = root / settings_rel
    enabled: dict[str, object] = {}
    settings_ok = settings_path.is_file()
    if settings_ok:
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            enabled = settings.get("enabledPlugins", {})
        except json.JSONDecodeError:
            settings_ok = False

    plugins_root = root / ".claude" / "plugins"

    for entry in plugins:
        plugin_name = entry.get("name", "")
        source = entry.get("source", "")
        normalized = source[2:] if source.startswith("./") else source
        source_dir = plugins_root / normalized
        plugin_json_rel = (
            f".claude/plugins/{normalized}/.claude-plugin/plugin.json"
        )

        if not source_dir.is_dir():
            violations.append(
                Violation(
                    file=plugin_json_rel,
                    line=1,
                    ssot=market_rel,
                    message_ko=f"플러그인 매니페스트 오류 [{plugin_name}]: source 디렉토리 없음 ({normalized})",
                )
            )
            continue

        plugin_json_path = source_dir / ".claude-plugin" / "plugin.json"
        if not plugin_json_path.is_file():
            violations.append(
                Violation(
                    file=plugin_json_rel,
                    line=1,
                    ssot=market_rel,
                    message_ko=f"플러그인 매니페스트 오류 [{plugin_name}]: plugin.json 없음",
                )
            )
            continue

        try:
            plugin_json = json.loads(plugin_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            violations.append(
                Violation(
                    file=plugin_json_rel,
                    line=1,
                    ssot=market_rel,
                    message_ko=f"플러그인 매니페스트 오류 [{plugin_name}]: plugin.json JSON 파싱 실패 ({e})",
                )
            )
            continue

        actual_name = plugin_json.get("name")
        if actual_name is None:
            violations.append(
                Violation(
                    file=plugin_json_rel,
                    line=1,
                    ssot=market_rel,
                    message_ko=f"플러그인 매니페스트 오류 [{plugin_name}]: plugin.json에 name 필드 없음",
                )
            )
            continue

        if actual_name != plugin_name:
            violations.append(
                Violation(
                    file=plugin_json_rel,
                    line=1,
                    ssot=market_rel,
                    message_ko=f"플러그인 매니페스트 오류 [{plugin_name}]: name 불일치 (plugin.json: {actual_name})",
                )
            )
            continue

        if not settings_ok:
            violations.append(
                Violation(
                    file=plugin_json_rel,
                    line=1,
                    ssot=market_rel,
                    message_ko=f"플러그인 매니페스트 오류 [{plugin_name}]: settings.json 없음/파싱 실패",
                )
            )
            continue

        if not any(str(key).split("@", 1)[0] == plugin_name for key in enabled):
            violations.append(
                Violation(
                    file=plugin_json_rel,
                    line=1,
                    ssot=market_rel,
                    message_ko=f"플러그인 매니페스트 오류 [{plugin_name}]: settings.json enabledPlugins에 미등록",
                )
            )

    return violations


CHECKS: dict[str, Callable[[Path], CheckResult]] = {
    "dangling": check_dangling,
    "date_sync": check_date_sync,
    "freshness": check_freshness,
    "dup_test": check_dup_test,
    "manifest": check_manifest,
}

REQUIRED_INPUTS = (
    ".claude/plugins",
    ".claude/plugins/.claude-plugin/marketplace.json",
    "funds/fund_data.json",
    "funds/fund_fees.json",
    "funds/fund_classification.json",
    "tests",
)


def parse_args(argv: list[str] | None = None) -> Args:
    parser = argparse.ArgumentParser(
        description="SEMA 가이드 일관성 드리프트 검사용 scaffold 게이트",
    )
    _ = parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="검사할 저장소 루트 경로 (기본값: 현재 작업 디렉토리)",
    )
    _ = parser.add_argument(
        "--only",
        choices=sorted(CHECKS),
        help="지정한 단일 검사만 실행",
    )
    namespace = parser.parse_args(argv)
    return Args(root=cast(Path, namespace.root), only=cast(str | None, namespace.only))


def validate_root(root: Path) -> Path:
    resolved_root = root.expanduser().resolve()
    if not resolved_root.is_dir():
        raise FileNotFoundError(f"루트 디렉토리가 없습니다: {resolved_root}")

    missing = [relative for relative in REQUIRED_INPUTS if not (resolved_root / relative).exists()]
    if missing:
        raise FileNotFoundError(f"필수 입력 경로가 없습니다: {', '.join(missing)}")

    return resolved_root


def collect_violations(root: Path, only: str | None) -> CheckResult:
    check_names = [only] if only else list(CHECKS)
    violations: CheckResult = []

    for check_name in check_names:
        violations.extend(CHECKS[check_name](root))

    return violations


def print_report(root: Path, violations: CheckResult) -> None:
    print(f"검사 시작... (루트: {root})")

    for violation in violations:
        message = f"[위반] {violation.file}:{violation.line} — {violation.message_ko} [SSOT: {violation.ssot}]"
        print(message)

    print(f"검사 완료: 총 {len(violations)}개 위반 발견")


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        root = validate_root(args.root)
        violations = collect_violations(root, args.only)
        print_report(root, violations)
        return 1 if violations else 0
    except Exception as e:
        print(f"[오류] 내부 오류: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
