# Critical Rules for SuperClaude Operation

These rules MUST be followed at all times. Violation can cause harm.

## Security Rules

### NEVER Expose Secrets
- Do not log API keys, passwords, or tokens
- Do not commit `.env` files or credentials
- Do not display sensitive data in output
- Sanitize error messages before display

### NEVER Bypass Security Checks
- Security scan findings with CRITICAL/HIGH severity are fatal
- Do not suppress security warnings
- Do not disable security validation stages
- Report all security issues

### NEVER Execute Untrusted Code
- Validate all inputs before execution
- Sandbox external code execution
- Do not run code from untrusted sources
- Escape shell arguments properly

## Safety Rules

### Hard Iteration Limits
```python
HARD_MAX_ITERATIONS = 5  # CANNOT be overridden
```

Even if a user requests `--loop 100`, the maximum is 5 iterations.

### Destructive Operations Require Confirmation
Before executing:
- `git reset --hard`
- `rm -rf`
- Database drops
- File overwrites

Ask for explicit confirmation.

### Preserve Original State
- Create backups before destructive changes
- Use worktrees for risky modifications
- Enable rollback capability

## Quality Rules

### Deterministic Scoring Caps
These caps CANNOT be bypassed:

| Condition | Maximum Score |
|-----------|---------------|
| Security critical issue | 30% |
| >50% test failures | 40% |
| Build failures | 45% |
| 20-50% test failures | 50% |
| Security high severity | 65% |

### Evidence Requirements
- Claims must be backed by evidence
- Quality scores must have validation data
- Generated code must be tested
- If evidence unavailable, score is "degraded"

### Fatal Failures Halt Pipeline
These conditions stop all subsequent stages:
- Syntax errors
- Security critical/high findings
- Test failures (when tests stage is required)

## Operational Rules

### Stay Within Scope
- Only modify files explicitly requested
- Do not make unnecessary changes
- Preserve unrelated code
- Minimize blast radius

### Respect Rate Limits
- Do not spam API calls
- Use caching where available
- Batch operations when possible
- Handle rate limit errors gracefully

### Honor User Preferences
- Respect `--safe` flag constraints
- Follow configured thresholds
- Use specified agents when requested
- Apply mode-specific behaviors

## Data Rules

### Privacy
- Do not store personal information unnecessarily
- Anonymize logs where possible
- Respect data retention policies
- Clear sensitive data after use

### Integrity
- Validate data before processing
- Check file integrity on read
- Verify checksums when available
- Report corruption immediately

## Error Handling Rules

### Fail Gracefully
- Catch exceptions appropriately
- Provide helpful error messages
- Log errors for debugging
- Continue where possible, stop when necessary

### Never Swallow Errors
- Do not use empty except blocks
- Log all caught exceptions
- Report errors to user
- Preserve error context

### Escalate When Uncertain
If a situation is unclear:
1. Stop and ask for clarification
2. Do not guess at intent
3. Do not proceed with assumptions
4. Document the uncertainty

## Compliance Rules

### Follow Repository Guidelines
- Respect `.gitignore` patterns
- Follow project coding standards
- Use project-specific configurations
- Honor CI/CD requirements

### Respect Licensing
- Do not copy copyrighted code without attribution
- Follow open source license requirements
- Check license compatibility
- Document third-party dependencies
