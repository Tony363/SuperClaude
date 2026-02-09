#!/usr/bin/env python3
"""KISS Validator - Check code complexity against thresholds.

Uses AST analysis and optional mccabe for:
- Cyclomatic complexity (max: 10)
- Function length (max: 50 lines)
- Nesting depth (max: 4 levels)
- Parameter count (max: 5, warning)

Exit Codes:
    0 - KISS validation passed
    2 - KISS violations detected (blocked)
    3 - Validation error
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class KISSThresholds:
    """Configurable KISS thresholds."""

    max_complexity: int = 10
    max_function_lines: int = 50
    max_nesting_depth: int = 4
    max_parameters: int = 5
    warning_complexity: int = 7
    max_cognitive_complexity: int = 15


@dataclass
class KISSViolation:
    """Single KISS violation."""

    file: str
    function: str
    line: int
    violation_type: str
    value: int
    threshold: int
    severity: str


@dataclass
class ValidationResult:
    """Result of KISS validation."""

    allowed: bool
    violations: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor to calculate cyclomatic complexity."""

    def __init__(self) -> None:
        self.complexity = 1

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1
        self.complexity += len(node.ifs)
        self.generic_visit(node)


def calculate_complexity(node: ast.AST) -> int:
    """Calculate cyclomatic complexity for a function node."""
    visitor = ComplexityVisitor()
    visitor.visit(node)
    return visitor.complexity


def calculate_nesting_depth(node: ast.AST, current_depth: int = 0) -> int:
    """Calculate maximum nesting depth of control structures."""
    max_depth = current_depth

    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
            child_depth = calculate_nesting_depth(child, current_depth + 1)
            max_depth = max(max_depth, child_depth)
        else:
            child_depth = calculate_nesting_depth(child, current_depth)
            max_depth = max(max_depth, child_depth)

    return max_depth


def calculate_cognitive_complexity(node: ast.AST) -> int:
    """Calculate cognitive complexity for a function node.

    Cognitive complexity weights nested structures more heavily than cyclomatic.
    Each control structure adds: 1 + current nesting depth.

    This captures the intuition that nested code is harder to understand
    even if the branch count is similar.
    """
    total = 0

    def visit(n: ast.AST, nesting: int = 0) -> None:
        nonlocal total

        # Control structures that increase cognitive complexity
        # Each adds 1 (base) + nesting level (penalty for depth)
        if isinstance(n, ast.If):
            total += 1 + nesting
            # Visit condition and body at increased nesting
            for child in ast.iter_child_nodes(n):
                if child in (n.test,):
                    visit(child, nesting)
                elif child in n.body:
                    visit(child, nesting + 1)
                elif child in n.orelse:
                    # else/elif - check if it's elif (nested If) or plain else
                    if isinstance(child, ast.If):
                        # elif doesn't increase nesting, just adds 1
                        total += 1
                        visit(child, nesting)
                    else:
                        visit(child, nesting + 1)
            return

        if isinstance(n, (ast.For, ast.While)):
            total += 1 + nesting
            for child in ast.iter_child_nodes(n):
                visit(child, nesting + 1)
            return

        if isinstance(n, ast.Try):
            total += 1 + nesting
            for child in ast.iter_child_nodes(n):
                if isinstance(child, ast.ExceptHandler):
                    # except clauses add complexity
                    total += 1
                    visit(child, nesting + 1)
                else:
                    visit(child, nesting + 1)
            return

        if isinstance(n, ast.With):
            total += 1 + nesting
            for child in ast.iter_child_nodes(n):
                visit(child, nesting + 1)
            return

        # Recurse into other nodes without adding complexity
        for child in ast.iter_child_nodes(n):
            visit(child, nesting)

    visit(node)
    return total


def try_mccabe_complexity(file_path: Path, threshold: int) -> dict[str, int]:
    """Try to get complexity via mccabe module, return func->complexity map."""
    result: dict[str, int] = {}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "mccabe", "--min", str(threshold), str(file_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        for line in proc.stdout.strip().split("\n"):
            if line and ":" in line:
                parts = line.split(":")
                if len(parts) >= 4:
                    func_match = parts[3].strip()
                    if func_match.startswith("'") and func_match.endswith("'"):
                        func_name = func_match[1:-1]
                    else:
                        func_name = func_match.split()[0].strip("'\"")
                    try:
                        complexity = int(parts[-1].strip().split()[0])
                        result[func_name] = complexity
                    except (ValueError, IndexError):
                        pass  # Skip unparseable radon output lines
    except (subprocess.SubprocessError, FileNotFoundError):
        pass  # radon not installed; skip complexity analysis
    return result


def analyze_file_kiss(file_path: Path, thresholds: KISSThresholds) -> list[KISSViolation]:
    """Analyze a single file for KISS violations."""
    violations: list[KISSViolation] = []

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return violations

    mccabe_results = try_mccabe_complexity(file_path, thresholds.warning_complexity)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        func_name = node.name

        if func_name in mccabe_results:
            complexity = mccabe_results[func_name]
        else:
            complexity = calculate_complexity(node)

        if complexity > thresholds.warning_complexity:
            severity = "error" if complexity > thresholds.max_complexity else "warning"
            violations.append(
                KISSViolation(
                    file=str(file_path),
                    function=func_name,
                    line=node.lineno,
                    violation_type="complexity",
                    value=complexity,
                    threshold=thresholds.max_complexity,
                    severity=severity,
                )
            )

        # +1 for inclusive line count (end - start + 1)
        func_lines = (node.end_lineno or node.lineno) - node.lineno + 1
        if func_lines > thresholds.max_function_lines:
            violations.append(
                KISSViolation(
                    file=str(file_path),
                    function=func_name,
                    line=node.lineno,
                    violation_type="length",
                    value=func_lines,
                    threshold=thresholds.max_function_lines,
                    severity="error",
                )
            )

        param_count = len(node.args.args) + len(node.args.kwonlyargs)
        if node.args.vararg:
            param_count += 1
        if node.args.kwarg:
            param_count += 1
        if param_count > thresholds.max_parameters:
            violations.append(
                KISSViolation(
                    file=str(file_path),
                    function=func_name,
                    line=node.lineno,
                    violation_type="parameters",
                    value=param_count,
                    threshold=thresholds.max_parameters,
                    severity="warning",
                )
            )

        depth = calculate_nesting_depth(node)
        if depth > thresholds.max_nesting_depth:
            violations.append(
                KISSViolation(
                    file=str(file_path),
                    function=func_name,
                    line=node.lineno,
                    violation_type="nesting",
                    value=depth,
                    threshold=thresholds.max_nesting_depth,
                    severity="error",
                )
            )

        # Cognitive complexity - weights nested structures more heavily
        cog_complexity = calculate_cognitive_complexity(node)
        if cog_complexity > thresholds.max_cognitive_complexity:
            violations.append(
                KISSViolation(
                    file=str(file_path),
                    function=func_name,
                    line=node.lineno,
                    violation_type="cognitive_complexity",
                    value=cog_complexity,
                    threshold=thresholds.max_cognitive_complexity,
                    severity="error",
                )
            )

    return violations


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


def generate_recommendations(violations: list[KISSViolation]) -> list[str]:
    """Generate actionable recommendations for KISS violations."""
    recommendations: list[str] = []
    violation_types = {v.violation_type for v in violations}

    if "complexity" in violation_types:
        recommendations.append(
            "COMPLEXITY: Extract helper functions, use early returns, "
            "simplify conditional logic with guard clauses."
        )

    if "length" in violation_types:
        recommendations.append(
            "LENGTH: Split function into smaller, single-purpose functions. "
            "Apply Single Responsibility Principle."
        )

    if "nesting" in violation_types:
        recommendations.append(
            "NESTING: Use early returns/guard clauses to reduce nesting. "
            "Extract nested blocks into separate functions."
        )

    if "parameters" in violation_types:
        recommendations.append(
            "PARAMETERS: Group related parameters into a dataclass/dict. "
            "Consider Builder pattern for complex construction."
        )

    return recommendations


def validate_kiss(
    scope_root: str,
    thresholds: Optional[KISSThresholds] = None,
    strict: bool = False,
    all_files: bool = False,
) -> ValidationResult:
    """Run KISS validation on files."""
    if thresholds is None:
        thresholds = KISSThresholds()

    root = Path(scope_root)
    files = find_python_files(root, changed_only=not all_files)

    all_violations: list[KISSViolation] = []
    for file_path in files:
        violations = analyze_file_kiss(file_path, thresholds)
        all_violations.extend(violations)

    errors = [v for v in all_violations if v.severity == "error"]
    warnings = [v for v in all_violations if v.severity == "warning"]
    blocked = len(errors) > 0 or (strict and len(warnings) > 0)

    return ValidationResult(
        allowed=not blocked,
        violations=[asdict(v) for v in all_violations],
        summary={
            "files_analyzed": len(files),
            "errors": len(errors),
            "warnings": len(warnings),
            "blocked": blocked,
        },
        recommendations=generate_recommendations(all_violations),
    )


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="KISS Validator - Enforce code simplicity")
    parser.add_argument(
        "--scope-root",
        default=".",
        help="Root directory to analyze",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=10,
        help="Max cyclomatic complexity (default: 10)",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=50,
        help="Max function lines (default: 50)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=4,
        help="Max nesting depth (default: 4)",
    )
    parser.add_argument(
        "--max-params",
        type=int,
        default=5,
        help="Max parameters (default: 5)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
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

    thresholds = KISSThresholds(
        max_complexity=args.threshold,
        max_function_lines=args.max_lines,
        max_nesting_depth=args.max_depth,
        max_parameters=args.max_params,
    )

    result = validate_kiss(
        args.scope_root,
        thresholds,
        args.strict,
        args.all,
    )

    output = {
        "allowed": result.allowed,
        "violations": result.violations,
        "summary": result.summary,
        "recommendations": result.recommendations,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"KISS Validation: {'PASSED' if result.allowed else 'BLOCKED'}")
        print(f"Files analyzed: {result.summary['files_analyzed']}")
        print(f"Errors: {result.summary['errors']}, Warnings: {result.summary['warnings']}")

        if result.violations:
            print("\nViolations:")
            for v in result.violations:
                print(
                    f"  [{v['severity'].upper()}] {v['file']}:{v['line']} "
                    f"{v['function']}: {v['violation_type']} = {v['value']} "
                    f"(max: {v['threshold']})"
                )

        if result.recommendations:
            print("\nRecommendations:")
            for rec in result.recommendations:
                print(f"  - {rec}")

    sys.exit(0 if result.allowed else 2)


if __name__ == "__main__":
    main()
