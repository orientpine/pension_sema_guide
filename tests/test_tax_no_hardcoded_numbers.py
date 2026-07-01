"""
Literal number scanner for .claude/plugins/pension-tax-advisor/**/*.md files.
Tax/law numbers and structural constants must NOT appear as bare literals.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PLUGIN_DIR = ROOT / ".claude" / "plugins" / "pension-tax-advisor"

# Regex to detect bare numeric tokens that are likely tax/structural values
# Matches: integers, decimals, numbers with comma (e.g., 9,000,000), 만원 suffix
# Must NOT be inside {id:...} references, code fences with <!-- illustrative -->, or pure math
BARE_NUMBER_PATTERN = re.compile(
    r"""(?x)
    (?<!\{id:)          # not a parameter_id reference
    (?<!\w)             # not part of a word
    (
        \d{1,3}(?:,\d{3})+  # comma-formatted numbers: 9,000,000
        |
        \d+(?:\.\d+)?       # plain integers and decimals
    )
    (?:만원|원|%)?       # optional Korean unit suffix
    (?!\w)              # not part of a word
    """,
    re.UNICODE
)

# Allowlist: pure math/structural markers not related to tax values
PURE_MATH_ALLOWLIST = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100, 12, 365}

# Known tax/structural numbers that must NOT appear as bare literals
FORBIDDEN_VALUES = {
    # Tax limits
    900, 600, 300, 1800, 9000000, 6000000, 3000000, 18000000, 15000000,
    1500, 15000,
    # Tax rates
    12, 15, 13.2, 16.5, 5.5, 4.4, 3.3, 10,
    # Structural constants
    11, 120, 70, 60, 50,
    # Common amounts written differently
    9000, 6000, 1800,
}


def get_all_md_files():
    if not PLUGIN_DIR.exists():
        return []
    return list(PLUGIN_DIR.rglob("*.md"))


def is_inside_allowed_context(line: str, match_start: int) -> bool:
    """Check if a match is inside an allowed context (parameter_id ref, comment, code)"""
    before = line[:match_start]
    # Inside {id:...} reference
    if "{id:" in before and "}" not in before.split("{id:")[-1]:
        return True
    # The match itself is after {id:
    if line[max(0, match_start-5):match_start].rstrip().endswith("id:"):
        return True
    # Inside HTML/markdown comment
    if "<!--" in before and "-->" not in before.split("<!--")[-1]:
        return True
    return False


def scan_file_for_bare_numbers(filepath: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_num, matched_text, line_content) for violations"""
    violations = []
    in_code_fence = False
    has_illustrative = False

    lines = filepath.read_text(encoding="utf-8").splitlines()

    for line_num, line in enumerate(lines, 1):
        # Track code fence
        if line.strip().startswith("```"):
            if not in_code_fence:
                in_code_fence = True
                has_illustrative = "<!-- illustrative" in line
            else:
                in_code_fence = False
                has_illustrative = False
            continue

        # Skip lines with illustrative annotation
        if "<!-- illustrative" in line or "<!-- semantic-date" in line:
            continue

        # In code fence with illustrative annotation - skip
        if in_code_fence and has_illustrative:
            continue

        # Neutralize leading markdown heading section numbers (e.g. "### 3.3 Title")
        scan_target = line
        heading = re.match(r"^(\s*#{1,6}\s+)(\d+(?:\.\d+)*)(?=\s|$)", line)
        if heading:
            h_start, h_end = heading.start(2), heading.end(2)
            scan_target = line[:h_start] + (" " * (h_end - h_start)) + line[h_end:]

        for match in BARE_NUMBER_PATTERN.finditer(scan_target):
            matched_text = match.group(0)
            match_start = match.start()

            # Section/statute cross-reference (§4.4, §59의3) — structural, not a tax value
            if match_start > 0 and line[match_start - 1] == "§":
                continue

            # Skip if inside allowed context
            if is_inside_allowed_context(line, match_start):
                continue

            # Try to extract numeric value
            num_str = re.sub(r"[만원,%]", "", matched_text).replace(",", "")
            try:
                num_val = float(num_str)
            except ValueError:
                continue

            # Skip pure math allowlist values
            if num_val in PURE_MATH_ALLOWLIST:
                continue

            # Flag forbidden tax/structural values
            if num_val in FORBIDDEN_VALUES or int(num_val) in FORBIDDEN_VALUES:
                violations.append((line_num, matched_text, line.strip()))

    return violations


@pytest.mark.parametrize("filepath", get_all_md_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_no_hardcoded_tax_numbers(filepath):
    """Verify no bare tax/structural number literals in pension-tax-advisor .md files"""
    violations = scan_file_for_bare_numbers(filepath)
    if violations:
        details = "\n".join(f"  line {ln}: {txt!r} in: {ctx!r}" for ln, txt, ctx in violations[:5])
        pytest.fail(
            f"{filepath.relative_to(ROOT)}: Found {len(violations)} bare number literal(s):\n{details}"
        )
