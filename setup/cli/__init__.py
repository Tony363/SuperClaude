"""
SuperClaude CLI Module
Command-line interface operations for SuperClaude installation system
"""

from .base import OperationBase

_OPERATION_IMPORTS = {
    "BackupOperation": "commands",
    "InstallOperation": "commands",
    "UninstallOperation": "commands",
    "UpdateOperation": "commands",
}


def __getattr__(name: str):
    if name in _OPERATION_IMPORTS:
        import importlib

        module = importlib.import_module(f".{_OPERATION_IMPORTS[name]}", __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "OperationBase",
    # BackupOperation, InstallOperation, UninstallOperation, UpdateOperation
    # are lazy-loaded via __getattr__ above and intentionally omitted from
    # __all__ to avoid static analysis warnings.
]
