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

# Prefer VERSION file in repo; fall back to installed package metadata
try:
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        __version__ = version_file.read_text().strip()
    else:
        raise FileNotFoundError
except Exception:
    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as _ver

        try:
            __version__ = _ver("SuperClaude")
        except PackageNotFoundError:
            __version__ = "6.0.0-alpha"
    except Exception:
        __version__ = "6.0.0-alpha"

__author__ = "NomenAK, Mithun Gowda B"
__email__ = "anton.knoery@gmail.com"
__license__ = "MIT"
