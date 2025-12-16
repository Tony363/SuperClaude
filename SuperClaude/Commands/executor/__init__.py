"""
Executor package for the SuperClaude Command Framework.

This package contains the decomposed modules from the original executor.py,
providing better maintainability and clearer responsibility boundaries.

Modules:
- ast_analysis: Python AST semantic analysis
- utils: Common utility functions
- git_operations: Repository and git operations
- testing: Test execution and result parsing
- change_management: Change plans, stubs, and file operations
- telemetry: Metrics, artifacts, and event recording
- quality: Quality assessment utilities and helpers
- agent_orchestration: Agent selection, delegation, and orchestration
- consensus: Consensus building and policy resolution
"""

from .agent_orchestration import (
    BACKEND_SIGNALS,
    FRONTEND_SIGNALS,
    PERSONA_TO_AGENT,
    STRATEGIST_FALLBACK_ORDER,
    build_agent_payload,
    build_delegation_context,
    detect_task_domain,
    extract_delegate_targets,
    extract_files_from_parameters,
    ingest_agent_result,
    map_persona_to_agent,
    select_strategist_candidate,
)
from .ast_analysis import PythonSemanticAnalyzer, _PythonSemanticAnalyzer
from .change_management import (
    apply_changes_fallback,
    assess_stub_requirement,
    build_auto_stub_entry,
    build_default_evidence_entry,
    build_generic_stub_change,
    derive_change_plan,
    extract_agent_change_specs,
    infer_auto_stub_category,
    infer_auto_stub_extension,
    normalize_change_descriptor,
    render_auto_stub_content,
    render_default_evidence_document,
)
from .consensus import (
    VoteType as ConsensusVoteType,
)
from .consensus import (
    build_consensus_prompt,
    consensus_failed_message,
    extract_consensus_metadata,
    format_consensus_result,
    load_consensus_policies,
    normalize_vote_type,
    resolve_consensus_policy,
)
from .git_operations import (
    clean_build_artifacts,
    collect_diff_stats,
    detect_repo_root,
    diff_snapshots,
    extract_changed_paths,
    extract_feature_list,
    extract_heading_titles,
    format_change_entry,
    generate_commit_message,
    git_has_modifications,
    is_artifact_change,
    normalize_repo_root,
    partition_change_entries,
    relative_to_repo_path,
    run_command,
    select_feature_owner,
    snapshot_repo_changes,
)
from .quality import (
    aggregate_dimension_scores,
    build_quality_context,
    calculate_pass_rate,
    derive_quality_status,
    extract_quality_improvements,
    format_quality_summary,
    serialize_assessment,
    validate_quality_threshold,
)
from .telemetry import (
    MetricType,
    TelemetryConfig,
    build_metric_tags,
    format_evidence_event,
    format_fast_codex_event,
    format_plan_only_event,
    format_quality_artifact_summary,
    format_test_artifact_summary,
    prune_safe_apply_snapshots,
    summarize_rube_context,
    truncate_fast_codex_stream,
    write_safe_apply_snapshot,
)
from .testing import (
    parse_pytest_output,
    run_requested_tests,
    should_run_tests,
    summarize_test_results,
)
from .utils import (
    clamp_int,
    coerce_float,
    deduplicate,
    ensure_list,
    extract_output_evidence,
    is_truthy,
    normalize_evidence_value,
    slugify,
    to_list,
    truncate_output,
)

__all__ = [
    # AST Analysis
    "PythonSemanticAnalyzer",
    "_PythonSemanticAnalyzer",
    # Change Management
    "apply_changes_fallback",
    "assess_stub_requirement",
    "build_auto_stub_entry",
    "build_default_evidence_entry",
    "build_generic_stub_change",
    "derive_change_plan",
    "extract_agent_change_specs",
    "infer_auto_stub_category",
    "infer_auto_stub_extension",
    "normalize_change_descriptor",
    "render_auto_stub_content",
    "render_default_evidence_document",
    # Utils
    "clamp_int",
    "coerce_float",
    "deduplicate",
    "ensure_list",
    "extract_output_evidence",
    "is_truthy",
    "normalize_evidence_value",
    "slugify",
    "to_list",
    "truncate_output",
    # Git Operations
    "clean_build_artifacts",
    "collect_diff_stats",
    "detect_repo_root",
    "diff_snapshots",
    "extract_changed_paths",
    "extract_feature_list",
    "extract_heading_titles",
    "format_change_entry",
    "generate_commit_message",
    "git_has_modifications",
    "is_artifact_change",
    "normalize_repo_root",
    "partition_change_entries",
    "relative_to_repo_path",
    "run_command",
    "select_feature_owner",
    "snapshot_repo_changes",
    # Testing
    "parse_pytest_output",
    "run_requested_tests",
    "should_run_tests",
    "summarize_test_results",
    # Telemetry
    "MetricType",
    "TelemetryConfig",
    "build_metric_tags",
    "format_evidence_event",
    "format_fast_codex_event",
    "format_plan_only_event",
    "format_quality_artifact_summary",
    "format_test_artifact_summary",
    "prune_safe_apply_snapshots",
    "summarize_rube_context",
    "truncate_fast_codex_stream",
    "write_safe_apply_snapshot",
    # Quality
    "aggregate_dimension_scores",
    "build_quality_context",
    "calculate_pass_rate",
    "derive_quality_status",
    "extract_quality_improvements",
    "format_quality_summary",
    "serialize_assessment",
    "validate_quality_threshold",
    # Agent Orchestration
    "BACKEND_SIGNALS",
    "FRONTEND_SIGNALS",
    "PERSONA_TO_AGENT",
    "STRATEGIST_FALLBACK_ORDER",
    "build_agent_payload",
    "build_delegation_context",
    "detect_task_domain",
    "extract_delegate_targets",
    "extract_files_from_parameters",
    "ingest_agent_result",
    "map_persona_to_agent",
    "select_strategist_candidate",
    # Consensus
    "ConsensusVoteType",
    "build_consensus_prompt",
    "consensus_failed_message",
    "extract_consensus_metadata",
    "format_consensus_result",
    "load_consensus_policies",
    "normalize_vote_type",
    "resolve_consensus_policy",
]
