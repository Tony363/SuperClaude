"""
SuperClaude main entry point compatibility module.

Re-exports __main__ from the archived Python SDK.
"""

import sys
from pathlib import Path

_archive_path = Path(__file__).parent.parent / "archive" / "python-sdk-v5"
if str(_archive_path) not in sys.path:
    sys.path.insert(0, str(_archive_path))

from __main__ import *

if __name__ == "__main__":
    import __main__ as archived_main

    if hasattr(archived_main, "main"):
        archived_main.main()
