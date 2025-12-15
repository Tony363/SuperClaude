#!/usr/bin/env python3
"""
SuperClaude Framework Management Hub
Unified entry point for all SuperClaude operations

Usage:
    SuperClaude install [options]
    SuperClaude update [options]
    SuperClaude uninstall [options]
    SuperClaude backup [options]
    SuperClaude --help
"""

import argparse
import difflib
import importlib
import os
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Callable, Dict, Optional

# Add the local 'setup' directory to the Python import path
current_dir = Path(__file__).parent
project_root = current_dir.parent
setup_dir = project_root / "setup"

# Default install directory
DEFAULT_INSTALL_DIR = Path.home() / ".claude"

# Try to import utilities from the setup package
SETUP_IMPORT_FAILED = False
_BOOTSTRAP_SKIP_VALUES = {"1", "true", "yes", "on"}


def _import_setup_symbols():
    from setup import DEFAULT_INSTALL_DIR as setup_default_dir
    from setup.utils.logger import LogLevel, get_logger, setup_logging
    from setup.utils.ui import (
        Colors,
        display_error,
        display_header,
        display_info,
        display_success,
        display_warning,
    )

    return (
        display_header,
        display_info,
        display_success,
        display_error,
        display_warning,
        Colors,
        setup_logging,
        get_logger,
        LogLevel,
        setup_default_dir,
    )


def _handle_setup_import_failure(error: ImportError, *, retry: bool) -> None:
    """
    Attempt to bootstrap the setup package or exit with actionable guidance.
    """
    global SETUP_IMPORT_FAILED

    skip_bootstrap = (
        os.environ.get("SUPERCLAUDE_SKIP_BOOTSTRAP", "").strip().lower()
        in _BOOTSTRAP_SKIP_VALUES
    )

    attempted = False
    bootstrap_error: Optional[str] = None

    if not skip_bootstrap and not retry:
        bootstrap_cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-e",
            str(project_root),
        ]
        cmd_display = " ".join(shlex.quote(part) for part in bootstrap_cmd)
        sys.stderr.write(
            f"[SuperClaude] setup imports failed ({error}).\n"
            f"[SuperClaude] Attempting bootstrap via: {cmd_display}\n"
        )
        try:
            result = subprocess.run(
                bootstrap_cmd,
                check=True,
                cwd=str(project_root),
            )
            attempted = True
        except subprocess.CalledProcessError as bootstrap_exc:
            attempted = True
            bootstrap_error = (
                f"bootstrap command exited with status {bootstrap_exc.returncode}"
            )
        except FileNotFoundError as bootstrap_exc:
            attempted = True
            bootstrap_error = f"pip executable not found: {bootstrap_exc}"
        except Exception as bootstrap_exc:
            attempted = True
            bootstrap_error = str(bootstrap_exc)
        else:
            if result.returncode == 0:
                importlib.invalidate_caches()
                return
            bootstrap_error = (
                f"bootstrap command exited with status {result.returncode}"
            )

    error_desc = str(error) or error.__class__.__name__
    cmd_display = f"{sys.executable} -m pip install -e {shlex.quote(str(project_root))}"

    reason_lines = []
    if skip_bootstrap:
        reason_lines.append(
            "Automatic bootstrapping is disabled (SUPERCLAUDE_SKIP_BOOTSTRAP is set)."
        )
    elif attempted:
        reason_lines.append(
            f"Automatic bootstrap attempt failed: {bootstrap_error or 'unknown error'}."
        )

    guidance = textwrap.dedent(
        f"""
        SuperClaude CLI requires the bundled setup package but it could not be imported ({error_desc}).
        """
    ).strip()

    if reason_lines:
        guidance = f"{guidance}\n\n" + "\n".join(reason_lines)

    guidance = (
        f"{guidance}\n\n"
        "To resolve the issue:\n"
        "  1. Activate your preferred virtual environment (if applicable).\n"
        f"  2. Install SuperClaude in editable mode:\n     {cmd_display}\n"
        "  3. Re-run the SuperClaude command.\n\n"
        "Set SUPERCLAUDE_SKIP_BOOTSTRAP=1 to bypass automatic installation attempts.\n"
    )

    SETUP_IMPORT_FAILED = True
    raise SystemExit(guidance)


try:
    (
        display_header,
        display_info,
        display_success,
        display_error,
        display_warning,
        Colors,
        setup_logging,
        get_logger,
        LogLevel,
        DEFAULT_INSTALL_DIR,
    ) = _import_setup_symbols()
except ImportError as import_error:
    if setup_dir.exists():
        sys.path.insert(0, str(setup_dir.parent))
        try:
            (
                display_header,
                display_info,
                display_success,
                display_error,
                display_warning,
                Colors,
                setup_logging,
                get_logger,
                LogLevel,
                DEFAULT_INSTALL_DIR,
            ) = _import_setup_symbols()
        except ImportError as retry_error:
            _handle_setup_import_failure(retry_error, retry=False)
            try:
                (
                    display_header,
                    display_info,
                    display_success,
                    display_error,
                    display_warning,
                    Colors,
                    setup_logging,
                    get_logger,
                    LogLevel,
                    DEFAULT_INSTALL_DIR,
                ) = _import_setup_symbols()
            except ImportError as final_error:
                _handle_setup_import_failure(final_error, retry=True)
    else:
        _handle_setup_import_failure(import_error, retry=False)
        try:
            (
                display_header,
                display_info,
                display_success,
                display_error,
                display_warning,
                Colors,
                setup_logging,
                get_logger,
                LogLevel,
                DEFAULT_INSTALL_DIR,
            ) = _import_setup_symbols()
        except ImportError as final_error:
            _handle_setup_import_failure(final_error, retry=True)


def create_global_parser() -> argparse.ArgumentParser:
    """Create shared parser for global flags used by all commands"""
    global_parser = argparse.ArgumentParser(add_help=False)

    global_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    global_parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress all output except errors"
    )
    global_parser.add_argument(
        "--install-dir",
        type=Path,
        default=DEFAULT_INSTALL_DIR,
        help=f"Target installation directory (default: {DEFAULT_INSTALL_DIR})",
    )
    global_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate operation without making changes",
    )
    global_parser.add_argument(
        "--force", action="store_true", help="Force execution, skipping checks"
    )
    global_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Automatically answer yes to all prompts",
    )
    global_parser.add_argument(
        "--no-update-check", action="store_true", help="Skip checking for updates"
    )
    global_parser.add_argument(
        "--auto-update",
        action="store_true",
        help="Automatically install updates without prompting",
    )

    # Agent system flags
    global_parser.add_argument(
        "--delegate",
        action="store_true",
        help="Automatically delegate to the best agent for the task",
    )
    global_parser.add_argument(
        "--suggest-agents",
        action="store_true",
        help="Show top 5 recommended agents for the task",
    )
    global_parser.add_argument(
        "--agent", type=str, metavar="NAME", help="Specify a particular agent to use"
    )

    return global_parser


def create_parser():
    """Create the main CLI parser and attach subcommand parsers"""
    global_parser = create_global_parser()

    parser = argparse.ArgumentParser(
        prog="SuperClaude",
        description="SuperClaude Framework Management Hub - Unified CLI",
        epilog="""
Examples:
  SuperClaude install --dry-run
  SuperClaude update --verbose
  SuperClaude backup --create
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[global_parser],
    )

    from SuperClaude import __version__

    parser.add_argument(
        "--version", action="version", version=f"SuperClaude {__version__}"
    )

    subparsers = parser.add_subparsers(
        dest="operation",
        title="Operations",
        description="Framework operations to perform",
    )

    return parser, subparsers, global_parser


def setup_global_environment(args: argparse.Namespace):
    """Set up logging and shared runtime environment based on args"""
    # Determine log level
    if args.quiet:
        level = LogLevel.ERROR
    elif args.verbose:
        level = LogLevel.DEBUG
    else:
        level = LogLevel.INFO

    # Define log directory unless it's a dry run
    log_dir = args.install_dir / "logs" if not args.dry_run else None
    setup_logging("superclaude_hub", log_dir=log_dir, console_level=level)

    # Log startup context
    logger = get_logger()
    if logger:
        logger.debug(
            f"SuperClaude called with operation: {getattr(args, 'operation', 'None')}"
        )
        logger.debug(f"Arguments: {vars(args)}")


def get_operation_modules() -> Dict[str, str]:
    """Return supported operations and their descriptions"""
    return {
        "install": "Install SuperClaude framework components",
        "update": "Update existing SuperClaude installation",
        "uninstall": "Remove SuperClaude installation",
        "backup": "Backup and restore operations",
        "clean": "Clean corrupted metadata, cache, and temporary files",
        "agent": "Interact with the agent system",
    }


def load_operation_module(name: str):
    """Try to dynamically import an operation module"""
    try:
        return __import__(f"setup.cli.commands.{name}", fromlist=[name])
    except ImportError as e:
        logger = get_logger()
        if logger:
            logger.error(f"Module '{name}' failed to load: {e}")
        return None


def register_operation_parsers(subparsers, global_parser) -> Dict[str, Callable]:
    """Register subcommand parsers and map operation names to their run functions"""
    operations = {}
    for name, desc in get_operation_modules().items():
        module = load_operation_module(name)
        if module and hasattr(module, "register_parser") and hasattr(module, "run"):
            module.register_parser(subparsers, global_parser)
            operations[name] = module.run
        else:
            # If module doesn't exist, register a stub parser and fallback to legacy
            parser = subparsers.add_parser(
                name, help=f"{desc} (legacy fallback)", parents=[global_parser]
            )
            parser.add_argument(
                "--legacy", action="store_true", help="Use legacy script"
            )
            operations[name] = None
    return operations


def handle_legacy_fallback(op: str, args: argparse.Namespace) -> int:
    """Run a legacy operation script if module is unavailable"""
    script_path = Path(__file__).parent / f"{op}.py"

    if not script_path.exists():
        display_error(f"No module or legacy script found for operation '{op}'")
        return 1

    display_warning(f"Falling back to legacy script for '{op}'...")

    cmd = [sys.executable, str(script_path)]

    # Convert args into CLI flags
    for k, v in vars(args).items():
        if k in ["operation", "install_dir"] or v in [None, False]:
            continue
        flag = f"--{k.replace('_', '-')}"
        if v is True:
            cmd.append(flag)
        else:
            cmd.extend([flag, str(v)])

    try:
        return subprocess.call(cmd)
    except Exception as e:
        display_error(f"Legacy execution failed: {e}")
        return 1


def main() -> int:
    """Main entry point"""
    if SETUP_IMPORT_FAILED:
        display_error(
            "SuperClaude setup utilities are unavailable. Install the setup package before running the CLI."
        )
        return 2

    try:
        parser, subparsers, global_parser = create_parser()
        operations = register_operation_parsers(subparsers, global_parser)
        try:
            args = parser.parse_args()
        except SystemExit as se:
            # Convert invalid operation into graceful error path for tests
            if se.code == 2 and len(sys.argv) > 1:
                candidate = sys.argv[1]
                if candidate not in operations:
                    display_error(f"Unknown operation: '{candidate}'.")
                    return 1
            raise

        # Check for updates unless disabled
        if not args.quiet and not getattr(args, "no_update_check", False):
            try:
                from setup.utils.updater import check_for_updates

                # Check for updates in the background
                from SuperClaude import __version__

                updated = check_for_updates(
                    current_version=__version__,
                    auto_update=getattr(args, "auto_update", False),
                )
                # If updated, suggest restart
                if updated:
                    print(
                        "\n🔄 SuperClaude was updated. Please restart to use the new version."
                    )
                    return 0
            except ImportError:
                # Updater module not available, skip silently
                pass
            except Exception:
                # Any other error, skip silently
                pass

        # No operation provided? Show help manually unless in quiet mode
        if not args.operation:
            if not args.quiet:
                from SuperClaude import __version__

                display_header(
                    f"SuperClaude Framework v{__version__}",
                    "Unified CLI for all operations",
                )
                print(f"{Colors.CYAN}Available operations:{Colors.RESET}")
                for op, desc in get_operation_modules().items():
                    print(f"  {op:<12} {desc}")
            return 0

        # Handle unknown operations and suggest corrections
        if args.operation not in operations:
            close = difflib.get_close_matches(args.operation, operations.keys(), n=1)
            suggestion = f"Did you mean: {close[0]}?" if close else ""
            display_error(f"Unknown operation: '{args.operation}'. {suggestion}")
            return 1

        # Setup global context (logging, install path, etc.)
        setup_global_environment(args)
        logger = get_logger()

        # Execute operation
        run_func = operations.get(args.operation)
        if run_func:
            if logger:
                logger.info(f"Executing operation: {args.operation}")
            return run_func(args)
        else:
            # Fallback to legacy script
            if logger:
                logger.warning(
                    f"Module for '{args.operation}' missing, using legacy fallback"
                )
            return handle_legacy_fallback(args.operation, args)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Operation cancelled by user{Colors.RESET}")
        return 130
    except Exception as e:
        try:
            logger = get_logger()
            if logger:
                logger.exception(f"Unhandled error: {e}")
        except:
            print(f"{Colors.RED}[ERROR] {e}{Colors.RESET}")
        return 1


# Entrypoint guard
if __name__ == "__main__":
    sys.exit(main())
