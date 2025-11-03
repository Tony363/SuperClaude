"""
Test CLI functionality and argument parsing.
"""

import argparse
import sys
from pathlib import Path

import pytest

# Add parent directory to path for direct module imports
sys.path.insert(0, str(Path(__file__).parent.parent))


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
        "--install-dir", "/tmp/test",
        "--dry-run",
        "--force",
        "--yes",
        "--no-update-check",
        "--auto-update"
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

def test_main_no_args(monkeypatch, capsys):
    """Running the CLI with no args should list available operations."""
    from SuperClaude.__main__ import main

    monkeypatch.setattr(sys, 'argv', ['SuperClaude'])
    exit_code = main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Available operations" in captured.out


def test_main_invalid_operation(monkeypatch, capsys):
    """Invalid operations should return exit code 1 and print an error."""
    from SuperClaude.__main__ import main

    monkeypatch.setattr(sys, 'argv', ['SuperClaude', 'invalid_op'])
    exit_code = main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Unknown operation" in captured.out


def test_main_keyboard_interrupt(monkeypatch, capsys):
    """If parser setup raises KeyboardInterrupt the CLI should exit cleanly."""
    import SuperClaude.__main__ as cli

    def raising_create_parser():
        raise KeyboardInterrupt()

    monkeypatch.setattr(cli, 'create_parser', raising_create_parser)
    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 130
    assert "Operation cancelled by user" in captured.out


def test_fallback_functions():
    """Test that fallback UI functions exist when imports fail."""
    # Test the fallback classes/functions defined in __main__.py
    from SuperClaude.__main__ import (
        Colors, display_error, display_warning,
        display_success, display_info, display_header
    )

    # Test Colors class
    assert hasattr(Colors, 'RED')
    assert hasattr(Colors, 'YELLOW')
    assert hasattr(Colors, 'GREEN')
    assert hasattr(Colors, 'CYAN')
    assert hasattr(Colors, 'RESET')

    # Test display functions work without errors
    display_error("test error")
    display_warning("test warning")
    display_success("test success")
    display_info("test info")
    display_header("test title", "test subtitle")


def test_version_flag():
    """Test that --version flag works correctly."""
    from SuperClaude.__main__ import create_parser
    from SuperClaude import __version__

    parser, _, _ = create_parser()

    # Test version flag
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(['--version'])
    assert excinfo.value.code == 0


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
