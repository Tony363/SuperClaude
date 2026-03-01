---
name: sc-log-fix
description: Analyze application logs, identify errors, perform root cause analysis, and interactively fix issues with a learned knowledge base. Use when debugging from logs, triaging errors, or fixing recurring issues.
---

# Log-Fix: Iterative Bug Fixing from Log Analysis

Analyze logs from multiple sources, identify errors, perform root cause analysis, and interactively fix issues with pattern learning.

## Quick Start

```bash
# Analyze recent errors from all log sources
/sc:log-fix

# Filter by time and severity
/sc:log-fix --time 1h --level ERROR

# Target specific log source
/sc:log-fix --source backend --component app.services

# Trace a specific request
/sc:log-fix --request-id abc-123-def

# Dry run - analyze without fixing
/sc:log-fix --dry-run
```

## Behavioral Flow

1. **Discover** - Detect available log sources (files, docker, systemd)
2. **Load Knowledge** - Check for learned patterns from previous fixes
3. **Collect** - Parse and normalize logs from detected sources
4. **Triage** - Cluster errors, rank by severity, match known patterns
5. **Analyze** - Root cause analysis with stack traces and code inspection
6. **Fix** - Interactive fix loop with user approval
7. **Learn** - Save successful fix patterns to knowledge base
8. **Report** - Summary of session with remaining issues

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--time` | string | 1h | Time range: `30m`, `1h`, `1d`, `7d` |
| `--source` | string | all | Log source: `backend`, `frontend`, `docker`, `all` |
| `--level` | string | ERROR | Minimum severity: `ERROR`, `WARNING`, `all` |
| `--component` | string | - | Filter by logger/module name |
| `--request-id` | string | - | Trace specific request across logs |
| `--dry-run` | bool | false | Analyze and report without applying fixes |
| `--fix` | bool | true | Enable interactive fix loop |

## Phase 0: Log Source Discovery

Auto-detect all available log sources before analysis.

### Detection Strategy

| Source | Detection Method | Common Locations |
|--------|-----------------|------------------|
| File logs | Glob for `logs/**/*.log`, `*.log` | `logs/`, `var/log/` |
| Docker | Check `docker compose ps` | `docker-compose.yml` |
| Systemd | Check `journalctl` availability | System services |
| PM2 | Check `pm2 list` | Node.js apps |

### Log Format Detection

Auto-detect log format:
- **JSON** (structured) - Parse with `jq`
- **Text** (unstructured) - Parse with regex patterns
- **Combined** (nginx/apache style) - Parse with format-specific regex

```bash
# Detect format by reading first line
head -1 logs/app.log | python3 -c "import sys,json; json.loads(sys.stdin.read()); print('json')" 2>/dev/null || echo "text"
```

## Phase 1: Knowledge Loading

Load historical fix knowledge for enhanced analysis.

### Knowledge File Structure

```json
{
  "version": "1.0",
  "error_patterns": [
    {
      "id": "pattern-001",
      "signature": {
        "message_pattern": "Connection refused.*port \\d+",
        "component": "app.services.database",
        "exception_type": "ConnectionError"
      },
      "fixes": [{
        "description": "Check database is running, verify connection string",
        "file_changed": "src/config.py",
        "validation_command": "pytest tests/test_db.py -v",
        "success_count": 3,
        "confidence": 0.9
      }]
    }
  ],
  "component_knowledge": {},
  "metadata": {
    "total_fixes": 0,
    "updated_at": null
  }
}
```

**Location**: `.claude/knowledge/log-fix-knowledge.json`

When knowledge is loaded:
- **Triage**: Show "Known issue" badge for previously seen errors
- **Root Cause**: Suggest fixes with historical success rates
- **Fix Loop**: Offer one-click application of proven fixes

## Phase 2: Triage and Clustering

### Incident Clustering

Group by:
1. Same error type (identical/similar messages)
2. Same component (logger/service name)
3. Same request (request_id correlation)
4. Same time window (errors within 5s)

### Severity Ranking

| Priority | Criteria |
|----------|----------|
| P0 | Stack trace, service crash, database errors |
| P1 | ERROR level, API failures, auth issues |
| P2 | WARNING level, deprecation, performance |
| P3 | Informational, cleanup suggestions |

### Triage Summary Output

```
## Error Triage Summary

**Time Range**: [start] to [end]
**Total Errors**: N | **Unique Types**: M | **Known Patterns**: K

### Top Issues by Frequency

| # | Count | Component | Error Pattern | Priority | Historical |
|---|-------|-----------|---------------|----------|------------|
| 1 | 15 | app.services.api | Connection timeout | P1 | Known: 3 fixes, 90% |
| 2 | 8 | app.models | Validation failed | P1 | New pattern |
```

## Phase 3: Root Cause Analysis

For each incident cluster:

1. **Stack Trace Analysis** - Extract file paths, identify failing line, map to components
2. **Log Correlation** - Follow request_id across services
3. **Pattern Matching** - Check knowledge base, then use code-level analysis
4. **Code Inspection** - Read relevant source files, identify the bug

### Root Cause Output

```
## Root Cause: [Error Type]

**Occurrences**: N | **Component**: [logger]

### Error Details
[Full error and stack trace]

### Relevant Code
**File**: `src/services/api.py:145`
[Code context with highlighted line]

### Probable Cause
[Analysis explaining why the error occurs]

### Suggested Fix
[Specific code change with diff preview]
```

## Phase 4: Interactive Fix Loop

### Fix Workflow

1. **Present** - Show error, root cause, affected files
2. **Show diff** - Display exact code changes proposed
3. **Ask permission** - User approves, skips, or modifies
4. **Apply if approved** - Use Edit tool
5. **Validate** - Run relevant tests
6. **Learn** - Offer to save pattern to knowledge base

### User Options

| Action | Description |
|--------|-------------|
| Apply | Apply the proposed fix |
| Skip | Skip this issue, move to next |
| Edit | Modify the proposed fix before applying |
| Test first | Write a test before fixing (invoke /sc:tdd) |
| Details | Show more context about the error |
| Quit | Exit fix loop |

### Validation After Fix

| Fix Type | Validation |
|----------|------------|
| Python code | `pytest -k "test_function" -v` |
| JavaScript | `npm test -- --testPathPattern=file` |
| Config | Restart and verify health |
| Database | Run migrations |

## Phase 5: Knowledge Learning

After a successful fix, offer to save the pattern:

1. **Extract error signature** - Convert specific values to regex patterns
2. **Record fix details** - What changed, where, validation command
3. **Update knowledge file** - Append or update existing pattern
4. **Report confidence** - Initial confidence 1.0, adjusted over time

### Learning Prompt

```
Fix applied and validated!

Save this pattern for future similar errors?
  [Y] Yes, save pattern and fix
  [n] No, this was a one-off fix
  [e] Yes, but let me edit the description first
```

## Phase 6: Session Report

```
## Log-Fix Session Summary

**Logs Analyzed**: [sources] | **Time Range**: [range]
**Errors Found**: N | **Unique Issues**: M

### Issues Addressed

| # | Component | Issue | Status | Action |
|---|-----------|-------|--------|--------|
| 1 | app.services | Connection timeout | FIXED | Added retry config |
| 2 | app.models | Validation error | SKIPPED | User deferred |

### Files Modified
- src/services/api.py
- src/config.py

### Patterns Learned
- 1 new pattern saved to knowledge base

### Next Steps
- Run `/sc:pr-check` to validate all changes
- Consider `/sc:tdd` for issues without test coverage
```

## MCP Integration

### PAL MCP (Debugging & Analysis)

| Tool | When to Use | Purpose |
|------|-------------|---------|
| `mcp__pal__debug` | Complex bugs | Multi-stage root cause analysis |
| `mcp__pal__thinkdeep` | Unclear patterns | Deep investigation of recurring issues |
| `mcp__pal__codereview` | Fix validation | Review proposed fix quality |
| `mcp__pal__apilookup` | Dependency errors | Get current docs for version issues |

### PAL Usage Patterns

```bash
# Debug complex error pattern
mcp__pal__debug(
    step="Investigating recurring connection timeout in API layer",
    hypothesis="Connection pool exhaustion under load",
    confidence="medium",
    relevant_files=["src/services/api.py", "src/config.py"]
)

# Deep analysis of unclear pattern
mcp__pal__thinkdeep(
    step="Why do these errors only occur during peak hours?",
    hypothesis="Race condition in connection pooling",
    confidence="low"
)
```

### Rube MCP (Notifications)

| Tool | When to Use | Purpose |
|------|-------------|---------|
| `mcp__rube__RUBE_SEARCH_TOOLS` | External logging | Find logging service tools |
| `mcp__rube__RUBE_MULTI_EXECUTE_TOOL` | Notifications | Post fix summary to Slack/Jira |

## Tool Coordination

- **Bash** - Log parsing (jq, grep), test execution, docker commands
- **Glob** - Log file discovery
- **Grep** - Error pattern search, request ID tracing
- **Read** - Source code inspection, log file reading
- **Edit** - Apply code fixes
- **Write** - Knowledge base updates, session reports

## Related Skills

- `/sc:tdd` - Write tests before fixing (TDD approach)
- `/sc:pr-check` - Validate all changes before PR
- `/sc:analyze` - Deeper code analysis when root cause is unclear
