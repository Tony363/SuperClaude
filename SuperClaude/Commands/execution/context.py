"""Execution context compatibility module."""

from __future__ import annotations

import sys
from pathlib import Path

_archive_path = Path(__file__).parent.parent.parent.parent / "archive" / "python-sdk-v5"
if str(_archive_path) not in sys.path:
    sys.path.insert(0, str(_archive_path))

from Commands.execution.context import *
