#!/usr/bin/env bash
# verify_plugin.sh — validate vendored plugin manifests and that referenced paths resolve.
# Exit 0 = valid, nonzero = invalid.
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 2
fail=0

MKTROOT=".claude/plugins"
PLUGIN_DIR="$MKTROOT/investments-portfolio"
MARKET="$MKTROOT/.claude-plugin/marketplace.json"
PLUGIN="$PLUGIN_DIR/.claude-plugin/plugin.json"

echo "== [1] JSON validity =="
for f in "$MARKET" "$PLUGIN" ".claude/settings.json"; do
  if [ ! -f "$f" ]; then
    echo "  FAIL: missing $f"; fail=1; continue
  fi
  if jq -e . "$f" >/dev/null 2>&1; then
    echo "  OK: valid JSON $f"
  else
    echo "  FAIL: invalid JSON $f"; fail=1
  fi
done

echo "== [2] Plugin source dir resolves =="
src=$(jq -r '.plugins[0].source' "$MARKET" 2>/dev/null)
if [ -d "$MKTROOT/$src" ]; then
  echo "  OK: source dir exists ($MKTROOT/$src)"
else
  echo "  FAIL: source dir missing ($MKTROOT/$src)"; fail=1
fi

echo "== [3] Agents / commands / skills present =="
for sub in agents commands skills; do
  cnt=$(find "$PLUGIN_DIR/$sub" -type f 2>/dev/null | wc -l)
  if [ "$cnt" -gt 0 ]; then
    echo "  OK: $sub has $cnt files"
  else
    echo "  FAIL: $sub empty/missing"; fail=1
  fi
done

echo "== [4] Orchestrator command present =="
if [ -f "$PLUGIN_DIR/commands/portfolio-analyze.md" ]; then
  echo "  OK: portfolio-analyze.md present"
else
  echo "  FAIL: portfolio-analyze.md missing"; fail=1
fi

echo "== [5] settings.json enables plugin =="
if jq -e '.enabledPlugins | to_entries | map(select(.key|test("investments-portfolio"))) | length > 0' .claude/settings.json >/dev/null 2>&1; then
  echo "  OK: plugin enabled in settings"
else
  echo "  FAIL: plugin not enabled in settings.json"; fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "RESULT: PASS (plugin valid)"
  exit 0
else
  echo "RESULT: FAIL (plugin invalid)"
  exit 1
fi
