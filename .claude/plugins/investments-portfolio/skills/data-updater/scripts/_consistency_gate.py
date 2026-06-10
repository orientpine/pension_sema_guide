#!/usr/bin/env python3
"""Shared consistency-gate runner for data-updater scripts.

데이터 갱신 스크립트의 성공 경로 끝에서 호출되어 저장소 정합성 게이트
(`scripts/verify_consistency.py`)를 실행한다. 게이트가 실패(non-zero)하면
데이터 갱신을 차단하기 위해 동일 종료 코드로 프로세스를 종료한다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    """Resolve the repository root from this script's location.

    scripts -> data-updater -> skills -> investments-portfolio -> plugins
    -> .claude -> <repo root> == parents[6]
    """
    return Path(__file__).resolve().parents[6]


def run_consistency_gate() -> None:
    """Run the repository consistency gate; exit non-zero on failure.

    데이터 갱신 후 필수 게이트. exit 0 이 아니면 갱신을 차단한다.
    """
    gate_path = _repo_root() / "scripts" / "verify_consistency.py"
    result = subprocess.run([sys.executable, str(gate_path)], capture_output=False)
    if result.returncode != 0:
        message = "⚠️  일관성 게이트 실패 — 데이터 갱신 차단. 위반 사항을 수정 후 재실행하세요."
        print(message)
        sys.exit(result.returncode)
