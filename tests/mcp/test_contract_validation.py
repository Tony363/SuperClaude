"""Contract validation tests for MCP schema drift detection.

These tests compare FakeMCPServer responses against live MCP responses
to detect when the fake server's schema has drifted from reality.

Run with: pytest tests/mcp/test_contract_validation.py -m live

Note: These tests require actual MCP access and are marked for nightly runs.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import pytest

from tests.mcp.conftest import FakeMCPServer
from tests.mcp.contract_helpers import assert_schema_matches, schema_diff
from tests.mcp.live_mcp_client import (
    FailureCategory,
    MCPInvocationResult,
    invoke_real_mcp,
    log_invocation_result,
)

logger = logging.getLogger(__name__)


# Canonical requests for each MCP tool - simple requests designed to succeed
# IMPORTANT: Canonical requests must be designed to return non-empty lists
# for any array fields to ensure their element schemas are validated.
# Empty lists bypass element schema validation.
CANONICAL_PAL_REQUESTS = {
    "mcp__pal__codereview": {
        "step": "Review basic Python function",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "",
        "relevant_files": ["test.py"],
        "model": "gpt-5",
    },
    "mcp__pal__debug": {
        "step": "Analyze test error",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "",
        "hypothesis": "Configuration issue",
        "model": "gpt-5",
    },
    "mcp__pal__thinkdeep": {
        "step": "Analyze architecture",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "",
        "model": "gpt-5",
    },
    "mcp__pal__consensus": {
        "step": "Evaluate approach",
        "step_number": 1,
        "total_steps": 3,
        "next_step_required": True,
        "findings": "",
        "models": [
            {"model": "gpt-5", "stance": "for"},
            {"model": "gemini-2.5-pro", "stance": "against"},
        ],
    },
}

CANONICAL_RUBE_REQUESTS = {
    "mcp__rube__RUBE_SEARCH_TOOLS": {
        "queries": [{"use_case": "send a message to a slack channel"}],
        "session": {"generate_id": True},
    },
    "mcp__rube__RUBE_MULTI_EXECUTE_TOOL": {
        "tools": [
            {
                "tool_slug": "SLACK_SEND_MESSAGE",
                "arguments": {"channel": "#test", "text": "Hello"},
            }
        ],
        "sync_response_to_workbench": False,
    },
    "mcp__rube__RUBE_MANAGE_CONNECTIONS": {
        "toolkits": ["slack", "github"],
    },
}


def invoke_real_mcp(tool_name: str, request_body: dict) -> Optional[dict]:
    """
    Invoke a real MCP tool and return the response.

    This is a placeholder that should be replaced with actual MCP invocation
    logic when running live tests.

    In a real implementation, this would:
    1. Use Claude Code's MCP infrastructure
    2. Handle authentication
    3. Manage timeouts and retries

    Returns:
        The response dict from the MCP tool, or None if unavailable.
    """
    # Check if we're in a live test environment
    if not os.environ.get("MCP_LIVE_TESTING_ENABLED"):
        return None

    # Placeholder - in production, this would invoke the actual MCP tool
    # via Claude Code's infrastructure
    #
    # Example implementation outline:
    # from claude_code.mcp import invoke_tool
    # return invoke_tool(tool_name, request_body, timeout=30)
    #
    return None


class TestContractHelpers:
    """Tests for the contract validation helper functions."""

    def test_assert_schema_matches_identical_dicts(self):
        """Identical dicts should pass."""
        ref = {"a": 1, "b": "hello", "c": [1, 2, 3]}
        cand = {"a": 2, "b": "world", "c": [4, 5]}  # Different values, same schema
        assert_schema_matches(ref, cand)  # Should not raise

    def test_assert_schema_matches_missing_key(self):
        """Missing key should fail."""
        ref = {"a": 1, "b": 2}
        cand = {"a": 1}
        with pytest.raises(AssertionError, match="Missing keys"):
            assert_schema_matches(ref, cand)

    def test_assert_schema_matches_extra_key(self):
        """Extra key should fail by default."""
        ref = {"a": 1}
        cand = {"a": 1, "b": 2}
        with pytest.raises(AssertionError, match="Extra keys"):
            assert_schema_matches(ref, cand)

    def test_assert_schema_matches_extra_key_allowed(self):
        """Extra key should pass when allowed."""
        ref = {"a": 1}
        cand = {"a": 1, "b": 2}
        assert_schema_matches(ref, cand, allow_extra_keys=True)  # Should not raise

    def test_assert_schema_matches_type_mismatch(self):
        """Type mismatch should fail."""
        ref = {"a": 1}
        cand = {"a": "string"}
        with pytest.raises(AssertionError, match="Type mismatch"):
            assert_schema_matches(ref, cand)

    def test_assert_schema_matches_numeric_interchangeable(self):
        """Int and float should be interchangeable."""
        ref = {"a": 1}
        cand = {"a": 1.0}
        assert_schema_matches(ref, cand)  # Should not raise

    def test_assert_schema_matches_nested_dicts(self):
        """Nested dicts should be recursively checked."""
        ref = {"outer": {"inner": {"deep": 1}}}
        cand = {"outer": {"inner": {"deep": 2}}}
        assert_schema_matches(ref, cand)  # Should not raise

    def test_assert_schema_matches_lists(self):
        """Lists should compare first element schemas."""
        ref = {"items": [{"id": 1, "name": "a"}]}
        cand = {"items": [{"id": 2, "name": "b"}, {"id": 3, "name": "c"}]}
        assert_schema_matches(ref, cand)  # Should not raise

    def test_assert_schema_matches_list_element_mismatch(self):
        """List element schema mismatch should fail."""
        ref = {"items": [{"id": 1}]}
        cand = {"items": [{"id": "string"}]}
        with pytest.raises(AssertionError, match="Type mismatch"):
            assert_schema_matches(ref, cand)

    def test_schema_diff_returns_all_differences(self):
        """schema_diff should return all differences."""
        ref = {"a": 1, "b": {"c": 2}, "d": "string"}
        cand = {"a": "wrong", "b": {"c": 2, "extra": 3}}  # Missing 'd', extra 'b.extra'

        diffs = schema_diff(ref, cand)

        assert len(diffs) >= 2
        assert any("type mismatch" in d for d in diffs)
        assert any("missing" in d.lower() or "extra" in d.lower() for d in diffs)


class TestFakeMCPServerSchemaConsistency:
    """Tests that FakeMCPServer responses have consistent internal schemas."""

    def test_pal_codereview_response_schema(self, fake_mcp_server):
        """PAL codereview response should have consistent schema."""
        response = fake_mcp_server.invoke(
            "mcp__pal__codereview",
            CANONICAL_PAL_REQUESTS["mcp__pal__codereview"],
        )

        # Verify required top-level structure
        assert "success" in response
        assert "data" in response
        assert isinstance(response["success"], bool)
        assert isinstance(response["data"], dict)

        # Verify data structure
        data = response["data"]
        assert "issues_found" in data
        assert "review_type" in data
        assert "step_number" in data
        assert "findings" in data

    def test_pal_debug_response_schema(self, fake_mcp_server):
        """PAL debug response should have consistent schema."""
        response = fake_mcp_server.invoke(
            "mcp__pal__debug",
            CANONICAL_PAL_REQUESTS["mcp__pal__debug"],
        )

        assert response["success"] is True
        data = response["data"]
        assert "hypothesis" in data
        assert "confidence" in data
        assert "findings" in data

    def test_rube_search_tools_response_schema(self, fake_mcp_server):
        """Rube search tools response should have consistent schema."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            CANONICAL_RUBE_REQUESTS["mcp__rube__RUBE_SEARCH_TOOLS"],
        )

        assert response["success"] is True
        data = response["data"]
        assert "tools" in data
        assert "session_id" in data
        assert isinstance(data["tools"], list)

    def test_rube_multi_execute_response_schema(self, fake_mcp_server):
        """Rube multi-execute response should have consistent schema."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
            CANONICAL_RUBE_REQUESTS["mcp__rube__RUBE_MULTI_EXECUTE_TOOL"],
        )

        assert response["success"] is True
        data = response["data"]
        assert "results" in data
        assert "all_succeeded" in data
        assert isinstance(data["results"], list)


@pytest.mark.live
@pytest.mark.nightly
class TestLiveContractValidation:
    """
    Live contract validation tests that compare fake vs real MCP responses.

    These tests only run when MCP_LIVE_TESTING_ENABLED=1 is set.
    Run with: MCP_LIVE_TESTING_ENABLED=1 pytest -m live

    Observability features:
    - Structured logging of all failures with full request/response
    - Failure categorization (network, timeout, auth, schema mismatch)
    - Latency tracking for performance monitoring
    """

    @pytest.fixture(autouse=True)
    def skip_if_no_live_mcp(self):
        """Skip tests if live MCP testing is not enabled."""
        if not os.environ.get("MCP_LIVE_TESTING_ENABLED"):
            pytest.skip("Live MCP testing not enabled (set MCP_LIVE_TESTING_ENABLED=1)")

    def _handle_live_result(
        self,
        result: MCPInvocationResult,
        tool_name: str,
    ) -> dict:
        """
        Handle the live MCP invocation result with proper observability.

        Args:
            result: The MCPInvocationResult from invoke_real_mcp.
            tool_name: Name of the tool for error messages.

        Returns:
            The response body if successful.

        Raises:
            pytest.fail: If the invocation failed.
            pytest.skip: If MCP is not available.
        """
        # Log all results for observability
        log_invocation_result(result)

        # Handle non-configured/unavailable states
        if result.category in (
            FailureCategory.NOT_CONFIGURED,
            FailureCategory.MCP_NOT_AVAILABLE,
        ):
            pytest.skip(f"Live MCP not available for {tool_name}: {result.error_message}")

        # Handle failures with detailed logging
        if not result.is_success:
            logger.error(
                "Live MCP call failed for %s:\n%s",
                tool_name,
                result.to_json(),
            )
            pytest.fail(
                f"Live MCP call for '{tool_name}' failed.\n"
                f"Category: {result.category.value}\n"
                f"Error: {result.error_message}\n"
                f"Latency: {result.latency_ms:.2f}ms\n"
                f"See logs for full request/response details."
            )

        return result.response_body

    @pytest.mark.parametrize(
        "tool_name,request_body",
        list(CANONICAL_PAL_REQUESTS.items()),
        ids=list(CANONICAL_PAL_REQUESTS.keys()),
    )
    def test_pal_contract_matches_live(
        self,
        tool_name: str,
        request_body: dict,
        fake_mcp_server: FakeMCPServer,
    ):
        """
        Compare fake PAL response schema against live response.

        Args:
            tool_name: The MCP tool to test.
            request_body: Canonical request for the tool.
            fake_mcp_server: Fake MCP server fixture.
        """
        # Get fake response
        fake_response = fake_mcp_server.invoke(tool_name, request_body)

        # Get live response with observability
        live_result = invoke_real_mcp(tool_name, request_body)
        live_response = self._handle_live_result(live_result, tool_name)

        # Compare schemas (allow live to have extra fields)
        try:
            assert_schema_matches(
                reference=fake_response,
                candidate=live_response,
                allow_extra_keys=True,  # Live may evolve to include more fields
            )
        except AssertionError as e:
            # Log schema mismatch with both responses for debugging
            logger.error(
                "Schema mismatch for %s:\n"
                "Assertion: %s\n"
                "Fake response: %s\n"
                "Live response: %s",
                tool_name,
                str(e),
                json.dumps(fake_response, indent=2),
                json.dumps(live_response, indent=2),
            )
            raise

    @pytest.mark.parametrize(
        "tool_name,request_body",
        list(CANONICAL_RUBE_REQUESTS.items()),
        ids=list(CANONICAL_RUBE_REQUESTS.keys()),
    )
    def test_rube_contract_matches_live(
        self,
        tool_name: str,
        request_body: dict,
        fake_mcp_server: FakeMCPServer,
    ):
        """
        Compare fake Rube response schema against live response.

        Args:
            tool_name: The MCP tool to test.
            request_body: Canonical request for the tool.
            fake_mcp_server: Fake MCP server fixture.
        """
        # Get fake response
        fake_response = fake_mcp_server.invoke(tool_name, request_body)

        # Get live response with observability
        live_result = invoke_real_mcp(tool_name, request_body)
        live_response = self._handle_live_result(live_result, tool_name)

        # Compare schemas (allow live to have extra fields)
        try:
            assert_schema_matches(
                reference=fake_response,
                candidate=live_response,
                allow_extra_keys=True,
            )
        except AssertionError as e:
            # Log schema mismatch with both responses for debugging
            logger.error(
                "Schema mismatch for %s:\n"
                "Assertion: %s\n"
                "Fake response: %s\n"
                "Live response: %s",
                tool_name,
                str(e),
                json.dumps(fake_response, indent=2),
                json.dumps(live_response, indent=2),
            )
            raise


class TestSchemaDocumentation:
    """Tests that document expected schemas for reference."""

    def test_document_pal_codereview_schema(self, fake_mcp_server):
        """Document the expected PAL codereview response schema."""
        response = fake_mcp_server.invoke(
            "mcp__pal__codereview",
            CANONICAL_PAL_REQUESTS["mcp__pal__codereview"],
        )

        # This test serves as documentation of the expected schema
        expected_schema = {
            "success": bool,
            "data": {
                "issues_found": list,  # List of {severity, description}
                "review_type": str,  # "quick", "full", "security"
                "step_number": int,
                "total_steps": int,
                "next_step_required": bool,
                "findings": str,
                "confidence": str,  # "exploring" to "certain"
                "relevant_files": list,
            },
        }

        # Verify structure matches documentation
        assert isinstance(response["success"], bool)
        assert isinstance(response["data"]["issues_found"], list)
        assert isinstance(response["data"]["review_type"], str)
        assert isinstance(response["data"]["step_number"], int)

    def test_document_rube_search_tools_schema(self, fake_mcp_server):
        """Document the expected Rube search tools response schema."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            CANONICAL_RUBE_REQUESTS["mcp__rube__RUBE_SEARCH_TOOLS"],
        )

        # Expected schema documentation
        expected_schema = {
            "success": bool,
            "data": {
                "tools": list,  # List of {tool_slug, description, input_schema}
                "session_id": str,
                "total_tools": int,
            },
        }

        # Verify structure
        assert isinstance(response["success"], bool)
        assert isinstance(response["data"]["tools"], list)
        assert isinstance(response["data"]["session_id"], str)

        # Verify tool structure if tools exist
        if response["data"]["tools"]:
            tool = response["data"]["tools"][0]
            assert "tool_slug" in tool
            assert "description" in tool
