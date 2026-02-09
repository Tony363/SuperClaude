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
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


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


class SRPVisitor(ast.NodeVisitor):
    """Detect Single Responsibility Principle violations."""

    def __init__(self, thresholds: SOLIDThresholds) -> None:
        self.thresholds = thresholds
        self.violations: list[SOLIDViolation] = []
        self.file_path = ""

    def check_file_length(self, source: str) -> Optional[SOLIDViolation]:
        """Check if file exceeds line limit."""
        lines = source.count("\n") + 1
        if lines > self.thresholds.max_file_lines:
            return SOLIDViolation(
                file=self.file_path,
                line=1,
                violation_type="srp_file_length",
                message=f"File has {lines} lines (max: {self.thresholds.max_file_lines})",
                principle="SRP",
                severity="warning",
            )
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class for too many public methods."""
        public_methods = [
            n
            for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")
        ]

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

        self.generic_visit(node)


class OCPVisitor(ast.NodeVisitor):
    """Detect Open-Closed Principle violations."""

    def __init__(self, thresholds: SOLIDThresholds) -> None:
        self.thresholds = thresholds
        self.violations: list[SOLIDViolation] = []
        self.file_path = ""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check for isinstance cascades in functions."""
        self._check_isinstance_cascade(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check for isinstance cascades in async functions."""
        self._check_isinstance_cascade(node)
        self.generic_visit(node)

    def _check_isinstance_cascade(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Detect isinstance cascade patterns."""
        isinstance_count = 0

        for child in ast.walk(node):
            if isinstance(child, ast.If):
                # Check if condition uses isinstance
                if self._is_isinstance_check(child.test):
                    isinstance_count += 1

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

    def _is_isinstance_check(self, node: ast.expr) -> bool:
        """Check if expression is an isinstance call."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                return True
        return False


class LSPVisitor(ast.NodeVisitor):
    """Detect Liskov Substitution Principle violations."""

    def __init__(self) -> None:
        self.violations: list[SOLIDViolation] = []
        self.file_path = ""
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track current class for context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check for NotImplementedError raises."""
        if self.current_class:
            self._check_not_implemented(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check for NotImplementedError raises in async methods."""
        if self.current_class:
            self._check_not_implemented(node)
        self.generic_visit(node)

    def _check_not_implemented(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Detect NotImplementedError in method bodies."""
        for child in ast.walk(node):
            if isinstance(child, ast.Raise):
                if child.exc is not None:
                    # Check for raise NotImplementedError(...)
                    if isinstance(child.exc, ast.Call):
                        if isinstance(child.exc.func, ast.Name):
                            if child.exc.func.id == "NotImplementedError":
                                self.violations.append(
                                    SOLIDViolation(
                                        file=self.file_path,
                                        line=child.lineno,
                                        violation_type="lsp_not_implemented",
                                        message=f"Method '{node.name}' in class '{self.current_class}' "
                                        "raises NotImplementedError, violating LSP.",
                                        principle="LSP",
                                        severity="error",
                                        context=f"{self.current_class}.{node.name}",
                                    )
                                )
                    # Check for raise NotImplementedError (without call)
                    elif isinstance(child.exc, ast.Name):
                        if child.exc.id == "NotImplementedError":
                            self.violations.append(
                                SOLIDViolation(
                                    file=self.file_path,
                                    line=child.lineno,
                                    violation_type="lsp_not_implemented",
                                    message=f"Method '{node.name}' in class '{self.current_class}' "
                                    "raises NotImplementedError, violating LSP.",
                                    principle="LSP",
                                    severity="error",
                                    context=f"{self.current_class}.{node.name}",
                                )
                            )


class ISPVisitor(ast.NodeVisitor):
    """Detect Interface Segregation Principle violations."""

    def __init__(self, thresholds: SOLIDThresholds) -> None:
        self.thresholds = thresholds
        self.violations: list[SOLIDViolation] = []
        self.file_path = ""

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check for fat interfaces (Protocol or ABC)."""
        is_protocol = self._is_protocol(node)
        is_abc = self._is_abc(node)

        if is_protocol or is_abc:
            method_count = len(
                [
                    n
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not n.name.startswith("_")
                ]
            )

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

        self.generic_visit(node)

    def _is_protocol(self, node: ast.ClassDef) -> bool:
        """Check if class inherits from Protocol."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "Protocol":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "Protocol":
                return True
        return False

    def _is_abc(self, node: ast.ClassDef) -> bool:
        """Check if class inherits from ABC."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "ABC":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "ABC":
                return True
        return False


class DIPVisitor(ast.NodeVisitor):
    """Detect Dependency Inversion Principle violations."""

    def __init__(self, is_core: bool) -> None:
        self.is_core = is_core
        self.violations: list[SOLIDViolation] = []
        self.file_path = ""
        self.current_function: Optional[str] = None

    # Common service/infrastructure class name patterns
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

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check for direct instantiation in functions."""
        old_func = self.current_function
        self.current_function = node.name
        self._check_instantiation(node)
        self.generic_visit(node)
        self.current_function = old_func

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check for direct instantiation in async functions."""
        old_func = self.current_function
        self.current_function = node.name
        self._check_instantiation(node)
        self.generic_visit(node)
        self.current_function = old_func

    def _check_instantiation(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Detect direct instantiation of service classes."""
        if not self.is_core:
            return  # Only check core paths

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
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

    def _get_class_name(self, node: ast.expr) -> Optional[str]:
        """Extract class name from call expression."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _is_service_class(self, name: str) -> bool:
        """Check if name looks like a service/infrastructure class."""
        return any(pattern in name for pattern in self.SERVICE_PATTERNS)


def analyze_file_solid(
    file_path: Path,
    thresholds: SOLIDThresholds,
) -> list[SOLIDViolation]:
    """Analyze a single file for SOLID violations."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    violations: list[SOLIDViolation] = []
    file_str = str(file_path)
    is_core = is_core_path(file_path)

    # SRP checks
    srp_visitor = SRPVisitor(thresholds)
    srp_visitor.file_path = file_str
    file_length_violation = srp_visitor.check_file_length(source)
    if file_length_violation:
        violations.append(file_length_violation)
    srp_visitor.visit(tree)
    violations.extend(srp_visitor.violations)

    # OCP checks
    ocp_visitor = OCPVisitor(thresholds)
    ocp_visitor.file_path = file_str
    ocp_visitor.visit(tree)
    violations.extend(ocp_visitor.violations)

    # LSP checks
    lsp_visitor = LSPVisitor()
    lsp_visitor.file_path = file_str
    lsp_visitor.visit(tree)
    violations.extend(lsp_visitor.violations)

    # ISP checks
    isp_visitor = ISPVisitor(thresholds)
    isp_visitor.file_path = file_str
    isp_visitor.visit(tree)
    violations.extend(isp_visitor.violations)

    # DIP checks (only in core paths)
    dip_visitor = DIPVisitor(is_core)
    dip_visitor.file_path = file_str
    dip_visitor.visit(tree)
    violations.extend(dip_visitor.violations)

    return violations


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
