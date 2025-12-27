#!/usr/bin/env python3
"""Run semantic validation checks against Python source files."""

from __future__ import annotations

import argparse
import ast
import py_compile
import sys
from pathlib import Path

from SuperClaude.Commands.executor import _PythonSemanticAnalyzer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Semantic validator for SuperClaude Python files")
    parser.add_argument("paths", nargs="+", help="File or directory paths to validate")
    return parser.parse_args()


def iter_python_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.suffix == ".py":
            files.append(path)
    return files


def validate_file(path: Path, repo_root: Path) -> list[str]:
    rel_path = str(path.relative_to(repo_root) if path.is_relative_to(repo_root) else path)
    issues: list[str] = []
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        issues.append(f"{rel_path}: python syntax error — {getattr(exc, 'msg', exc)}")
        return issues
    except Exception as exc:
        issues.append(f"{rel_path}: python validation failed — {exc}")
        return issues

    try:
        source = path.read_text(encoding="utf-8")
    except Exception as exc:
        issues.append(f"{rel_path}: unable to read file — {exc}")
        return issues

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:  # pragma: no cover - already handled above
        issues.append(f"{rel_path}: python syntax error — {exc.msg}")
        return issues

    analyzer = _PythonSemanticAnalyzer(path, repo_root)
    analyzer.visit(tree)
    for detail in analyzer.report():
        issues.append(f"{rel_path}: {detail}")
    return issues


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()
    files = iter_python_files(args.paths)
    if not files:
        print("No Python files to validate.")
        return 0

    all_issues: list[str] = []
    for file_path in files:
        all_issues.extend(validate_file(file_path, repo_root))

    if all_issues:
        for issue in all_issues:
            print(issue)
        return 1

    print(f"Semantic validation passed for {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
