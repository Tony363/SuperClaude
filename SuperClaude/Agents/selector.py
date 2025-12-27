"""
Selector compatibility module.

Re-exports the selector from the archived Python SDK.
"""

import sys
from pathlib import Path

# Ensure archive is in path
_archive_path = Path(__file__).parent.parent.parent / "archive" / "python-sdk-v5"
if str(_archive_path) not in sys.path:
    sys.path.insert(0, str(_archive_path))

# Re-export everything from the archived selector
from selector import *
