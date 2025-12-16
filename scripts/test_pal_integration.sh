#!/bin/bash

# PAL MCP Integration Test Script
# Tests the configuration and integration of PAL MCP with SuperClaude Framework

echo "======================================="
echo "  PAL MCP Integration Test"
echo "======================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
tests_passed=0
tests_failed=0

# Function to test a condition
test_condition() {
    local test_name=$1
    local condition=$2
    
    echo -n "Testing: $test_name... "
    
    if eval "$condition"; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((tests_passed++))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        ((tests_failed++))
        return 1
    fi
}

# Function to check file content
check_file_content() {
    local file=$1
    local pattern=$2
    grep -qi "$pattern" "$file" 2>/dev/null
}

echo "1. Configuration Files"
echo "----------------------"
test_condition "~/.claude/settings.json exists" "[ -f ~/.claude/settings.json ]"
test_condition "settings.json has pal config" "check_file_content ~/.claude/settings.json 'PAL_MCP'"
test_condition "Claude Desktop config exists" "[ -f ~/.config/Claude/claude_desktop_config.json ]"
test_condition "Desktop config has pal-mcp" "check_file_content ~/.config/Claude/claude_desktop_config.json 'pal-mcp'"
echo ""

echo "2. API Keys"
echo "-----------"
echo "🔴 CRITICAL for long context operations:"
test_condition "GEMINI_API_KEY set (2M context)" "[ -n \"\$GEMINI_API_KEY\" ]"
echo ""
echo "🟡 ESSENTIAL for standard operations:"
test_condition "OPENAI_API_KEY set (GPT-5)" "[ -n \"\$OPENAI_API_KEY\" ]"

# Optional API keys (warn if not set)
echo -n "Testing: ANTHROPIC_API_KEY set... "
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((tests_passed++))
else
    echo -e "${YELLOW}⚠️  OPTIONAL (not set)${NC}"
fi

echo -n "Testing: GROK_API_KEY set... "
if [ -n "$GROK_API_KEY" ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((tests_passed++))
else
    echo -e "${YELLOW}⚠️  OPTIONAL (not set)${NC}"
fi

echo -n "Testing: OPENROUTER_API_KEY set... "
if [ -n "$OPENROUTER_API_KEY" ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
    ((tests_passed++))
else
    echo -e "${YELLOW}⚠️  OPTIONAL (not set)${NC}"
fi
echo ""

echo "3. PAL MCP Server Installation"
echo "-------------------------------"
test_condition "pal-mcp-server directory exists" "[ -d ~/.pal-mcp-server ]"
test_condition "pal server.py exists" "[ -f ~/.pal-mcp-server/server.py ]"
test_condition "pal virtual environment exists" "[ -d ~/.pal-mcp-server/.pal_venv ]"
echo ""

echo "4. SuperClaude Framework Integration"
echo "-------------------------------------"
test_condition "FLAGS.md exists" "[ -f ~/.claude/FLAGS.md ]"
test_condition "FLAGS.md contains --pal flag" "check_file_content ~/.claude/FLAGS.md 'pal'"
test_condition "FLAGS.md contains --consensus" "check_file_content ~/.claude/FLAGS.md 'consensus'"
test_condition "FLAGS.md contains --pal-review" "check_file_content ~/.claude/FLAGS.md 'pal-review'"
echo ""

echo "5. Environment Validation"
echo "-------------------------"
test_condition "Node.js version >= 16" "node_version=\$(node -v | sed 's/v//g' | cut -d. -f1); [ \$node_version -ge 16 ]"
test_condition "npm installed" "which npm &>/dev/null"
echo ""

echo "======================================="
echo "  Test Results Summary"
echo "======================================="
echo -e "Tests Passed: ${GREEN}$tests_passed${NC}"
echo -e "Tests Failed: ${RED}$tests_failed${NC}"
echo ""

if [ $tests_failed -eq 0 ]; then
    echo -e "${GREEN}🎉 All required tests passed! PAL MCP is properly configured.${NC}"
    echo ""
    echo "You can now use these SuperClaude features:"
    echo "  • Multi-model orchestration with --pal"
    echo "  • Consensus decisions with --consensus"
    echo "  • Production validation with --pal-review"
    echo "  • Deep analysis with --thinkdeep"
    echo ""
    echo "Context-aware model routing enabled:"
    echo "  • Standard ops (≤400K): GPT-5 → Claude Opus 4.1 → GPT-4.1"
    echo "  • Long context (>400K): Gemini-2.5-pro → GPT-4.1 → GPT-5"
    echo ""
    echo "Long context examples:"
    echo "  • --pal-review --extended-context (bulk codebase analysis)"
    echo "  • --thinkdeep --bulk-analysis src/ docs/ (multi-file processing)"
else
    echo -e "${RED}⚠️  Some tests failed. Please review the configuration.${NC}"
    echo ""
    echo "To fix issues:"
    echo "  1. Run: ./scripts/setup_pal_api_keys.sh"
    echo "  2. Restart Claude Desktop"
    echo "  3. Check the configuration files manually"
fi

echo ""
echo "Note: You may need to restart Claude Desktop for changes to take effect."