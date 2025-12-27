"""Shared pytest configuration for SuperClaude test suite."""

from __future__ import annotations

import asyncio
import inspect
import os
import shutil
from pathlib import Path

import pytest

# Try to import usage_tracker - if it fails, archived SDK is not available
try:
    from SuperClaude.Agents import usage_tracker

    _ARCHIVED_SDK_AVAILABLE = True
except ImportError:
    usage_tracker = None  # type: ignore[assignment]
    _ARCHIVED_SDK_AVAILABLE = False

# List of test files/directories that require the archived SDK
# These will be ignored during collection if archived SDK imports fail
_ARCHIVED_SDK_TEST_FILES = [
    "test_agents.py",
    "test_commands.py",
    "test_extended_loader.py",
    "test_integration.py",
    "test_agents_cli.py",
    "test_cli.py",
    "test_skills_integration.py",
    "test_version.py",
    "agents",
    "commands",
    "sdk/test_coordination_integration.py",
    "sdk/test_selector_integration.py",
    "sdk/test_executor.py",
    "telemetry/test_factory.py",
]


def pytest_ignore_collect(collection_path: Path, config) -> bool | None:
    """Ignore test files that require the archived SDK when it's not available."""
    if _ARCHIVED_SDK_AVAILABLE:
        return None  # Don't ignore anything if SDK is available

    # Get relative path from tests directory
    tests_dir = Path(__file__).parent
    try:
        rel_path = collection_path.relative_to(tests_dir)
        rel_path_str = str(rel_path)
    except ValueError:
        return None

    # Check if this file/directory should be ignored
    for pattern in _ARCHIVED_SDK_TEST_FILES:
        if rel_path_str == pattern or rel_path_str.startswith(pattern + "/"):
            return True

    return None


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Set deterministic environment defaults for the test session."""

    metrics_dir = tmp_path_factory.mktemp("metrics")
    os.environ.setdefault("SUPERCLAUDE_METRICS_DIR", str(metrics_dir))
    os.environ.setdefault("SUPERCLAUDE_OFFLINE_MODE", "1")
    os.environ.setdefault("SC_NETWORK_MODE", "offline")

    yield Path(metrics_dir)

    # Ensure metric artefacts from one run do not leak into another.
    if usage_tracker is not None:
        usage_tracker.reset_usage_stats(for_tests=True)
    if Path(metrics_dir).exists():
        shutil.rmtree(metrics_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_agent_usage() -> None:
    """Clear agent usage counters before and after every test."""
    if usage_tracker is not None:
        usage_tracker.reset_usage_stats(for_tests=True)
    yield
    if usage_tracker is not None:
        usage_tracker.reset_usage_stats(for_tests=True)


@pytest.fixture(autouse=True)
def reset_working_directory() -> None:
    """Ensure working directory is reset after each test.

    Some tests use monkeypatch.chdir() to change directories, but if a test
    fails or if multiple fixtures interact, the working directory may not
    be properly restored. This fixture ensures we always return to the
    original directory.
    """
    original_cwd = os.getcwd()
    yield
    if os.getcwd() != original_cwd:
        os.chdir(original_cwd)


@pytest.fixture(autouse=True)
def reset_superclaude_env_vars() -> None:
    """Reset SuperClaude environment variables between tests.

    CommandExecutor uses setdefault() to set SUPERCLAUDE_REPO_ROOT and
    SUPERCLAUDE_METRICS_DIR, which means values persist across tests.
    This can cause cross-test pollution when different tests use
    different repo_root values.
    """
    # Store original values
    original_repo_root = os.environ.get("SUPERCLAUDE_REPO_ROOT")
    original_metrics_dir = os.environ.get("SUPERCLAUDE_METRICS_DIR")

    yield

    # Restore original values (or remove if not set originally)
    if original_repo_root is None:
        os.environ.pop("SUPERCLAUDE_REPO_ROOT", None)
    else:
        os.environ["SUPERCLAUDE_REPO_ROOT"] = original_repo_root

    if original_metrics_dir is None:
        os.environ.pop("SUPERCLAUDE_METRICS_DIR", None)
    else:
        os.environ["SUPERCLAUDE_METRICS_DIR"] = original_metrics_dir


@pytest.fixture(scope="session")
def fixture_root() -> Path:
    """Return the path containing test fixtures."""

    return Path(__file__).parent / "fixtures"


def pytest_pyfunc_call(pyfuncitem):
    marker = pyfuncitem.keywords.get("asyncio")
    test_func = pyfuncitem.obj
    if marker and inspect.iscoroutinefunction(test_func):
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            argnames = pyfuncitem._fixtureinfo.argnames  # type: ignore[attr-defined]
            kwargs = {name: pyfuncitem.funcargs[name] for name in argnames}
            loop.run_until_complete(test_func(**kwargs))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            asyncio.set_event_loop(None)
        return True
    return None
