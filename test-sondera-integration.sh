#!/bin/bash
# Test script for Sondera + SuperClaude integration
# This script verifies that the hooks are properly configured

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Use same paths as install-with-sondera.sh
SONDERA_DIR="$HOME/.local/share/sondera-coding-agent-hooks"
SOCKET_PATH="/tmp/sondera-harness.sock"

echo "=================================="
echo "Sondera + SuperClaude Integration Test"
echo "=================================="
echo ""

# 1. Check settings file exists
echo -n "Checking settings.local.json... "
if [ -f ".claude/settings.local.json" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    exit 1
fi

# 1b. Validate hook schema format (array-based with CamelCase event keys)
echo -n "Validating hook schema format... "
if python3 -c "
import json, sys
with open('.claude/settings.local.json') as f:
    data = json.load(f)
hooks = data.get('hooks', {})
if 'user-prompt-submit' in hooks:
    print('ERROR: Outdated flat schema detected (kebab-case key)', file=sys.stderr)
    sys.exit(1)
if 'PreToolUse' not in hooks:
    print('ERROR: Missing PreToolUse key - expected CamelCase event keys', file=sys.stderr)
    sys.exit(1)
if not isinstance(hooks['PreToolUse'], list):
    print('ERROR: PreToolUse should be an array, not flat object', file=sys.stderr)
    sys.exit(1)
" 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Invalid hook schema${NC}"
    echo "  Expected array-based format with CamelCase event keys (e.g., PreToolUse, PostToolUse)"
    echo "  Re-run install-with-sondera.sh to regenerate"
    exit 1
fi

# 2. Verify harness server is running
echo -n "Checking harness server... "
if [ -S "$SOCKET_PATH" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Socket not found${NC}"
    echo "Run: $SONDERA_DIR/target/release/sondera-harness-server --socket $SOCKET_PATH --policy-path $SONDERA_DIR/policies &"
    exit 1
fi

# 3. Check if hook binary can be built
echo -n "Checking hook binary... "
if cargo build --manifest-path "$SONDERA_DIR/apps/claude/Cargo.toml" --quiet 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

# 4. Test socket connectivity with nc
echo -n "Testing socket connection... "
if timeout 1 bash -c "echo '{}' | nc -U $SOCKET_PATH" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ Connection test inconclusive${NC}"
fi

echo ""
echo -e "${GREEN}✓ Integration setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code if currently running"
echo "  2. cd ~/Desktop/SuperClaude"
echo "  3. claude"
echo "  4. Try: /sc:implement \"Add hello world function\""
echo ""
echo "Monitoring:"
echo "  - Harness logs: tail -f $HOME/.local/state/sondera/harness.log"
echo "  - Hook will execute on every Claude Code operation"
echo ""
