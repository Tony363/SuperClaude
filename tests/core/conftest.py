"""Shared fixtures for SuperClaude Core module tests."""

import pytest

from SuperClaude.Core.unified_store import SymbolInfo, UnifiedStore


@pytest.fixture
def memory_store(tmp_path):
    """Create an isolated UnifiedStore using a temporary path.

    Yields:
        UnifiedStore: A fresh store instance for testing.
    """
    db_path = tmp_path / "test_store.db"
    store = UnifiedStore(str(db_path))
    yield store
    store.close()


@pytest.fixture
def sample_symbol():
    """Create a sample SymbolInfo for testing.

    Returns:
        SymbolInfo: A test symbol with realistic values.
    """
    return SymbolInfo(
        name="test_function",
        kind="function",
        file_path="/path/to/file.py",
        line=42,
        signature="def test_function(x: int) -> str",
    )


@pytest.fixture
def sample_symbols():
    """Create multiple sample SymbolInfo objects for testing.

    Returns:
        list[SymbolInfo]: A list of test symbols with different kinds.
    """
    return [
        SymbolInfo(
            name="MyClass",
            kind="class",
            file_path="/path/to/models.py",
            line=10,
            signature="class MyClass:",
        ),
        SymbolInfo(
            name="helper_func",
            kind="function",
            file_path="/path/to/utils.py",
            line=25,
            signature="def helper_func(a, b):",
        ),
        SymbolInfo(
            name="CONSTANT",
            kind="variable",
            file_path="/path/to/constants.py",
            line=1,
            signature=None,
        ),
        SymbolInfo(
            name="process_data",
            kind="function",
            file_path="/path/to/processor.py",
            line=100,
            signature="def process_data(data: dict) -> list:",
        ),
    ]
