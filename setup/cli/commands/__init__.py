"""
SuperClaude CLI Commands
Individual command implementations for the CLI interface
"""

from ..base import OperationBase

# Operation classes are loaded on demand by load_operation_module()
# in the CLI hub. Eager imports here pull in optional dependencies.
_OPERATION_IMPORTS = {
    "BackupOperation": "backup",
    "InstallOperation": "install",
    "UninstallOperation": "uninstall",
    "UpdateOperation": "update",
}


def __getattr__(name: str):
    if name in _OPERATION_IMPORTS:
        import importlib

        module = importlib.import_module(f".{_OPERATION_IMPORTS[name]}", __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BackupOperation",
    "InstallOperation",
    "OperationBase",
    "UninstallOperation",
    "UpdateOperation",
]
