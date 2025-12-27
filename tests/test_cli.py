"""Test CLI functionality and argument parsing.

These tests require the archived SDK to be properly installed.
Skip if the archived SDK compatibility layer has import issues.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Add parent directory to path for direct module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Check if archived SDK imports work - skip entire module if not
try:
    from SuperClaude import __main__ as superclaude_main  # noqa: F401
except ImportError:
    pytest.skip(
        "Archived SDK compatibility layer not available",
        allow_module_level=True,
    )


def test_cli_imports():
    """Test that CLI module can be imported without errors."""
    try:
        from SuperClaude import __main__

        assert __main__ is not None
    except ImportError as e:
        pytest.fail(f"Failed to import CLI module: {e}")


def test_create_parser():
    """Test that CLI parser can be created."""
    from SuperClaude.__main__ import create_parser

    parser, subparsers, global_parser = create_parser()

    assert parser is not None
    assert isinstance(parser, argparse.ArgumentParser)
    assert subparsers is not None
    assert global_parser is not None


def test_global_parser_flags():
    """Test that global parser has all expected flags."""
    from SuperClaude.__main__ import create_global_parser

    parser = create_global_parser()

    # Parse with all flags to ensure they exist
    test_args = [
        "--verbose",
        "--quiet",
        "--install-dir",
        "/tmp/test",
        "--dry-run",
        "--force",
        "--yes",
        "--no-update-check",
        "--auto-update",
    ]

    # Should not raise an error
    args = parser.parse_args(test_args)
    assert args.verbose is True
    assert args.quiet is True
    assert args.dry_run is True
    assert args.force is True
    assert args.yes is True
    assert args.no_update_check is True
    assert args.auto_update is True
    assert str(args.install_dir) == "/tmp/test"


def test_operation_modules():
    """Test that operation modules are defined correctly."""
    from SuperClaude.__main__ import get_operation_modules

    operations = get_operation_modules()

    assert "install" in operations
    assert "update" in operations
    assert "uninstall" in operations
    assert "backup" in operations

    # Check descriptions exist
    for op, desc in operations.items():
        assert isinstance(desc, str)
        assert len(desc) > 0


def _cli_env() -> dict:
    env = os.environ.copy()
    env.setdefault("SUPERCLAUDE_OFFLINE_MODE", "1")
    env.setdefault("SC_NETWORK_MODE", "offline")
    return env


def test_main_no_args():
    """Running the CLI with no args should list available operations."""
    result = subprocess.run(
        [sys.executable, "-m", "SuperClaude"],
        capture_output=True,
        text=True,
        env=_cli_env(),
    )

    assert result.returncode == 0
    assert "Available operations" in result.stdout


def test_main_invalid_operation():
    """Invalid operations should return exit code 1 and print an error."""
    result = subprocess.run(
        [sys.executable, "-m", "SuperClaude", "invalid_op"],
        capture_output=True,
        text=True,
        env=_cli_env(),
    )

    assert result.returncode == 1
    assert "Unknown operation" in result.stdout


def test_main_keyboard_interrupt():
    """KeyboardInterrupt during parser creation exits with 130."""
    script = (
        "import SuperClaude.__main__ as cli\n"
        "def raising():\n"
        "    raise KeyboardInterrupt()\n"
        "cli.create_parser = raising\n"
        "exit(cli.main())\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=_cli_env(),
    )

    assert result.returncode == 130
    assert "Operation cancelled by user" in result.stdout


def test_fallback_functions():
    """Test that fallback UI functions exist when imports fail."""
    # Test the fallback classes/functions defined in __main__.py
    from SuperClaude.__main__ import (
        Colors,
        display_error,
        display_header,
        display_info,
        display_success,
        display_warning,
    )

    # Test Colors class
    assert hasattr(Colors, "RED")
    assert hasattr(Colors, "YELLOW")
    assert hasattr(Colors, "GREEN")
    assert hasattr(Colors, "CYAN")
    assert hasattr(Colors, "RESET")

    # Test display functions work without errors
    display_error("test error")
    display_warning("test warning")
    display_success("test success")
    display_info("test info")
    display_header("test title", "test subtitle")


def test_version_flag():
    """Test that --version flag works correctly."""
    from SuperClaude.__main__ import create_parser

    parser, _, _ = create_parser()

    # Test version flag
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["--version"])
    assert excinfo.value.code == 0


def test_main_invokes_stub_operation(monkeypatch):
    import SuperClaude.__main__ as cli

    class StubModule:
        def __init__(self):
            self.calls = 0

        def register_parser(self, subparsers, global_parser):
            parser = subparsers.add_parser("install", help="stub install", parents=[global_parser])
            parser.add_argument("--flag", action="store_true", help="stub flag")

        def run(self, args):
            self.calls += 1
            assert args.operation == "install"
            assert args.flag is True
            return 99

    stub_module = StubModule()

    monkeypatch.setattr(cli, "get_operation_modules", lambda: {"install": "Install SuperClaude"})
    monkeypatch.setattr(cli, "load_operation_module", lambda name: stub_module)
    monkeypatch.setattr(cli, "setup_global_environment", lambda args: None)
    monkeypatch.setattr(cli, "get_logger", lambda: None)
    monkeypatch.setattr(sys, "argv", ["SuperClaude", "install", "--no-update-check", "--flag"])

    exit_code = cli.main()

    assert exit_code == 99
    assert stub_module.calls == 1


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
