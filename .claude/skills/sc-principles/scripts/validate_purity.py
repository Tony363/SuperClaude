#!/usr/bin/env python3
"""Purity Validator - Detect functions mixing I/O with business logic.

Applies "Functional Core, Imperative Shell" principle:
- Core (business logic, data transformation): MUST be pure
- Shell (handlers, adapters, CLI): MAY be impure

Detects:
- File I/O in business logic functions
- Network calls in data transformation
- Database queries mixed with business rules
- Mutable global state access
- print/logging in pure-context functions

Exit Codes:
    0 - Purity validation passed
    2 - Purity violations detected (blocked)
    3 - Validation error
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

IO_CALL_PATTERNS: dict[str, list[str]] = {
    "file_io": [
        "open",
        "read_text",
        "write_text",
        "read_bytes",
        "write_bytes",
        "mkdir",
        "rmdir",
        "unlink",
        "rename",
        "shutil.copy",
        "shutil.move",
    ],
    "network": [
        "requests.get",
        "requests.post",
        "requests.put",
        "requests.delete",
        "requests.patch",
        "httpx.get",
        "httpx.post",
        "http.request",
        "urllib.request",
        "urlopen",
        "socket.connect",
        "socket.send",
        "socket.recv",
    ],
    "database": [
        "execute",
        "query",
        "cursor",
        "commit",
        "rollback",
        "add",
        "delete",
        "flush",
        "merge",
        "refresh",
    ],
    "subprocess": [
        "run",
        "call",
        "check_output",
        "check_call",
        "Popen",
        "system",
        "spawn",
    ],
    "side_effects": [
        "print",
        "pprint",
        "logging",
        "logger",
        "log",
        "debug",
        "info",
        "warning",
        "error",
        "critical",
    ],
}

IO_MODULE_PATTERNS: dict[str, list[str]] = {
    "file_io": ["os", "shutil", "pathlib", "io", "tempfile"],
    "network": ["requests", "httpx", "aiohttp", "urllib", "socket", "http"],
    "database": ["sqlite3", "psycopg2", "mysql", "pymongo", "redis", "sqlalchemy"],
    "subprocess": ["subprocess", "os"],
}

CORE_PATH_PATTERNS = [
    "*/domain/*",
    "*/models/*",
    "*/services/*",
    "*/logic/*",
    "*/core/*",
    "*/business/*",
    "*/utils/*",
    "*/helpers/*",
    "*_service.py",
    "*_logic.py",
    "*_utils.py",
    "*_helpers.py",
    "*_domain.py",
]

SHELL_PATH_PATTERNS = [
    "*/handlers/*",
    "*/views/*",
    "*/routes/*",
    "*/api/*",
    "*/cli/*",
    "*/adapters/*",
    "*/controllers/*",
    "*/endpoints/*",
    "*/scripts/*",  # CLI scripts are inherently impure
    "*/tests/*",  # Test files are allowed to have I/O
    "*/examples/*",  # Example files demonstrate usage
    "*/benchmarks/*",  # Benchmark files do I/O
    "*/archive/*",  # Archived code - don't enforce
    "*_handler.py",
    "*_view.py",
    "*_controller.py",
    "*_adapter.py",
    "*_endpoint.py",
    "*_api.py",
    "*_cli.py",
    "*__main__.py",  # Entry points are shell
    "conftest.py",  # pytest config
    "setup.py",  # Package setup
]


@dataclass
class PurityViolation:
    """Single purity violation."""

    file: str
    function: str
    line: int
    io_type: str
    pattern: str
    context: str
    severity: str


@dataclass
class ValidationResult:
    """Result of purity validation."""

    allowed: bool
    violations: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    architecture_hint: str = ""


class PurityAnalyzer(ast.NodeVisitor):
    """AST visitor to detect I/O patterns in functions."""

    def __init__(self, file_path: str, context: str) -> None:
        self.file_path = file_path
        self.context = context
        self.violations: list[PurityViolation] = []
        self.current_function: Optional[str] = None
        self.current_line: int = 0
        self.imported_modules: set[str] = set()

    def _add_violation(
        self,
        line: int,
        io_type: str,
        pattern: str,
        function: Optional[str] = None,
    ) -> None:
        """Add a violation with context-aware severity.

        Centralizes violation creation to ensure consistent severity rules:
        - core context → error (must fix)
        - shell context → warning (allowed but noted)
        """
        severity = "error" if self.context == "core" else "warning"
        self.violations.append(
            PurityViolation(
                file=self.file_path,
                function=function or self.current_function or "<module>",
                line=line,
                io_type=io_type,
                pattern=pattern,
                context=self.context,
                severity=severity,
            )
        )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imported_modules.add(alias.name.split(".")[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.imported_modules.add(node.module.split(".")[0])
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        # Flag async functions as impure - they imply I/O scheduling
        self._add_violation(
            line=node.lineno,
            io_type="async_io",
            pattern=f"async def {node.name}",
            function=node.name,
        )
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        prev_function = self.current_function
        prev_line = self.current_line

        self.current_function = node.name
        self.current_line = node.lineno
        self.generic_visit(node)

        self.current_function = prev_function
        self.current_line = prev_line

    def visit_Call(self, node: ast.Call) -> None:
        if self.current_function:
            func_name = self._get_call_name(node)
            self._check_io_pattern(func_name, node.lineno)
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        if self.current_function:
            self._add_violation(
                line=node.lineno,
                io_type="global_state",
                pattern=f"global {', '.join(node.names)}",
            )

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        if self.current_function:
            self._add_violation(
                line=node.lineno,
                io_type="nonlocal_state",
                pattern=f"nonlocal {', '.join(node.names)}",
            )

    def visit_Await(self, node: ast.Await) -> None:
        """Detect await expressions as I/O patterns."""
        if self.current_function:
            expr_name = self._get_expr_name(node.value)
            self._add_violation(
                line=node.lineno,
                io_type="async_io",
                pattern=f"await {expr_name}",
            )
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Detect async for loops as I/O patterns."""
        if self.current_function:
            iter_name = self._get_expr_name(node.iter)
            self._add_violation(
                line=node.lineno,
                io_type="async_io",
                pattern=f"async for ... in {iter_name}",
            )
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        """Detect async with context managers as I/O patterns."""
        if self.current_function:
            items = [self._get_expr_name(item.context_expr) for item in node.items]
            self._add_violation(
                line=node.lineno,
                io_type="async_io",
                pattern=f"async with {', '.join(items)}",
            )
        self.generic_visit(node)

    def _get_expr_name(self, node: ast.expr) -> str:
        """Extract a readable name from any expression node.

        Handles Call, Name, Attribute, and falls back to '<expression>'.
        """
        if isinstance(node, ast.Call):
            return self._get_call_name(node)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parts: list[str] = []
            current: ast.expr = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return "<expression>"

    def _get_call_name(self, node: ast.Call) -> str:
        """Extract full function name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts: list[str] = []
            current: ast.expr = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    def _check_io_pattern(self, func_name: str, line: int) -> None:
        """Check if function call matches I/O patterns."""
        func_parts = func_name.split(".")
        base_name = func_parts[-1] if func_parts else ""
        module_name = func_parts[0] if func_parts else ""

        for io_type, patterns in IO_CALL_PATTERNS.items():
            for pattern in patterns:
                if base_name == pattern or pattern in func_name:
                    severity = "error" if self.context == "core" else "warning"
                    self.violations.append(
                        PurityViolation(
                            file=self.file_path,
                            function=self.current_function or "<module>",
                            line=line,
                            io_type=io_type,
                            pattern=func_name,
                            context=self.context,
                            severity=severity,
                        )
                    )
                    return

        for io_type, modules in IO_MODULE_PATTERNS.items():
            if module_name in modules:
                severity = "error" if self.context == "core" else "warning"
                self.violations.append(
                    PurityViolation(
                        file=self.file_path,
                        function=self.current_function or "<module>",
                        line=line,
                        io_type=io_type,
                        pattern=func_name,
                        context=self.context,
                        severity=severity,
                    )
                )
                return


def match_path_pattern(path: str, pattern: str) -> bool:
    """Check if path matches a glob-like pattern."""
    if fnmatch.fnmatch(path, pattern):
        return True
    pattern_part = pattern.replace("*", "").strip("/")
    return pattern_part in path


def determine_context(file_path: Path) -> str:
    """Determine if file is in 'core' (purity required) or 'shell' (impure allowed)."""
    path_str = str(file_path)

    for pattern in SHELL_PATH_PATTERNS:
        if match_path_pattern(path_str, pattern):
            return "shell"

    for pattern in CORE_PATH_PATTERNS:
        if match_path_pattern(path_str, pattern):
            return "core"

    return "core"


def analyze_file_purity(file_path: Path, context: str) -> list[PurityViolation]:
    """Analyze a single file for purity violations."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    analyzer = PurityAnalyzer(str(file_path), context)
    analyzer.visit(tree)
    return analyzer.violations


def find_python_files(scope_root: Path, changed_only: bool = True) -> list[Path]:
    """Find Python files to analyze."""
    if changed_only:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached", "HEAD"],
                capture_output=True,
                text=True,
                cwd=scope_root,
                timeout=30,
            )
            staged = result.stdout.strip().split("\n") if result.stdout.strip() else []

            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                cwd=scope_root,
                timeout=30,
            )
            unstaged = result.stdout.strip().split("\n") if result.stdout.strip() else []

            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True,
                text=True,
                cwd=scope_root,
                timeout=30,
            )
            untracked = result.stdout.strip().split("\n") if result.stdout.strip() else []

            all_files = set(staged + unstaged + untracked)
            py_files = [
                scope_root / f for f in all_files if f.endswith(".py") and (scope_root / f).exists()
            ]

            if py_files:
                return py_files
        except (subprocess.SubprocessError, FileNotFoundError):
            pass  # Fall back to rglob below when git is unavailable

    return list(scope_root.rglob("*.py"))


def generate_recommendations(violations: list[PurityViolation]) -> list[str]:
    """Generate actionable recommendations for purity violations."""
    recommendations: list[str] = []
    io_types = {v.io_type for v in violations if v.context == "core"}

    if "file_io" in io_types:
        recommendations.append(
            "FILE I/O: Move file operations to adapter layer. "
            "Pass data as function arguments instead of reading inside logic."
        )

    if "network" in io_types:
        recommendations.append(
            "NETWORK: Extract HTTP calls to repository/adapter pattern. "
            "Business logic should receive data, not fetch it."
        )

    if "database" in io_types:
        recommendations.append(
            "DATABASE: Use repository pattern. Business logic receives/returns data, "
            "database operations happen in repository layer."
        )

    if "subprocess" in io_types:
        recommendations.append(
            "SUBPROCESS: Move shell commands to adapter/infrastructure layer. "
            "Core logic should work with data, not execute processes."
        )

    if "global_state" in io_types or "nonlocal_state" in io_types:
        recommendations.append(
            "GLOBAL STATE: Pass state as explicit parameters. "
            "Use dependency injection for shared state."
        )

    if "side_effects" in io_types:
        recommendations.append(
            "SIDE EFFECTS: Return values instead of printing. "
            "Let calling code handle output/logging."
        )

    if "async_io" in io_types:
        recommendations.append(
            "ASYNC I/O: Move async functions to shell/adapter layer. "
            "Core business logic should be synchronous and pure. "
            "Pass data to core functions, await in shell."
        )

    return recommendations


def validate_purity(
    scope_root: str,
    strict: bool = False,
    core_only: bool = False,
    all_files: bool = False,
) -> ValidationResult:
    """Run purity validation on files."""
    root = Path(scope_root)
    files = find_python_files(root, changed_only=not all_files)

    all_violations: list[PurityViolation] = []

    for file_path in files:
        context = determine_context(file_path)

        if core_only and context != "core":
            continue

        violations = analyze_file_purity(file_path, context)
        all_violations.extend(violations)

    errors = [v for v in all_violations if v.severity == "error"]
    warnings = [v for v in all_violations if v.severity == "warning"]
    blocked = len(errors) > 0 or (strict and len(warnings) > 0)

    core_violations = [v for v in all_violations if v.context == "core"]
    shell_warnings = [v for v in all_violations if v.context == "shell"]

    return ValidationResult(
        allowed=not blocked,
        violations=[asdict(v) for v in all_violations],
        summary={
            "files_analyzed": len(files),
            "core_violations": len(core_violations),
            "shell_warnings": len(shell_warnings),
            "errors": len(errors),
            "warnings": len(warnings),
            "blocked": blocked,
        },
        recommendations=generate_recommendations(all_violations),
        architecture_hint=(
            "Consider 'Functional Core, Imperative Shell' pattern: "
            "Keep business logic pure, push I/O to edges (handlers, adapters)."
        ),
    )


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Purity Validator - Enforce functional core pattern"
    )
    parser.add_argument(
        "--scope-root",
        default=".",
        help="Root directory to analyze",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat shell warnings as errors",
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Only check files in core paths",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all files, not just changed",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format",
    )

    args = parser.parse_args()

    result = validate_purity(
        args.scope_root,
        args.strict,
        args.core_only,
        args.all,
    )

    output = {
        "allowed": result.allowed,
        "violations": result.violations,
        "summary": result.summary,
        "recommendations": result.recommendations,
        "architecture_hint": result.architecture_hint,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"Purity Validation: {'PASSED' if result.allowed else 'BLOCKED'}")
        print(f"Files analyzed: {result.summary['files_analyzed']}")
        print(
            f"Core violations: {result.summary['core_violations']}, "
            f"Shell warnings: {result.summary['shell_warnings']}"
        )

        if result.violations:
            print("\nViolations:")
            for v in result.violations:
                print(
                    f"  [{v['severity'].upper()}] {v['file']}:{v['line']} "
                    f"{v['function']}: {v['io_type']} - {v['pattern']} "
                    f"(context: {v['context']})"
                )

        if result.recommendations:
            print("\nRecommendations:")
            for rec in result.recommendations:
                print(f"  - {rec}")

        print(f"\nHint: {result.architecture_hint}")

    sys.exit(0 if result.allowed else 2)


if __name__ == "__main__":
    main()
