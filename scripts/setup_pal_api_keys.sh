#!/bin/bash

# Zen MCP API Keys Setup Script
# This script helps set up the necessary API keys for Zen MCP multi-model orchestration

echo "==================================="
echo "  Zen MCP API Keys Setup"
echo "==================================="
echo ""

# Function to check if API key is already set
check_api_key() {
    local key_name=$1
    if [ -n "${!key_name}" ]; then
        echo "✅ $key_name is already set"
        return 0
    else
        echo "❌ $key_name is not set"
        return 1
    fi
}

# Function to add API key to shell profile
add_to_profile() {
    local key_name=$1
    local key_value=$2
    local shell_profile=""
    
    # Determine shell profile file
    if [ -n "$BASH_VERSION" ]; then
        shell_profile="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        shell_profile="$HOME/.zshrc"
    else
        shell_profile="$HOME/.profile"
    fi
    
    # Add export statement if not already present
    if ! grep -q "export $key_name=" "$shell_profile" 2>/dev/null; then
        echo "export $key_name=\"$key_value\"" >> "$shell_profile"
        echo "Added $key_name to $shell_profile"
    else
        echo "$key_name already exists in $shell_profile"
    fi
}

echo "Current API Key Status:"
echo "-----------------------"
echo "🔴 CRITICAL for long context operations (>400K tokens, bulk analysis):"
check_api_key "GEMINI_API_KEY"
echo ""
echo "🟡 ESSENTIAL for standard operations:"
check_api_key "OPENAI_API_KEY"
check_api_key "ANTHROPIC_API_KEY"
echo ""
echo "🟢 OPTIONAL for enhanced capabilities:"
check_api_key "GROK_API_KEY"
check_api_key "OPENROUTER_API_KEY"
echo ""

echo "To obtain API keys, visit:"
echo "---------------------------"
echo "🔷 Gemini (2M context):     https://aistudio.google.com/apikey"
echo "🟢 OpenAI (GPT-5):          https://platform.openai.com/api-keys"
echo "🔵 Anthropic (Claude):      https://console.anthropic.com/settings/keys"
echo "⚡ Grok (X.AI):             https://console.x.ai/"
echo "🌐 OpenRouter:              https://openrouter.ai/keys"
echo ""
echo "⚠️  NOTE: Gemini-2.5-pro is now used for ALL long context operations"
echo "   including bulk file analysis, large codebase reviews, and"
echo "   extended documentation processing (>400K tokens)."
echo ""

# Interactive setup for missing keys
echo "Would you like to set up missing API keys now? (y/n)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo ""
    
    # ANTHROPIC_API_KEY
    if ! check_api_key "ANTHROPIC_API_KEY" > /dev/null 2>&1; then
        echo "Enter your Anthropic API key (or press Enter to skip):"
        read -r anthropic_key
        if [ -n "$anthropic_key" ]; then
            add_to_profile "ANTHROPIC_API_KEY" "$anthropic_key"
            export ANTHROPIC_API_KEY="$anthropic_key"
        fi
    fi
    
    # GROK_API_KEY
    if ! check_api_key "GROK_API_KEY" > /dev/null 2>&1; then
        echo "Enter your Grok (X.AI) API key (or press Enter to skip):"
        read -r grok_key
        if [ -n "$grok_key" ]; then
            add_to_profile "GROK_API_KEY" "$grok_key"
            export GROK_API_KEY="$grok_key"
        fi
    fi
    
    # OPENROUTER_API_KEY
    if ! check_api_key "OPENROUTER_API_KEY" > /dev/null 2>&1; then
        echo "Enter your OpenRouter API key (or press Enter to skip):"
        read -r openrouter_key
        if [ -n "$openrouter_key" ]; then
            add_to_profile "OPENROUTER_API_KEY" "$openrouter_key"
            export OPENROUTER_API_KEY="$openrouter_key"
        fi
    fi
    
    echo ""
    echo "API keys have been configured!"
    echo "Please run: source ~/.bashrc (or ~/.zshrc) to load the new environment variables"
    echo "Or restart your terminal/Claude Desktop for changes to take effect."
else
    echo ""
    echo "You can run this script again later to set up API keys."
fi

echo ""
echo "==================================="
echo "  Configuration Summary"
echo "==================================="
echo ""
echo "📝 API keys have been set in environment variables"
echo "📝 You may need to manually configure:"
echo "   - ~/.claude/settings.json (if using Claude settings)"
echo "   - ~/.config/Claude/claude_desktop_config.json (for MCP servers)"
echo ""
echo "⚠️  NOTE: Zen MCP Server integration is planned for future versions"
echo ""
echo "These features are planned for future releases:"
echo "  --zen          : Enable multi-model orchestration"
echo "  --consensus    : Get consensus from multiple models"
echo "  --zen-review   : Production validation with multiple models"
echo "  --thinkdeep    : Deep multi-angle analysis"
echo ""
echo "Context-aware model routing:"
echo "  Standard ops (≤400K): GPT-5 → Claude Opus 4.1 → GPT-4.1"
echo "  Long context (>400K): Gemini-2.5-pro → GPT-4.1 → GPT-5"
echo ""
echo "Long context examples:"
echo "  'Analyze entire codebase --zen-review --extended-context'"
echo "  'Review all files --thinkdeep --bulk-analysis src/ docs/'"