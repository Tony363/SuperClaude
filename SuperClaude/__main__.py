"""
SuperClaude main entry point compatibility module.

Provides backward compatibility with the archived Python SDK CLI.
For v6, the recommended approach is using Claude Code with /sc: commands directly.
"""

import importlib.util
import sys
from pathlib import Path


def main() -> int:
    """
    Main entry point for SuperClaude CLI.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    _archive_path = Path(__file__).parent.parent / "archive" / "python-sdk-v5"

    if not _archive_path.exists():
        print("SuperClaude CLI requires the archived SDK.")
        print("For v6, use Claude Code with /sc: commands directly.")
        print()
        print("If you need CLI functionality, ensure the archive directory exists:")
        print(f"  {_archive_path}")
        return 1

    # Load the archived __main__.py using importlib to avoid self-import
    # when running as python -m SuperClaude
    archived_main_path = _archive_path / "__main__.py"
    if not archived_main_path.exists():
        print(f"Archived CLI not found: {archived_main_path}")
        return 1

    try:
        # Use importlib to load the specific file, avoiding name collision
        spec = importlib.util.spec_from_file_location(
            "archived_superclaude_main", archived_main_path
        )
        if spec is None or spec.loader is None:
            print("Failed to load archived CLI module spec.")
            return 1

        archived_module = importlib.util.module_from_spec(spec)

        # Add archive to path for its dependencies
        if str(_archive_path) not in sys.path:
            sys.path.insert(0, str(_archive_path))

        spec.loader.exec_module(archived_module)

        if hasattr(archived_module, "main"):
            return archived_module.main()
        else:
            print("Archived CLI module has no main() function.")
            return 1

    except ImportError as e:
        print(f"Failed to load CLI: {e}")
        print()
        print("The CLI requires additional dependencies. Install with:")
        print("  pip install .[cli]")
        return 1
    except Exception as e:
        print(f"Error running archived CLI: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
