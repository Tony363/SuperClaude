name: reflect
description: "Task reflection and validation using built-in analysis and UnifiedStore context"
category: special
complexity: standard
mcp-servers: []
personas: []
---

# /sc:reflect - Task Reflection and Validation

## Triggers
- Task completion requiring validation and quality assessment
- Session progress analysis and reflection on work accomplished
- Cross-session learning and insight capture for project improvement
- Quality gates requiring comprehensive task adherence verification

## Usage
```
/sc:reflect [--type task|session|completion] [--analyze] [--validate]
```

## Behavioral Flow
1. **Analyze**: Examine current task state and session progress using native reflection tools
2. **Validate**: Assess task adherence, completion quality, and requirement fulfillment
3. **Reflect**: Apply deep analysis of collected information and session insights
4. **Document**: Update session metadata and capture learning insights
5. **Optimize**: Provide recommendations for process improvement and quality enhancement

Key behaviors:
- Built-in reflection heuristics for comprehensive analysis and task validation
- Bridge between TodoWrite patterns and native reflection capabilities
- Session lifecycle integration with UnifiedStore persistence and learning capture
- Performance expectations: <200ms core reflection and validation
## Persistence Layer
- **UnifiedStore**: Used for reflection analysis, task validation, and session metadata
- **Reflection Tools**: think_about_task_adherence, think_about_collected_information, think_about_whether_you_are_done
- **Memory Operations**: Cross-session persistence with UnifiedStore read/write/list helpers
- **Performance Critical**: <200ms for core reflection operations, <1s for checkpoint creation

## Tool Coordination
- **TodoRead/TodoWrite**: Bridge between traditional task management and advanced reflection analysis
- **think_about_task_adherence**: Validates current approach against project goals and session objectives
- **think_about_collected_information**: Analyzes session work and information gathering completeness
- **think_about_whether_you_are_done**: Evaluates task completion criteria and remaining work identification
- **UnifiedStore**: Session metadata updates and cross-session learning capture

## Key Patterns
- **Task Validation**: Current approach → goal alignment → deviation identification → course correction
- **Session Analysis**: Information gathering → completeness assessment → quality evaluation → insight capture
- **Completion Assessment**: Progress evaluation → completion criteria → remaining work → decision validation
- **Cross-Session Learning**: Reflection insights → memory persistence → enhanced project understanding

## Examples

### Task Adherence Reflection
```
/sc:reflect --type task --analyze
# Validates current approach against project goals
# Identifies deviations and provides course correction recommendations
```

### Session Progress Analysis
```
/sc:reflect --type session --validate
# Comprehensive analysis of session work and information gathering
# Quality assessment and gap identification for project improvement
```

### Completion Validation
```
/sc:reflect --type completion
# Evaluates task completion criteria against actual progress
# Determines readiness for task completion and identifies remaining blockers
```

## Boundaries

**Will:**
- Perform comprehensive task reflection and validation using built-in analysis tools
- Bridge TodoWrite patterns with advanced reflection capabilities for enhanced task management
- Provide cross-session learning capture and session lifecycle integration

**Will Not:**
- Operate without UnifiedStore accessibility for session data
- Override task completion decisions without proper adherence and quality validation
- Bypass session integrity checks and cross-session persistence requirements
