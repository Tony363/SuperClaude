"""
AST Analysis utilities for the SuperClaude Command Executor.

Provides lightweight semantic analysis for Python files including
import validation and unresolved symbol detection.
"""

import ast
import builtins
import importlib.util
from pathlib import Path
from typing import List, Optional, Set


class PythonSemanticAnalyzer(ast.NodeVisitor):
    """Very lightweight semantic analyzer for Python files."""

    _BUILTINS = set(dir(builtins)) | {
        "self",
        "cls",
        "__name__",
        "__file__",
        "__package__",
        "__doc__",
        "__all__",
        "__annotations__",
    }

    def __init__(self, file_path: Path, repo_root: Optional[Path]):
        self.file_path = Path(file_path)
        self.repo_root = Path(repo_root) if repo_root else self.file_path.parent
        self.scopes: List[Set[str]] = [set(self._BUILTINS)]
        self.missing_imports: List[str] = []
        self.unresolved_names: Set[str] = set()
        self.imported_symbols: Set[str] = set()
        self.module_name = self._derive_module_name()

    def _derive_module_name(self) -> Optional[str]:
        try:
            relative = self.file_path.relative_to(self.repo_root)
        except ValueError:
            return None
        parts = list(relative.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts) if parts else None

    # Scope helpers --------------------------------------------------

    def _push_scope(self) -> None:
        self.scopes.append(set())

    def _pop_scope(self) -> None:
        if len(self.scopes) > 1:
            self.scopes.pop()

    def _define(self, name: str) -> None:
        if name:
            self.scopes[-1].add(name)

    def _is_defined(self, name: str) -> bool:
        return any(name in scope for scope in reversed(self.scopes))

    # Visitors -------------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._define(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self._push_scope()
        self._define_arguments(node.args)
        for stmt in node.body:
            self.visit(stmt)
        self._pop_scope()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._define(node.name)
        for base in node.bases:
            self.visit(base)
        self._push_scope()
        for stmt in node.body:
            self.visit(stmt)
        self._pop_scope()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            defined = alias.asname or alias.name.split(".")[0]
            self._define(defined)
            self.imported_symbols.add(defined)
            self._validate_import(alias.name, level=0)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                continue
            defined = alias.asname or alias.name
            self._define(defined)
            self.imported_symbols.add(defined)
        self._validate_import(module, level=node.level or 0)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._define_target(target)
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.target:
            self._define_target(node.target)
        if node.annotation:
            self.visit(node.annotation)
        if node.value:
            self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.target)
        self.visit(node.value)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self._define_target(node.target)
        self._push_scope()
        for stmt in node.body:
            self.visit(stmt)
        self._pop_scope()
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.visit_For(node)  # type: ignore[arg-type]

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self._define_target(item.optional_vars)
        self._push_scope()
        for stmt in node.body:
            self.visit(stmt)
        self._pop_scope()

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.visit_With(node)  # type: ignore[arg-type]

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if not self._is_defined(node.id) and node.id not in self.imported_symbols:
                self.unresolved_names.add(node.id)
        elif isinstance(node.ctx, (ast.Store, ast.Param)):
            self._define(node.id)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node.generators, node.elt)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node.generators, node.elt)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node.generators, node.elt)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node.generators, node.key, node.value)

    def _visit_comprehension(
        self, generators: List[ast.comprehension], *exprs: ast.AST
    ) -> None:
        self._push_scope()
        for comp in generators:
            self.visit(comp.iter)
            self._define_target(comp.target)
            for if_clause in comp.ifs:
                self.visit(if_clause)
        for expr in exprs:
            self.visit(expr)
        self._pop_scope()

    def visit_Attribute(self, node: ast.Attribute) -> None:
        self.visit(node.value)

    # Helper operations -----------------------------------------------

    def _define_arguments(self, args: ast.arguments) -> None:
        for arg in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
            self._define(arg.arg)
        if args.vararg:
            self._define(args.vararg.arg)
        if args.kwarg:
            self._define(args.kwarg.arg)

    def _define_target(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self._define(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._define_target(elt)
        elif isinstance(target, ast.Attribute):
            self.visit(target.value)
        elif isinstance(target, ast.Subscript):
            self.visit(target.value)
            self.visit(target.slice)

    def _validate_import(self, module: str, level: int) -> None:
        module = module or ""
        candidate = self._resolve_module_name(module, level)
        if not candidate:
            return

        if self._module_exists(candidate):
            return

        try:
            spec = importlib.util.find_spec(candidate)
        except Exception:
            spec = None

        if spec is None:
            self.missing_imports.append(f"missing import '{candidate}'")

    def _resolve_module_name(self, module: str, level: int) -> Optional[str]:
        if level == 0:
            return module

        if not self.module_name:
            return module

        parts = self.module_name.split(".")
        if level > len(parts):
            return module

        base = parts[:-level]
        if module:
            base.append(module)
        return ".".join(base) if base else module

    def _module_exists(self, module_name: str) -> bool:
        parts = module_name.split(".")
        candidate_dir = self.repo_root.joinpath(*parts)
        if candidate_dir.with_suffix(".py").exists():
            return True
        if candidate_dir.exists() and (candidate_dir / "__init__.py").exists():
            return True
        return False

    def report(self) -> List[str]:
        issues: List[str] = []
        issues.extend(self.missing_imports)
        unresolved = sorted(
            self.unresolved_names - self._BUILTINS - set(self.imported_symbols)
        )
        for name in unresolved:
            issues.append(f"unresolved symbol '{name}'")
        return issues


# Backwards compatibility alias (underscore prefix was internal convention)
_PythonSemanticAnalyzer = PythonSemanticAnalyzer

__all__ = ["PythonSemanticAnalyzer", "_PythonSemanticAnalyzer"]
