# SuperClaude SDK Integration Contract

Developer-facing contract for the Claude Agent SDK integration layer.

## Scope / Non-goals

**Scope:**
- Single command execution with optional SDK path
- Fallback behavior to Skills/Legacy handlers
- Quality scoring and evidence collection
- Agentic loop for iterative improvement

**Non-goals (explicit):**
- Multi-request session continuity (each execution is independent)
- Standalone MCP configuration (relies on Claude Code)
- Token/cost accounting (not exposed in current integration)

## High-level Flow

```
ExecutionFacade.execute(context)
    │
    ├── SDK enabled? Agent eligible?
    │   ├── Yes → SDKExecutor.execute()
    │   │         ├── Success (should_fallback=False) → Return SDK result
    │   │         └── Fallback (should_fallback=True) → Continue to Skills/Legacy
    │   │
    │   └── No → Skip SDK path
    │
    ├── Skills Runtime available?
    │   ├── Yes → Execute via SkillsRuntime
    │   └── No → Continue to Legacy
    │
    └── Legacy handler → Execute via legacy_executor()
```

**Key invariants:**
- Hooks are observers only (no control flow mutation)
- External callers see only `CommandResult`, not internal routing details
- `SDKExecutionResult` carries full attempt metadata for debugging

## Entry Points & Primary APIs

### ExecutionFacade.execute()

```python
async def execute(
    context: CommandContext,
    legacy_executor: Callable | None = None,
    force_sdk: bool = False,
    disable_sdk: bool = False,
) -> dict[str, Any]
```

**Responsibilities:**
- Route between SDK, Skills, and Legacy paths
- Record telemetry events for routing decisions
- Return normalized command output

### SDKExecutor.execute()

```python
async def execute(
    context: CommandContext,
    force_sdk: bool = False,
    disable_sdk: bool = False,
) -> SDKExecutionResult
```

**Guarantees:**
- Never throws exceptions to caller (degrades gracefully)
- Returns `SDKExecutionResult` with `should_fallback` decision
- Collects evidence via hooks when `requires_evidence=True`

### QualityScorer.agentic_loop()

```python
def agentic_loop(
    initial_output: Any,
    context: dict[str, Any],
    improver_func: Callable,
    max_iterations: int | None = None,
    min_improvement: float | None = None,
) -> tuple[Any, QualityAssessment, list[IterationResult]]
```

**Loop contract:**
- Maximum iterations: `MAX_ITERATIONS = 5` (configurable)
- Stagnation detection: `MIN_IMPROVEMENT = 2.0` points
- Oscillation detection: score bouncing between values
- Scorer exceptions: degrade gracefully, never crash

## Data Contracts

### CommandContext (Input)

Required fields:
- `command.name: str` - Command name
- `command.arguments: list[str]` - Command arguments
- `session_id: str` - Correlation ID for telemetry

Optional fields:
- `cwd: str` - Working directory
- `requires_evidence: bool` - Enable evidence collection
- `command.parameters: dict` - Named parameters
- `command.flags: dict` - Boolean flags

### SDKExecutionResult (Internal)

```python
@dataclass
class SDKExecutionResult:
    success: bool                    # Execution completed successfully
    output: dict[str, Any]           # Command output
    should_fallback: bool            # Caller should try Skills/Legacy
    routing_decision: str            # Why SDK was used or not
    fallback_reason: str | None      # Specific fallback reason
    agent_used: str | None           # Agent that executed task
    confidence: float                # Selection confidence (0.0-1.0)
    evidence: dict[str, Any] | None  # Collected execution evidence
    error_type: str | None           # Exception class name
    termination_reason: TerminationReason | None  # Why loop stopped
    iteration_count: int             # Number of iterations (1 = no loop)
```

### TerminationReason (Enum)

```python
class TerminationReason(str, Enum):
    # Success conditions
    THRESHOLD_MET = "threshold_met"      # Quality score met threshold
    SINGLE_ITERATION = "single_iteration" # No loop needed

    # Stop conditions (not failures)
    MAX_ITERATIONS = "max_iterations"    # Hit iteration limit
    STAGNATION = "stagnation"            # Improvement below threshold
    OSCILLATION = "oscillation"          # Score bouncing
    TIMEOUT = "timeout"                  # Wall-clock timeout

    # Error conditions
    SCORER_ERROR = "scorer_error"        # QualityScorer exception
    EXECUTION_ERROR = "execution_error"  # SDK execution failed

    # Fallback conditions
    FALLBACK = "fallback"                # Requested fallback
    SDK_UNAVAILABLE = "sdk_unavailable"  # SDK not installed
```

### Routing Decision Codes

| Code | Meaning |
|------|---------|
| `sdk_executed` | SDK execution completed successfully |
| `sdk_disabled_override` | `disable_sdk=True` override active |
| `sdk_unavailable` | Claude Agent SDK not installed |
| `sdk_not_enabled` | Feature flag disabled |
| `command_not_allowed` | Command not in allowlist |
| `no_selector` | Agent selector not configured |
| `selection_declined` | Agent selection returned `use_sdk=False` |
| `low_confidence` | Confidence below threshold |
| `no_sdk_definition` | Agent has no SDK definition |
| `sdk_error_message` | SDK returned error in stream |
| `sdk_exception` | SDK raised exception |

## Behavioral Guarantees

### Deterministic Selection
- Agent selection is deterministic given same inputs
- Tie-breaking uses stable ordering (agent name)
- Selection context includes: task, command name, cwd

### Loop Termination Guarantees
- **Max iterations**: Hard stop at `MAX_ITERATIONS` (default 5)
- **Stagnation**: Stop if improvement < `MIN_IMPROVEMENT` (default 2.0)
- **Oscillation**: Stop if score bounces between values
- **Timeout**: Wall-clock timeout (best-effort, see below)

### Wall-clock Timeout (Best-Effort)

The agentic loop supports a `timeout_seconds` parameter for wall-clock timeout:

```python
scorer.agentic_loop(
    initial_output=output,
    context=context,
    improver_func=improver,
    timeout_seconds=300.0,  # 5 minute budget
    time_provider=time.monotonic,  # Inject for testing
)
```

**Important limitations:**
- The loop will not **start** new iterations after the budget is exceeded
- The loop **cannot interrupt** a running `evaluate()` or `improver_func()` call
- Overall wall time may exceed `timeout_seconds` if those calls run long
- Use `time_provider` injection for deterministic testing

**Timeout check locations:**
1. Before starting each iteration
2. Immediately after scoring (`evaluate()`)
3. After improver returns (before accepting new output)

**On timeout, the loop:**
- Returns the last safely-scored output (not the just-improved one)
- Records `termination_reason = IterationTermination.TIMEOUT`
- Logs elapsed time and iteration count

### Scorer Safety
- Scorer exceptions never crash the facade
- Invalid scores (None/NaN) treated as low score
- Degrades gracefully to fallback on scorer failure

### Hooks Invariants
- Hooks are observer-only (no prompt/flow mutation)
- Hooks are idempotent (safe to invoke multiple times)
- Hook ordering is stable (CompositeHooks preserves order)

## Fallback Policy

### When `should_fallback=True` is returned:
1. SDK not available or not enabled
2. Command not in allowlist
3. Agent selection declined or low confidence
4. No SDK definition for selected agent
5. SDK execution raised exception
6. SDK returned error message in stream

### What metadata is preserved across fallback:
- `session_id` for correlation
- Routing decision and reason (logged)
- Evidence collected before failure (if any)

## Operational Dependencies

### Runtime Environment
- Runs under Claude Code environment
- MCP server configuration provided by Claude Code (not configured here)
- Requires Python 3.8+ with async support

### Logging/Tracing
- Logger name: `SuperClaude.SDK.*`
- Routing decisions logged at DEBUG level
- Errors logged at WARNING/ERROR level
- Iteration counts and termination reasons in execution events

### Telemetry Events
- `execution.routed` - Routing decision made
- `execution.sdk_routed` - SDK-specific routing
- `execution.completed` - Execution finished

## Testing Guidance

### Integration Test Suites
Located in `tests/sdk/test_integration.py`:

- **Suite A**: Routing & fallback decisions (Facade contract)
- **Suite B**: Agent selection & delegation boundary
- **Suite C**: Agentic loop control (termination + quality)
- **Suite E**: Hooks/evidence correctness

### Stubbing the SDK Client
```python
class MockSDKClient:
    def __init__(self, responses: list[list[dict]]):
        self._responses = responses
        self._call_count = 0
        self._sdk_available = True

    async def execute_with_agent(self, task, context, agent_name, hooks=None):
        messages = self._responses[self._call_count]
        self._call_count += 1
        for msg in messages:
            yield MockMessage(type=msg["type"], content=msg["content"])
```

### Determinism Requirements
- Mock RNG if any randomness in selection
- Use scripted responses for SDK client
- Fix time provider for timeout tests

## Future Hooks (Deferred Phase 5)

Reserved extension points for future session/MCP features:

```python
# SDKExecutionResult (optional future fields)
session_id: str | None           # SDK session ID
mcp_context: dict | None         # MCP server state
usage_metadata: dict | None      # Token/cost tracking

# ExecutionContext (optional future fields)
resume_session: str | None       # Session to resume
mcp_servers: list[str] | None    # Required MCP servers
```

These fields are NOT implemented - this documents where they would attach.

## How to Add a New Agent

1. Create agent definition in `SuperClaude/Agents/Extended/`
2. Ensure `AgentToSDKAdapter` can convert it (check `adapter.py`)
3. Register in `AgentRegistry` (auto-discovered from markdown)
4. Verify selection via `selector.select_for_sdk()`
5. Add test case in `tests/sdk/test_selector_integration.py`

## How to Add a New Hook

1. Create hook class extending base in `SDK/hooks.py`
2. Implement required methods (`on_tool_start`, `on_tool_end`, etc.)
3. Register in `CompositeHooks` via `create_quality_hooks()`
4. Add test case verifying observer invariants
5. Document any new evidence fields collected
