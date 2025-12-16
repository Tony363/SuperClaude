"""SuperClaude Framework MCP Server Reference.

This module documents the native MCP tools available through Claude Code.
SuperClaude no longer uses custom HTTP wrappers - all MCP functionality
is accessed through Claude Code's native tool invocation.

Native MCP Tools Available:
---------------------------

Rube MCP (mcp__rube__*):
    - RUBE_SEARCH_TOOLS: Discover available tools and integrations
    - RUBE_MULTI_EXECUTE_TOOL: Execute tools in parallel
    - RUBE_CREATE_PLAN: Create execution plans for workflows
    - RUBE_MANAGE_CONNECTIONS: Manage app connections
    - RUBE_REMOTE_WORKBENCH: Execute Python in remote sandbox
    - RUBE_REMOTE_BASH_TOOL: Execute bash in remote sandbox
    - RUBE_FIND_RECIPE: Find recipes by natural language
    - RUBE_EXECUTE_RECIPE: Execute saved recipes
    - RUBE_MANAGE_RECIPE_SCHEDULE: Manage scheduled recipe runs

PAL MCP (mcp__pal__*):
    - chat: General chat and collaborative thinking
    - thinkdeep: Multi-stage investigation and reasoning
    - planner: Interactive sequential planning
    - consensus: Multi-model consensus building
    - codereview: Systematic code review
    - precommit: Git change validation
    - debug: Systematic debugging and root cause analysis
    - challenge: Critical thinking and analysis
    - apilookup: Current API/SDK documentation lookup
    - listmodels: List available AI models
    - clink: Link to external AI CLIs (Gemini, Codex, etc.)

Usage:
------
These tools are invoked directly by Claude Code's tool system.
No Python wrapper code is needed - just call the tools directly
in your prompts or command implementations.

Example in documentation/prompts:
    "Use mcp__rube__RUBE_SEARCH_TOOLS to find available integrations"
    "Use mcp__pal__codereview for code review tasks"
"""

from __future__ import annotations

__version__ = "6.0.0"

# Native MCP tool namespaces (for documentation/reference only)
RUBE_TOOLS = [
    "RUBE_SEARCH_TOOLS",
    "RUBE_MULTI_EXECUTE_TOOL",
    "RUBE_CREATE_PLAN",
    "RUBE_MANAGE_CONNECTIONS",
    "RUBE_REMOTE_WORKBENCH",
    "RUBE_REMOTE_BASH_TOOL",
    "RUBE_FIND_RECIPE",
    "RUBE_EXECUTE_RECIPE",
    "RUBE_GET_RECIPE_DETAILS",
    "RUBE_GET_TOOL_SCHEMAS",
    "RUBE_MANAGE_RECIPE_SCHEDULE",
    "RUBE_CREATE_UPDATE_RECIPE",
]

PAL_TOOLS = [
    "chat",
    "thinkdeep",
    "planner",
    "consensus",
    "codereview",
    "precommit",
    "debug",
    "challenge",
    "apilookup",
    "listmodels",
    "version",
    "clink",
]

__all__ = [
    "RUBE_TOOLS",
    "PAL_TOOLS",
]
