#!/usr/bin/env python3
"""
SuperClaude Agent Discovery Tool
Helps find the right agent from 131 available agents based on context
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class AgentDiscovery:
    def __init__(self, registry_path: str):
        """Initialize with agent registry"""
        self.registry_path = registry_path
        self.agents = []
        self.load_registry()

    def load_registry(self):
        """Load agent registry from YAML file"""
        try:
            with open(self.registry_path) as f:
                data = yaml.safe_load(f)

            # Flatten all agent categories into single list
            registry = data.get("registry", {})
            for category, agents in registry.items():
                if isinstance(agents, list):
                    for agent in agents:
                        agent["category"] = category
                        self.agents.append(agent)

            self.selection_config = data.get("selection", {})
            print(f"Loaded {len(self.agents)} agents from registry")

        except Exception as e:
            print(f"Error loading registry: {e}")
            sys.exit(1)

    def search_by_keyword(self, keyword: str) -> List[Dict]:
        """Search agents by keyword in name, description, keywords, domains"""
        keyword_lower = keyword.lower()
        matches = []

        for agent in self.agents:
            score = 0

            # Check name
            if keyword_lower in agent.get("name", "").lower():
                score += 3

            # Check keywords
            keywords = agent.get("keywords", [])
            if any(keyword_lower in k.lower() for k in keywords):
                score += 2

            # Check domains
            domains = agent.get("domains", [])
            if any(keyword_lower in d.lower() for d in domains):
                score += 2

            # Check description
            if keyword_lower in agent.get("description", "").lower():
                score += 1

            # Check languages
            languages = agent.get("languages", [])
            if any(keyword_lower in l.lower() for l in languages):
                score += 1

            if score > 0:
                matches.append((agent, score))

        # Sort by score and priority
        matches.sort(key=lambda x: (-x[1], x[0].get("priority", 99)))
        return [m[0] for m in matches[:10]]

    def find_by_file(self, filepath: str) -> List[Dict]:
        """Find agents based on file extension and content"""
        path = Path(filepath)
        extension = path.suffix
        matches = []

        # Read file content for import detection
        imports = []
        if path.exists():
            try:
                with open(path) as f:
                    content = f.read()
                    # Simple import detection
                    imports = re.findall(r"import\s+(\S+)|from\s+(\S+)", content)
                    imports = [i[0] or i[1] for i in imports]
            except:
                pass

        for agent in self.agents:
            score = 0

            # Check file patterns
            file_patterns = agent.get("file_patterns", [])
            for pattern in file_patterns:
                if pattern.replace("*", "") in str(filepath):
                    score += 3

            # Check imports
            agent_imports = agent.get("imports", [])
            for imp in imports:
                if any(ai in imp for ai in agent_imports):
                    score += 2

            # Check languages based on extension
            languages = agent.get("languages", [])
            ext_map = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".rs": "rust",
                ".go": "go",
                ".java": "java",
                ".rb": "ruby",
                ".php": "php",
                ".cs": "csharp",
                ".cpp": "cpp",
                ".c": "c",
                ".swift": "swift",
                ".kt": "kotlin",
                ".scala": "scala",
                ".sol": "solidity",
            }

            if extension in ext_map and ext_map[extension] in languages:
                score += 2

            if score > 0:
                matches.append((agent, score))

        # Sort by score and priority
        matches.sort(key=lambda x: (-x[1], x[0].get("priority", 99)))
        return [m[0] for m in matches[:5]]

    def suggest_agents(self, context: Dict) -> List[Dict]:
        """Suggest agents based on full context"""
        all_scores = {}

        # Score based on files
        for filepath in context.get("files", []):
            file_agents = self.find_by_file(filepath)
            for i, agent in enumerate(file_agents):
                agent_id = agent["id"]
                if agent_id not in all_scores:
                    all_scores[agent_id] = {"agent": agent, "score": 0}
                all_scores[agent_id]["score"] += (5 - i) if i < 5 else 1

        # Score based on keywords
        for keyword in context.get("keywords", []):
            keyword_agents = self.search_by_keyword(keyword)
            for i, agent in enumerate(keyword_agents):
                agent_id = agent["id"]
                if agent_id not in all_scores:
                    all_scores[agent_id] = {"agent": agent, "score": 0}
                all_scores[agent_id]["score"] += (3 - i) if i < 3 else 1

        # Sort by total score and priority
        sorted_agents = sorted(
            all_scores.values(),
            key=lambda x: (-x["score"], x["agent"].get("priority", 99)),
        )

        return [item["agent"] for item in sorted_agents[:5]]

    def display_agent(self, agent: Dict, score: Optional[float] = None):
        """Pretty print agent information"""
        priority_map = {1: "Core", 2: "Extended", 3: "Specialized"}
        priority = priority_map.get(agent.get("priority", 2), "Unknown")

        print(f"\n🤖 {agent['name']} ({agent['id']})")
        print(f"   Priority: {priority}")
        print(f"   Path: {agent.get('path', 'N/A')}")
        print(f"   Description: {agent.get('description', 'N/A')}")

        if agent.get("domains"):
            print(f"   Domains: {', '.join(agent['domains'])}")

        if agent.get("keywords"):
            print(f"   Keywords: {', '.join(agent['keywords'][:5])}")

        if agent.get("languages") and agent["languages"] != ["any"]:
            print(f"   Languages: {', '.join(agent['languages'])}")

        if score:
            print(f"   Match Score: {score:.2f}")


def main():
    parser = argparse.ArgumentParser(description="SuperClaude Agent Discovery Tool")
    parser.add_argument("--search", type=str, help="Search agents by keyword")
    parser.add_argument("--file", type=str, help="Find agents for specific file")
    parser.add_argument(
        "--suggest", action="store_true", help="Suggest agents for current context"
    )
    parser.add_argument(
        "--list-all", action="store_true", help="List all available agents"
    )
    parser.add_argument(
        "--list-core", action="store_true", help="List core agents only"
    )
    parser.add_argument(
        "--list-extended", action="store_true", help="List extended agents only"
    )
    parser.add_argument(
        "--registry",
        type=str,
        default="/home/tony/Desktop/SuperClaude_Framework/SuperClaude/Core/agent_registry.yaml",
        help="Path to agent registry",
    )

    args = parser.parse_args()

    discovery = AgentDiscovery(args.registry)

    if args.search:
        print(f"\n🔍 Searching for agents matching: '{args.search}'")
        agents = discovery.search_by_keyword(args.search)
        if agents:
            for agent in agents:
                discovery.display_agent(agent)
        else:
            print("No agents found matching your search.")

    elif args.file:
        print(f"\n📄 Finding agents for file: {args.file}")
        agents = discovery.find_by_file(args.file)
        if agents:
            for agent in agents:
                discovery.display_agent(agent)
        else:
            print("No specific agents found. Consider using general-purpose agent.")

    elif args.suggest:
        # Get context from current directory
        cwd = os.getcwd()
        files = []
        for root, _, filenames in os.walk(cwd):
            for filename in filenames[:20]:  # Limit to first 20 files
                files.append(os.path.join(root, filename))

        context = {
            "files": files,
            "keywords": [],  # Could be enhanced with git history, README parsing, etc.
        }

        print("\n💡 Suggesting agents for current project...")
        agents = discovery.suggest_agents(context)
        if agents:
            for agent in agents:
                discovery.display_agent(agent)
        else:
            print("Using general-purpose agent as default.")

    elif args.list_all:
        print(f"\n📚 All {len(discovery.agents)} Available Agents:")
        for agent in sorted(
            discovery.agents, key=lambda x: (x.get("priority", 99), x["id"])
        ):
            print(f"  • {agent['id']}: {agent.get('description', 'N/A')}")

    elif args.list_core:
        print("\n⭐ Core Agents (Priority 1):")
        core_agents = [a for a in discovery.agents if a.get("priority") == 1]
        for agent in sorted(core_agents, key=lambda x: x["id"]):
            print(f"  • {agent['id']}: {agent.get('description', 'N/A')}")

    elif args.list_extended:
        print("\n🚀 Extended Agents (Priority 2+):")
        extended_agents = [a for a in discovery.agents if a.get("priority", 2) >= 2]
        for agent in sorted(
            extended_agents, key=lambda x: (x.get("priority", 99), x["id"])
        ):
            print(f"  • {agent['id']}: {agent.get('description', 'N/A')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
