# Recommended Practices for SuperClaude

These are best practices that improve outcomes. They are not mandatory but strongly encouraged.

## Workflow Practices

### Plan Before Acting
1. Read and understand the request fully
2. Identify the best agent for the task
3. Consider edge cases and risks
4. Outline the approach
5. Then execute

### Use TodoWrite for Complex Tasks
When a task has 3+ steps:
- Create a todo list
- Mark items as in_progress when starting
- Mark items as completed when done
- Update the list as you discover new work

### Iterate with the Loop Flag
For quality-sensitive work:
```bash
/sc:implement --loop 3 "feature description"
```

This enables automatic iteration until quality threshold is met.

### Request PAL Review for Critical Changes
```bash
/sc:implement --pal-review "security-sensitive change"
```

External code review catches issues you might miss.

## Code Quality Practices

### Test Your Changes
Always run tests after implementation:
```bash
/sc:test --coverage
```

### Run Full Validation
For important changes, run the complete validation pipeline:
- Syntax check
- Security scan
- Style/lint check
- Tests
- Type checking

### Document Significant Decisions
Use `/sc:document` to capture:
- Why a particular approach was chosen
- Trade-offs considered
- Known limitations

## Agent Selection Practices

### Let the System Choose
The agent selector usually picks well based on:
- Task context
- File patterns
- Keywords in the request

### Override When Specific
If you know exactly which expert is needed:
```bash
/sc:implement --agent=security-engineer "Add auth"
```

### Use Consensus for Critical Decisions
For architectural or security decisions:
```bash
/sc:design --consensus "API architecture"
```

## Communication Practices

### Be Specific in Requests
Good: "Add input validation for the email field in UserForm"
Bad: "Fix the form"

### Provide Context
Include relevant information:
- What's the current behavior?
- What's the expected behavior?
- Are there constraints?

### Ask Questions Early
If requirements are unclear:
- Ask before implementing
- Validate assumptions
- Confirm edge cases

## Performance Practices

### Use Appropriate Thinking Depth
- `--think 1`: Quick, simple tasks
- `--think 2`: Balanced (default)
- `--think 3`: Complex analysis

### Enable Token Efficiency When Needed
When context is limited:
```bash
/sc:implement --uc "feature"
```

### Batch Related Operations
Instead of:
```bash
/sc:analyze file1.py
/sc:analyze file2.py
/sc:analyze file3.py
```

Use:
```bash
/sc:analyze src/
```

## Error Recovery Practices

### Check Termination Reasons
When a loop terminates, check why:
- QUALITY_MET: Success
- OSCILLATION: Conflicting improvements
- STAGNATION: No progress
- MAX_ITERATIONS: Hit limit

### Adjust Strategy on Failure
If initial approach fails:
1. Review the feedback
2. Try a different agent
3. Break into smaller steps
4. Ask for clarification

### Use Safe Mode for Uncertainty
When unsure:
```bash
/sc:implement --safe "risky change"
```

## Maintenance Practices

### Keep Documentation Updated
After significant changes:
```bash
/sc:document --readme
```

### Review Quality Metrics
Check `.superclaude_metrics/` for:
- Quality trends
- Common issues
- Performance data

### Clean Up
- Remove generated artifacts when done
- Clear stale worktrees
- Archive old evidence

## Collaboration Practices

### Provide Clear Summaries
After completing work:
- What was done
- What was changed
- What to verify

### Flag Concerns
If you notice:
- Potential issues
- Technical debt
- Security concerns

Report them clearly.

### Enable Future Maintenance
- Write self-documenting code
- Add helpful comments for complex logic
- Update relevant documentation
