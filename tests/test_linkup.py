"""Tests for LinkUp integration built into RubeIntegration."""

from typing import Any, Dict, List

import pytest

from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry
from SuperClaude.Commands.executor import CommandContext
from SuperClaude.Commands.parser import ParsedCommand
from SuperClaude.Commands.registry import CommandMetadata
from SuperClaude.MCP.rube_integration import RubeIntegration


class DummyRube(RubeIntegration):
    """Stub RubeIntegration that records invocations without HTTP calls."""

    def __init__(self, config: Dict[str, Any] = None) -> None:
        super().__init__(config=config or {})
        self.calls: List[Dict[str, Any]] = []
        self._session_ready = True  # Skip init for tests

    async def invoke(self, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append({"tool": tool, "payload": payload})
        return {
            "status": "success",
            "tool": tool,
            "payload": payload,
        }


@pytest.mark.asyncio
async def test_linkup_search_invokes_with_expected_payload():
    """Test that linkup_search calls invoke with correct tool and payload."""
    rube = DummyRube(config={"linkup": {"default_output_type": "structured"}})

    response = await rube.linkup_search("latest pytest news", depth="deep")

    assert response["status"] == "success"
    assert rube.calls[0]["tool"] == "LINKUP_SEARCH"
    assert rube.calls[0]["payload"]["query"] == "latest pytest news"
    assert rube.calls[0]["payload"]["output_type"] == "structured"
    assert rube.calls[0]["payload"]["depth"] == "deep"


@pytest.mark.asyncio
async def test_linkup_batch_search_processes_multiple_queries():
    """Test that linkup_batch_search handles multiple queries with concurrency."""
    rube = DummyRube()

    queries = ["query one", "query two", "query three"]
    responses = await rube.linkup_batch_search(queries)

    assert len(responses) == 3
    assert all(r["status"] == "success" for r in responses)
    assert len(rube.calls) == 3
    assert {c["payload"]["query"] for c in rube.calls} == set(queries)


@pytest.mark.asyncio
async def test_linkup_batch_search_returns_empty_for_empty_input():
    """Test that linkup_batch_search handles empty query list."""
    rube = DummyRube()

    responses = await rube.linkup_batch_search([])

    assert responses == []
    assert len(rube.calls) == 0


@pytest.mark.asyncio
async def test_linkup_search_rejects_empty_query():
    """Test that linkup_search raises ValueError for empty queries."""
    rube = DummyRube()

    with pytest.raises(ValueError, match="LinkUp query cannot be empty"):
        await rube.linkup_search("")

    with pytest.raises(ValueError, match="LinkUp query cannot be empty"):
        await rube.linkup_search("   ")


@pytest.mark.asyncio
async def test_execute_linkup_queries_attaches_results():
    """Test executor integration with RubeIntegration linkup methods."""
    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)

    metadata = CommandMetadata(
        name="test",
        description="",
        category="test",
        complexity="standard",
        mcp_servers=["rube"],
    )
    parsed = ParsedCommand(
        name="test",
        raw_string="/sc:test --linkup --query 'pytest best practices'",
        flags={"linkup": True},
        parameters={"query": "pytest best practices"},
    )
    context = CommandContext(command=parsed, metadata=metadata)

    rube = DummyRube()
    executor.active_mcp_servers["rube"] = {"instance": rube, "config": {"linkup": {}}}

    result = await executor._execute_linkup_queries(context, scenario_hint="unit")

    assert result["status"] == "linkup_completed"
    assert "linkup_queries" in context.results
    stored = context.results["linkup_queries"][0]
    assert stored["query"] == "pytest best practices"
    assert stored["status"] == "completed"
    assert rube.calls[0]["tool"] == "LINKUP_SEARCH"


@pytest.mark.asyncio
async def test_execute_linkup_queries_handles_missing_query():
    """Test executor handles missing query parameter gracefully."""
    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)

    metadata = CommandMetadata(
        name="test",
        description="",
        category="test",
        complexity="standard",
        mcp_servers=["rube"],
    )
    parsed = ParsedCommand(
        name="test",
        raw_string="/sc:test --linkup",
        flags={"linkup": True},
    )
    context = CommandContext(command=parsed, metadata=metadata)

    executor.active_mcp_servers["rube"] = {
        "instance": DummyRube(),
        "config": {"linkup": {}},
    }

    result = await executor._execute_linkup_queries(context, scenario_hint="unit")

    assert result["status"] == "linkup_failed"
    assert any("LinkUp web search requires" in err for err in context.errors)
