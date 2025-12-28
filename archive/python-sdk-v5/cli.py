"""
CLI Interface for Extended Agent System

Provides command-line tools for exploring, testing, and managing
the 131-agent system.
"""

import argparse

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from .extended_loader import AgentCategory, ExtendedAgentLoader

console = Console()


def cmd_list_agents(loader: ExtendedAgentLoader, category: str | None = None):
    """List all agents, optionally filtered by category."""
    if category:
        try:
            cat_enum = AgentCategory(category)
            agents = loader.get_agents_by_category(cat_enum)
            title = f"Agents in {category}"
        except ValueError:
            console.print(f"[red]Invalid category: {category}[/red]")
            return
    else:
        agents = list(loader._agent_metadata.values())
        title = "All Agents"

    # Create table
    table = Table(title=title, box=box.ROUNDED)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Priority", justify="center")
    table.add_column("Domains", style="magenta")
    table.add_column("Languages", style="blue")

    for agent in sorted(agents, key=lambda a: (a.priority, a.name)):
        table.add_row(
            agent.id,
            agent.name,
            agent.category.value if agent.category else "core",
            str(agent.priority),
            ", ".join(agent.domains[:3]) + ("..." if len(agent.domains) > 3 else ""),
            ", ".join(agent.languages[:3])
            + ("..." if len(agent.languages) > 3 else ""),
        )

    console.print(table)
    console.print(f"\n[bold]Total agents:[/bold] {len(agents)}")


def cmd_list_categories(loader: ExtendedAgentLoader):
    """List all categories with agent counts."""
    categories = loader.list_categories()

    table = Table(title="Agent Categories", box=box.ROUNDED)
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Description", style="yellow")

    category_descriptions = {
        AgentCategory.CORE_DEVELOPMENT: "Core development patterns and APIs",
        AgentCategory.LANGUAGE_SPECIALISTS: "Language-specific experts",
        AgentCategory.INFRASTRUCTURE: "DevOps, cloud, and infrastructure",
        AgentCategory.QUALITY_SECURITY: "Testing, security, and quality assurance",
        AgentCategory.DATA_AI: "Data engineering, ML, and AI",
        AgentCategory.DEVELOPER_EXPERIENCE: "DX, tooling, and workflow",
        AgentCategory.SPECIALIZED_DOMAINS: "Domain-specific specialists",
        AgentCategory.BUSINESS_PRODUCT: "Business and product management",
        AgentCategory.META_ORCHESTRATION: "Multi-agent coordination",
        AgentCategory.RESEARCH_ANALYSIS: "Research and competitive analysis",
    }

    for cat, count in sorted(categories.items(), key=lambda x: x[0].value):
        table.add_row(cat.value, str(count), category_descriptions.get(cat, ""))

    console.print(table)
    console.print(f"\n[bold]Total categories:[/bold] {len(categories)}")


def cmd_search_agents(loader: ExtendedAgentLoader, query: str):
    """Search agents by keyword."""
    results = loader.search_agents(query)

    if not results:
        console.print(f"[yellow]No agents found matching '{query}'[/yellow]")
        return

    table = Table(title=f"Search Results for '{query}'", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Match Reason", style="yellow")
    table.add_column("Domains", style="magenta")

    for agent in results:
        # Determine match reason
        match_reason = []
        if query.lower() in agent.name.lower():
            match_reason.append("name")
        if query.lower() in agent.description.lower():
            match_reason.append("description")
        if any(query.lower() in k.lower() for k in agent.keywords):
            match_reason.append("keywords")
        if any(query.lower() in d.lower() for d in agent.domains):
            match_reason.append("domains")

        table.add_row(
            agent.id, agent.name, ", ".join(match_reason), ", ".join(agent.domains[:3])
        )

    console.print(table)
    console.print(f"\n[bold]Found:[/bold] {len(results)} agents")


def cmd_select_agent(loader: ExtendedAgentLoader, context: dict, top_n: int = 5):
    """Select best agents for a context."""
    matches = loader.select_agent(context, top_n=top_n)

    if not matches:
        console.print("[yellow]No suitable agents found for the given context[/yellow]")
        return

    console.print("\n[bold]Context:[/bold]")
    console.print(f"  Task: {context.get('task', 'N/A')}")
    console.print(f"  Files: {', '.join(context.get('files', []))[:100]}")
    console.print(f"  Languages: {', '.join(context.get('languages', []))}")
    console.print(f"  Domains: {', '.join(context.get('domains', []))}")
    console.print()

    table = Table(title=f"Top {len(matches)} Agent Suggestions", box=box.ROUNDED)
    table.add_column("Rank", justify="center", style="cyan")
    table.add_column("Agent", style="green")
    table.add_column("Score", justify="right", style="yellow")
    table.add_column("Confidence", style="magenta")
    table.add_column("Matched", style="blue")

    for i, match in enumerate(matches, 1):
        agent = loader._agent_metadata.get(match.agent_id)
        if not agent:
            continue

        # Confidence color
        conf_color = {
            "excellent": "green",
            "high": "blue",
            "medium": "yellow",
            "low": "red",
        }.get(match.confidence, "white")

        table.add_row(
            str(i),
            agent.name,
            f"{match.total_score:.3f}",
            f"[{conf_color}]{match.confidence}[/{conf_color}]",
            ", ".join(match.matched_criteria[:2]),
        )

    console.print(table)

    # Show best match details
    if matches:
        best = matches[0]
        explanation = loader.explain_selection(best.agent_id, context)

        panel = Panel(
            f"""[bold]Agent:[/bold] {explanation["agent_name"]}
[bold]Category:[/bold] {explanation["category"]}
[bold]Priority:[/bold] {explanation["priority"]}
[bold]Confidence:[/bold] {explanation["confidence"]}

[bold]Score Breakdown:[/bold]
  Keywords:  {explanation["breakdown"].get("keywords", 0):.3f} (30% weight)
  Domains:   {explanation["breakdown"].get("domains", 0):.3f} (25% weight)
  Languages: {explanation["breakdown"].get("languages", 0):.3f} (20% weight)
  Files:     {explanation["breakdown"].get("file_patterns", 0):.3f} (15% weight)
  Imports:   {explanation["breakdown"].get("imports", 0):.3f} (10% weight)
  Priority:  {explanation["breakdown"].get("priority", 0):.3f} (bonus)

[bold]Matched Criteria:[/bold]
{chr(10).join(f"  • {c}" for c in explanation["matched_criteria"])}
""",
            title="[bold cyan]Best Match Details[/bold cyan]",
            border_style="cyan",
        )
        console.print(panel)


def cmd_agent_info(loader: ExtendedAgentLoader, agent_id: str):
    """Show detailed information about an agent."""
    if agent_id not in loader._agent_metadata:
        console.print(f"[red]Agent not found: {agent_id}[/red]")
        return

    agent = loader._agent_metadata[agent_id]

    info = f"""[bold cyan]Agent Information[/bold cyan]

[bold]Identity:[/bold]
  ID:          {agent.id}
  Name:        {agent.name}
  Category:    {agent.category.value if agent.category else "core"}
  Priority:    {agent.priority}

[bold]Capabilities:[/bold]
  Domains:     {", ".join(agent.domains) if agent.domains else "N/A"}
  Languages:   {", ".join(agent.languages) if agent.languages else "N/A"}
  Keywords:    {", ".join(agent.keywords) if agent.keywords else "N/A"}

[bold]File Patterns:[/bold]
  {chr(10).join(f"  • {p}" for p in agent.file_patterns) if agent.file_patterns else "  N/A"}

[bold]Import Patterns:[/bold]
  {chr(10).join(f"  • {p}" for p in agent.imports) if agent.imports else "  N/A"}

[bold]Description:[/bold]
  {agent.description}

[bold]Usage Stats:[/bold]
  Loaded:      {agent.is_loaded}
  Load Count:  {agent.load_count}
  Last Access: {agent.last_accessed:.0f} (timestamp)
"""

    panel = Panel(info, border_style="cyan", box=box.ROUNDED)
    console.print(panel)


def cmd_statistics(loader: ExtendedAgentLoader):
    """Show loader statistics."""
    stats = loader.get_statistics()

    info = f"""[bold cyan]Extended Agent Loader Statistics[/bold cyan]

[bold]Agent Inventory:[/bold]
  Total Agents:     {stats["total_agents"]}
  Cached Agents:    {stats["cached_agents"]} / {stats["max_cache_size"]}

[bold]Performance Metrics:[/bold]
  Total Loads:      {stats["agent_loads"]}
  Cache Hits:       {stats["cache_hits"]}
  Cache Misses:     {stats["cache_misses"]}
  Hit Rate:         {stats["cache_hit_rate"]:.1%}
  Evictions:        {stats["evictions"]}
  Avg Load Time:    {stats["avg_load_time"]:.3f}s
  Selection Queries: {stats["selection_queries"]}

[bold]Category Distribution:[/bold]
"""
    for category, count in sorted(stats["category_distribution"].items()):
        info += f"  {category}: {count}\n"

    info += "\n[bold]Top Accessed Agents:[/bold]\n"
    for agent_id, count in list(stats["top_accessed_agents"].items())[:5]:
        info += f"  {agent_id}: {count} accesses\n"

    panel = Panel(info, border_style="cyan", box=box.ROUNDED)
    console.print(panel)


def cmd_category_tree(loader: ExtendedAgentLoader):
    """Show agent hierarchy as a tree."""
    tree = Tree("[bold cyan]Agent Categories[/bold cyan]")

    categories = loader.list_categories()

    for cat, count in sorted(categories.items(), key=lambda x: x[0].value):
        cat_branch = tree.add(f"[yellow]{cat.value}[/yellow] ({count} agents)")

        # Add top 5 agents from this category
        agents = loader.get_agents_by_category(cat)
        for agent in sorted(agents, key=lambda a: a.priority)[:5]:
            cat_branch.add(
                f"[green]{agent.name}[/green] "
                f"[dim](P{agent.priority}, {', '.join(agent.domains[:2])})[/dim]"
            )

        if len(agents) > 5:
            cat_branch.add(f"[dim]... and {len(agents) - 5} more[/dim]")

    console.print(tree)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extended Agent System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List agents")
    list_parser.add_argument("--category", "-c", help="Filter by category")

    # categories command
    subparsers.add_parser("categories", help="List all categories")

    # search command
    search_parser = subparsers.add_parser("search", help="Search agents")
    search_parser.add_argument("query", help="Search query")

    # select command
    select_parser = subparsers.add_parser(
        "select", help="Select best agent for context"
    )
    select_parser.add_argument("--task", "-t", required=True, help="Task description")
    select_parser.add_argument(
        "--files", "-f", nargs="*", default=[], help="File paths"
    )
    select_parser.add_argument(
        "--languages", "-l", nargs="*", default=[], help="Languages"
    )
    select_parser.add_argument("--domains", "-d", nargs="*", default=[], help="Domains")
    select_parser.add_argument(
        "--keywords", "-k", nargs="*", default=[], help="Keywords"
    )
    select_parser.add_argument(
        "--top", type=int, default=5, help="Number of suggestions"
    )

    # info command
    info_parser = subparsers.add_parser("info", help="Show agent information")
    info_parser.add_argument("agent_id", help="Agent ID")

    # stats command
    subparsers.add_parser("stats", help="Show statistics")

    # tree command
    subparsers.add_parser("tree", help="Show category tree")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize loader
    console.print("[dim]Loading agent metadata...[/dim]")
    loader = ExtendedAgentLoader()

    # Execute command
    try:
        if args.command == "list":
            cmd_list_agents(loader, args.category)
        elif args.command == "categories":
            cmd_list_categories(loader)
        elif args.command == "search":
            cmd_search_agents(loader, args.query)
        elif args.command == "select":
            context = {
                "task": args.task,
                "files": args.files,
                "languages": args.languages,
                "domains": args.domains,
                "keywords": args.keywords,
            }
            cmd_select_agent(loader, context, args.top)
        elif args.command == "info":
            cmd_agent_info(loader, args.agent_id)
        elif args.command == "stats":
            cmd_statistics(loader)
        elif args.command == "tree":
            cmd_category_tree(loader)
        else:
            parser.print_help()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
