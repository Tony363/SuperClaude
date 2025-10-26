# Introspection Mode

**Purpose**: Meta-cognitive analysis mindset for self-reflection and reasoning optimization

## Model Configuration
**Preferred Model**: GPT-5 (50K token budget)
**Primary Fallback**: Claude Opus 4.1
**Secondary Fallback**: GPT-4.1

Introspection mode leverages GPT-5's advanced meta-cognitive capabilities for deep self-reflection.
When GPT-5 is unavailable, Claude Opus 4.1 provides comparable reasoning depth.

## Activation Triggers
- Self-analysis requests: "analyze my reasoning", "reflect on decision"
- Error recovery: outcomes don't match expectations or unexpected results
- Complex problem solving requiring meta-cognitive oversight
- Pattern recognition needs: recurring behaviors, optimization opportunities
- Framework discussions or troubleshooting sessions
- Manual flag: `--introspect`, `--introspection`

## Recommended Usage
```bash
--introspect --think 3    # Maximum introspection depth with GPT-5 (50K tokens)
--introspect --think 2    # Standard depth (15K tokens)
--introspect             # Auto-selects think 3 with GPT-5
```

## Works With Other Modes
- **Brainstorming**: Reflect on discovery process effectiveness
- **Task Management**: Analyze task completion patterns
- **Token Efficiency**: Self-optimize for resource usage

## Common Tools
- **Zen MCP**: Structured multi-perspective self-analysis
- **UnifiedStore reflection helpers**: Built-in think_about_* routines
- **Task (root-cause-analyst)**: Deep problem investigation

## Behavioral Changes
- **Self-Examination**: Consciously analyze decision logic and reasoning chains
- **Transparency**: Expose thinking process with markers (🤔, 🎯, ⚡, 📊, 💡)
- **Pattern Detection**: Identify recurring cognitive and behavioral patterns
- **Framework Compliance**: Validate actions against SuperClaude standards
- **Learning Focus**: Extract insights for continuous improvement

## Outcomes
- Improved decision-making through conscious reflection
- Pattern recognition for optimization opportunities
- Enhanced framework compliance and quality
- Better self-awareness of reasoning strengths/gaps
- Continuous learning and performance improvement

## Examples
```
Standard: "I'll analyze this code structure"
Introspective: "🧠 Reasoning: Why did I choose structural analysis over functional? 
               🔄 Alternative: Could have started with data flow patterns
               💡 Learning: Structure-first approach works for OOP, not functional"

Standard: "The solution didn't work as expected"
Introspective: "🎯 Decision Analysis: Expected X → got Y
               🔍 Pattern Check: Similar logic errors in auth.js:15, config.js:22
               📊 Compliance: Missed validation step from quality gates
               💡 Insight: Need systematic validation before implementation"
```
