#!/bin/bash
# SuperClaude Manual Uninstallation Script

TARGET="$HOME/.claude"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║         SuperClaude Manual Uninstallation                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Create backup first
BACKUP_DIR="$TARGET.backup.$(date +%Y%m%d_%H%M%S)"
echo "📦 Creating backup before uninstall: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
cp -r "$TARGET"/*.md "$BACKUP_DIR/" 2>/dev/null
cp -r "$TARGET/superclaude" "$BACKUP_DIR/" 2>/dev/null
cp -r "$TARGET/skills" "$BACKUP_DIR/" 2>/dev/null
echo "   ✓ Backup created"
echo ""

# Remove framework files
echo "🗑️  Removing framework files..."
rm -f "$TARGET"/{AGENTS,CLAUDE_CORE,FLAGS,PRINCIPLES,QUICKSTART,RULES_CRITICAL,RULES_RECOMMENDED,TOOLS}.md
echo "   ✓ Framework files removed"

# Remove agents directory
echo "🗑️  Removing agent personas..."
rm -rf "$TARGET/superclaude"
echo "   ✓ Agent directory removed"

# Ask about skills
echo ""
echo "📚 Skills directory: $TARGET/skills/"
read -p "   Remove learned skills? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$TARGET/skills"
    echo "   ✓ Skills removed"
else
    echo "   ✓ Skills preserved"
fi

# Ask about CLAUDE.md
echo ""
echo "⚙️  Configuration: $TARGET/CLAUDE.md"
read -p "   Remove CLAUDE.md? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f "$TARGET/CLAUDE.md"
    echo "   ✓ CLAUDE.md removed"
else
    echo "   ✓ CLAUDE.md preserved"
fi

# Summary
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║            Uninstallation Complete! 🗑️                   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Backup saved to: $BACKUP_DIR"
echo ""
echo "To restore: cp -r $BACKUP_DIR/* $TARGET/"
