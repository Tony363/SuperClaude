"""
SuperClaude v6.0.0 Compatibility Layer.

This module provides backwards compatibility with the v5 Python SDK
that is now archived. It re-exports modules from archive/python-sdk-v5/
to maintain test compatibility.

In v6.0.0, SuperClaude is a "pure prompts/config" framework. The Python
SDK was archived but tests still reference it. This layer bridges that gap.
"""

from pathlib import Path

# Version info
__version__ = "6.0.0"
__author__ = "NomenAK, Mithun Gowda B"
__license__ = "MIT"

# Add archive to Python path for compatibility
import sys
_archive_path = Path(__file__).parent.parent / "archive" / "python-sdk-v5"
if _archive_path.exists() and str(_archive_path) not in sys.path:
    sys.path.insert(0, str(_archive_path))
