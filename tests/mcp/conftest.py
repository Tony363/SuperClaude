"""Fixtures for MCP integration tests.

Provides fake MCP server responses and fixtures for testing:
- PAL MCP tools (codereview, debug, thinkdeep, consensus)
- Rube MCP tools (RUBE_SEARCH_TOOLS, RUBE_MULTI_EXECUTE_TOOL)

Fixture Loading:
    The FakeMCPServer can load fixtures from captured live interactions:

    server = FakeMCPServer.from_fixtures(Path("tests/mcp/fixtures/captured"))

    Fixture files should be JSON with structure:
    {
        "tool_name": "mcp__pal__codereview",
        "request": {...},
        "response": {...},
        "metadata": {"timestamp": "...", "latency_ms": ...}
    }
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

logger = logging.getLogger(__name__)


@dataclass
class FakeMCPResponse:
    """Simulates an MCP tool response."""

    success: bool = True
    data: dict = field(default_factory=dict)
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary format matching real MCP responses."""
        result = {
            "success": self.success,
            "data": self.data,
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class FakePALCodeReviewResponse(FakeMCPResponse):
    """Simulates mcp__pal__codereview response."""

    def __post_init__(self):
        if not self.data:
            self.data = {
                "issues_found": [],
                "review_type": "full",
                "step_number": 1,
                "total_steps": 2,
                "next_step_required": False,
                "findings": "No critical issues found.",
                "confidence": "high",
                "relevant_files": [],
            }


@dataclass
class FakePALDebugResponse(FakeMCPResponse):
    """Simulates mcp__pal__debug response."""

    def __post_init__(self):
        if not self.data:
            self.data = {
                "hypothesis": "Root cause identified",
                "confidence": "high",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "Issue traced to configuration.",
                "relevant_files": [],
                "issues_found": [],
            }


@dataclass
class FakeRubeSearchToolsResponse(FakeMCPResponse):
    """Simulates mcp__rube__RUBE_SEARCH_TOOLS response."""

    def __post_init__(self):
        if not self.data:
            self.data = {
                "tools": [
                    {
                        "tool_slug": "SLACK_SEND_MESSAGE",
                        "description": "Send a message to a Slack channel",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "channel": {"type": "string"},
                                "text": {"type": "string"},
                            },
                            "required": ["channel", "text"],
                        },
                    }
                ],
                "session_id": "test-session-123",
                "total_tools": 1,
            }


@dataclass
class FakeRubeMultiExecuteResponse(FakeMCPResponse):
    """Simulates mcp__rube__RUBE_MULTI_EXECUTE_TOOL response."""

    def __post_init__(self):
        if not self.data:
            self.data = {
                "results": [
                    {
                        "tool_slug": "SLACK_SEND_MESSAGE",
                        "success": True,
                        "data": {"message_id": "msg-123", "timestamp": "1234567890"},
                        "error": None,
                    }
                ],
                "all_succeeded": True,
                "partial_failure": False,
            }


class FakeMCPServer:
    """Fake MCP server for testing signal→call→response→state pipeline.

    Supports two modes:
    1. Default responses - Hardcoded reasonable defaults for all tools
    2. Captured fixtures - Load from JSON files captured from live MCP

    Captured fixtures take precedence over defaults when request matches exactly.
    """

    def __init__(self):
        self.call_history: List[Dict[str, Any]] = []
        self.responses: Dict[str, FakeMCPResponse] = {}
        self.captured_fixtures: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._setup_default_responses()

    @classmethod
    def from_fixtures(cls, fixture_dir: Path) -> "FakeMCPServer":
        """Create a FakeMCPServer loaded with captured fixtures.

        Args:
            fixture_dir: Path to directory containing .json or .jsonl fixture files.
                         Each file should contain fixtures with structure:
                         {"tool_name": str, "request": dict, "response": dict, ...}

        Returns:
            FakeMCPServer instance with loaded fixtures.

        Example:
            server = FakeMCPServer.from_fixtures(Path("tests/mcp/fixtures/captured"))
            response = server.invoke("mcp__pal__codereview", captured_request)
        """
        server = cls()

        if not fixture_dir.exists():
            logger.warning("Fixture directory does not exist: %s", fixture_dir)
            return server

        # Load .json files (single fixture per file)
        for fixture_file in sorted(fixture_dir.glob("*.json")):
            try:
                with open(fixture_file) as f:
                    data = json.load(f)
                if cls._is_valid_fixture(data):
                    server.captured_fixtures[data["tool_name"]].append(data)
                    logger.debug("Loaded fixture for %s from %s", data["tool_name"], fixture_file)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load fixture %s: %s", fixture_file, e)

        # Load .jsonl files (multiple fixtures per file, one per line)
        for fixture_file in sorted(fixture_dir.glob("*.jsonl")):
            try:
                with open(fixture_file) as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if cls._is_valid_fixture(data):
                                server.captured_fixtures[data["tool_name"]].append(data)
                        except json.JSONDecodeError as e:
                            logger.warning(
                                "Failed to parse line %d in %s: %s", line_num, fixture_file, e
                            )
            except IOError as e:
                logger.warning("Failed to read fixture file %s: %s", fixture_file, e)

        total_fixtures = sum(len(v) for v in server.captured_fixtures.values())
        logger.info(
            "Loaded %d fixtures for %d tools from %s",
            total_fixtures,
            len(server.captured_fixtures),
            fixture_dir,
        )

        return server

    @staticmethod
    def _is_valid_fixture(data: Any) -> bool:
        """Check if data is a valid fixture structure."""
        return (
            isinstance(data, dict)
            and "tool_name" in data
            and "request" in data
            and "response" in data
        )

    def _setup_default_responses(self):
        """Set up default responses for all MCP tools."""
        self.responses = {
            "mcp__pal__codereview": FakePALCodeReviewResponse(),
            "mcp__pal__debug": FakePALDebugResponse(),
            "mcp__pal__thinkdeep": FakeMCPResponse(
                data={
                    "step": "Analysis complete",
                    "findings": "System architecture is sound.",
                    "confidence": "high",
                }
            ),
            "mcp__pal__consensus": FakeMCPResponse(
                data={
                    "consensus_reached": True,
                    "recommendation": "Proceed with implementation",
                    "models_consulted": ["model-a", "model-b"],
                }
            ),
            "mcp__rube__RUBE_SEARCH_TOOLS": FakeRubeSearchToolsResponse(),
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL": FakeRubeMultiExecuteResponse(),
            "mcp__rube__RUBE_CREATE_PLAN": FakeMCPResponse(
                data={
                    "plan_id": "plan-123",
                    "steps": ["Step 1", "Step 2"],
                    "status": "created",
                }
            ),
            "mcp__rube__RUBE_MANAGE_CONNECTIONS": FakeMCPResponse(
                data={
                    "connections": [
                        {"toolkit": "slack", "status": "active"},
                        {"toolkit": "github", "status": "active"},
                    ]
                }
            ),
        }

    def set_response(self, tool_name: str, response: FakeMCPResponse):
        """Override the response for a specific tool."""
        self.responses[tool_name] = response

    def set_error_response(self, tool_name: str, error: str):
        """Set an error response for a tool."""
        self.responses[tool_name] = FakeMCPResponse(success=False, error=error)

    def set_timeout_response(self, tool_name: str):
        """Simulate a timeout for a tool."""
        self.responses[tool_name] = FakeMCPResponse(
            success=False, error="timeout", metadata={"timeout_seconds": 30}
        )

    def set_partial_failure_response(self, tool_name: str, results: list[dict]):
        """Set a partial failure response for multi-execute."""
        self.responses[tool_name] = FakeMCPResponse(
            success=True,
            data={
                "results": results,
                "all_succeeded": False,
                "partial_failure": True,
            },
        )

    def invoke(self, tool_name: str, parameters: dict) -> dict:
        """Simulate invoking an MCP tool.

        Resolution order:
        1. Check captured fixtures for exact request match
        2. Fall back to default responses
        3. Return error if tool unknown
        """
        self.call_history.append(
            {
                "tool": tool_name,
                "parameters": parameters,
            }
        )

        # Check captured fixtures first (exact match)
        for fixture in self.captured_fixtures.get(tool_name, []):
            if fixture["request"] == parameters:
                logger.debug("Using captured fixture for %s", tool_name)
                return fixture["response"]

        # Fall back to default responses
        if tool_name in self.responses:
            return self.responses[tool_name].to_dict()

        return FakeMCPResponse(
            success=False, error=f"Unknown tool: {tool_name}"
        ).to_dict()

    def get_call_count(self, tool_name: str) -> int:
        """Get the number of times a tool was called."""
        return sum(1 for call in self.call_history if call["tool"] == tool_name)

    def get_last_call(self, tool_name: str) -> Optional[dict]:
        """Get the last call to a specific tool."""
        for call in reversed(self.call_history):
            if call["tool"] == tool_name:
                return call
        return None

    def reset(self):
        """Reset call history and responses to defaults."""
        self.call_history = []
        self._setup_default_responses()


@pytest.fixture
def fake_mcp_server():
    """Provide a fresh fake MCP server for each test."""
    server = FakeMCPServer()
    yield server
    server.reset()


@pytest.fixture
def pal_codereview_response():
    """Provide a standard PAL codereview response."""
    return FakePALCodeReviewResponse()


@pytest.fixture
def pal_codereview_with_issues():
    """Provide a PAL codereview response with issues found."""
    return FakePALCodeReviewResponse(
        data={
            "issues_found": [
                {"severity": "critical", "description": "SQL injection vulnerability"},
                {"severity": "high", "description": "Missing input validation"},
                {"severity": "medium", "description": "Inconsistent error handling"},
            ],
            "review_type": "full",
            "step_number": 1,
            "total_steps": 2,
            "next_step_required": True,
            "findings": "Found 3 issues requiring attention.",
            "confidence": "high",
            "relevant_files": ["src/db.py", "src/api.py"],
        }
    )


@pytest.fixture
def pal_debug_response():
    """Provide a standard PAL debug response."""
    return FakePALDebugResponse()


@pytest.fixture
def rube_search_response():
    """Provide a standard Rube search tools response."""
    return FakeRubeSearchToolsResponse()


@pytest.fixture
def rube_multi_execute_partial_failure():
    """Provide a Rube multi-execute response with partial failure."""
    return FakeMCPResponse(
        success=True,
        data={
            "results": [
                {
                    "tool_slug": "SLACK_SEND_MESSAGE",
                    "success": True,
                    "data": {"message_id": "msg-123"},
                    "error": None,
                },
                {
                    "tool_slug": "GITHUB_CREATE_ISSUE",
                    "success": False,
                    "data": None,
                    "error": "Rate limit exceeded",
                },
            ],
            "all_succeeded": False,
            "partial_failure": True,
        },
    )


@pytest.fixture
def mcp_timeout_response():
    """Provide a timeout response."""
    return FakeMCPResponse(
        success=False, error="timeout", metadata={"timeout_seconds": 30}
    )


@pytest.fixture
def mcp_malformed_response():
    """Provide a malformed response for error handling tests."""
    return {"unexpected_field": "value", "missing_required": True}
