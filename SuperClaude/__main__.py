"""
SuperClaude v7 CLI entry point.

Dispatches to setup operations (install, update, uninstall, backup, clean, agent)
when given a subcommand, or shows usage info when invoked without arguments.

Usage:
    python -m SuperClaude install [options]
    python -m SuperClaude update [options]
    python -m SuperClaude uninstall [options]
    python -m SuperClaude backup [options]
    python -m SuperClaude clean [options]
    python -m SuperClaude agent [options]
"""

import argparse
import importlib
import sys
from pathlib import Path

from SuperClaude import __version__

DEFAULT_INSTALL_DIR = Path.home() / ".claude"

_OPERATIONS = {
    "install": "Install SuperClaude framework components",
    "update": "Update existing SuperClaude installation",
    "uninstall": "Remove SuperClaude installation",
    "backup": "Backup and restore operations",
    "clean": "Clean corrupted metadata, cache, and temporary files",
    "agent": "Interact with the agent system",
}


def _load_operation(name: str):
    """Dynamically import a setup CLI operation module."""
    try:
        return importlib.import_module(f"setup.cli.commands.{name}")
    except ImportError as e:
        print(f"Error: could not load '{name}' module: {e}", file=sys.stderr)
        return None


def _create_global_parser() -> argparse.ArgumentParser:
    """Create shared parser for global flags used by all subcommands."""
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    p.add_argument("--quiet", "-q", action="store_true", help="Suppress non-error output")
    p.add_argument(
        "--install-dir",
        type=Path,
        default=DEFAULT_INSTALL_DIR,
        help=f"Target installation directory (default: {DEFAULT_INSTALL_DIR})",
    )
    p.add_argument("--dry-run", action="store_true", help="Simulate without making changes")
    p.add_argument("--force", action="store_true", help="Force execution, skipping checks")
    p.add_argument("--yes", "-y", action="store_true", help="Answer yes to all prompts")
    return p


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the SuperClaude CLI.

    Args:
        argv: Command-line arguments to parse. Uses sys.argv[1:] if None.
    """
    global_parser = _create_global_parser()

    parser = argparse.ArgumentParser(
        prog="SuperClaude",
        description=f"SuperClaude v{__version__} - Framework Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[global_parser],
    )
    parser.add_argument("--version", action="version", version=f"SuperClaude {__version__}")

    subparsers = parser.add_subparsers(
        dest="operation",
        title="Operations",
        description="Available operations",
    )

    # Register each operation's subparser and collect run functions
    operations = {}
    for name, desc in _OPERATIONS.items():
        mod = _load_operation(name)
        if mod and hasattr(mod, "register_parser") and hasattr(mod, "run"):
            mod.register_parser(subparsers, global_parser)
            operations[name] = mod.run
        else:
            subparsers.add_parser(name, help=desc, parents=[global_parser])
            operations[name] = None

    args = parser.parse_args(argv)

    if not args.operation:
        print(f"SuperClaude v{__version__}")
        print()
        print("For framework management (install/update/uninstall):")
        print("  python -m SuperClaude install")
        print()
        print("For Claude Code /sc: commands:")
        print("  Run 'claude' to start, then use /sc:implement, /sc:test, etc.")
        print()
        print("Run 'python -m SuperClaude --help' for all options.")
        return 0

    run_func = operations.get(args.operation)
    if run_func is None:
        print(f"Error: operation '{args.operation}' is not available.", file=sys.stderr)
        return 1

    try:
        return run_func(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
