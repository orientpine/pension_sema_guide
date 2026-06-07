#!/usr/bin/env bash
# verify_no_pii.sh — fail if any PII string or PII path exists in the FULL git history.
# Usage: run inside a git repo. Exit 0 = clean, nonzero = PII found.
set -u

fail=0

echo "== [1] Scanning ALL history for PII strings =="
PII_STRINGS=("***" "정부출연연구원")
for s in "${PII_STRINGS[@]}"; do
  # search every blob across all commits
  hits=$(git log --all -p -S"$s" --pretty=format:'%H' 2>/dev/null | grep -c "$s" || true)
  if git grep -q "$s" $(git rev-list --all) 2>/dev/null; then
    echo "  FAIL: '$s' found in history"
    fail=1
  else
    echo "  OK: '$s' absent from history"
  fi
done

echo "== [2] Scanning ALL history for PII paths =="
PII_PATHS_REGEX='(^|/)cbd\.md$|(^|/)nouse/|(^|/)portfolios/previous/|(^|/)portfolios/2026-|/node_modules/|__pycache__'
allpaths=$(git log --all --name-only --pretty=format: 2>/dev/null | sort -u | grep -vE '^$' || true)
badpaths=$(echo "$allpaths" | grep -E "$PII_PATHS_REGEX" || true)
if [ -n "$badpaths" ]; then
  echo "  FAIL: PII paths present in history:"
  echo "$badpaths" | sed 's/^/    /'
  fail=1
else
  echo "  OK: no PII paths in history"
fi

echo "== [3] Working tree check =="
if git grep -q "***" 2>/dev/null; then
  echo "  FAIL: '***' in working tree"
  fail=1
else
  echo "  OK: working tree has no '***'"
fi

if [ "$fail" -eq 0 ]; then
  echo "RESULT: PASS (no PII)"
  exit 0
else
  echo "RESULT: FAIL (PII detected)"
  exit 1
fi
