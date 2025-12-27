"""
SuperClaude CLI Module
Command-line interface operations for SuperClaude installation system
"""

from .base import OperationBase
from .commands import (
    BackupOperation,
    InstallOperation,
    UninstallOperation,
    UpdateOperation,
)

__all__ = [
    "BackupOperation",
    "InstallOperation",
    "OperationBase",
    "UninstallOperation",
    "UpdateOperation",
]
