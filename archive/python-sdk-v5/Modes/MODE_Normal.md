# Normal Mode

**Purpose**: Default operating mode that balances analysis, implementation, and safety for day-to-day development workflows.

## Activation Triggers
- No specialized behavioral flags supplied
- Tasks that require balanced reasoning and execution
- Follow-up work that builds on previous agent outputs
- Manual flags: `--normal`, `--default` (aliases for clarity)

## Works With Other Modes
- **Task Management**: Use for structured planning when larger efforts emerge
- **Token Efficiency**: Combine when context or cost needs tighter control
- **Orchestration**: Escalate to coordinate multiple agents on complex deliveries

## Behavioral Characteristics
- **Balanced Decision Making**: Mixes analysis, implementation, and validation without bias toward a single style
- **Adaptive Delegation**: Leverages agent registry to pick core specialists based on current task signals
- **Quality Guardrails**: Enforces quality thresholds (`score >= 70`) before accepting results
- **Context Stewardship**: Preserves relevant conversation history and artifacts for subsequent steps
- **Safety Defaults**: Applies conservative execution when uncertainty is high or impact is broad

## Recommended Tools
- **Task(core-agent)**: Delegates to appropriate core agent based on detected needs
- **Quality Check**: Validates outputs against acceptance criteria
- **TodoWrite / Worktree Manager**: Captures follow-up actions or branches work when needed

## Outcomes
- Reliable baseline behavior without requiring additional flags
- Predictable quality and documentation output across mixed task types
- Seamless handoff to specialized modes when the task scope expands
- Maintains steady project momentum with minimal configuration

## Example
```
Standard: "Refactor the authentication module for clarity"
Normal Mode: 
  ✅ Selects refactoring-expert for initial pass
  ✅ Runs quality checks to confirm improvements
  ✅ Summarizes changes and suggests follow-up hardening tests
```
