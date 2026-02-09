"""Pytest fixtures for E2E application generation tests."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest
import yaml


@pytest.fixture(scope="session")
def e2e_config() -> dict[str, Any]:
    """Load E2E test configuration."""
    config_path = Path(__file__).parent.parent.parent / "evals" / "e2e_apps.yaml"
    if not config_path.exists():
        pytest.skip("E2E config not found")

    with open(config_path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def e2e_apps(e2e_config: dict[str, Any]) -> dict[str, Any]:
    """Get all app configurations."""
    return e2e_config.get("apps", {})


@pytest.fixture(scope="session")
def e2e_settings(e2e_config: dict[str, Any]) -> dict[str, Any]:
    """Get global E2E settings."""
    return e2e_config.get("settings", {})


@pytest.fixture
def e2e_workdir() -> Generator[Path, None, None]:
    """Create and clean up a temporary working directory for E2E tests."""
    workdir = Path(tempfile.mkdtemp(prefix="e2e_test_"))
    yield workdir

    # Cleanup
    if workdir.exists():
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.fixture
def python_validator():
    """Get Python validator instance."""
    from tests.e2e.validators import PythonValidator

    return PythonValidator()


@pytest.fixture
def node_validator():
    """Get Node.js validator instance."""
    from tests.e2e.validators import NodeValidator

    return NodeValidator()


@pytest.fixture
def rust_validator():
    """Get Rust validator instance."""
    from tests.e2e.validators import RustValidator

    return RustValidator()


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "e2e: marks tests as end-to-end application generation tests (may be slow)",
    )
    config.addinivalue_line(
        "markers",
        "e2e_python: marks tests as Python E2E tests",
    )
    config.addinivalue_line(
        "markers",
        "e2e_node: marks tests as Node.js E2E tests",
    )
    config.addinivalue_line(
        "markers",
        "e2e_rust: marks tests as Rust E2E tests",
    )


def pytest_collection_modifyitems(config, items):
    """Skip E2E tests marked with @pytest.mark.e2e if ANTHROPIC_API_KEY is not set."""
    skip_e2e = pytest.mark.skip(reason="ANTHROPIC_API_KEY not set")

    for item in items:
        # Only skip tests explicitly marked with @pytest.mark.e2e
        # Not tests that happen to be in a path containing 'e2e'
        markers = [m.name for m in item.iter_markers()]
        if "e2e" in markers:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                item.add_marker(skip_e2e)


# Fixtures for specific app types


@pytest.fixture
def python_calculator_config(e2e_apps: dict[str, Any]) -> dict[str, Any]:
    """Get Python CLI calculator configuration."""
    return e2e_apps.get("python-cli-calculator", {})


@pytest.fixture
def python_rest_api_config(e2e_apps: dict[str, Any]) -> dict[str, Any]:
    """Get Python REST API configuration."""
    return e2e_apps.get("python-rest-api", {})


@pytest.fixture
def react_todo_config(e2e_apps: dict[str, Any]) -> dict[str, Any]:
    """Get React todo component configuration."""
    return e2e_apps.get("react-todo-component", {})


@pytest.fixture
def node_cli_config(e2e_apps: dict[str, Any]) -> dict[str, Any]:
    """Get Node CLI tool configuration."""
    return e2e_apps.get("node-cli-tool", {})


@pytest.fixture
def rust_fibonacci_config(e2e_apps: dict[str, Any]) -> dict[str, Any]:
    """Get Rust fibonacci configuration."""
    return e2e_apps.get("rust-fibonacci", {})
