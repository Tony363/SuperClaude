"""Conftest for .github/scripts tests.

Mocks the `anthropic` module since it's not installed in the test environment.
The .github/scripts files do `import anthropic` at module level and sys.exit(1)
if it's missing. We need to provide a fake module before importing them.
"""

import sys
import types
from unittest.mock import MagicMock


def _ensure_anthropic_mock():
    """Install a fake anthropic module if the real one isn't available."""
    if "anthropic" not in sys.modules:
        mock_mod = types.ModuleType("anthropic")
        mock_mod.Anthropic = MagicMock
        mock_mod.APIError = type("APIError", (Exception,), {})
        sys.modules["anthropic"] = mock_mod


_ensure_anthropic_mock()
