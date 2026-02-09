#!/bin/bash
# SuperClaude Manual Installation Script

SOURCE="/home/tony/Desktop/SuperClaude"
TARGET="$HOME/.claude"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║         SuperClaude Manual Installation                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Create backup
if [ -d "$TARGET" ]; then
    BACKUP_DIR="$TARGET.backup.$(date +%Y%m%d_%H%M%S)"
    echo "📦 Creating backup: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    cp -r "$TARGET"/*.md "$BACKUP_DIR/" 2>/dev/null
    cp -r "$TARGET/superclaude" "$BACKUP_DIR/" 2>/dev/null
    echo "   ✓ Backup created"
    echo ""
fi

# Copy framework files
echo "📝 Installing framework files..."
cp "$SOURCE"/{AGENTS,CLAUDE_CORE,FLAGS,PRINCIPLES,QUICKSTART,RULES_CRITICAL,RULES_RECOMMENDED,TOOLS}.md "$TARGET/" 2>/dev/null
echo "   ✓ Core framework files (8)"

# Copy agents directory
echo "🤖 Installing agent personas..."
mkdir -p "$TARGET/superclaude/agents"
cp -r "$SOURCE/agents"/* "$TARGET/superclaude/agents/" 2>/dev/null
AGENT_COUNT=$(find "$TARGET/superclaude/agents" -name "*.md" 2>/dev/null | wc -l)
echo "   ✓ Agent personas ($AGENT_COUNT)"

# Create skills directory
echo "📚 Setting up skills directory..."
mkdir -p "$TARGET/skills/learned"
echo "   ✓ Skills directory created"

# Update CLAUDE.md
echo "⚙️  Updating configuration..."
if [ -f "$TARGET/CLAUDE.md" ]; then
    echo "   ✓ CLAUDE.md already exists"
else
    cat > "$TARGET/CLAUDE.md" << 'CLAUDE_MD'
# SuperClaude Entry Point

This file serves as the entry point for the SuperClaude framework.
You can add your own custom instructions and configurations here.

The SuperClaude framework components will be automatically imported below.

# ═══════════════════════════════════════════════════
# SuperClaude Framework Components
# ═══════════════════════════════════════════════════

# Core Framework
@AGENTS.md
@CLAUDE_CORE.md
@FLAGS.md
@PRINCIPLES.md
@QUICKSTART.md
@RULES_CRITICAL.md
@RULES_RECOMMENDED.md
@TOOLS.md
CLAUDE_MD
    echo "   ✓ CLAUDE.md created"
fi

# Summary
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              Installation Complete! 🎉                   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Installed to: $TARGET"
echo "Framework files: 8"
echo "Agent personas: $AGENT_COUNT"
echo ""
echo "🚀 SuperClaude is ready! Just use Claude Code normally."
