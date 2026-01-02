# MCP Integration Tests

This directory contains the testing infrastructure for MCP (Model Context Protocol) integration with SuperClaude.

## Architecture

```
tests/mcp/
├── conftest.py                    # FakeMCPServer and fixtures
├── contract_helpers.py            # Schema comparison utilities
├── live_mcp_client.py             # Observable client for live MCP calls
├── test_contract_validation.py    # Schema drift detection tests
├── test_mcp_contracts.py          # MCP contract tests
├── test_pal_response_parsing.py   # PAL response handling tests
├── test_rube_response_parsing.py  # Rube response handling tests
├── fixtures/
│   └── captured/                  # Captured live MCP interactions
└── README.md                      # This file
```

## Testing Tiers

### Tier 1: Unit Tests (Always Run)
Tests that use `FakeMCPServer` with hardcoded responses. No external dependencies.

```bash
pytest tests/mcp/ -m "not live"
```

### Tier 2: Contract Validation (Nightly)
Tests that compare `FakeMCPServer` schemas against live MCP responses to detect drift.

```bash
MCP_LIVE_TESTING_ENABLED=1 pytest tests/mcp/ -m live
```

### Tier 3: Smoke Tests (Nightly CI)
Full integration tests with real MCP tools. See `.github/workflows/agentic-tests-mcp.yml`.

## Key Components

### FakeMCPServer

A deterministic mock server for testing MCP tool integrations without network calls.

```python
from tests.mcp.conftest import FakeMCPServer

# Basic usage
server = FakeMCPServer()
response = server.invoke("mcp__pal__codereview", {"step": "Review", ...})

# Override responses for specific tests
server.set_response("mcp__pal__codereview", FakePALCodeReviewResponse(
    data={"issues_found": [{"severity": "critical", ...}]}
))

# Load from captured fixtures
server = FakeMCPServer.from_fixtures(Path("tests/mcp/fixtures/captured"))
```

### MCPInvocationResult

Structured result type with observability for live MCP calls.

```python
from tests.mcp.live_mcp_client import invoke_real_mcp, FailureCategory

result = invoke_real_mcp("mcp__pal__codereview", request_body)

if result.is_success:
    process(result.response_body)
elif result.is_retryable:
    retry_with_backoff(...)
else:
    handle_permanent_failure(result.error_message)

# Structured logging
log_invocation_result(result)
```

### Contract Validation Helpers

```python
from tests.mcp.contract_helpers import assert_schema_matches, schema_diff

# Assert schemas match (fails on first difference)
assert_schema_matches(fake_response, live_response, allow_extra_keys=True)

# Get all differences for debugging
diffs = schema_diff(fake_response, live_response)
for diff in diffs:
    print(diff)
```

## Fixture Capture Mode

Capture live MCP interactions for fixture generation:

```bash
# Set capture file and enable live testing
export MCP_CAPTURE_FILE=tests/mcp/fixtures/captured/pal_tools.jsonl
export MCP_LIVE_TESTING_ENABLED=1

# Run contract validation tests
pytest tests/mcp/test_contract_validation.py -m live

# Captured fixtures are appended to the JSONL file
```

Captured fixture format:
```json
{
  "tool_name": "mcp__pal__codereview",
  "request": {"step": "Review", "step_number": 1, ...},
  "response": {"success": true, "data": {...}},
  "metadata": {"timestamp": "2024-01-15T...", "latency_ms": 1234.5}
}
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MCP_LIVE_TESTING_ENABLED` | Enable live MCP tests | For live tests |
| `MCP_API_BASE_URL` | HTTP MCP endpoint URL | For HTTP-based MCP |
| `MCP_API_KEY` | API key for MCP auth | For HTTP-based MCP |
| `MCP_CAPTURE_FILE` | Path to capture fixture file | For fixture capture |
| `MCP_REQUEST_TIMEOUT` | Request timeout in seconds (default: 30) | No |

## Failure Categories

The `FailureCategory` enum categorizes MCP call outcomes:

| Category | Description | Retryable |
|----------|-------------|-----------|
| `SUCCESS` | Call succeeded | N/A |
| `NETWORK_ERROR` | DNS/connection failure | Yes |
| `TIMEOUT` | Request timed out | Yes |
| `AUTH_ERROR` | 401/403 response | No |
| `RATE_LIMIT` | 429 response | Yes |
| `SERVER_ERROR` | 5xx response | Yes |
| `CLIENT_ERROR` | 4xx (other) response | No |
| `INVALID_JSON` | Unparseable response | No |
| `NOT_CONFIGURED` | MCP not set up | No |
| `MCP_NOT_AVAILABLE` | No MCP infrastructure | No |

## Adding New MCP Tools

1. Add a response dataclass in `conftest.py`:
   ```python
   @dataclass
   class FakeNewToolResponse(FakeMCPResponse):
       def __post_init__(self):
           if not self.data:
               self.data = {"field": "value", ...}
   ```

2. Register in `FakeMCPServer._setup_default_responses()`:
   ```python
   "mcp__namespace__NEW_TOOL": FakeNewToolResponse(),
   ```

3. Add canonical request in `test_contract_validation.py`:
   ```python
   CANONICAL_REQUESTS = {
       "mcp__namespace__NEW_TOOL": {"param": "value", ...},
   }
   ```

4. Add schema documentation test:
   ```python
   def test_document_new_tool_schema(self, fake_mcp_server):
       response = fake_mcp_server.invoke("mcp__namespace__NEW_TOOL", {...})
       assert isinstance(response["data"]["field"], str)
   ```

## Running Tests

```bash
# All MCP tests (unit only)
pytest tests/mcp/

# With live contract validation
MCP_LIVE_TESTING_ENABLED=1 pytest tests/mcp/ -m live

# With capture mode
MCP_LIVE_TESTING_ENABLED=1 \
MCP_CAPTURE_FILE=tests/mcp/fixtures/captured/session.jsonl \
pytest tests/mcp/test_contract_validation.py -m live

# Specific test classes
pytest tests/mcp/test_contract_validation.py::TestContractHelpers -v
```

## CI Integration

Live MCP tests run nightly via `.github/workflows/agentic-tests-mcp.yml`:

- Runs at 3 AM UTC daily
- Uses GitHub secrets for MCP credentials
- Captures artifacts on failure for debugging
- 20-minute timeout per test suite
