#!/bin/bash
# SuperClaude + Sondera Security Layer Installation Script
# This script installs SuperClaude with optional Sondera security harness

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SONDERA_REPO="${SONDERA_REPO:-https://github.com/your-org/sondera-coding-agent-hooks}"
SONDERA_VERSION="${SONDERA_VERSION:-v0.1.0}"  # Pin to a specific release tag
SONDERA_DIR="$HOME/.local/share/sondera-coding-agent-hooks"
SOCKET_PATH="/tmp/sondera-harness.sock"

echo -e "${BLUE}=================================="
echo "SuperClaude + Sondera Installation"
echo -e "==================================${NC}"
echo ""

# Check if we're in the SuperClaude directory
if [ ! -f "CLAUDE.md" ]; then
    echo -e "${RED}Error: Must be run from SuperClaude root directory${NC}"
    exit 1
fi

# Validate repo URL is not the placeholder
if [[ "$SONDERA_REPO" == *"your-org"* ]]; then
    echo -e "${RED}Error: SONDERA_REPO still contains placeholder URL.${NC}"
    echo "Set the actual repo URL before running:"
    echo "  export SONDERA_REPO='https://github.com/actual-org/sondera-coding-agent-hooks'"
    echo "  export SONDERA_VERSION='v0.1.0'  # optional: pin to specific tag"
    exit 1
fi

echo -e "${YELLOW}This installer will set up SuperClaude with Sondera security layer.${NC}"
echo ""
echo "Prerequisites:"
echo "  - Rust toolchain (cargo)"
echo "  - Ollama with models: ministral-3:14b-cloud, gpt-oss-safeguard:20b"
echo "  - Unix socket support (Linux/macOS)"
echo ""
read -p "Continue with Sondera installation? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Skipping Sondera installation. Using SuperClaude without security layer.${NC}"
    exit 0
fi

# 1. Check prerequisites
echo ""
echo -e "${BLUE}[1/6] Checking prerequisites...${NC}"

echo -n "  Checking Rust/Cargo... "
if command -v cargo &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Install Rust from: https://rustup.rs/"
    exit 1
fi

echo -n "  Checking Ollama... "
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Install Ollama from: https://ollama.ai/"
    exit 1
fi

echo -n "  Checking Ollama models... "
MISSING_MODELS=()
if ! ollama list | grep -q "ministral-3:14b-cloud"; then
    MISSING_MODELS+=("ministral-3:14b-cloud")
fi
if ! ollama list | grep -q "gpt-oss-safeguard:20b"; then
    MISSING_MODELS+=("gpt-oss-safeguard:20b")
fi

if [ ${#MISSING_MODELS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC}"
    echo "  Missing models: ${MISSING_MODELS[*]}"
    echo "  Run: ollama pull ministral-3:14b-cloud && ollama pull gpt-oss-safeguard:20b"
    read -p "  Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 2. Clone/update Sondera repository
echo ""
echo -e "${BLUE}[2/6] Installing Sondera harness...${NC}"

if [ -d "$SONDERA_DIR" ]; then
    echo "  Updating existing installation..."
    cd "$SONDERA_DIR"
    git fetch --tags
    git checkout "$SONDERA_VERSION"
else
    echo "  Cloning repository (pinned to $SONDERA_VERSION)..."
    mkdir -p "$(dirname "$SONDERA_DIR")"
    git clone --branch "$SONDERA_VERSION" --depth 1 "$SONDERA_REPO" "$SONDERA_DIR"
    cd "$SONDERA_DIR"
fi

# 3. Build Sondera components
echo ""
echo -e "${BLUE}[3/6] Building Sondera components...${NC}"

echo "  Building harness server..."
cargo build --release --bin sondera-harness-server

echo "  Building Claude Code hook..."
cargo build --release --manifest-path apps/claude/Cargo.toml

echo -e "${GREEN}✓ Build complete${NC}"

# 4. Create SuperClaude settings.local.json
echo ""
echo -e "${BLUE}[4/6] Configuring SuperClaude...${NC}"

cd "$OLDPWD"  # Return to SuperClaude directory

mkdir -p .claude

HOOK_PATH="$SONDERA_DIR/apps/claude/target/release/sondera-claude-hook"

cat > .claude/settings.local.json <<EOF
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose pre-tool-use" }] }
    ],
    "PermissionRequest": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose permission-request" }] }
    ],
    "PostToolUse": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose post-tool-use" }] }
    ],
    "PostToolUseFailure": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose post-tool-use-failure" }] }
    ],
    "UserPromptSubmit": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose user-prompt-submit" }] }
    ],
    "Notification": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose notification" }] }
    ],
    "Stop": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose stop" }] }
    ],
    "SubagentStart": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose subagent-start" }] }
    ],
    "SubagentStop": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose subagent-stop" }] }
    ],
    "TeammateIdle": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose teammate-idle" }] }
    ],
    "TaskCompleted": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose task-completed" }] }
    ],
    "PreCompact": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose pre-compact" }] }
    ],
    "SessionStart": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose session-start" }] }
    ],
    "SessionEnd": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "$HOOK_PATH --verbose session-end" }] }
    ]
  }
}
EOF

echo -e "${GREEN}✓ Created .claude/settings.local.json${NC}"

# 5. Install systemd service (optional, Linux only)
echo ""
echo -e "${BLUE}[5/6] Setting up harness service...${NC}"

if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v systemctl &> /dev/null; then
    read -p "  Install systemd service for auto-start? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat > /tmp/sondera-harness.service <<EOF
[Unit]
Description=Sondera Security Harness
After=network.target

[Service]
Type=simple
ExecStart=$SONDERA_DIR/target/release/sondera-harness-server --socket $SOCKET_PATH --policy-path $SONDERA_DIR/policies
Restart=always
User=$USER

[Install]
WantedBy=default.target
EOF
        mkdir -p ~/.config/systemd/user/
        mv /tmp/sondera-harness.service ~/.config/systemd/user/
        systemctl --user daemon-reload
        systemctl --user enable sondera-harness.service
        systemctl --user start sondera-harness.service
        echo -e "${GREEN}✓ Systemd service installed and started${NC}"
    fi
else
    echo -e "${YELLOW}  Manual start required (not Linux or no systemd)${NC}"
    echo "  Start harness with:"
    echo "    $SONDERA_DIR/target/release/sondera-harness-server --socket $SOCKET_PATH --policy-path $SONDERA_DIR/policies &"
fi

# 6. Start harness server if not running
echo ""
echo -e "${BLUE}[6/6] Starting harness server...${NC}"

if [ -S "$SOCKET_PATH" ]; then
    echo -e "${GREEN}✓ Already running${NC}"
else
    if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v systemctl &> /dev/null; then
        # Started by systemd above
        sleep 2
        if [ -S "$SOCKET_PATH" ]; then
            echo -e "${GREEN}✓ Started via systemd${NC}"
        else
            echo -e "${RED}✗ Failed to start${NC}"
            exit 1
        fi
    else
        # Manual start for macOS or non-systemd systems
        "$SONDERA_DIR/target/release/sondera-harness-server" \
            --socket "$SOCKET_PATH" \
            --policy-path "$SONDERA_DIR/policies" \
            > /tmp/sondera-harness.log 2>&1 &

        sleep 2
        if [ -S "$SOCKET_PATH" ]; then
            echo -e "${GREEN}✓ Started in background${NC}"
            echo "  Logs: tail -f /tmp/sondera-harness.log"
        else
            echo -e "${RED}✗ Failed to start${NC}"
            echo "  Check logs: cat /tmp/sondera-harness.log"
            exit 1
        fi
    fi
fi

# Verification
echo ""
echo -e "${GREEN}=================================="
echo "✓ Installation Complete!"
echo -e "==================================${NC}"
echo ""
echo "Sondera security layer is now active for SuperClaude."
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Restart Claude Code if currently running"
echo "  2. Test with: ./test-sondera-integration.sh"
echo ""
echo -e "${YELLOW}Monitoring:${NC}"
echo "  - Harness logs: tail -f /tmp/sondera-harness.log"
echo "  - Hook executes on every Claude Code tool use"
echo ""
echo -e "${YELLOW}To disable Sondera:${NC}"
echo "  - Remove: .claude/settings.local.json"
echo "  - Stop harness: kill \$(pgrep sondera-harness)"
echo ""
