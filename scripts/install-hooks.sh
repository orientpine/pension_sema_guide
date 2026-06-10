#!/usr/bin/env bash
# Install git pre-commit hook for consistency gate + pytest
set -e
HOOK=".git/hooks/pre-commit"
cat > "$HOOK" << 'EOF'
#!/usr/bin/env bash
set -e
echo "Running consistency gate..."
python3 scripts/verify_consistency.py
echo "Running pytest..."
python3 -m pytest -q
EOF
chmod +x "$HOOK"
echo "Pre-commit hook installed at $HOOK"
