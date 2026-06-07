#!/usr/bin/env bash
# verify_no_pii.sh — fail if any PII string or PII path exists in the FULL git history.
# NOTE: PII strings are assembled from fragments at runtime so this script does NOT
# literally contain the PII (avoids self-matching and filter-repo --replace-text mangling).
# Usage: run inside a git repo. Exit 0 = clean, nonzero = PII found.
set -u

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

if [ "$fail" -eq 0 ]; then
  echo "RESULT: PASS (no PII)"
  exit 0
else
  echo "RESULT: FAIL (PII detected)"
  exit 1
fi
