"""Agent command module for the SuperClaude CLI."""

import argparse
import json
import logging
import os
import traceback
from collections.abc import Iterable
from pathlib import Path
from typing import Any

# Try to import from the installed package
try:
    from SuperClaude.Agents import AgentLoader, AgentRegistry, AgentSelector

    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False

# Import UI utilities
try:
    from setup.utils.ui import (
        Colors,
        display_error,
        display_info,
        display_success,
        display_warning,
    )
except ImportError:
    # Fallback if UI utilities are not available
    def display_info(msg):
        print(f"[INFO] {msg}")

    def display_success(msg):
        print(f"[SUCCESS] {msg}")

    def display_error(msg):
        print(f"[ERROR] {msg}")

    def display_warning(msg):
        print(f"[WARNING] {msg}")

    class Colors:
        CYAN = YELLOW = GREEN = RED = RESET = ""


logger = logging.getLogger(__name__)


DIAGNOSTIC_PATHS: Iterable[Path] = (
    Path.home() / ".claude" / "logs",
    Path.home() / ".cache" / "uv",
    Path.home() / ".cache" / "uv" / "sdists-v9",
)


def register_parser(subparsers, global_parser):
    """Register the agent subcommand parser"""
    parser = subparsers.add_parser(
        "agent",
        help="Interact with the agent system",
        parents=[global_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
Agent System Commands
--------------------
List, select, and execute agents for specialized tasks.

Examples:
  SuperClaude agent list              # List all available agents
  SuperClaude agent list --category code  # List agents by category
  SuperClaude agent info general-purpose  # Show agent details
  SuperClaude agent run --delegate "Debug this code"  # Auto-select agent
  SuperClaude agent run --name root-cause-analyst "Why is this failing?"
        """,
    )

    # Create subcommands for agent operations
    agent_subparsers = parser.add_subparsers(
        dest="agent_command", help="Agent operations"
    )

    # List command
    list_parser = agent_subparsers.add_parser("list", help="List available agents")
    list_parser.add_argument(
        "--category", type=str, help="Filter by category (core, code, test, docs, etc.)"
    )
    list_parser.add_argument(
        "--extended",
        action="store_true",
        help="Include extended agents (not just core)",
    )

    # Info command
    info_parser = agent_subparsers.add_parser(
        "info", help="Show detailed information about an agent"
    )
    info_parser.add_argument("name", type=str, help="Agent name to get info about")

    # Run command
    run_parser = agent_subparsers.add_parser("run", help="Execute an agent with a task")
    run_parser.add_argument("task", type=str, help="Task description for the agent")
    run_parser.add_argument("--name", type=str, help="Specific agent to use")
    run_parser.add_argument(
        "--delegate",
        action="store_true",
        help="Auto-select the best agent for the task",
    )
    run_parser.add_argument(
        "--suggest",
        action="store_true",
        help="Show top 5 agent suggestions without executing",
    )
    run_parser.add_argument("--files", nargs="+", help="Files to include in context")
    run_parser.add_argument("--json", action="store_true", help="Output result as JSON")


def run(args: argparse.Namespace) -> int:
    """Execute agent command"""
    if not AGENT_AVAILABLE:
        display_error("Agent system not available. Please install SuperClaude first.")
        return 1

    try:
        # Initialize agent system
        registry = AgentRegistry()
        selector = AgentSelector(registry)
        loader = AgentLoader(registry)

        # Handle different agent commands
        if args.agent_command == "list":
            return list_agents(registry, args)
        elif args.agent_command == "info":
            return show_agent_info(registry, args)
        elif args.agent_command == "run":
            return run_agent(selector, loader, args)
        else:
            display_warning("Please specify an agent command: list, info, or run")
            return 1

    except Exception as e:
        display_error(f"Agent operation failed: {e}")
        return 1


def list_agents(registry: "AgentRegistry", args: argparse.Namespace) -> int:
    """List available agents"""
    agents = registry.list_agents(
        category=args.category if hasattr(args, "category") else None
    )

    if not agents:
        display_warning("No agents found")
        return 0

    # Group by category
    by_category = {}
    for agent_name in agents:
        config = registry.get_agent_config(agent_name)
        if config:
            category = config.get("category", "uncategorized")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append((agent_name, config))

    # Display agents
    print(f"\n{Colors.CYAN}Available Agents:{Colors.RESET}")
    for category in sorted(by_category.keys()):
        print(f"\n  {Colors.YELLOW}{category.upper()}:{Colors.RESET}")
        for agent_name, config in sorted(by_category[category]):
            desc = config.get("description", "No description")[:60]
            if len(config.get("description", "")) > 60:
                desc += "..."
            print(f"    • {Colors.GREEN}{agent_name:<30}{Colors.RESET} {desc}")

    total = len(agents)
    core_count = len(
        [a for a in agents if registry.get_agent_config(a).get("category") == "core"]
    )
    print(
        f"\n  Total: {total} agents ({core_count} core, {total - core_count} extended)"
    )

    return 0


def show_agent_info(registry: "AgentRegistry", args: argparse.Namespace) -> int:
    """Show detailed information about an agent"""
    config = registry.get_agent_config(args.name)

    if not config:
        display_error(f"Agent '{args.name}' not found")
        return 1

    print(f"\n{Colors.CYAN}Agent: {args.name}{Colors.RESET}")
    print("-" * 40)

    # Basic info
    print(
        f"{Colors.YELLOW}Category:{Colors.RESET} {config.get('category', 'uncategorized')}"
    )
    print(
        f"{Colors.YELLOW}Description:{Colors.RESET} {config.get('description', 'No description')}"
    )

    # Triggers
    if "triggers" in config:
        print(f"\n{Colors.YELLOW}Triggers:{Colors.RESET}")
        for trigger in config["triggers"][:5]:
            print(f"  • {trigger}")

    # Tools
    if "tools" in config:
        print(f"\n{Colors.YELLOW}Required Tools:{Colors.RESET}")
        for tool in config["tools"]:
            print(f"  • {tool}")

    # Focus areas
    if "focus_areas" in config:
        print(f"\n{Colors.YELLOW}Focus Areas:{Colors.RESET}")
        for area, desc in config["focus_areas"].items():
            print(f"  • {Colors.GREEN}{area}:{Colors.RESET} {desc}")

    # Key actions
    if "key_actions" in config:
        print(f"\n{Colors.YELLOW}Key Actions:{Colors.RESET}")
        for i, action in enumerate(config["key_actions"][:5], 1):
            print(f"  {i}. {action}")

    return 0


def run_agent(
    selector: "AgentSelector", loader: "AgentLoader", args: argparse.Namespace
) -> int:
    """Execute an agent with a task"""
    # Build context
    files_arg = getattr(args, "files", None) or []
    context = {
        "task": args.task,
        "files": files_arg,
    }

    # Select agent
    if hasattr(args, "name") and args.name:
        agent_name = args.name
        display_info(f"Using specified agent: {agent_name}")
    elif hasattr(args, "delegate") and args.delegate:
        # Auto-select best agent
        scores = selector.select_agent(context)
        if not scores:
            display_error("No suitable agent found for this task")
            return 1

        if hasattr(args, "suggest") and args.suggest:
            # Just show suggestions
            print(f"\n{Colors.CYAN}Agent Suggestions:{Colors.RESET}")
            for agent_name, score in scores[:5]:
                print(
                    f"  • {Colors.GREEN}{agent_name:<30}{Colors.RESET} (score: {score:.2f})"
                )
            return 0

        agent_name = scores[0][0]
        display_info(f"Selected agent: {agent_name} (score: {scores[0][1]:.2f})")
    else:
        display_error("Please specify --name or --delegate")
        return 1

    _log_agent_context(agent_name, context)
    _probe_critical_paths()

    # Load and execute agent
    try:
        agent = loader.load_agent(agent_name)
        if not agent:
            display_error(f"Failed to load agent: {agent_name}")
            return 1

        display_info("Executing agent...")
        result = agent.execute(context)

        # Display result
        if hasattr(args, "json") and args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                display_success("Agent execution completed successfully")
                print(f"\n{Colors.CYAN}Output:{Colors.RESET}")
                print(result["output"])

                if result.get("actions_taken"):
                    print(f"\n{Colors.YELLOW}Actions Taken:{Colors.RESET}")
                    for action in result["actions_taken"]:
                        print(f"  • {action}")
            else:
                display_error("Agent execution failed")
                if result.get("errors"):
                    print(f"\n{Colors.RED}Errors:{Colors.RESET}")
                    for error in result["errors"]:
                        print(f"  • {error}")

        return 0 if result["success"] else 1

    except Exception as exc:  # pragma: no cover - defensive logging path
        display_error(f"Agent execution failed: {exc}")
        _log_exception_trace()
        logger.debug("Agent execution failed", exc_info=exc)
        return 1


def _log_agent_context(agent_name: str, context: dict[str, Any]) -> None:
    """Emit a concise diagnostics block for the agent invocation."""

    task = str(context.get("task", "")).strip()
    files = context.get("files") or []
    display_info(f"Agent diagnostics → name: {agent_name}")
    if task:
        clipped = (task[:200] + "…") if len(task) > 200 else task
        display_info(f"Agent diagnostics → task: {clipped}")
    display_info(f"Agent diagnostics → files: {len(files)} attached")


def _probe_critical_paths() -> None:
    """Check whether key directories are writable and warn when they are not."""

    for path in DIAGNOSTIC_PATHS:
        if not path.exists():
            logger.debug("Diagnostics skipped; path does not exist: %s", path)
            continue
        probe_name = path / f".superclaude_probe_{os.getpid()}"
        try:
            with open(probe_name, "w", encoding="utf-8") as handle:
                handle.write("probe")
        except Exception as exc:
            display_warning(f"Diagnostics: cannot write to {path}: {exc}")
            logger.debug("Path probe failed for %s", path, exc_info=exc)
        else:
            try:
                probe_name.unlink(missing_ok=True)
            except OSError:
                pass


def _log_exception_trace() -> None:
    """Print a stack trace to help diagnose unexpected failures."""

    trace = traceback.format_exc()
    if not trace:
        return
    display_warning("Stack trace:")
    print(trace)


def _indent_block(text: str, prefix: str = "    ") -> str:
    lines = text.strip().splitlines() or ["<no output>"]
    return "\n".join(f"{prefix}{line}" for line in lines)
