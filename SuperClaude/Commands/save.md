name: save
description: "Session lifecycle management with UnifiedStore-backed persistence"
category: session
complexity: standard
mcp-servers: []
personas: []
---

# /sc:save - Session Context Persistence

## Triggers
- Session completion and project context persistence needs
- Cross-session memory management and checkpoint creation requests
- Project understanding preservation and discovery archival scenarios
- Session lifecycle management and progress tracking requirements

## Usage
```
/sc:save [--type session|learnings|context|all] [--summarize] [--checkpoint]
```

## Behavioral Flow
1. **Analyze**: Examine session progress and identify discoveries worth preserving
2. **Persist**: Save session context and learnings using the UnifiedStore API
3. **Checkpoint**: Create recovery points for complex sessions and progress tracking
4. **Validate**: Ensure session data integrity and cross-session compatibility
5. **Prepare**: Ready session context for seamless continuation in future sessions

Key behaviors:
- UnifiedStore persistence for memory management and cross-session continuity
- Automatic checkpoint creation based on session progress and critical tasks
- Session context preservation with comprehensive discovery and pattern archival
- Cross-session learning with accumulated project insights and technical decisions

## Persistence Layer
- **UnifiedStore**: Lightweight SQLite-backed store for session checkpoints and learnings
- **Memory Operations**: `write_memory`, `read_memory`, and `delete_memory` for session payloads
- **Performance Expectations**: <200ms for typical writes, <1s for checkpoint creation

## Tool Coordination
- **UnifiedStore.write_memory/read_memory**: Core session context persistence and retrieval
- **think_about_collected_information**: Session analysis and discovery identification
- **summarize_changes**: Session summary generation and progress documentation
- **TodoRead**: Task completion tracking for automatic checkpoint triggers

## Key Patterns
- **Session Preservation**: Discovery analysis → memory persistence → checkpoint creation
- **Cross-Session Learning**: Context accumulation → pattern archival → enhanced project understanding
- **Progress Tracking**: Task completion → automatic checkpoints → session continuity
- **Recovery Planning**: State preservation → checkpoint validation → restoration readiness

## Examples

### Basic Session Save
```
/sc:save
# Saves current session discoveries and context to UnifiedStore
# Automatically creates checkpoint if session exceeds 30 minutes
```

### Comprehensive Session Checkpoint
```
/sc:save --type all --checkpoint
# Complete session preservation with recovery checkpoint
# Includes all learnings, context, and progress for session restoration
```

### Session Summary Generation
```
/sc:save --summarize
# Creates session summary with discovery documentation
# Updates cross-session learning patterns and project insights
```

### Discovery-Only Persistence
```
/sc:save --type learnings
# Saves only new patterns and insights discovered during session
# Updates project understanding without full session preservation
```

## Boundaries

**Will:**
- Save session context using UnifiedStore for cross-session persistence
- Create automatic checkpoints based on session progress and task completion
- Preserve discoveries and patterns for enhanced project understanding

**Will Not:**
- Operate without UnifiedStore availability or local storage access
- Save session data without validation and integrity verification
- Override existing session context without proper checkpoint preservation
