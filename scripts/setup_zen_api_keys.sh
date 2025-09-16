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
check_api_key "GEMINI_API_KEY"
check_api_key "OPENAI_API_KEY"
check_api_key "ANTHROPIC_API_KEY"
check_api_key "GROK_API_KEY"
check_api_key "OPENROUTER_API_KEY"
echo ""

echo "To obtain API keys, visit:"
echo "---------------------------"
echo "🔷 Gemini:     https://aistudio.google.com/apikey"
echo "🟢 OpenAI:     https://platform.openai.com/api-keys"
echo "🔵 Anthropic:  https://console.anthropic.com/settings/keys"
echo "⚡ Grok (X.AI): https://console.x.ai/"
echo "🌐 OpenRouter: https://openrouter.ai/keys"
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
echo "✅ Settings configured in: ~/.claude/settings.json"
echo "✅ Claude Desktop config: ~/.config/Claude/claude_desktop_config.json"
echo "✅ Zen MCP Server installed: zen-mcp-server-199bio"
echo ""
echo "To test the integration, use these SuperClaude flags:"
echo "  --zen          : Enable multi-model orchestration"
echo "  --consensus    : Get consensus from multiple models"
echo "  --zen-review   : Production validation with multiple models"
echo "  --thinkdeep    : Deep multi-angle analysis"
echo ""
echo "Example: 'Analyze this code --zen'"