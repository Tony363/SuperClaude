"""
Client for making live calls to the real MCP service for testing purposes.

This client is designed for observability, returning a structured result object
that categorizes the outcome of the call and includes relevant data for debugging.

Usage:
    Set environment variables:
    - MCP_LIVE_TESTING_ENABLED=1
    - MCP_API_KEY=your_key (if using HTTP-based MCP)

    result = invoke_real_mcp("mcp__pal__codereview", {"files": ["main.py"]})
    if result.category == FailureCategory.SUCCESS:
        process(result.response_body)

Capture Mode:
    To capture live interactions for fixture generation:
    - MCP_CAPTURE_FILE=/path/to/capture.jsonl

    Each successful interaction is appended as a JSON line containing:
    - tool_name: The MCP tool invoked
    - request: The request body sent
    - response: The response received
    - metadata: Timestamp and latency
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Configuration from environment
MCP_REQUEST_TIMEOUT_SECONDS = float(os.getenv("MCP_REQUEST_TIMEOUT", "30.0"))


class FailureCategory(Enum):
    """Categorizes the outcome of a live MCP call."""

    SUCCESS = "success"
    NETWORK_ERROR = "network_error"  # DNS failure, connection refused
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"  # 401 or 403
    RATE_LIMIT = "rate_limit"  # 429
    SERVER_ERROR = "server_error"  # 5xx
    CLIENT_ERROR = "client_error"  # 4xx other than auth/rate-limit
    INVALID_JSON = "invalid_json"  # Response body is not valid JSON
    NOT_CONFIGURED = "not_configured"  # MCP not set up for live testing
    MCP_NOT_AVAILABLE = "mcp_not_available"  # MCP infrastructure not present


@dataclass
class MCPInvocationResult:
    """Structured result of a live MCP call for observability."""

    tool_name: str
    category: FailureCategory
    status_code: Optional[int] = None
    response_body: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    request_body: Optional[Dict[str, Any]] = None
    latency_ms: Optional[float] = None
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serializes the result to a JSON string for logging."""
        data = asdict(self)
        # Handle Enum serialization
        data["category"] = self.category.value
        return json.dumps(data, indent=2, default=str)

    @property
    def is_success(self) -> bool:
        """Check if the invocation was successful."""
        return self.category == FailureCategory.SUCCESS

    @property
    def is_retryable(self) -> bool:
        """Check if the failure is potentially retryable."""
        return self.category in (
            FailureCategory.TIMEOUT,
            FailureCategory.NETWORK_ERROR,
            FailureCategory.RATE_LIMIT,
            FailureCategory.SERVER_ERROR,
        )


def invoke_real_mcp(
    tool_name: str,
    request_body: Dict[str, Any],
    timeout: Optional[float] = None,
) -> MCPInvocationResult:
    """
    Invokes the real MCP service with robust error handling and observability.

    This function attempts to invoke MCP tools through available infrastructure.
    Currently implemented as a placeholder that can be extended to:
    1. Use Claude Code's native MCP infrastructure
    2. Use HTTP-based MCP endpoints
    3. Use local MCP server for testing

    Args:
        tool_name: The name of the MCP tool to invoke (e.g., "mcp__pal__codereview").
        request_body: The request payload for the tool.
        timeout: Optional timeout in seconds (defaults to MCP_REQUEST_TIMEOUT_SECONDS).

    Returns:
        An MCPInvocationResult object with the outcome of the call.
    """
    timeout = timeout or MCP_REQUEST_TIMEOUT_SECONDS
    start_time = time.monotonic()

    # Check if live testing is enabled
    if not os.environ.get("MCP_LIVE_TESTING_ENABLED"):
        return MCPInvocationResult(
            tool_name=tool_name,
            category=FailureCategory.NOT_CONFIGURED,
            error_message="MCP_LIVE_TESTING_ENABLED environment variable not set.",
            request_body=request_body,
        )

    # Try different MCP invocation methods
    result = _try_http_mcp(tool_name, request_body, timeout, start_time)
    if result is not None:
        return result

    # Fallback: MCP infrastructure not available
    return MCPInvocationResult(
        tool_name=tool_name,
        category=FailureCategory.MCP_NOT_AVAILABLE,
        error_message=(
            "No MCP infrastructure available. "
            "Set MCP_API_BASE_URL and MCP_API_KEY for HTTP-based MCP, "
            "or run within Claude Code for native MCP."
        ),
        request_body=request_body,
        latency_ms=(time.monotonic() - start_time) * 1000,
    )


def _try_http_mcp(
    tool_name: str,
    request_body: Dict[str, Any],
    timeout: float,
    start_time: float,
) -> Optional[MCPInvocationResult]:
    """
    Try to invoke MCP via HTTP endpoint.

    Returns None if HTTP MCP is not configured.
    """
    base_url = os.environ.get("MCP_API_BASE_URL")
    api_key = os.environ.get("MCP_API_KEY")

    if not base_url:
        return None  # HTTP MCP not configured

    # Import requests only when needed
    try:
        import requests
    except ImportError:
        logger.warning("requests library not installed, HTTP MCP unavailable")
        return None

    if not api_key:
        return MCPInvocationResult(
            tool_name=tool_name,
            category=FailureCategory.AUTH_ERROR,
            error_message="MCP_API_KEY environment variable is not set.",
            request_body=request_body,
        )

    endpoint = f"{base_url}/invoke/{tool_name}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Request-Source": "superclaude-agentic-tests",
    }

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=request_body,
            timeout=timeout,
        )
        latency_ms = (time.monotonic() - start_time) * 1000

        # Extract trace ID if present
        trace_id = response.headers.get("X-Trace-ID")

        # Handle HTTP status codes
        if response.ok:
            try:
                response_json = response.json()
                return MCPInvocationResult(
                    tool_name=tool_name,
                    category=FailureCategory.SUCCESS,
                    status_code=response.status_code,
                    response_body=response_json,
                    request_body=request_body,
                    latency_ms=latency_ms,
                    trace_id=trace_id,
                )
            except json.JSONDecodeError as e:
                return MCPInvocationResult(
                    tool_name=tool_name,
                    category=FailureCategory.INVALID_JSON,
                    status_code=response.status_code,
                    error_message=f"Failed to decode JSON response: {e}",
                    request_body=request_body,
                    latency_ms=latency_ms,
                    trace_id=trace_id,
                )

        # Categorize HTTP errors
        if response.status_code in (401, 403):
            category = FailureCategory.AUTH_ERROR
        elif response.status_code == 429:
            category = FailureCategory.RATE_LIMIT
        elif 400 <= response.status_code < 500:
            category = FailureCategory.CLIENT_ERROR
        else:  # 5xx errors
            category = FailureCategory.SERVER_ERROR

        return MCPInvocationResult(
            tool_name=tool_name,
            category=category,
            status_code=response.status_code,
            error_message=response.text[:500],  # Truncate long error messages
            request_body=request_body,
            latency_ms=latency_ms,
            trace_id=trace_id,
        )

    except requests.exceptions.Timeout as e:
        latency_ms = (time.monotonic() - start_time) * 1000
        return MCPInvocationResult(
            tool_name=tool_name,
            category=FailureCategory.TIMEOUT,
            error_message=f"Request timed out after {timeout}s: {e}",
            request_body=request_body,
            latency_ms=latency_ms,
        )

    except requests.exceptions.ConnectionError as e:
        latency_ms = (time.monotonic() - start_time) * 1000
        return MCPInvocationResult(
            tool_name=tool_name,
            category=FailureCategory.NETWORK_ERROR,
            error_message=f"Connection error: {e}",
            request_body=request_body,
            latency_ms=latency_ms,
        )

    except requests.exceptions.RequestException as e:
        latency_ms = (time.monotonic() - start_time) * 1000
        return MCPInvocationResult(
            tool_name=tool_name,
            category=FailureCategory.NETWORK_ERROR,
            error_message=f"Request failed: {e}",
            request_body=request_body,
            latency_ms=latency_ms,
        )


def log_invocation_result(result: MCPInvocationResult, level: int = logging.INFO) -> None:
    """
    Log an MCPInvocationResult with appropriate detail level.

    Args:
        result: The result to log.
        level: Logging level (default: INFO for success, ERROR for failures).
    """
    if result.is_success:
        logger.log(
            level,
            "MCP call succeeded: tool=%s latency=%.2fms",
            result.tool_name,
            result.latency_ms or 0,
        )
    else:
        logger.error(
            "MCP call failed: tool=%s category=%s error=%s\nFull result:\n%s",
            result.tool_name,
            result.category.value,
            result.error_message,
            result.to_json(),
        )


# =============================================================================
# Capture Mode - For generating test fixtures from live interactions
# =============================================================================

# =============================================================================
# Data Sanitization - Prevents sensitive data from being captured in fixtures
# =============================================================================

# Registry for tool-specific sanitizers
_TOOL_SANITIZERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

# Global sanitization patterns (applied to all captures)
_GLOBAL_SANITIZATION_PATTERNS = [
    # Email addresses
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "user@example.com"),
    # API keys / tokens (common formats)
    (re.compile(r"(?:api[_-]?key|token|secret|password|auth)[\"']?\s*[:=]\s*[\"']?[\w\-]{16,}[\"']?", re.I), "[REDACTED_CREDENTIAL]"),
    # Bearer tokens
    (re.compile(r"Bearer\s+[\w\-\.]+", re.I), "Bearer [REDACTED]"),
    # AWS-style keys
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    # Generic long alphanumeric tokens (likely secrets)
    (re.compile(r"[\"'][a-zA-Z0-9]{32,}[\"']"), '"[REDACTED_TOKEN]"'),
    # IP addresses (private ranges kept, public sanitized)
    (re.compile(r"\b(?!10\.)(?!172\.(?:1[6-9]|2\d|3[01])\.)(?!192\.168\.)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "203.0.113.1"),
    # Phone numbers (US format)
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "555-000-0000"),
    # Credit card numbers (basic pattern)
    (re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), "[REDACTED_CC]"),
]


def register_tool_sanitizer(
    tool_name: str,
    sanitizer: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> None:
    """
    Register a tool-specific sanitizer function.

    The sanitizer receives the response data dict and should return
    a sanitized copy. It runs AFTER global sanitization.

    Args:
        tool_name: The MCP tool name (e.g., "mcp__pal__codereview").
        sanitizer: Function that takes response dict and returns sanitized dict.

    Example:
        def sanitize_user_data(data: dict) -> dict:
            data = copy.deepcopy(data)
            if "user" in data:
                data["user"]["name"] = "Test User"
                data["user"]["email"] = "test@example.com"
            return data

        register_tool_sanitizer("mcp__rube__GET_USER", sanitize_user_data)
    """
    _TOOL_SANITIZERS[tool_name] = sanitizer
    logger.debug("Registered sanitizer for %s", tool_name)


def _apply_global_sanitization(text: str) -> str:
    """Apply global regex-based sanitization patterns to a string."""
    for pattern, replacement in _GLOBAL_SANITIZATION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _sanitize_dict_strings(data: Any) -> Any:
    """Recursively sanitize all string values in a data structure."""
    if isinstance(data, str):
        return _apply_global_sanitization(data)
    elif isinstance(data, dict):
        return {k: _sanitize_dict_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_sanitize_dict_strings(item) for item in data]
    else:
        return data


def sanitize_capture(tool_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply sanitization to captured data before writing to fixture file.

    Two-pass sanitization:
    1. Global patterns (emails, API keys, tokens, etc.)
    2. Tool-specific sanitizer if registered

    Args:
        tool_name: The MCP tool name.
        data: The data to sanitize.

    Returns:
        Sanitized copy of the data.
    """
    import copy

    # Pass 1: Global sanitization via regex
    sanitized = _sanitize_dict_strings(copy.deepcopy(data))

    # Pass 2: Tool-specific sanitization
    if tool_name in _TOOL_SANITIZERS:
        try:
            sanitized = _TOOL_SANITIZERS[tool_name](sanitized)
        except Exception as e:
            logger.warning("Tool sanitizer for %s failed: %s", tool_name, e)

    return sanitized


def capture_interaction(result: MCPInvocationResult) -> None:
    """
    Capture a successful MCP interaction to a JSONL file for fixture generation.

    Only captures successful interactions. Set MCP_CAPTURE_FILE environment
    variable to enable capture mode.

    Security: All captured data is sanitized before writing to prevent
    sensitive information (emails, API keys, tokens) from being stored.

    Args:
        result: The MCPInvocationResult to capture.
    """
    capture_file = os.environ.get("MCP_CAPTURE_FILE")
    if not capture_file:
        return

    if not result.is_success:
        return  # Only capture successful interactions

    # Build the raw capture entry
    raw_response = {
        "success": True,
        "data": result.response_body.get("data", result.response_body)
        if result.response_body
        else {},
    }

    # Sanitize request and response data
    sanitized_request = sanitize_capture(result.tool_name, result.request_body or {})
    sanitized_response = sanitize_capture(result.tool_name, raw_response)

    capture_entry = {
        "tool_name": result.tool_name,
        "request": sanitized_request,
        "response": sanitized_response,
        "metadata": {
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "latency_ms": result.latency_ms,
            "trace_id": result.trace_id,
            "sanitized": True,  # Flag indicating sanitization was applied
        },
    }

    try:
        with open(capture_file, "a") as f:
            f.write(json.dumps(capture_entry) + "\n")
        logger.debug("Captured sanitized interaction for %s to %s", result.tool_name, capture_file)
    except IOError as e:
        logger.warning("Failed to capture interaction: %s", e)


def invoke_and_capture(
    tool_name: str,
    request_body: Dict[str, Any],
    timeout: Optional[float] = None,
) -> MCPInvocationResult:
    """
    Invoke MCP and capture the interaction if capture mode is enabled.

    This is a convenience wrapper around invoke_real_mcp that automatically
    captures successful interactions.

    Args:
        tool_name: The MCP tool to invoke.
        request_body: The request payload.
        timeout: Optional timeout in seconds.

    Returns:
        The MCPInvocationResult from the invocation.
    """
    result = invoke_real_mcp(tool_name, request_body, timeout)
    capture_interaction(result)
    return result


# =============================================================================
# Fixture Staleness Checking
# =============================================================================


@dataclass
class FixtureStalenessReport:
    """Report on fixture staleness for a directory."""

    total_fixtures: int
    stale_fixtures: int
    stale_threshold_days: int
    stale_files: list  # List of (path, age_days) tuples
    warnings: list  # List of warning messages


def check_fixture_staleness(
    fixture_dir: Path,
    max_age_days: int = 30,
) -> FixtureStalenessReport:
    """
    Check fixtures in a directory for staleness based on captured_at metadata.

    Args:
        fixture_dir: Path to directory containing fixture files.
        max_age_days: Maximum age in days before a fixture is considered stale.

    Returns:
        FixtureStalenessReport with details about stale fixtures.
    """
    total = 0
    stale = 0
    stale_files = []
    warnings = []
    now = datetime.utcnow()
    threshold = timedelta(days=max_age_days)

    if not fixture_dir.exists():
        return FixtureStalenessReport(
            total_fixtures=0,
            stale_fixtures=0,
            stale_threshold_days=max_age_days,
            stale_files=[],
            warnings=[f"Fixture directory does not exist: {fixture_dir}"],
        )

    # Check .json files
    for fixture_file in fixture_dir.glob("*.json"):
        try:
            with open(fixture_file) as f:
                data = json.load(f)
            total += 1
            captured_at = _parse_captured_at(data)
            if captured_at:
                age = now - captured_at
                if age > threshold:
                    stale += 1
                    stale_files.append((str(fixture_file), age.days))
            else:
                warnings.append(f"No captured_at metadata in {fixture_file.name}")
        except (json.JSONDecodeError, IOError) as e:
            warnings.append(f"Failed to read {fixture_file.name}: {e}")

    # Check .jsonl files
    for fixture_file in fixture_dir.glob("*.jsonl"):
        try:
            with open(fixture_file) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        total += 1
                        captured_at = _parse_captured_at(data)
                        if captured_at:
                            age = now - captured_at
                            if age > threshold:
                                stale += 1
                                stale_files.append((f"{fixture_file.name}:{line_num}", age.days))
                        else:
                            warnings.append(f"No captured_at in {fixture_file.name}:{line_num}")
                    except json.JSONDecodeError:
                        warnings.append(f"Invalid JSON at {fixture_file.name}:{line_num}")
        except IOError as e:
            warnings.append(f"Failed to read {fixture_file.name}: {e}")

    return FixtureStalenessReport(
        total_fixtures=total,
        stale_fixtures=stale,
        stale_threshold_days=max_age_days,
        stale_files=stale_files,
        warnings=warnings,
    )


def _parse_captured_at(data: Dict[str, Any]) -> Optional[datetime]:
    """Parse captured_at timestamp from fixture metadata."""
    metadata = data.get("metadata", {})
    captured_at_str = metadata.get("captured_at") or metadata.get("timestamp")
    if not captured_at_str:
        return None
    try:
        # Handle ISO format with Z suffix
        if captured_at_str.endswith("Z"):
            captured_at_str = captured_at_str[:-1]
        return datetime.fromisoformat(captured_at_str)
    except ValueError:
        return None


def log_staleness_report(report: FixtureStalenessReport) -> None:
    """Log a staleness report with appropriate severity levels."""
    if report.stale_fixtures > 0:
        logger.warning(
            "Fixture staleness check: %d/%d fixtures are older than %d days",
            report.stale_fixtures,
            report.total_fixtures,
            report.stale_threshold_days,
        )
        for path, age_days in report.stale_files:
            logger.warning("  Stale fixture: %s (age: %d days)", path, age_days)
    else:
        logger.info(
            "Fixture staleness check: All %d fixtures are fresh (<%d days old)",
            report.total_fixtures,
            report.stale_threshold_days,
        )

    for warning in report.warnings:
        logger.warning("Fixture warning: %s", warning)
