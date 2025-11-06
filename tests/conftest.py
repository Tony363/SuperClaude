"""Shared pytest configuration for SuperClaude test suite."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from SuperClaude.Agents import usage_tracker


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Set deterministic environment defaults for the test session."""

    metrics_dir = tmp_path_factory.mktemp("metrics")
    os.environ.setdefault("SUPERCLAUDE_METRICS_DIR", str(metrics_dir))
    os.environ.setdefault("SUPERCLAUDE_OFFLINE_MODE", "1")
    os.environ.setdefault("SC_NETWORK_MODE", "offline")

    yield Path(metrics_dir)

    # Ensure metric artefacts from one run do not leak into another.
    usage_tracker.reset_usage_stats(for_tests=True)
    if Path(metrics_dir).exists():
        shutil.rmtree(metrics_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_agent_usage() -> None:
    """Clear agent usage counters before and after every test."""

    usage_tracker.reset_usage_stats(for_tests=True)
    yield
    usage_tracker.reset_usage_stats(for_tests=True)


@pytest.fixture(scope="session")
def fixture_root() -> Path:
    """Return the path containing test fixtures."""

    return Path(__file__).parent / "fixtures"

