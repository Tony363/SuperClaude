"""CLI gate for CodeRabbit review thresholds used during CI."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:  # Optional dependency required only when YAML config is parsed
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None  # type: ignore

from ..MCP.coderabbit import CodeRabbitClient, CodeRabbitError, CodeRabbitReview, scrub_secrets
from ..Monitoring.paths import get_metrics_dir

LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "Config" / "coderabbit.yaml"
CI_FILENAME = "coderabbit_gate.jsonl"


@dataclass
class GateResult:
    """Structured result returned by the gate."""

    status: str
    score: Optional[float]
    threshold: float
    degraded: bool
    message: str
    repo: Optional[str]
    pr_number: Optional[int]
    error: Optional[str] = None
    review_status: Optional[str] = None


def load_coderabbit_config(path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load the CodeRabbit YAML config when available."""

    if yaml is None or not path.exists():
        if yaml is None:
            LOGGER.debug("PyYAML not installed; skipping config load")
        return {}

    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except Exception as exc:  # pragma: no cover - defensive log only
        LOGGER.warning("Failed to read %s: %s", path, exc)
        return {}


def resolve_threshold(raw: Optional[str], config: Dict[str, Any]) -> float:
    """Resolve a threshold value from CLI or config."""

    thresholds = (config.get("thresholds") or {}) if isinstance(config, dict) else {}

    if raw:
        try:
            return float(raw)
        except ValueError:
            key = raw.strip().lower()
            if key in thresholds:
                return float(thresholds[key])
            raise ValueError(f"Unknown threshold '{raw}'. Provide a float or one of {list(thresholds.keys())}")

    if "production_ready" in thresholds:
        return float(thresholds["production_ready"])
    return 90.0


def resolve_allow_degraded(arg_value: Optional[bool], config: Dict[str, Any]) -> bool:
    if arg_value is not None:
        return arg_value
    ci_cfg = config.get("ci", {}) if isinstance(config, dict) else {}
    return bool(ci_cfg.get("allow_degraded", False))


def _metrics_file(metrics_dir: Optional[Path]) -> Path:
    base = metrics_dir or get_metrics_dir()
    ci_dir = base / "ci"
    ci_dir.mkdir(parents=True, exist_ok=True)
    return ci_dir / CI_FILENAME


def _read_diff(diff_path: Optional[str]) -> Optional[str]:
    if not diff_path:
        return None
    try:
        return Path(diff_path).read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - CLI warning only
        LOGGER.warning("Unable to read diff from %s: %s", diff_path, exc)
        return None


def run_gate(
    *,
    repo: str,
    pr_number: int,
    threshold: float,
    allow_degraded: bool,
    diff: Optional[str] = None,
    client: Optional[CodeRabbitClient] = None,
    config: Optional[Dict[str, Any]] = None,
    metrics_dir: Optional[Path] = None,
    force_refresh: bool = False,
) -> GateResult:
    """Execute the gate and persist a telemetry record."""

    if not repo:
        raise ValueError("Repository slug is required")
    if pr_number <= 0:
        raise ValueError("Pull request number must be positive")

    cfg = config or {}
    gate_client = client or CodeRabbitClient(config=cfg)
    metadata = {'command': 'coderabbit_gate'}

    try:
        review = gate_client.review_pull_request(
            repo=repo,
            pr_number=pr_number,
            diff=diff,
            metadata=metadata,
            force_refresh=force_refresh,
        )
    except CodeRabbitError as exc:
        status = "degraded" if allow_degraded else "error"
        message = f"CodeRabbit unavailable: {exc}"
        result = GateResult(
            status=status,
            score=None,
            threshold=threshold,
            degraded=True,
            message=message,
            repo=repo,
            pr_number=pr_number,
            error=str(exc),
        )
        _write_gate_record(result, metrics_dir, allow_degraded)
        return result

    if review.degraded and not allow_degraded:
        message = review.degraded_reason or "CodeRabbit degraded; blocking per policy."
        result = GateResult(
            status="error",
            score=review.score,
            threshold=threshold,
            degraded=True,
            message=message,
            repo=repo,
            pr_number=pr_number,
            review_status=review.status,
        )
        _write_gate_record(result, metrics_dir, allow_degraded, review)
        return result

    if review.degraded:
        message = review.degraded_reason or "CodeRabbit degraded; continuing per policy."
        result = GateResult(
            status="degraded",
            score=review.score,
            threshold=threshold,
            degraded=True,
            message=message,
            repo=repo,
            pr_number=pr_number,
            review_status=review.status,
        )
        _write_gate_record(result, metrics_dir, allow_degraded, review)
        return result

    if review.score >= threshold:
        result = GateResult(
            status="passed",
            score=review.score,
            threshold=threshold,
            degraded=False,
            message=f"CodeRabbit score {review.score:.1f} >= {threshold:.1f}; gate passed.",
            repo=repo,
            pr_number=pr_number,
            review_status=review.status,
        )
    else:
        result = GateResult(
            status="failed",
            score=review.score,
            threshold=threshold,
            degraded=False,
            message=f"CodeRabbit score {review.score:.1f} < {threshold:.1f}; gate failed.",
            repo=repo,
            pr_number=pr_number,
            review_status=review.status,
        )

    _write_gate_record(result, metrics_dir, allow_degraded, review)
    return result


def _write_gate_record(
    result: GateResult,
    metrics_dir: Optional[Path],
    allow_degraded: bool,
    review: Optional[CodeRabbitReview] = None,
) -> None:
    """Persist a sanitized telemetry record for the gate evaluation."""

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo": result.repo,
        "pr_number": result.pr_number,
        "status": result.status,
        "score": result.score,
        "threshold": result.threshold,
        "allow_degraded": allow_degraded,
        "degraded": result.degraded,
        "message": result.message,
        "error": result.error,
        "review_status": result.review_status,
    }

    if review is not None:
        record["review"] = {
            "status": review.status,
            "issues": len(review.issues),
        }

    sanitized = scrub_secrets(record)
    metrics_path = _metrics_file(metrics_dir)
    with metrics_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(sanitized) + "\n")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gate PRs based on CodeRabbit score")
    parser.add_argument("--repo", help="GitHub repository slug, defaults to CODERABBIT_REPO env")
    parser.add_argument("--pr-number", help="Pull request number or CODERABBIT_PR_NUMBER env")
    parser.add_argument("--threshold", help="Score threshold float or named value from config thresholds")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to coderabbit.yaml")
    parser.add_argument("--diff-path", help="Optional path to diff text sent to CodeRabbit")
    parser.add_argument("--force-refresh", action="store_true", help="Bypass cache when calling CodeRabbit")
    parser.add_argument("--allow-degraded", dest="allow_degraded", action="store_true", help="Allow gate to pass when CodeRabbit is degraded")
    parser.add_argument("--no-allow-degraded", dest="allow_degraded", action="store_false", help="Block when CodeRabbit is degraded")
    parser.set_defaults(allow_degraded=None)
    return parser.parse_args(argv)


def _resolve_repo_and_pr(args: argparse.Namespace) -> tuple[str, int]:
    repo = args.repo or os.getenv("CODERABBIT_REPO")
    pr_value = args.pr_number or os.getenv("CODERABBIT_PR_NUMBER")
    if not repo or not pr_value:
        raise ValueError("Both repository (--repo) and --pr-number (or CODERABBIT_* env) are required")
    try:
        pr_number = int(str(pr_value).strip())
    except ValueError as exc:
        raise ValueError("--pr-number must be an integer") from exc
    return repo, pr_number


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=os.getenv("CODERABBIT_GATE_LOG", "INFO"))
    args = parse_args(argv)
    try:
        repo, pr_number = _resolve_repo_and_pr(args)
    except ValueError as exc:
        print(f"[coderabbit-gate] {exc}", file=sys.stderr)
        return 1

    config_path = Path(args.config)
    config = load_coderabbit_config(config_path)

    try:
        threshold = resolve_threshold(args.threshold, config)
    except ValueError as exc:
        print(f"[coderabbit-gate] {exc}", file=sys.stderr)
        return 1

    allow_degraded = resolve_allow_degraded(args.allow_degraded, config)
    diff_blob = _read_diff(args.diff_path)

    try:
        result = run_gate(
            repo=repo,
            pr_number=pr_number,
            threshold=threshold,
            allow_degraded=allow_degraded,
            diff=diff_blob,
            config=config,
            force_refresh=args.force_refresh,
        )
    except ValueError as exc:
        print(f"[coderabbit-gate] {exc}", file=sys.stderr)
        return 1

    print(f"[coderabbit-gate] {result.message}")
    if result.status in {"passed", "degraded"}:
        return 0
    if result.status == "failed":
        return 2
    return 3


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
