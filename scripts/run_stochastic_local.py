#!/usr/bin/env python3
"""
Local runner for stochastic agent evaluations.

Simulates the GitHub Actions workflow locally for testing and debugging.

Usage:
    python scripts/run_stochastic_local.py                    # Run all agents, 1 run each
    python scripts/run_stochastic_local.py --runs 3           # 3 runs per agent
    python scripts/run_stochastic_local.py --agent python-expert  # Single agent
    python scripts/run_stochastic_local.py --dry-run          # Show what would run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml


def load_test_config(config_path: Path) -> dict[str, Any]:
    """Load test configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def find_agent_file(agent_name: str, base_dir: Path) -> Path | None:
    """Find the agent file in core or extensions directory."""
    candidates = [
        base_dir / "agents" / "core" / f"{agent_name}.md",
        base_dir / "agents" / "extensions" / f"{agent_name}.md",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def run_claude_evaluation(
    agent_name: str,
    agent_file: Path,
    prompt: str,
    timeout: int = 180,
) -> tuple[str, bool]:
    """Run Claude Code CLI and return response."""
    full_prompt = f"""First, read and adopt the persona from: {agent_file}

Then complete this task with your full expertise:
{prompt}

You have full tool access. Demonstrate your capabilities thoroughly.

IMPORTANT: After completing your work, provide a brief text summary of what you implemented. Include key code snippets inline so your response contains the implementation details."""

    cmd = [
        "claude",
        "-p",
        full_prompt,
        "--allowedTools",
        "Bash,Read,Write,Edit",
        "--output-format",
        "text",  # Use text format to get actual response
        "--max-turns",
        "15",  # Increased from 10 to allow more complex tasks
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(agent_file.parent.parent.parent),  # SuperClaude root
        )

        # With text output format, stdout contains the actual response
        output = result.stdout.strip()

        if output:
            return output, True

        # Fallback to stderr if stdout is empty
        if result.stderr:
            # Check if stderr contains useful info (not just warnings)
            stderr_clean = result.stderr.strip()
            if stderr_clean and not stderr_clean.startswith("Warning"):
                return stderr_clean, False

        return "No response generated", False

    except subprocess.TimeoutExpired:
        return "TIMEOUT", False
    except FileNotFoundError:
        return (
            "ERROR: Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code",
            False,
        )
    except Exception as e:
        return f"ERROR: {e}", False


def find_recent_files(base_dir: Path, extensions: list[str], minutes: int = 5) -> list[Path]:
    """Find files created in the last N minutes."""
    import time

    cutoff = time.time() - (minutes * 60)
    recent = []

    for ext in extensions:
        for f in base_dir.rglob(f"*{ext}"):
            if f.is_file() and f.stat().st_mtime > cutoff:
                # Skip common non-output directories
                if any(skip in str(f) for skip in ["node_modules", "__pycache__", ".git", "venv"]):
                    continue
                recent.append(f)

    return recent


def validate_response(
    response: str,
    keywords: list[str],
    min_length: int = 50,
    base_dir: Path | None = None,
) -> tuple[bool, str]:
    """Validate response against keywords and minimum length.

    Also checks for recently created files as evidence of work if response is too short.
    """
    response_lower = response.lower()
    matched = []

    # Check for keywords in response
    for keyword in keywords:
        if keyword.lower() in response_lower:
            matched.append(keyword)

    if len(response) >= min_length and matched:
        return True, f"Matched keywords: {', '.join(matched)}"

    # Fallback: Check for recently created files (evidence of work)
    if base_dir and "max turns" in response_lower:
        # Look for code files created during the test
        recent_files = find_recent_files(
            base_dir, [".py", ".ts", ".tsx", ".js", ".jsx", ".yml", ".yaml"], minutes=5
        )

        if recent_files:
            # Read recent files and check for keywords
            file_contents = []
            for f in recent_files[:5]:  # Check first 5 files
                try:
                    content = f.read_text()
                    file_contents.append(content)
                except Exception:
                    pass

            combined = " ".join(file_contents).lower()
            file_matched = []
            for keyword in keywords:
                if keyword.lower() in combined:
                    file_matched.append(keyword)

            if file_matched:
                return True, f"Max turns reached but found work in files: {', '.join(file_matched)}"

    if len(response) < min_length:
        return False, f"Response too short ({len(response)} < {min_length} chars)"

    return False, f"No keywords found (expected one of: {', '.join(keywords)})"


def run_single_test(
    agent_name: str,
    agent_config: dict[str, Any],
    run_number: int,
    base_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run a single agent test."""
    agent_file = find_agent_file(agent_name, base_dir)
    if not agent_file:
        return {
            "agent": agent_name,
            "run": run_number,
            "passed": False,
            "reason": f"Agent file not found for {agent_name}",
            "response_length": 0,
            "test_type": agent_config.get("type", "standard"),
            "threshold": agent_config.get("threshold", 0.8),
        }

    prompt = agent_config.get("prompt", f"Demonstrate your expertise as {agent_name}")
    keywords = agent_config.get("keywords", [])
    test_type = agent_config.get("type", "standard")
    threshold = agent_config.get("threshold", 0.8)

    print(f"\n{'=' * 60}")
    print(f"Running: {agent_name} (run {run_number})")
    print(f"Agent file: {agent_file}")
    print(f"Keywords: {keywords}")

    if dry_run:
        print("[DRY RUN] Would execute Claude CLI here")
        result = {
            "agent": agent_name,
            "run": run_number,
            "passed": True,
            "reason": "DRY RUN",
            "response_length": 100,
            "test_type": test_type,
            "threshold": threshold,
        }
    else:
        start_time = time.time()
        response, success = run_claude_evaluation(agent_name, agent_file, prompt)
        elapsed = time.time() - start_time

        print(f"Execution time: {elapsed:.1f}s")
        print(f"Response length: {len(response)} chars")

        if not success:
            passed = False
            reason = f"Execution failed: {response[:200]}"
        else:
            passed, reason = validate_response(response, keywords, base_dir=base_dir)

        print(f"Result: {'PASS' if passed else 'FAIL'} - {reason}")

        result = {
            "agent": agent_name,
            "run": run_number,
            "passed": passed,
            "reason": reason,
            "response_length": len(response),
            "test_type": test_type,
            "threshold": threshold,
        }

        # Save full response for debugging
        response_file = output_dir / f"response-{agent_name}-run{run_number}.txt"
        response_file.write_text(response)

    # Save result JSON
    result_file = output_dir / f"result-{agent_name}-run{run_number}" / "eval-result.json"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(json.dumps(result, indent=2))

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run stochastic agent evaluations locally")
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of runs per agent (default: 1)",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default=None,
        help="Specific agent to test (default: all)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Pass rate threshold (default: 0.8)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be run without executing",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("evals/tests.yaml"),
        help="Test configuration file",
    )

    args = parser.parse_args()

    # Determine base directory
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent  # SuperClaude root

    config_path = base_dir / args.config
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return 1

    # Load configuration
    config = load_test_config(config_path)
    agents = config.get("agents", {})

    if args.agent:
        if args.agent not in agents:
            print(f"Error: Agent '{args.agent}' not found in config")
            print(f"Available agents: {', '.join(agents.keys())}")
            return 1
        agents = {args.agent: agents[args.agent]}

    # Setup output directory
    output_dir = base_dir / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clear previous results
    for f in output_dir.glob("result-*"):
        if f.is_dir():
            for sf in f.iterdir():
                sf.unlink()
            f.rmdir()
        else:
            f.unlink()

    print("Stochastic Agent Evaluation")
    print(f"{'=' * 60}")
    print(f"Agents: {len(agents)}")
    print(f"Runs per agent: {args.runs}")
    print(f"Total evaluations: {len(agents) * args.runs}")
    print(f"Threshold: {args.threshold:.0%}")
    print(f"Output directory: {output_dir}")
    print(f"Dry run: {args.dry_run}")

    # Run evaluations
    all_results = []
    for agent_name, agent_config in agents.items():
        for run in range(1, args.runs + 1):
            result = run_single_test(
                agent_name,
                agent_config,
                run,
                base_dir,
                output_dir,
                args.dry_run,
            )
            all_results.append(result)

    # Compute pass rates
    print(f"\n{'=' * 60}")
    print("Computing Pass Rates...")
    print(f"{'=' * 60}\n")

    compute_script = base_dir / "scripts" / "compute_pass_rates.py"
    if compute_script.exists():
        subprocess.run(
            [
                sys.executable,
                str(compute_script),
                "--input",
                str(output_dir),
                "--threshold",
                str(args.threshold),
                "--format",
                "console",
            ],
            cwd=str(base_dir),
        )
    else:
        # Fallback: simple summary
        from collections import defaultdict

        agent_results = defaultdict(list)
        for r in all_results:
            agent_results[r["agent"]].append(r)

        for agent, runs in agent_results.items():
            passes = sum(1 for r in runs if r["passed"])
            total = len(runs)
            rate = passes / total if total > 0 else 0
            status = "PASS" if rate >= args.threshold else "FAIL"
            print(f"{agent}: {passes}/{total} ({rate:.0%}) - {status}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
