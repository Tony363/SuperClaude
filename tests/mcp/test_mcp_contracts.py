"""Contract tests for MCP tool schemas.

Validates JSON schema / typed contracts for:
- PAL MCP tools (codereview, debug, thinkdeep, consensus)
- Rube MCP tools (RUBE_SEARCH_TOOLS, RUBE_MULTI_EXECUTE_TOOL)

These tests run without a model, without Claude; just parser + adapter validation.
"""

from tests.mcp.conftest import (
    FakeMCPResponse,
    FakeMCPServer,
    FakeRubeMultiExecuteResponse,
)


class TestPALCodeReviewContract:
    """Contract tests for mcp__pal__codereview response schema."""

    def test_required_fields_present(self, pal_codereview_response):
        """Response must contain all required fields."""
        data = pal_codereview_response.to_dict()["data"]

        required_fields = [
            "issues_found",
            "review_type",
            "step_number",
            "total_steps",
            "next_step_required",
            "findings",
            "confidence",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_issues_found_is_list(self, pal_codereview_response):
        """issues_found must be a list."""
        data = pal_codereview_response.to_dict()["data"]
        assert isinstance(data["issues_found"], list)

    def test_issue_structure(self, pal_codereview_with_issues):
        """Each issue must have severity and description."""
        data = pal_codereview_with_issues.to_dict()["data"]

        for issue in data["issues_found"]:
            assert "severity" in issue, "Issue missing severity"
            assert "description" in issue, "Issue missing description"
            assert issue["severity"] in [
                "critical",
                "high",
                "medium",
                "low",
            ], f"Invalid severity: {issue['severity']}"

    def test_step_number_positive_integer(self, pal_codereview_response):
        """step_number must be a positive integer."""
        data = pal_codereview_response.to_dict()["data"]
        assert isinstance(data["step_number"], int)
        assert data["step_number"] >= 1

    def test_total_steps_positive_integer(self, pal_codereview_response):
        """total_steps must be a positive integer."""
        data = pal_codereview_response.to_dict()["data"]
        assert isinstance(data["total_steps"], int)
        assert data["total_steps"] >= 1

    def test_next_step_required_boolean(self, pal_codereview_response):
        """next_step_required must be a boolean."""
        data = pal_codereview_response.to_dict()["data"]
        assert isinstance(data["next_step_required"], bool)

    def test_review_type_valid_enum(self, pal_codereview_response):
        """review_type must be one of the valid types."""
        data = pal_codereview_response.to_dict()["data"]
        valid_types = ["full", "quick", "security", "performance"]
        assert data["review_type"] in valid_types, f"Invalid review_type: {data['review_type']}"

    def test_confidence_valid_enum(self, pal_codereview_response):
        """confidence must be one of the valid levels."""
        data = pal_codereview_response.to_dict()["data"]
        valid_levels = [
            "exploring",
            "low",
            "medium",
            "high",
            "very_high",
            "almost_certain",
            "certain",
        ]
        assert data["confidence"] in valid_levels, f"Invalid confidence: {data['confidence']}"


class TestPALDebugContract:
    """Contract tests for mcp__pal__debug response schema."""

    def test_required_fields_present(self, pal_debug_response):
        """Response must contain all required fields."""
        data = pal_debug_response.to_dict()["data"]

        required_fields = [
            "hypothesis",
            "confidence",
            "step_number",
            "total_steps",
            "next_step_required",
            "findings",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_hypothesis_is_string(self, pal_debug_response):
        """hypothesis must be a non-empty string."""
        data = pal_debug_response.to_dict()["data"]
        assert isinstance(data["hypothesis"], str)
        assert len(data["hypothesis"]) > 0

    def test_confidence_valid_enum(self, pal_debug_response):
        """confidence must be one of the valid levels."""
        data = pal_debug_response.to_dict()["data"]
        valid_levels = [
            "exploring",
            "low",
            "medium",
            "high",
            "very_high",
            "almost_certain",
            "certain",
        ]
        assert data["confidence"] in valid_levels, f"Invalid confidence: {data['confidence']}"


class TestRubeSearchToolsContract:
    """Contract tests for mcp__rube__RUBE_SEARCH_TOOLS response schema."""

    def test_required_fields_present(self, rube_search_response):
        """Response must contain all required fields."""
        data = rube_search_response.to_dict()["data"]

        required_fields = ["tools", "session_id"]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_tools_is_list(self, rube_search_response):
        """tools must be a list."""
        data = rube_search_response.to_dict()["data"]
        assert isinstance(data["tools"], list)

    def test_tool_structure(self, rube_search_response):
        """Each tool must have required fields."""
        data = rube_search_response.to_dict()["data"]

        for tool in data["tools"]:
            assert "tool_slug" in tool, "Tool missing tool_slug"
            assert "description" in tool, "Tool missing description"
            assert isinstance(tool["tool_slug"], str)
            assert len(tool["tool_slug"]) > 0

    def test_tool_slug_format(self, rube_search_response):
        """tool_slug should be uppercase with underscores."""
        data = rube_search_response.to_dict()["data"]

        for tool in data["tools"]:
            slug = tool["tool_slug"]
            # Should be uppercase letters, numbers, and underscores
            assert slug == slug.upper(), f"Slug should be uppercase: {slug}"
            assert "_" in slug or slug.isalpha(), f"Slug format invalid: {slug}"

    def test_session_id_format(self, rube_search_response):
        """session_id should be a non-empty string."""
        data = rube_search_response.to_dict()["data"]
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0


class TestRubeMultiExecuteContract:
    """Contract tests for mcp__rube__RUBE_MULTI_EXECUTE_TOOL response schema."""

    def test_required_fields_present(self):
        """Response must contain all required fields."""
        response = FakeRubeMultiExecuteResponse()
        data = response.to_dict()["data"]

        required_fields = ["results", "all_succeeded", "partial_failure"]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_results_is_list(self):
        """results must be a list."""
        response = FakeRubeMultiExecuteResponse()
        data = response.to_dict()["data"]
        assert isinstance(data["results"], list)

    def test_result_structure(self):
        """Each result must have required fields."""
        response = FakeRubeMultiExecuteResponse()
        data = response.to_dict()["data"]

        for result in data["results"]:
            assert "tool_slug" in result, "Result missing tool_slug"
            assert "success" in result, "Result missing success"
            assert isinstance(result["success"], bool)

    def test_partial_failure_consistent(self, rube_multi_execute_partial_failure):
        """partial_failure should match all_succeeded."""
        data = rube_multi_execute_partial_failure.to_dict()["data"]

        if data["all_succeeded"]:
            assert data["partial_failure"] is False
        else:
            # Check if any succeeded and any failed
            successes = [r["success"] for r in data["results"]]
            if any(successes) and not all(successes):
                assert data["partial_failure"] is True


class TestMCPResponseEnvelope:
    """Contract tests for the MCP response envelope structure."""

    def test_success_response_structure(self, fake_mcp_server):
        """Success response must have correct structure."""
        response = fake_mcp_server.invoke(
            "mcp__pal__codereview",
            {"files": ["main.py"], "review_type": "full"},
        )

        assert "success" in response
        assert "data" in response
        assert response["success"] is True

    def test_error_response_structure(self, fake_mcp_server):
        """Error response must have correct structure."""
        fake_mcp_server.set_error_response("mcp__pal__codereview", "Authentication failed")

        response = fake_mcp_server.invoke(
            "mcp__pal__codereview",
            {"files": ["main.py"]},
        )

        assert "success" in response
        assert "error" in response
        assert response["success"] is False
        assert response["error"] == "Authentication failed"

    def test_timeout_response_structure(self, fake_mcp_server):
        """Timeout response must have correct structure."""
        fake_mcp_server.set_timeout_response("mcp__pal__codereview")

        response = fake_mcp_server.invoke(
            "mcp__pal__codereview",
            {"files": ["main.py"]},
        )

        assert response["success"] is False
        assert response["error"] == "timeout"
        assert "metadata" in response
        assert "timeout_seconds" in response["metadata"]

    def test_unknown_tool_response(self, fake_mcp_server):
        """Unknown tool should return error."""
        response = fake_mcp_server.invoke(
            "mcp__unknown__tool",
            {"param": "value"},
        )

        assert response["success"] is False
        assert "Unknown tool" in response["error"]


class TestFakeMCPServerBehavior:
    """Tests for the fake MCP server test infrastructure."""

    def test_call_history_tracked(self, fake_mcp_server):
        """All calls should be tracked in history."""
        fake_mcp_server.invoke("mcp__pal__codereview", {"files": ["a.py"]})
        fake_mcp_server.invoke("mcp__pal__debug", {"issue": "crash"})
        fake_mcp_server.invoke("mcp__pal__codereview", {"files": ["b.py"]})

        assert fake_mcp_server.get_call_count("mcp__pal__codereview") == 2
        assert fake_mcp_server.get_call_count("mcp__pal__debug") == 1

    def test_last_call_retrieved(self, fake_mcp_server):
        """Should retrieve the last call to a specific tool."""
        fake_mcp_server.invoke("mcp__pal__codereview", {"files": ["a.py"]})
        fake_mcp_server.invoke("mcp__pal__codereview", {"files": ["b.py"]})

        last_call = fake_mcp_server.get_last_call("mcp__pal__codereview")
        assert last_call is not None
        assert last_call["parameters"]["files"] == ["b.py"]

    def test_reset_clears_history(self, fake_mcp_server):
        """Reset should clear call history."""
        fake_mcp_server.invoke("mcp__pal__codereview", {"files": ["a.py"]})
        fake_mcp_server.reset()

        assert fake_mcp_server.get_call_count("mcp__pal__codereview") == 0
        assert len(fake_mcp_server.call_history) == 0

    def test_custom_response_override(self, fake_mcp_server):
        """Custom response should override default."""
        custom_response = FakeMCPResponse(
            success=True,
            data={"custom": "data"},
        )
        fake_mcp_server.set_response("mcp__pal__codereview", custom_response)

        response = fake_mcp_server.invoke("mcp__pal__codereview", {})
        assert response["data"]["custom"] == "data"


class TestFakeMCPServerFixtureLoading:
    """Tests for FakeMCPServer.from_fixtures() functionality."""

    def test_from_fixtures_nonexistent_directory(self, tmp_path):
        """Should return empty server for nonexistent directory."""
        server = FakeMCPServer.from_fixtures(tmp_path / "nonexistent")
        # Should still work with default responses
        response = server.invoke("mcp__pal__codereview", {"files": ["main.py"]})
        assert response["success"] is True

    def test_from_fixtures_empty_directory(self, tmp_path):
        """Should return empty server for empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        server = FakeMCPServer.from_fixtures(empty_dir)
        assert len(server.captured_fixtures) == 0

    def test_from_fixtures_loads_json_file(self, tmp_path):
        """Should load fixtures from .json files."""
        import json

        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()

        fixture = {
            "tool_name": "mcp__pal__codereview",
            "request": {"files": ["test.py"]},
            "response": {"success": True, "data": {"custom": "from_fixture"}},
        }

        with open(fixture_dir / "codereview.json", "w") as f:
            json.dump(fixture, f)

        server = FakeMCPServer.from_fixtures(fixture_dir)
        assert "mcp__pal__codereview" in server.captured_fixtures
        assert len(server.captured_fixtures["mcp__pal__codereview"]) == 1

    def test_from_fixtures_loads_jsonl_file(self, tmp_path):
        """Should load fixtures from .jsonl files."""
        import json

        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()

        fixtures = [
            {
                "tool_name": "mcp__pal__codereview",
                "request": {"files": ["a.py"]},
                "response": {"success": True, "data": {"id": 1}},
            },
            {
                "tool_name": "mcp__pal__codereview",
                "request": {"files": ["b.py"]},
                "response": {"success": True, "data": {"id": 2}},
            },
            {
                "tool_name": "mcp__pal__debug",
                "request": {"issue": "error"},
                "response": {"success": True, "data": {"id": 3}},
            },
        ]

        with open(fixture_dir / "captured.jsonl", "w") as f:
            for fixture in fixtures:
                f.write(json.dumps(fixture) + "\n")

        server = FakeMCPServer.from_fixtures(fixture_dir)
        assert len(server.captured_fixtures["mcp__pal__codereview"]) == 2
        assert len(server.captured_fixtures["mcp__pal__debug"]) == 1

    def test_captured_fixture_takes_precedence(self, tmp_path):
        """Captured fixtures should override default responses for exact matches."""
        import json

        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()

        fixture = {
            "tool_name": "mcp__pal__codereview",
            "request": {"files": ["exact_match.py"]},
            "response": {"success": True, "data": {"from_fixture": True}},
        }

        with open(fixture_dir / "captured.json", "w") as f:
            json.dump(fixture, f)

        server = FakeMCPServer.from_fixtures(fixture_dir)

        # Exact match should use fixture
        response = server.invoke("mcp__pal__codereview", {"files": ["exact_match.py"]})
        assert response["data"]["from_fixture"] is True

        # Non-matching request should use default
        response = server.invoke("mcp__pal__codereview", {"files": ["other.py"]})
        assert "from_fixture" not in response.get("data", {})

    def test_invalid_fixture_skipped(self, tmp_path):
        """Invalid fixtures should be skipped without error."""
        import json

        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()

        # Missing required fields
        invalid_fixture = {"tool_name": "mcp__pal__codereview"}  # Missing request/response

        with open(fixture_dir / "invalid.json", "w") as f:
            json.dump(invalid_fixture, f)

        server = FakeMCPServer.from_fixtures(fixture_dir)
        assert len(server.captured_fixtures["mcp__pal__codereview"]) == 0

    def test_malformed_json_skipped(self, tmp_path):
        """Malformed JSON files should be skipped."""
        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()

        with open(fixture_dir / "malformed.json", "w") as f:
            f.write("not valid json {")

        # Should not raise, just log warning
        server = FakeMCPServer.from_fixtures(fixture_dir)
        assert len(server.captured_fixtures) == 0
