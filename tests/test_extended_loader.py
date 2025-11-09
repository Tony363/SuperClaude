"""Integration-oriented tests for the extended agent loader."""

from __future__ import annotations

from typing import Iterable

import pytest

from SuperClaude.Agents.extended_loader import (
    AgentCategory,
    ExtendedAgentLoader,
    MatchScore,
)


@pytest.fixture
def extended_loader() -> Iterable[ExtendedAgentLoader]:
    """Provide a fresh loader instance backed by the real registry."""

    loader = ExtendedAgentLoader(cache_size=4, ttl_seconds=1)
    try:
        yield loader
    finally:
        loader.clear_cache()


def test_loader_discovers_all_categories(extended_loader: ExtendedAgentLoader) -> None:
    categories = extended_loader.list_categories()

    assert set(categories.keys()) == set(AgentCategory)
    assert all(count >= 0 for count in categories.values())
    assert extended_loader.get_statistics()["total_agents"] >= len(AgentCategory)


def test_agent_loading_uses_cache(extended_loader: ExtendedAgentLoader) -> None:
    agent = extended_loader.load_agent("general-purpose")
    assert agent is not None

    cached = extended_loader.load_agent("general-purpose")
    assert cached is agent

    stats = extended_loader.get_statistics()
    assert stats["cache_hits"] >= 1
    assert stats["cache_hit_rate"] > 0


def test_cache_respects_ttl_without_sleep(extended_loader: ExtendedAgentLoader) -> None:
    extended_loader.ttl = 1

    first = extended_loader.load_agent("refactoring-expert")
    assert first is not None

    cache_entry = extended_loader._cache.get("refactoring-expert")
    assert cache_entry, "expected cache entry to exist"
    cache_entry["timestamp"] -= extended_loader.ttl + 5

    second = extended_loader.load_agent("refactoring-expert")
    assert second is not None
    assert second is not first


def test_agent_selection_prefers_specialists(extended_loader: ExtendedAgentLoader) -> None:
    context = {
        "task": "Optimize a python machine learning pipeline",
        "files": ["train.py", "model.py"],
        "languages": ["python"],
        "domains": ["ml", "ai"],
        "keywords": ["tensorflow", "model", "optimizer"],
    }

    matches = extended_loader.select_agent(context, top_n=5)

    assert matches
    assert isinstance(matches[0], MatchScore)

    primary = matches[0]
    metadata = extended_loader._agent_metadata.get(primary.agent_id)
    assert metadata is not None
    assert "python" in {lang.lower() for lang in metadata.languages}
    assert primary.breakdown.get("keywords", 0) > 0


def test_preload_top_agents_uses_access_patterns(extended_loader: ExtendedAgentLoader) -> None:
    for _ in range(3):
        extended_loader.load_agent("general-purpose")
    for _ in range(2):
        extended_loader.load_agent("technical-writer")
    extended_loader.load_agent("performance-engineer")

    extended_loader.clear_cache()

    loaded_count = extended_loader.preload_top_agents(count=3)

    stats = extended_loader.get_statistics()
    top_agents = set(stats["top_accessed_agents"].keys())

    assert loaded_count == 3
    assert stats["cached_agents"] == 3
    assert {"general-purpose", "technical-writer", "performance-engineer"}.issubset(top_agents)


def test_explain_selection_returns_breakdown(extended_loader: ExtendedAgentLoader) -> None:
    context = {
        "task": "Design a resilient kubernetes deployment for our api",
        "files": ["infra/k8s/deployment.yaml"],
        "languages": ["yaml"],
        "domains": ["kubernetes", "infrastructure"],
        "keywords": ["k8s", "deployment"],
    }

    match = extended_loader.select_agent(context, top_n=1)[0]
    explanation = extended_loader.explain_selection(match.agent_id, context)

    assert explanation["agent_id"] == match.agent_id
    assert explanation["confidence"] == match.confidence
    assert set(["keywords", "domains", "languages", "file_patterns"]).issubset(explanation["breakdown"].keys())


def test_explain_selection_handles_missing_metadata(extended_loader: ExtendedAgentLoader) -> None:
    extended_loader._agent_metadata.pop("general-purpose", None)
    explanation = extended_loader.explain_selection("general-purpose", {"task": "triage"})

    assert explanation == {'error': 'Agent not found: general-purpose'}
