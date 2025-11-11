"""Tests for LinkUp integration built on Rube MCP."""

from typing import Any, Dict, List

import pytest

from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry
from SuperClaude.Commands.executor import CommandContext
from SuperClaude.Commands.registry import CommandMetadata
from SuperClaude.Commands.parser import ParsedCommand
from SuperClaude.MCP import LinkUpClient


class DummyRube:
    """Simple stub that records LinkUp invocations."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    async def invoke(self, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append({"tool": tool, "payload": payload})
        return {
            "status": "success",
            "tool": tool,
            "payload": payload,
        }


@pytest.mark.asyncio
async def test_linkup_client_invokes_rube_with_expected_payload():
    rube = DummyRube()
    client = LinkUpClient(rube, config={"default_output_type": "structured"})

    response = await client.search("latest pytest news", depth="deep")

    assert response["status"] == "success"
    assert rube.calls[0]["tool"] == "LINKUP_SEARCH"
    assert rube.calls[0]["payload"]["query"] == "latest pytest news"
    assert rube.calls[0]["payload"]["output_type"] == "structured"


@pytest.mark.asyncio
async def test_execute_linkup_queries_attaches_results():
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

    executor.active_mcp_servers["rube"] = {"instance": DummyRube(), "config": {"linkup": {}}}

    result = await executor._execute_linkup_queries(context, scenario_hint="unit")

    assert result["status"] == "linkup_failed"
    assert any("LinkUp web search requires" in err for err in context.errors)
