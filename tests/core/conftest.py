"""Shared fixtures for SuperClaude Core module tests."""

import pytest

# These imports may fail if the archived SDK is not available
# Fixtures using them will be skipped in that case
try:
    from SuperClaude.Core.unified_store import SymbolInfo, UnifiedStore

    _UNIFIED_STORE_AVAILABLE = True
except ImportError:
    _UNIFIED_STORE_AVAILABLE = False
    SymbolInfo = None
    UnifiedStore = None


@pytest.fixture
def memory_store(tmp_path):
    """Create an isolated UnifiedStore using a temporary path."""
    if not _UNIFIED_STORE_AVAILABLE:
        pytest.skip("UnifiedStore not available (archived SDK required)")
    return _memory_store_impl(tmp_path)


def _memory_store_impl(tmp_path):
    """Implementation for memory_store fixture."""
    db_path = tmp_path / "test_store.db"
    store = UnifiedStore(str(db_path))
    yield store
    store.close()


@pytest.fixture
def sample_symbol():
    """Create a sample SymbolInfo for testing."""
    if not _UNIFIED_STORE_AVAILABLE:
        pytest.skip("SymbolInfo not available (archived SDK required)")
    return SymbolInfo(
        name="test_function",
        kind="function",
        file_path="/path/to/file.py",
        line=42,
        signature="def test_function(x: int) -> str",
    )


@pytest.fixture
def sample_symbols():
    """Create multiple sample SymbolInfo objects for testing."""
    if not _UNIFIED_STORE_AVAILABLE:
        pytest.skip("SymbolInfo not available (archived SDK required)")
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
