"""R27: 실제 git 경계에서 개인 보유정보의 공개를 차단한다."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_no_pii.sh"


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, env={**os.environ, "GIT_MASTER": "1"},
        capture_output=True, text=True, check=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "user.name", "Fixture")
    (tmp_path / ".gitignore").write_text("confidentialData/\n", encoding="utf-8")
    shutil.copyfile(SCRIPT, tmp_path / "verify_no_pii.sh")
    git(tmp_path, "add", ".")
    git(tmp_path, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture")
    return tmp_path


@pytest.mark.parametrize("directory", ["consultations", "portfolios/samples"])
@pytest.mark.parametrize("state", ["committed", "staged", "working", "history"])
@pytest.mark.parametrize("content", [
    "보유 수량: 12주\n", "평단: 72,000원\n", "매입가 72000원\n",
    "평가금액: 864,000원\n", "계좌번호: 123-456-789\n", "잔고: 864000원\n",
    '{"holding_quantity": 12, "average_price": 72000}\n',
    "| 보유 수량 | 평단 |\n| --- | --- |\n| 12주 | 72,000원 |\n",
])
def test_r27_public_holdings_fail(repo: Path, directory: str, state: str, content: str) -> None:
    path = repo / directory / "report.md"
    path.parent.mkdir(parents=True)
    path.write_text("일반 시장 분석\n", encoding="utf-8")
    if state == "working":
        git(repo, "add", str(path))
        git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "clean")
    path.write_text(content, encoding="utf-8")
    if state != "working":
        git(repo, "add", str(path))
    if state in ("committed", "history"):
        git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "holdings")
    if state in ("staged", "history"):
        path.write_text("일반 시장 분석\n", encoding="utf-8")
    if state == "history":
        git(repo, "add", str(path))
        git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "clean again")
    result = subprocess.run(["bash", "verify_no_pii.sh"], cwd=repo, capture_output=True, check=False)
    assert result.returncode != 0


@pytest.mark.parametrize("private", [False, True])
def test_r27_market_report_and_ignored_holdings_pass(repo: Path, private: bool) -> None:
    public = repo / "consultations/report.md"
    public.parent.mkdir()
    public.write_text(
        "PER 12배, 주가 72000원\n| 보유 종목 수 | 556개 |\n"
        "| 거래소 잔고 | 감소 추세 |\n퇴직연금 계좌 활용\n"
        '{"balance": 5, "fed_balance_sheet": "확대"}\n'
        "| BTC | https://example.invalid/fed-balance-sheet/ | 2026-11-16 |\n"
        "예시(참고): 잔고 8000만원·연금수령 1년차의 연금수령한도\n"
        '{"amount_name": "연금수령한도 (예시: 잔고 8000만원·1년차)"}\n'
        "| 세액공제 | 연금계좌_세액공제한도 | 금액 |\n"
        "| 검증 | 출처 | 100원 |\n", encoding="utf-8",
    )
    git(repo, "add", str(public))
    git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "market")
    if private:
        path = repo / "confidentialData/consultations/report.md"
        path.parent.mkdir(parents=True)
        path.write_text("보유 수량: 12주, 평단: 72000원\n", encoding="utf-8")
        assert git(repo, "check-ignore", str(path)).returncode == 0
    result = subprocess.run(["bash", "verify_no_pii.sh"], cwd=repo, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout.decode()
