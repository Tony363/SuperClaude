# SuperClaude Entry Point - Optimized

This file serves as the optimized entry point for the SuperClaude framework.
It uses a modular loading system to stay under the 40KB performance threshold.

## 🚀 Core Configuration (Always Loaded)

The essential components are loaded from the optimized core:

@CLAUDE_CORE.md

## 📦 Extended Components (Load On-Demand)

Additional framework components load automatically when needed.
See @CLAUDE_EXTENDED.md for the full component list and triggers.

## 💡 Quick Reference

### Essential Commands
- `--brainstorm` → Interactive discovery mode
- `--delegate` → Auto-select best agent for task
- `--loop` → Quality-driven iteration
- `--think` → Structured analysis
- `--task-manage` → Multi-step operations
- `--uc` → Ultra-compressed output

### Component Loading
Components load automatically based on usage:
- Using `Task()` or `--delegate` → Loads agent framework
- Using mode flags → Loads relevant behavioral modes
- Complex operations → Loads workflows and patterns
- MCP server usage → Loads relevant documentation

## 🎯 Performance Optimization

This configuration uses intelligent conditional loading:
- **Baseline**: ~27KB (essential components only)
- **On-Demand**: Additional components load as needed
- **Full Access**: All features remain available
- **Performance**: Eliminates the >40KB warning

## 📚 Documentation Structure

- **CLAUDE_CORE.md**: Essential components (always loaded)
- **CLAUDE_EXTENDED.md**: Full component list (reference)
- **Individual components**: Load automatically when triggered

---
*SuperClaude Framework v4.0.8 - Performance Optimized*
*Using intelligent conditional loading for optimal performance*