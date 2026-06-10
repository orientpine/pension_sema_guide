import importlib
import json
import shutil
import subprocess
import sys
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "verify_consistency.py"


@pytest.fixture
def tmp_repo(tmp_path: Path, repo_root: Path) -> Iterator[Path]:
    destination = tmp_path / "repo"
    ignore = shutil.ignore_patterns(
        ".git",
        ".omo",
        ".pytest_cache",
        "__pycache__",
        "confidentialData",
    )
    _ = shutil.copytree(repo_root, destination, ignore=ignore)
    yield destination


def inject_drift(root: Path, kind: str) -> None:
    if kind == "dangling_ref":
        target = (
            root
            / ".claude"
            / "plugins"
            / "equity-research"
            / "agents"
            / "equity-research-analyst.md"
        )
        with target.open("a", encoding="utf-8") as handle:
            _ = handle.write('\nTask(subagent_type="nonexistent-foo")\n')
        return
    _ = root, kind


def _clear_logic_markdown(root: Path) -> None:
    plugins_root = root / ".claude" / "plugins"
    for pattern in ("**/agents/*.md", "**/skills/**/SKILL.md", "**/commands/*.md"):
        for path in plugins_root.glob(pattern):
            path.unlink()


def _set_fund_version(root: Path, value: str) -> None:
    fund_path = root / "funds" / "fund_data.json"
    data = json.loads(fund_path.read_text(encoding="utf-8"))
    data["_meta"]["version"] = value
    _ = fund_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _sync_tdf_base_date_note(root: Path) -> None:
    fund_path = root / "funds" / "fund_data.json"
    tdf_path = root / "funds" / "tdf_data.json"
    fund_data = json.loads(fund_path.read_text(encoding="utf-8"))
    tdf_data = json.loads(tdf_path.read_text(encoding="utf-8"))
    fund_version = fund_data["_meta"]["version"]
    tdf_data["_meta"][
        "baseDateNote"
    ] = f"fund_data.json 기준일 {fund_version}과 상이. 직접 교차비교 금지"
    _ = tdf_path.write_text(json.dumps(tdf_data, ensure_ascii=False), encoding="utf-8")


def _prepare_date_sync_repo(root: Path) -> None:
    _clear_logic_markdown(root)
    _sync_tdf_base_date_note(root)


def _write_date_agent(root: Path, body: str) -> Path:
    path = root / ".claude" / "plugins" / "investments-portfolio" / "agents" / "date-check.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(body, encoding="utf-8")
    return path


def run_gate(root: Path, only: str | None = None) -> tuple[int, str]:
    script = root / "scripts" / "verify_consistency.py"
    if not script.is_file():
        script = SCRIPT

    command = [sys.executable, str(script), "--root", str(root)]
    if only is not None:
        command.extend(["--only", only])

    cwd = root if root.is_dir() else REPO
    proc = subprocess.run(command, capture_output=True, text=True, cwd=str(cwd))
    return proc.returncode, proc.stdout


def test_help_exits_0():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )

    assert proc.returncode == 0, proc.stderr
    assert "--root" in proc.stdout
    assert "--only" in proc.stdout


def test_nonexistent_root_exits_2():
    exit_code, stdout = run_gate(Path("/nonexistent"))

    assert exit_code == 2
    assert "내부 오류" in stdout


def test_tmp_repo_fixture_works(tmp_repo: Path):
    # Scaffold test: verify the fixture copies repo and gate runs without crash.
    # HEAD has known violations (dangling refs, stale dates, freshness, dup tests),
    # so the gate exits 1. After Wave 3 fixes are applied this becomes exit 0.
    assert (tmp_repo / "scripts" / "verify_consistency.py").is_file()

    exit_code, stdout = run_gate(tmp_repo)

    assert exit_code in (0, 1), f"Unexpected exit {exit_code}: {stdout}"
    assert "검사 완료:" in stdout


def test_date_sync_mutation(tmp_repo: Path):
    _prepare_date_sync_repo(tmp_repo)
    _set_fund_version(tmp_repo, "2026-07-01")
    _sync_tdf_base_date_note(tmp_repo)
    _write_date_agent(
        tmp_repo,
        "<!-- semantic-date:funds/fund_data.json#_meta.version -->\n"
        "기준일: 2026-06-01\n",
    )

    exit_code, stdout = run_gate(tmp_repo, only="date_sync")

    assert exit_code == 1
    assert "date-check.md:2" in stdout
    assert "2026-06-01" in stdout
    assert "2026-07-01" in stdout


def test_tdf_lockstep_negative(tmp_repo: Path):
    _prepare_date_sync_repo(tmp_repo)
    _write_date_agent(
        tmp_repo,
        "---\n"
        "created: 2026-01-01\n"
        "updated: 2026-01-02\n"
        "---\n"
        "# 날짜 음성 대조군\n"
        "경로 예시: portfolios/2026-06-01-AGGRESSIVE/report.md\n"
        "<!-- illustrative-date -->\n"
        "샘플 일정: 2026-01-15\n"
        "```json\n"
        "{\"sampleDate\": \"2026-02-01\"}\n"
        "```\n",
    )

    exit_code, stdout = run_gate(tmp_repo, only="date_sync")

    assert exit_code == 0
    assert "총 0개 위반 발견" in stdout


def test_cross_ssot_isolation(tmp_repo: Path):
    _prepare_date_sync_repo(tmp_repo)
    tdf_path = tmp_repo / "funds" / "tdf_data.json"
    tdf_data = json.loads(tdf_path.read_text(encoding="utf-8"))
    tdf_data["_meta"]["version"] = "2026-06-04"
    _ = tdf_path.write_text(json.dumps(tdf_data, ensure_ascii=False), encoding="utf-8")
    _write_date_agent(
        tmp_repo,
        "<!-- semantic-date:funds/fund_data.json#_meta.version -->\n"
        "fund_data 기준일: 2026-06-01\n",
    )

    exit_code, stdout = run_gate(tmp_repo, only="date_sync")

    assert exit_code == 0, stdout
    assert "총 0개 위반 발견" in stdout


def test_misannotation_guard(tmp_repo: Path):
    _prepare_date_sync_repo(tmp_repo)
    _write_date_agent(
        tmp_repo,
        "<!-- illustrative-date -->\n"
        "기준일 예시: 2026-06-01\n",
    )

    exit_code, stdout = run_gate(tmp_repo, only="date_sync")

    assert exit_code == 1
    assert "date-check.md:2" in stdout
    assert "illustrative 오분류 가능" in stdout


def test_dup_test_mutation(tmp_repo: Path):
    dummy = tmp_repo / "tests" / "test_dummy_dup.py"
    _ = dummy.write_text(
        "def test_foo():\n"
        "    assert True\n"
        "\n"
        "\n"
        "def test_foo():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    exit_code, stdout = run_gate(tmp_repo, only="dup_test")

    assert exit_code == 1
    assert "test_foo" in stdout


def test_dup_test_head():
    exit_code, stdout = run_gate(REPO, only="dup_test")

    assert exit_code == 0
    assert "총 0개 위반 발견" in stdout


def test_dup_test_clean(tmp_repo: Path):
    dummy = tmp_repo / "tests" / "test_dummy_unique.py"
    _ = dummy.write_text(
        "def test_alpha():\n"
        "    assert True\n"
        "\n"
        "\n"
        "def test_beta():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    sys.path.insert(0, str(REPO / "scripts"))
    verify_consistency = importlib.import_module("verify_consistency")

    violations = verify_consistency.check_dup_test(tmp_repo)
    dummy_violations = [v for v in violations if v.file.endswith("test_dummy_unique.py")]

    assert dummy_violations == []


def _set_deposit_updated_at(root: Path, value: str) -> None:
    rates_path = root / "funds" / "deposit_rates.json"
    data = json.loads(rates_path.read_text(encoding="utf-8"))
    data["_meta"]["updatedAt"] = value
    _ = rates_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_freshness_stale(tmp_repo: Path):
    stale = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    _set_deposit_updated_at(tmp_repo, stale)

    exit_code, stdout = run_gate(tmp_repo, only="freshness")

    assert exit_code == 1
    assert "신선도 만료" in stdout


def test_freshness_fresh(tmp_repo: Path):
    fresh = datetime.now(timezone.utc).isoformat()
    _set_deposit_updated_at(tmp_repo, fresh)

    exit_code, stdout = run_gate(tmp_repo, only="freshness")

    assert exit_code == 0
    assert "총 0개 위반 발견" in stdout


def _second_plugin_json(root: Path) -> Path:
    market = json.loads(
        (root / ".claude" / "plugins" / ".claude-plugin" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    second = market["plugins"][1]
    source = second["source"]
    normalized = source[2:] if source.startswith("./") else source
    return root / ".claude" / "plugins" / normalized / ".claude-plugin" / "plugin.json"


def _second_plugin_name(root: Path) -> str:
    market = json.loads(
        (root / ".claude" / "plugins" / ".claude-plugin" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    return market["plugins"][1]["name"]


def test_manifest_clean_head():
    exit_code, stdout = run_gate(REPO, only="manifest")

    assert exit_code == 0, stdout
    assert "총 0개 위반 발견" in stdout


def test_manifest_mutation_broken_json(tmp_repo: Path):
    plugin_json = _second_plugin_json(tmp_repo)
    name = _second_plugin_name(tmp_repo)
    _ = plugin_json.write_text("{not valid json", encoding="utf-8")

    exit_code, stdout = run_gate(tmp_repo, only="manifest")

    assert exit_code == 1
    assert name in stdout


def test_manifest_mutation_missing_plugin_json(tmp_repo: Path):
    plugin_json = _second_plugin_json(tmp_repo)
    name = _second_plugin_name(tmp_repo)
    plugin_json.unlink()

    exit_code, stdout = run_gate(tmp_repo, only="manifest")

    assert exit_code == 1
    assert name in stdout


def test_dangling_head():
    exit_code, stdout = run_gate(REPO, only="dangling")

    assert exit_code == 0
    assert "총 0개 위반 발견" in stdout


def test_dangling_mutation(tmp_repo: Path):
    inject_drift(tmp_repo, "dangling_ref")

    exit_code, stdout = run_gate(tmp_repo, only="dangling")

    assert exit_code == 1
    assert "nonexistent-foo" in stdout
    assert (
        ".claude/plugins/equity-research/agents/equity-research-analyst.md" in stdout
    )
