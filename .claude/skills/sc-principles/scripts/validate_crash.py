#!/usr/bin/env python3
"""Let It Crash Validator - Check error handling patterns.

Uses AST analysis to detect anti-patterns:
- Bare except: clauses
- except Exception with no re-raise
- except: pass (silent failure)
- Nested try/except cascades

Exit Codes:
    0 - Crash validation passed
    2 - Crash violations detected (blocked)
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
class CrashThresholds:
    """Configurable thresholds for Let It Crash validation."""

    max_nested_try: int = 2  # Max nested try/except depth


@dataclass
class CrashViolation:
    """Single Let It Crash violation."""

    file: str
    line: int
    violation_type: str
    message: str
    severity: str
    context: str = ""


@dataclass
class ValidationResult:
    """Result of crash validation."""

    allowed: bool
    violations: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


# Shell paths where error handling is expected
SHELL_PATH_PATTERNS = ["handlers", "adapters", "api", "cli", "scripts", "tests"]


def is_shell_path(file_path: Path) -> bool:
    """Check if file is in a 'shell' directory (I/O boundary)."""
    parts = file_path.parts
    for pattern in SHELL_PATH_PATTERNS:
        if pattern in parts:
            return True
    return False


class CrashVisitor(ast.NodeVisitor):
    """Detect Let It Crash anti-patterns."""

    def __init__(self, thresholds: CrashThresholds, is_shell: bool) -> None:
        self.thresholds = thresholds
        self.is_shell = is_shell
        self.violations: list[CrashViolation] = []
        self.file_path = ""
        self.try_depth = 0
        self.current_function: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track current function context."""
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track current async function context."""
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func

    def visit_Try(self, node: ast.Try) -> None:
        """Check try/except patterns."""
        self.try_depth += 1

        # Check for nested try/except
        if self.try_depth > self.thresholds.max_nested_try:
            self.violations.append(
                CrashViolation(
                    file=self.file_path,
                    line=node.lineno,
                    violation_type="nested_try_except",
                    message=f"Nested try/except depth {self.try_depth} exceeds max "
                    f"{self.thresholds.max_nested_try}. Simplify error handling.",
                    severity="warning",
                    context=self.current_function or "",
                )
            )

        # Check each except handler
        for handler in node.handlers:
            self._check_handler(handler)

        self.generic_visit(node)
        self.try_depth -= 1

    def _check_handler(self, handler: ast.ExceptHandler) -> None:
        """Check a single exception handler for anti-patterns."""
        # Bare except (no exception type)
        if handler.type is None:
            self.violations.append(
                CrashViolation(
                    file=self.file_path,
                    line=handler.lineno,
                    violation_type="bare_except",
                    message="Bare 'except:' catches all exceptions including "
                    "KeyboardInterrupt and SystemExit. Use specific exceptions.",
                    severity="error",
                    context=self.current_function or "",
                )
            )

        # Check for except: pass or except Exception: pass
        if self._is_pass_only(handler.body):
            self.violations.append(
                CrashViolation(
                    file=self.file_path,
                    line=handler.lineno,
                    violation_type="except_pass",
                    message="Silent exception handling (except: pass) hides bugs. "
                    "Either let it crash or handle meaningfully.",
                    severity="error",
                    context=self.current_function or "",
                )
            )
            return  # Don't double-report

        # Check for except Exception without re-raise (only in core paths)
        if not self.is_shell and self._is_broad_exception(handler.type):
            if not self._has_reraise(handler.body):
                self.violations.append(
                    CrashViolation(
                        file=self.file_path,
                        line=handler.lineno,
                        violation_type="exception_swallowed",
                        message="Broad exception caught without re-raise. "
                        "In core logic, let errors propagate to boundaries.",
                        severity="warning",
                        context=self.current_function or "",
                    )
                )

    def _is_pass_only(self, body: list[ast.stmt]) -> bool:
        """Check if handler body is just 'pass'."""
        if len(body) == 1 and isinstance(body[0], ast.Pass):
            return True
        # Also check for pass with just a comment (Expr with string)
        if len(body) == 1 and isinstance(body[0], ast.Expr):
            if isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                return True  # Docstring-only is effectively pass
        return False

    def _is_broad_exception(self, exc_type: Optional[ast.expr]) -> bool:
        """Check if exception type is broad (Exception or BaseException)."""
        if exc_type is None:
            return True  # Bare except is broadest

        if isinstance(exc_type, ast.Name):
            return exc_type.id in ("Exception", "BaseException")

        if isinstance(exc_type, ast.Tuple):
            # Multiple exceptions - check if any is broad
            for elt in exc_type.elts:
                if isinstance(elt, ast.Name) and elt.id in ("Exception", "BaseException"):
                    return True

        return False

    def _has_reraise(self, body: list[ast.stmt]) -> bool:
        """Check if handler body contains a re-raise."""
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, ast.Raise):
                # raise (bare) or raise e
                return True
        return False


def analyze_file_crash(
    file_path: Path,
    thresholds: CrashThresholds,
) -> list[CrashViolation]:
    """Analyze a single file for Let It Crash violations."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    is_shell = is_shell_path(file_path)

    visitor = CrashVisitor(thresholds, is_shell)
    visitor.file_path = str(file_path)
    visitor.visit(tree)

    return visitor.violations


def find_python_files(scope_root: Path, changed_only: bool = True) -> list[Path]:
    """Find Python files to analyze."""
    if changed_only:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                cwd=scope_root,
                check=False,
            )
            staged = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                cwd=scope_root,
                check=False,
            )

            all_files = set(result.stdout.strip().split("\n"))
            all_files.update(staged.stdout.strip().split("\n"))
            all_files.discard("")

            py_files = [
                scope_root / f for f in all_files if f.endswith(".py") and (scope_root / f).exists()
            ]

            if py_files:
                return py_files
        except (subprocess.SubprocessError, FileNotFoundError):
            pass  # Fall back to rglob below when git is unavailable

    return list(scope_root.rglob("*.py"))


def generate_recommendations(violations: list[CrashViolation]) -> list[str]:
    """Generate actionable recommendations for crash violations."""
    recommendations: list[str] = []
    violation_types = {v.violation_type for v in violations}

    if "bare_except" in violation_types:
        recommendations.append(
            "BARE EXCEPT: Catch specific exceptions. Bare 'except:' catches "
            "KeyboardInterrupt and SystemExit, making programs hard to stop."
        )

    if "except_pass" in violation_types:
        recommendations.append(
            "SILENT FAILURE: Remove 'except: pass' blocks. Either let errors crash "
            "(preferred in core logic) or handle them meaningfully with logging."
        )

    if "exception_swallowed" in violation_types:
        recommendations.append(
            "SWALLOWED EXCEPTION: In core logic, let exceptions propagate. "
            "Handle them at boundaries (API, CLI, adapters) where you can respond appropriately."
        )

    if "nested_try_except" in violation_types:
        recommendations.append(
            "NESTED TRY/EXCEPT: Flatten error handling. Complex fallback cascades "
            "are hard to debug. Fail fast and handle at a single boundary."
        )

    return recommendations


def validate_crash(
    scope_root: str,
    thresholds: Optional[CrashThresholds] = None,
    strict: bool = False,
    all_files: bool = False,
) -> ValidationResult:
    """Run Let It Crash validation on files."""
    if thresholds is None:
        thresholds = CrashThresholds()

    root = Path(scope_root)
    files = find_python_files(root, changed_only=not all_files)

    all_violations: list[CrashViolation] = []
    for file_path in files:
        violations = analyze_file_crash(file_path, thresholds)
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
            "by_type": {
                "bare_except": len(
                    [v for v in all_violations if v.violation_type == "bare_except"]
                ),
                "except_pass": len(
                    [v for v in all_violations if v.violation_type == "except_pass"]
                ),
                "exception_swallowed": len(
                    [v for v in all_violations if v.violation_type == "exception_swallowed"]
                ),
                "nested_try_except": len(
                    [v for v in all_violations if v.violation_type == "nested_try_except"]
                ),
            },
        },
        recommendations=generate_recommendations(all_violations),
    )


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Let It Crash Validator - Enforce error handling patterns"
    )
    parser.add_argument(
        "--scope-root",
        default=".",
        help="Root directory to analyze",
    )
    parser.add_argument(
        "--max-nested-try",
        type=int,
        default=2,
        help="Max nested try/except depth (default: 2)",
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

    thresholds = CrashThresholds(
        max_nested_try=args.max_nested_try,
    )

    result = validate_crash(
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
        print(f"Let It Crash Validation: {'PASSED' if result.allowed else 'BLOCKED'}")
        print(f"Files analyzed: {result.summary['files_analyzed']}")
        print(f"Errors: {result.summary['errors']}, Warnings: {result.summary['warnings']}")

        if result.summary.get("by_type"):
            print("\nBy Type:")
            for vtype, count in result.summary["by_type"].items():
                if count > 0:
                    print(f"  {vtype}: {count}")

        if result.violations:
            print("\nViolations:")
            for v in result.violations:
                print(
                    f"  [{v['severity'].upper()}] {v['file']}:{v['line']} "
                    f"{v['violation_type']}: {v['message']}"
                )

        if result.recommendations:
            print("\nRecommendations:")
            for rec in result.recommendations:
                print(f"  - {rec}")

    sys.exit(0 if result.allowed else 2)


if __name__ == "__main__":
    main()
