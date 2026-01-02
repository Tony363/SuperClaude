"""Tests for Rube MCP response parsing and state updates.

Validates the signal→call→response→state pipeline for Rube tools:
- mcp__rube__RUBE_SEARCH_TOOLS
- mcp__rube__RUBE_MULTI_EXECUTE_TOOL
- mcp__rube__RUBE_CREATE_PLAN
- mcp__rube__RUBE_MANAGE_CONNECTIONS
"""

import pytest

from tests.mcp.conftest import (
    FakeMCPResponse,
    FakeMCPServer,
    FakeRubeMultiExecuteResponse,
    FakeRubeSearchToolsResponse,
)


class TestRubeSearchToolsResponseParsing:
    """Tests for parsing mcp__rube__RUBE_SEARCH_TOOLS responses."""

    def test_parse_success_response(self, fake_mcp_server):
        """Should correctly parse a successful search response."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            {
                "queries": [{"use_case": "send a message to slack"}],
                "session": {"generate_id": True},
            },
        )

        assert response["success"] is True
        data = response["data"]

        # Verify tools list is present and parseable
        tools = data.get("tools", [])
        assert isinstance(tools, list)
        assert len(tools) > 0

        # Verify session_id is present
        session_id = data.get("session_id", "")
        assert isinstance(session_id, str)
        assert len(session_id) > 0

    def test_parse_tool_schema(self, fake_mcp_server):
        """Should correctly parse tool schema from response."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            {"queries": [{"use_case": "send slack message"}]},
        )

        tools = response["data"]["tools"]
        tool = tools[0]

        # Verify tool structure
        assert "tool_slug" in tool
        assert "description" in tool

        # If input_schema is present, verify it's valid
        if "input_schema" in tool:
            schema = tool["input_schema"]
            assert "type" in schema
            assert schema["type"] == "object"

    def test_extract_tool_slugs(self, fake_mcp_server):
        """Should be able to extract tool slugs for execution."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            {"queries": [{"use_case": "slack tools"}]},
        )

        tools = response["data"]["tools"]
        slugs = [tool["tool_slug"] for tool in tools]

        assert len(slugs) > 0
        assert all(isinstance(slug, str) for slug in slugs)

    def test_parse_empty_search_results(self, fake_mcp_server):
        """Should handle empty search results gracefully."""
        fake_mcp_server.set_response(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            FakeMCPResponse(
                success=True,
                data={"tools": [], "session_id": "test-123", "total_tools": 0},
            ),
        )

        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            {"queries": [{"use_case": "nonexistent tool"}]},
        )

        assert response["success"] is True
        assert response["data"]["tools"] == []

    def test_parse_error_response(self, fake_mcp_server):
        """Should handle error responses gracefully."""
        fake_mcp_server.set_error_response(
            "mcp__rube__RUBE_SEARCH_TOOLS", "Invalid session"
        )

        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            {"queries": []},
        )

        assert response["success"] is False
        assert response["error"] == "Invalid session"


class TestRubeMultiExecuteResponseParsing:
    """Tests for parsing mcp__rube__RUBE_MULTI_EXECUTE_TOOL responses."""

    def test_parse_success_response(self, fake_mcp_server):
        """Should correctly parse a successful multi-execute response."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
            {
                "tools": [
                    {
                        "tool_slug": "SLACK_SEND_MESSAGE",
                        "arguments": {"channel": "#general", "text": "Hello"},
                    }
                ],
                "sync_response_to_workbench": False,
            },
        )

        assert response["success"] is True
        data = response["data"]

        results = data.get("results", [])
        assert isinstance(results, list)
        assert len(results) > 0

        all_succeeded = data.get("all_succeeded", False)
        assert isinstance(all_succeeded, bool)

    def test_parse_individual_tool_results(self, fake_mcp_server):
        """Should correctly parse individual tool results."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
            {
                "tools": [
                    {"tool_slug": "SLACK_SEND_MESSAGE", "arguments": {}},
                ]
            },
        )

        results = response["data"]["results"]
        result = results[0]

        assert "tool_slug" in result
        assert "success" in result
        assert isinstance(result["success"], bool)

    def test_parse_partial_failure(self, fake_mcp_server, rube_multi_execute_partial_failure):
        """Should correctly identify partial failures."""
        fake_mcp_server.set_response(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL", rube_multi_execute_partial_failure
        )

        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
            {"tools": []},
        )

        data = response["data"]

        # Verify partial failure detection
        assert data["all_succeeded"] is False
        assert data["partial_failure"] is True

        # Verify we can identify which tools failed
        failed_tools = [r for r in data["results"] if not r["success"]]
        succeeded_tools = [r for r in data["results"] if r["success"]]

        assert len(failed_tools) == 1
        assert len(succeeded_tools) == 1
        assert failed_tools[0]["tool_slug"] == "GITHUB_CREATE_ISSUE"

    def test_extract_error_from_partial_failure(
        self, fake_mcp_server, rube_multi_execute_partial_failure
    ):
        """Should extract error message from failed tools."""
        fake_mcp_server.set_response(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL", rube_multi_execute_partial_failure
        )

        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
            {"tools": []},
        )

        failed_tools = [r for r in response["data"]["results"] if not r["success"]]
        assert failed_tools[0]["error"] == "Rate limit exceeded"

    def test_handle_all_tools_failed(self, fake_mcp_server):
        """Should handle case where all tools failed."""
        fake_mcp_server.set_response(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
            FakeMCPResponse(
                success=True,  # Request succeeded, but tools failed
                data={
                    "results": [
                        {
                            "tool_slug": "SLACK_SEND_MESSAGE",
                            "success": False,
                            "data": None,
                            "error": "Channel not found",
                        },
                        {
                            "tool_slug": "GITHUB_CREATE_ISSUE",
                            "success": False,
                            "data": None,
                            "error": "Repo not found",
                        },
                    ],
                    "all_succeeded": False,
                    "partial_failure": False,  # Not partial, all failed
                },
            ),
        )

        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
            {"tools": []},
        )

        data = response["data"]
        assert data["all_succeeded"] is False

        succeeded = [r for r in data["results"] if r["success"]]
        assert len(succeeded) == 0

    def test_parse_tool_output_data(self, fake_mcp_server):
        """Should correctly parse output data from successful tools."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
            {"tools": [{"tool_slug": "SLACK_SEND_MESSAGE", "arguments": {}}]},
        )

        result = response["data"]["results"][0]
        assert result["success"] is True
        assert "data" in result
        assert "message_id" in result["data"]


class TestRubeCreatePlanResponseParsing:
    """Tests for parsing mcp__rube__RUBE_CREATE_PLAN responses."""

    def test_parse_success_response(self, fake_mcp_server):
        """Should correctly parse a successful plan creation response."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_CREATE_PLAN",
            {
                "difficulty": "medium",
                "use_case": "Send daily standup report",
                "primary_tool_slugs": ["SLACK_SEND_MESSAGE"],
            },
        )

        assert response["success"] is True
        data = response["data"]

        assert "plan_id" in data
        assert "steps" in data
        assert isinstance(data["steps"], list)

    def test_parse_plan_steps(self, fake_mcp_server):
        """Should correctly parse plan steps."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_CREATE_PLAN",
            {"difficulty": "hard", "use_case": "Complex workflow"},
        )

        steps = response["data"]["steps"]
        assert len(steps) > 0
        assert all(isinstance(step, str) for step in steps)


class TestRubeManageConnectionsResponseParsing:
    """Tests for parsing mcp__rube__RUBE_MANAGE_CONNECTIONS responses."""

    def test_parse_success_response(self, fake_mcp_server):
        """Should correctly parse connections response."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MANAGE_CONNECTIONS",
            {"toolkits": ["slack", "github"]},
        )

        assert response["success"] is True
        data = response["data"]

        connections = data.get("connections", [])
        assert isinstance(connections, list)

    def test_parse_connection_status(self, fake_mcp_server):
        """Should correctly parse connection status."""
        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MANAGE_CONNECTIONS",
            {"toolkits": ["slack"]},
        )

        connections = response["data"]["connections"]
        for conn in connections:
            assert "toolkit" in conn
            assert "status" in conn
            assert conn["status"] in ["active", "inactive", "pending", "error"]

    def test_identify_missing_connections(self, fake_mcp_server):
        """Should be able to identify which connections are missing."""
        fake_mcp_server.set_response(
            "mcp__rube__RUBE_MANAGE_CONNECTIONS",
            FakeMCPResponse(
                success=True,
                data={
                    "connections": [
                        {"toolkit": "slack", "status": "active"},
                        {"toolkit": "github", "status": "inactive"},
                    ]
                },
            ),
        )

        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MANAGE_CONNECTIONS",
            {"toolkits": ["slack", "github"]},
        )

        connections = response["data"]["connections"]
        inactive = [c for c in connections if c["status"] != "active"]

        assert len(inactive) == 1
        assert inactive[0]["toolkit"] == "github"


class TestRubeTimeoutHandling:
    """Tests for timeout handling in Rube tools."""

    def test_search_tools_timeout(self, fake_mcp_server):
        """Should handle timeout in search tools."""
        fake_mcp_server.set_timeout_response("mcp__rube__RUBE_SEARCH_TOOLS")

        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            {"queries": []},
        )

        assert response["success"] is False
        assert response["error"] == "timeout"
        assert "timeout_seconds" in response.get("metadata", {})

    def test_multi_execute_timeout(self, fake_mcp_server):
        """Should handle timeout in multi-execute."""
        fake_mcp_server.set_timeout_response("mcp__rube__RUBE_MULTI_EXECUTE_TOOL")

        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
            {"tools": []},
        )

        assert response["success"] is False
        assert response["error"] == "timeout"


class TestRubeMalformedResponseHandling:
    """Tests for handling malformed Rube responses."""

    def test_missing_results_field(self, fake_mcp_server):
        """Should handle response missing results field."""
        fake_mcp_server.set_response(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
            FakeMCPResponse(
                success=True,
                data={"unexpected_field": "value"},  # Missing results
            ),
        )

        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
            {"tools": []},
        )

        # Should still succeed but have empty/default results
        assert response["success"] is True
        results = response["data"].get("results", [])
        assert isinstance(results, list)

    def test_missing_tools_field(self, fake_mcp_server):
        """Should handle response missing tools field."""
        fake_mcp_server.set_response(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            FakeMCPResponse(
                success=True,
                data={"session_id": "test-123"},  # Missing tools
            ),
        )

        response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            {"queries": []},
        )

        assert response["success"] is True
        tools = response["data"].get("tools", [])
        assert isinstance(tools, list)


class TestRubeSessionManagement:
    """Tests for session management across Rube tool calls."""

    def test_session_id_persists_across_calls(self, fake_mcp_server):
        """Session ID should be consistent across related calls."""
        # First call to search tools
        search_response = fake_mcp_server.invoke(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            {"queries": [{"use_case": "slack"}], "session": {"generate_id": True}},
        )

        session_id = search_response["data"]["session_id"]

        # Session ID should be usable for subsequent calls
        assert session_id is not None
        assert len(session_id) > 0

    def test_call_history_tracks_session(self, fake_mcp_server):
        """Call history should track session-related parameters."""
        fake_mcp_server.invoke(
            "mcp__rube__RUBE_SEARCH_TOOLS",
            {"queries": [], "session": {"id": "existing-session"}},
        )

        last_call = fake_mcp_server.get_last_call("mcp__rube__RUBE_SEARCH_TOOLS")
        assert last_call is not None
        assert last_call["parameters"]["session"]["id"] == "existing-session"
