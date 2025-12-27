"""
SuperClaude Agents compatibility module.

Re-exports agent-related modules from the archived Python SDK.
"""

import sys
from pathlib import Path

# Ensure archive is in path
_archive_path = Path(__file__).parent.parent.parent / "archive" / "python-sdk-v5"
if str(_archive_path) not in sys.path:
    sys.path.insert(0, str(_archive_path))

# Import and re-export from archive
from usage_tracker import (
    classify_agents,
    export_json,
    get_top_agents,
    get_usage_snapshot,
    record_execution,
    record_load,
    record_plan_only,
    reset_usage_stats,
    write_markdown_report,
)

# Re-export usage_tracker module itself
from . import usage_tracker

__all__ = [
    "classify_agents",
    "export_json",
    "get_top_agents",
    "get_usage_snapshot",
    "record_execution",
    "record_load",
    "record_plan_only",
    "reset_usage_stats",
    "usage_tracker",
    "write_markdown_report",
]
