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

from pathlib import Path

# Use importlib.metadata for version (Python 3.8+)
try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("SuperClaude")
    except PackageNotFoundError:
        # Not installed as package, try VERSION file
        try:
            __version__ = (Path(__file__).parent.parent / "VERSION").read_text().strip()
        except Exception:
            __version__ = "4.1.0"  # Fallback
except ImportError:
    # Python < 3.8, fall back to VERSION file
    try:
        __version__ = (Path(__file__).parent.parent / "VERSION").read_text().strip()
    except Exception:
        __version__ = "4.1.0"  # Fallback

__author__ = "NomenAK, Mithun Gowda B"
__email__ = "anton.knoery@gmail.com"
__license__ = "MIT"
