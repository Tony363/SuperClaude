#!/bin/bash

# Zen MCP Integration Test Script
# Tests the configuration and integration of Zen MCP with SuperClaude Framework

echo "======================================="
echo "  Zen MCP Integration Test"
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
test_condition "settings.json has zen config" "check_file_content ~/.claude/settings.json 'ZEN_MCP'"
test_condition "Claude Desktop config exists" "[ -f ~/.config/Claude/claude_desktop_config.json ]"
test_condition "Desktop config has zen-mcp" "check_file_content ~/.config/Claude/claude_desktop_config.json 'zen-mcp'"
echo ""

echo "2. API Keys"
echo "-----------"
test_condition "GEMINI_API_KEY set" "[ -n \"\$GEMINI_API_KEY\" ]"
test_condition "OPENAI_API_KEY set" "[ -n \"\$OPENAI_API_KEY\" ]"

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

echo "3. Zen MCP Server Installation"
echo "-------------------------------"
test_condition "zen-mcp-server directory exists" "[ -d ~/.zen-mcp-server ]"
test_condition "zen server.py exists" "[ -f ~/.zen-mcp-server/server.py ]"
test_condition "zen virtual environment exists" "[ -d ~/.zen-mcp-server/.zen_venv ]"
echo ""

echo "4. SuperClaude Framework Integration"
echo "-------------------------------------"
test_condition "FLAGS.md exists" "[ -f ~/.claude/FLAGS.md ]"
test_condition "FLAGS.md contains --zen flag" "check_file_content ~/.claude/FLAGS.md 'zen'"
test_condition "FLAGS.md contains --consensus" "check_file_content ~/.claude/FLAGS.md 'consensus'"
test_condition "FLAGS.md contains --zen-review" "check_file_content ~/.claude/FLAGS.md 'zen-review'"
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
    echo -e "${GREEN}🎉 All required tests passed! Zen MCP is properly configured.${NC}"
    echo ""
    echo "You can now use these SuperClaude features:"
    echo "  • Multi-model orchestration with --zen"
    echo "  • Consensus decisions with --consensus"
    echo "  • Production validation with --zen-review"
    echo "  • Deep analysis with --thinkdeep"
else
    echo -e "${RED}⚠️  Some tests failed. Please review the configuration.${NC}"
    echo ""
    echo "To fix issues:"
    echo "  1. Run: ./scripts/setup_zen_api_keys.sh"
    echo "  2. Restart Claude Desktop"
    echo "  3. Check the configuration files manually"
fi

echo ""
echo "Note: You may need to restart Claude Desktop for changes to take effect."