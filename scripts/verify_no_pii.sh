#!/usr/bin/env bash
# verify_no_pii.sh — fail if any PII string or PII path exists in the FULL git history.
# NOTE: PII strings are assembled from fragments at runtime so this script does NOT
# literally contain the PII (avoids self-matching and filter-repo --replace-text mangling).
# Usage: run inside a git repo. Exit 0 = clean, nonzero = PII found.
set -u
export GIT_MASTER=1

fail=0

# Assemble PII needles from fragments (never store the full literal here)
NAME="$(printf '%s' '차백')$(printf '%s' '동')"
EMPLOYER="$(printf '%s' '한국기계')$(printf '%s' '연구원')"
PII_STRINGS=("$NAME" "$EMPLOYER")

echo "== [1] Scanning ALL history for PII strings =="
for s in "${PII_STRINGS[@]}"; do
  if git grep -q "$s" $(git rev-list --all) 2>/dev/null; then
    echo "  FAIL: PII string found in history"
    fail=1
  else
    echo "  OK: PII string absent from history"
  fi
done

echo "== [2] Scanning ALL history for PII paths =="
PII_PATHS_REGEX='(^|/)cbd\.md$|(^|/)nouse/|(^|/)portfolios/previous/|(^|/)portfolios/2026-|node_modules/|__pycache__|\.pyc$'
allpaths=$(git log --all --name-only --pretty=format: 2>/dev/null | sort -u | grep -vE '^$' || true)
badpaths=$(echo "$allpaths" | grep -E "$PII_PATHS_REGEX" || true)
if [ -n "$badpaths" ]; then
  echo "  FAIL: PII/junk paths present in history:"
  echo "$badpaths" | sed 's/^/    /'
  fail=1
else
  echo "  OK: no PII/junk paths in history"
fi

echo "== [3] Working tree check =="
if git grep -q "$NAME" 2>/dev/null; then
  echo "  FAIL: PII name in working tree"
  fail=1
else
  echo "  OK: working tree clean of PII name"
fi

echo "== [4] 공개 보고서의 개인 보유정보 검사 (작업트리·스테이지·전체 이력) =="
# 내용과 금액은 출력하지 않는다. confidentialData는 조회 대상에서 제외한다.
if python3 - <<'PY'
import re
import subprocess
import sys
from pathlib import Path

PUBLIC = ("consultations/", "portfolios/samples/")
MARKER = (
    r"보유\s*(?:수량|주수)|평단(?:가)?|평균\s*매입가|매입(?:가|단가)|"
    r"평가\s*금액|계좌(?:\s*번호)?|잔고|"
    r"holding[_ ]?quantity|average[_ ]?(?:price|cost)|"
    r"(?:evaluation|market)[_ ]?(?:amount|value)|account(?:[_ ]?(?:number|id))?|"
    r"(?:account|cash)[_ ]?balance"
)
VALUE = r"""[\s"'`*_:：=|()\[\]₩$-]*(?:KRW|USD)?\s*[0-9]"""
INLINE = re.compile(r"(?:" + MARKER + r")" + VALUE, re.IGNORECASE)
CELL = re.compile(r"""[\s*`"']*(?:""" + MARKER + r""")(?:\s*\([^)]*\))?[\s*`"']*""", re.IGNORECASE)
NUMBER = re.compile(r"[0-9]")


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def has_holdings(content: bytes) -> bool:
    text = content.decode("utf-8", errors="replace")
    # JSON의 기본 ASCII 이스케이프도 동일하게 검사한다.
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), text)
    columns = []
    for line in text.splitlines():
        # 실제 잔고가 아닌, 명시된 연금수령한도 계산 예시의 가상 잔고만 제외한다.
        # 보유 수량·평단·계좌 등 다른 필드는 같은 줄에 있어도 계속 검사한다.
        inline_line = line
        if "연금수령한도" in line and not re.search(r"내\s*잔고|본인|고객|실제\s*잔고", line):
            inline_line = re.sub(r"(예시(?:\(참고\))?:\s*)잔고", r"\1가상값", line)
        if INLINE.search(inline_line):
            return True
        if "|" not in line:
            columns = []
            continue
        cells = line.strip().strip("|").split("|")
        if columns and any(i < len(cells) and NUMBER.search(cells[i]) for i in columns):
            return True
        marked = [i for i, cell in enumerate(cells) if CELL.fullmatch(cell)]
        if marked:
            columns = marked
    return False


try:
    found = False
    paths = git("ls-files", "-z", "--", *PUBLIC).split(b"\0")
    for raw in filter(None, paths):
        path = Path(raw.decode())
        if path.is_file() and has_holdings(path.read_bytes()):
            print("  FAIL: 공개 작업트리에 개인 보유정보")
            found = True
    staged = git("ls-files", "--stage", "-z", "--", *PUBLIC).split(b"\0")
    blobs = {entry.split(b" ", 2)[1] for entry in staged if entry}
    # 삭제·수정된 과거 보고서도 빠지지 않게 모든 도달 가능한 커밋을 검사한다.
    for commit in git("rev-list", "--all").splitlines():
        entries = git("ls-tree", "-r", "-z", commit.decode(), "--", *PUBLIC).split(b"\0")
        for entry in filter(None, entries):
            metadata = entry.split(b"\t", 1)[0].split()
            if metadata[1] == b"blob":
                blobs.add(metadata[2])
    for blob in blobs:
        if has_holdings(git("cat-file", "blob", blob.decode())):
            print("  FAIL: 공개 스테이지 또는 이력에 개인 보유정보")
            found = True
            break
    if not found:
        print("  OK: 공개 보고서에 개인 보유정보 없음")
    sys.exit(1 if found else 0)
except (OSError, subprocess.CalledProcessError) as error:
    print(f"  FAIL: 보유정보 검사를 완료할 수 없음 ({type(error).__name__})")
    sys.exit(1)
PY
then
  :
else
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "RESULT: PASS (no PII)"
  exit 0
else
  echo "RESULT: FAIL (PII detected)"
  exit 1
fi
