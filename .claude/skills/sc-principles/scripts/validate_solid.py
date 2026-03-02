#!/usr/bin/env python3
"""SOLID Validator - Check code against SOLID design principles.

Uses AST analysis to detect:
- SRP: File length, class method count
- OCP: isinstance cascades, type switches
- LSP: NotImplementedError in overrides
- ISP: Fat interfaces/protocols
- DIP: Direct instantiation in business logic

Exit Codes:
    0 - SOLID validation passed
    2 - SOLID violations detected (blocked)
    3 - Validation error
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

try:
    from .shared import find_python_files
except ImportError:
    from shared import find_python_files


@dataclass
class SOLIDThresholds:
    """Configurable SOLID thresholds."""

    max_file_lines: int = 300
    max_class_public_methods: int = 5
    max_interface_methods: int = 7
    max_isinstance_chain: int = 2


@dataclass
class SOLIDViolation:
    """Single SOLID violation."""

    file: str
    line: int
    violation_type: str
    message: str
    principle: str
    severity: str
    context: str = ""


@dataclass
class ValidationResult:
    """Result of SOLID validation."""

    allowed: bool
    violations: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


# Core paths where DIP should be enforced strictly
CORE_PATH_PATTERNS = ["domain", "logic", "services", "utils", "core"]
SHELL_PATH_PATTERNS = ["handlers", "adapters", "api", "cli", "scripts", "tests"]


def is_core_path(file_path: Path) -> bool:
    """Check if file is in a 'core' directory (business logic)."""
    parts = file_path.parts
    for pattern in CORE_PATH_PATTERNS:
        if pattern in parts:
            return True
    return False


class CombinedSOLIDVisitor(ast.NodeVisitor):
    """Single-pass visitor that checks all 5 SOLID principles.

    Consolidates SRP, OCP, LSP, ISP, and DIP checks into one AST traversal
    instead of 5 separate passes over the same tree.
    """

    # DIP: Common service/infrastructure class name patterns
    SERVICE_PATTERNS = [
        "Connection",
        "Service",
        "Client",
        "Repository",
        "Database",
        "Cache",
        "Logger",
        "Queue",
        "Session",
    ]

    def __init__(self, thresholds: SOLIDThresholds, is_core: bool) -> None:
        self.thresholds = thresholds
        self.is_core = is_core
        self.violations: list[SOLIDViolation] = []
        self.file_path = ""
        # LSP + DIP: Track context
        self.current_class: Optional[str] = None
        self.current_class_is_abstract: bool = False
        self.current_function: Optional[str] = None

    def check_file_length(self, source: str) -> None:
        """SRP: Check if file exceeds line limit."""
        lines = source.count("\n") + 1
        if lines > self.thresholds.max_file_lines:
            self.violations.append(
                SOLIDViolation(
                    file=self.file_path,
                    line=1,
                    violation_type="srp_file_length",
                    message=f"File has {lines} lines (max: {self.thresholds.max_file_lines})",
                    principle="SRP",
                    severity="warning",
                )
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Combined class checks: SRP, ISP, LSP context tracking."""
        public_methods = [
            n
            for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")
        ]

        # SRP: Too many public methods
        if len(public_methods) > self.thresholds.max_class_public_methods:
            self.violations.append(
                SOLIDViolation(
                    file=self.file_path,
                    line=node.lineno,
                    violation_type="srp_class_methods",
                    message=f"Class '{node.name}' has {len(public_methods)} public methods "
                    f"(max: {self.thresholds.max_class_public_methods})",
                    principle="SRP",
                    severity="warning",
                    context=node.name,
                )
            )

        # ISP: Fat interfaces (Protocol or ABC)
        if self._is_protocol_or_abc(node):
            method_count = len(public_methods)
            if method_count > self.thresholds.max_interface_methods:
                self.violations.append(
                    SOLIDViolation(
                        file=self.file_path,
                        line=node.lineno,
                        violation_type="isp_fat_interface",
                        message=f"Interface '{node.name}' has {method_count} methods "
                        f"(max: {self.thresholds.max_interface_methods}). "
                        "Consider splitting into smaller interfaces.",
                        principle="ISP",
                        severity="warning",
                        context=node.name,
                    )
                )

        # LSP: Track class context for NotImplementedError checks
        old_class = self.current_class
        old_abstract = self.current_class_is_abstract
        self.current_class = node.name
        self.current_class_is_abstract = self._is_protocol_or_abc(node)
        self.generic_visit(node)
        self.current_class = old_class
        self.current_class_is_abstract = old_abstract

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Combined function checks: OCP, LSP, DIP."""
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Combined async function checks: OCP, LSP, DIP."""
        self._check_function(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Run OCP, LSP, and DIP checks in a single walk of the function body."""
        old_func = self.current_function
        self.current_function = node.name

        # Single walk over function body for OCP + LSP + DIP
        isinstance_count = 0
        for child in ast.walk(node):
            # OCP: Count isinstance checks in if-conditions
            if isinstance(child, ast.If):
                if self._is_isinstance_check(child.test):
                    isinstance_count += 1

            # LSP: Check for NotImplementedError raises (only in concrete class methods)
            if (
                self.current_class
                and not self.current_class_is_abstract
                and not self._has_abstractmethod_decorator(node)
                and isinstance(child, ast.Raise)
            ):
                self._check_not_implemented_raise(child, node.name)

            # DIP: Check for direct service instantiation (only in core paths)
            if self.is_core and isinstance(child, ast.Call):
                class_name = self._get_class_name(child.func)
                if class_name and self._is_service_class(class_name):
                    self.violations.append(
                        SOLIDViolation(
                            file=self.file_path,
                            line=child.lineno,
                            violation_type="dip_direct_instantiation",
                            message=f"Direct instantiation of '{class_name}' in function "
                            f"'{self.current_function}'. Consider dependency injection.",
                            principle="DIP",
                            severity="warning",
                            context=self.current_function or "",
                        )
                    )

        # OCP: Report isinstance cascade if threshold exceeded
        if isinstance_count > self.thresholds.max_isinstance_chain:
            self.violations.append(
                SOLIDViolation(
                    file=self.file_path,
                    line=node.lineno,
                    violation_type="ocp_isinstance_cascade",
                    message=f"Function '{node.name}' has {isinstance_count} isinstance checks. "
                    "Consider using polymorphism or strategy pattern.",
                    principle="OCP",
                    severity="warning",
                    context=node.name,
                )
            )

        self.generic_visit(node)
        self.current_function = old_func

    # --- Helper methods ---

    def _is_isinstance_check(self, node: ast.expr) -> bool:
        """OCP: Check if expression is an isinstance call."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                return True
        return False

    def _check_not_implemented_raise(self, child: ast.Raise, func_name: str) -> None:
        """LSP: Check if a Raise node raises NotImplementedError."""
        if child.exc is None:
            return
        exc_name: Optional[str] = None
        if isinstance(child.exc, ast.Call) and isinstance(child.exc.func, ast.Name):
            exc_name = child.exc.func.id
        elif isinstance(child.exc, ast.Name):
            exc_name = child.exc.id

        if exc_name == "NotImplementedError":
            self.violations.append(
                SOLIDViolation(
                    file=self.file_path,
                    line=child.lineno,
                    violation_type="lsp_not_implemented",
                    message=f"Method '{func_name}' in class '{self.current_class}' "
                    "raises NotImplementedError, violating LSP.",
                    principle="LSP",
                    severity="error",
                    context=f"{self.current_class}.{func_name}",
                )
            )

    def _has_abstractmethod_decorator(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """LSP: Check if method has @abstractmethod decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                return True
            if isinstance(decorator, ast.Attribute) and decorator.attr == "abstractmethod":
                return True
        return False

    def _is_protocol_or_abc(self, node: ast.ClassDef) -> bool:
        """ISP: Check if class inherits from Protocol/ABC or uses metaclass=ABCMeta."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in ("Protocol", "ABC"):
                return True
            if isinstance(base, ast.Attribute) and base.attr in ("Protocol", "ABC"):
                return True
        for kw in node.keywords:
            if kw.arg == "metaclass":
                if isinstance(kw.value, ast.Name) and kw.value.id == "ABCMeta":
                    return True
                if isinstance(kw.value, ast.Attribute) and kw.value.attr == "ABCMeta":
                    return True
        return False

    def _get_class_name(self, node: ast.expr) -> Optional[str]:
        """DIP: Extract class name from call expression."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _is_service_class(self, name: str) -> bool:
        """DIP: Check if name looks like a service/infrastructure class.

        Uses endswith to avoid false positives on unrelated classes like
        SessionToken, CacheKey, LoggerConfig, ServiceLevel, etc.
        """
        return name.endswith(tuple(self.SERVICE_PATTERNS))


def analyze_file_solid(
    file_path: Path,
    thresholds: SOLIDThresholds,
) -> list[SOLIDViolation]:
    """Analyze a single file for SOLID violations in a single AST pass."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    is_core = is_core_path(file_path)
    visitor = CombinedSOLIDVisitor(thresholds, is_core)
    visitor.file_path = str(file_path)
    visitor.check_file_length(source)
    visitor.visit(tree)

    return visitor.violations


def generate_recommendations(violations: list[SOLIDViolation]) -> list[str]:
    """Generate actionable recommendations for SOLID violations."""
    recommendations: list[str] = []
    principles = {v.principle for v in violations}

    if "SRP" in principles:
        recommendations.append(
            "SRP: Extract responsibilities into separate modules/classes. "
            "Each class should have one reason to change."
        )

    if "OCP" in principles:
        recommendations.append(
            "OCP: Use strategy pattern, registry, or polymorphism instead of "
            "type-checking cascades. Extend, don't modify."
        )

    if "LSP" in principles:
        recommendations.append(
            "LSP: Subclasses must honor base class contracts. If a method can't "
            "be implemented, the inheritance hierarchy is wrong."
        )

    if "ISP" in principles:
        recommendations.append(
            "ISP: Split fat interfaces into smaller, focused ones. "
            "Clients shouldn't depend on methods they don't use."
        )

    if "DIP" in principles:
        recommendations.append(
            "DIP: Inject dependencies instead of instantiating them directly. "
            "Business logic should depend on abstractions."
        )

    return recommendations


def validate_solid(
    scope_root: str,
    thresholds: Optional[SOLIDThresholds] = None,
    strict: bool = False,
    all_files: bool = False,
) -> ValidationResult:
    """Run SOLID validation on files."""
    if thresholds is None:
        thresholds = SOLIDThresholds()

    root = Path(scope_root)
    files = find_python_files(root, changed_only=not all_files)

    all_violations: list[SOLIDViolation] = []
    for file_path in files:
        violations = analyze_file_solid(file_path, thresholds)
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
            "by_principle": {
                "SRP": len([v for v in all_violations if v.principle == "SRP"]),
                "OCP": len([v for v in all_violations if v.principle == "OCP"]),
                "LSP": len([v for v in all_violations if v.principle == "LSP"]),
                "ISP": len([v for v in all_violations if v.principle == "ISP"]),
                "DIP": len([v for v in all_violations if v.principle == "DIP"]),
            },
        },
        recommendations=generate_recommendations(all_violations),
    )


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="SOLID Validator - Enforce design principles")
    parser.add_argument(
        "--scope-root",
        default=".",
        help="Root directory to analyze",
    )
    parser.add_argument(
        "--max-file-lines",
        type=int,
        default=300,
        help="Max file lines for SRP (default: 300)",
    )
    parser.add_argument(
        "--max-class-methods",
        type=int,
        default=5,
        help="Max public methods per class for SRP (default: 5)",
    )
    parser.add_argument(
        "--max-interface-methods",
        type=int,
        default=7,
        help="Max interface methods for ISP (default: 7)",
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

    thresholds = SOLIDThresholds(
        max_file_lines=args.max_file_lines,
        max_class_public_methods=args.max_class_methods,
        max_interface_methods=args.max_interface_methods,
    )

    result = validate_solid(
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
        print(f"SOLID Validation: {'PASSED' if result.allowed else 'BLOCKED'}")
        print(f"Files analyzed: {result.summary['files_analyzed']}")
        print(f"Errors: {result.summary['errors']}, Warnings: {result.summary['warnings']}")

        if result.summary.get("by_principle"):
            print("\nBy Principle:")
            for principle, count in result.summary["by_principle"].items():
                if count > 0:
                    print(f"  {principle}: {count}")

        if result.violations:
            print("\nViolations:")
            for v in result.violations:
                print(
                    f"  [{v['severity'].upper()}] {v['file']}:{v['line']} "
                    f"[{v['principle']}] {v['message']}"
                )

        if result.recommendations:
            print("\nRecommendations:")
            for rec in result.recommendations:
                print(f"  - {rec}")

    sys.exit(0 if result.allowed else 2)


if __name__ == "__main__":
    main()
