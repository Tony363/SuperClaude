"""
Execution module for SuperClaude Commands.

Contains decomposed command execution logic:
- context: CommandContext and CommandResult dataclasses
- routing: Command metadata resolution with Skills integration
- agents: Agent loading, pipeline, and orchestration
- repo_ops: Git snapshot, diff, and apply operations
- quality: Quality loop, test running, and evidence gating
- consensus: Consensus policies and enforcement
- artifacts: Artifact recording and management
"""

from .artifacts import ArtifactsService
from .consensus import ConsensusService, VoteType
from .context import CommandContext, CommandResult
from .facade import ExecutionFacade
from .repo_ops import RepoAndWorktreeService
from .routing import CommandMetadataResolver, CommandRouter, ExecutionPlan, RuntimeMode

__all__ = [
    "ArtifactsService",
    "CommandContext",
    "CommandResult",
    "CommandMetadataResolver",
    "CommandRouter",
    "ConsensusService",
    "ExecutionFacade",
    "ExecutionPlan",
    "RepoAndWorktreeService",
    "RuntimeMode",
    "VoteType",
]
