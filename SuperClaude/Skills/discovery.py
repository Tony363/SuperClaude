"""
Skill Discovery System for SuperClaude Framework.

Provides automatic discovery and indexing of Agent Skills from
.claude/skills/ directory with progressive loading support.
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .adapter import SkillAdapter, SkillMetadata

logger = logging.getLogger(__name__)


@dataclass
class SkillIndex:
    """
    Index of discovered skills with categorization and search.
    """

    skills: dict[str, SkillMetadata] = field(default_factory=dict)
    by_type: dict[str, list[str]] = field(default_factory=dict)
    by_domain: dict[str, list[str]] = field(default_factory=dict)
    by_category: dict[str, list[str]] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)

    def add(self, skill: SkillMetadata) -> None:
        """Add skill to index."""
        self.skills[skill.skill_id] = skill

        # Index by type
        if skill.skill_type not in self.by_type:
            self.by_type[skill.skill_type] = []
        self.by_type[skill.skill_type].append(skill.skill_id)

        # Index by domain
        if skill.domain not in self.by_domain:
            self.by_domain[skill.domain] = []
        self.by_domain[skill.domain].append(skill.skill_id)

        # Index by category
        if skill.category not in self.by_category:
            self.by_category[skill.category] = []
        self.by_category[skill.category].append(skill.skill_id)

        # Register aliases
        for alias in skill.aliases:
            self.aliases[alias] = skill.skill_id

    def get(self, skill_id: str) -> SkillMetadata | None:
        """Get skill by ID or alias."""
        if skill_id in self.skills:
            return self.skills[skill_id]
        if skill_id in self.aliases:
            return self.skills.get(self.aliases[skill_id])
        return None

    def search(self, query: str) -> list[tuple[str, float]]:
        """
        Search skills by query.

        Returns list of (skill_id, relevance_score) tuples.
        """
        query_lower = query.lower()
        matches = []

        for skill_id, skill in self.skills.items():
            score = 0.0

            # Exact ID match
            if skill_id == query_lower:
                score = 1.0
            # ID contains query
            elif query_lower in skill_id:
                score = 0.8
            # Name contains query
            elif query_lower in skill.name.lower():
                score = 0.7
            # Description contains query
            elif query_lower in skill.description.lower():
                score = 0.5
            # Domain match
            elif query_lower in skill.domain.lower():
                score = 0.3
            # Tool match
            elif any(query_lower in t.lower() for t in skill.tools):
                score = 0.4

            if score > 0:
                matches.append((skill_id, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def list_by_type(self, skill_type: str) -> list[str]:
        """List skill IDs by type."""
        return self.by_type.get(skill_type, [])

    def list_by_domain(self, domain: str) -> list[str]:
        """List skill IDs by domain."""
        return self.by_domain.get(domain, [])

    def stats(self) -> dict[str, Any]:
        """Get index statistics."""
        return {
            "total_skills": len(self.skills),
            "by_type": {k: len(v) for k, v in self.by_type.items()},
            "by_domain": {k: len(v) for k, v in self.by_domain.items()},
            "aliases": len(self.aliases),
        }


class SkillDiscovery:
    """
    Discovers and indexes Agent Skills from filesystem.

    Features:
    - Auto-discovery from .claude/skills/ directory
    - Progressive loading (metadata first, content on demand)
    - Skill categorization and indexing
    - Search and filtering
    """

    def __init__(
        self,
        skills_dir: str | Path | None = None,
        project_root: str | Path | None = None,
    ):
        """
        Initialize skill discovery.

        Args:
            skills_dir: Path to skills directory (defaults to .claude/skills/)
            project_root: Project root directory
        """
        self.adapter = SkillAdapter()
        self.index = SkillIndex()

        # Determine skills directory
        if skills_dir:
            self.skills_dir = Path(skills_dir)
        elif project_root:
            self.skills_dir = Path(project_root) / ".claude" / "skills"
        else:
            # Try to find .claude/skills in current or parent directories
            self.skills_dir = self._find_skills_dir()

        self._discovered = False

    def _find_skills_dir(self) -> Path:
        """Find .claude/skills directory by searching up from cwd."""
        current = Path.cwd()

        for _ in range(10):  # Limit search depth
            skills_path = current / ".claude" / "skills"
            if skills_path.exists():
                return skills_path
            parent = current.parent
            if parent == current:
                break
            current = parent

        # Default to cwd/.claude/skills
        return Path.cwd() / ".claude" / "skills"

    def discover(self, force: bool = False) -> SkillIndex:
        """
        Discover all skills in skills directory.

        Args:
            force: Force re-discovery even if already done

        Returns:
            SkillIndex with all discovered skills
        """
        if self._discovered and not force:
            return self.index

        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return self.index

        logger.info(f"Discovering skills in {self.skills_dir}")

        # Clear existing index
        self.index = SkillIndex()

        # Discover skill directories
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith(".") or skill_dir.name.startswith("_"):
                continue
            if skill_dir.name == "scripts":
                continue  # Skip shared scripts directory

            skill = self.adapter.load_skill(skill_dir)
            if skill:
                self.index.add(skill)
                self.adapter.cache_skill(skill)
                logger.debug(f"Discovered skill: {skill.skill_id}")

        self._discovered = True
        logger.info(f"Discovered {len(self.index.skills)} skills")

        return self.index

    def get_skill(self, skill_id: str, load_content: bool = False) -> SkillMetadata | None:
        """
        Get skill by ID.

        Args:
            skill_id: Skill identifier
            load_content: Whether to load full content

        Returns:
            SkillMetadata or None
        """
        if not self._discovered:
            self.discover()

        skill = self.index.get(skill_id)

        if skill and load_content and not skill.content:
            # Progressive loading: load content on demand
            full_skill = self.adapter.load_skill(Path(skill.skill_dir))
            if full_skill:
                skill = full_skill
                self.index.skills[skill_id] = skill

        return skill

    def find_skills(
        self,
        query: str | None = None,
        skill_type: str | None = None,
        domain: str | None = None,
        category: str | None = None,
        limit: int = 10,
    ) -> list[SkillMetadata]:
        """
        Find skills matching criteria.

        Args:
            query: Search query
            skill_type: Filter by type (command, agent, mode)
            domain: Filter by domain
            category: Filter by category
            limit: Maximum results

        Returns:
            List of matching SkillMetadata
        """
        if not self._discovered:
            self.discover()

        # Start with all skills or filtered set
        if skill_type:
            skill_ids = set(self.index.list_by_type(skill_type))
        else:
            skill_ids = set(self.index.skills.keys())

        # Apply domain filter
        if domain:
            domain_ids = set(self.index.list_by_domain(domain))
            skill_ids &= domain_ids

        # Apply category filter
        if category:
            category_ids = set(self.index.by_category.get(category, []))
            skill_ids &= category_ids

        # Apply search query
        if query:
            search_results = self.index.search(query)
            search_ids = {sid for sid, _ in search_results}
            skill_ids &= search_ids

            # Sort by relevance
            relevance = {sid: score for sid, score in search_results}
            skill_ids = sorted(skill_ids, key=lambda x: relevance.get(x, 0), reverse=True)
        else:
            skill_ids = sorted(skill_ids)

        # Limit results
        skill_ids = list(skill_ids)[:limit]

        return [self.index.skills[sid] for sid in skill_ids]

    def get_commands(self) -> list[SkillMetadata]:
        """Get all command skills (sc-* prefix)."""
        return self.find_skills(skill_type="command", limit=100)

    def get_agents(self) -> list[SkillMetadata]:
        """Get all agent skills (agent-* prefix)."""
        return self.find_skills(skill_type="agent", limit=200)

    def iter_skills(self) -> Iterator[SkillMetadata]:
        """Iterate over all skills."""
        if not self._discovered:
            self.discover()

        for skill in self.index.skills.values():
            yield skill

    def get_skill_for_task(
        self,
        task: str,
        files: list[str] | None = None,
        languages: list[str] | None = None,
    ) -> SkillMetadata | None:
        """
        Find best skill for a given task.

        Uses keyword matching and domain analysis to select
        the most appropriate skill.

        Args:
            task: Task description
            files: Files involved in task
            languages: Programming languages involved

        Returns:
            Best matching SkillMetadata or None
        """
        if not self._discovered:
            self.discover()

        task_lower = task.lower()

        # First, try exact command match
        command_patterns = [
            ("implement", "sc-implement"),
            ("analyze", "sc-analyze"),
            ("build", "sc-build"),
            ("test", "sc-test"),
            ("design", "sc-design"),
            ("document", "sc-document"),
            ("explain", "sc-explain"),
            ("improve", "sc-improve"),
            ("brainstorm", "sc-brainstorm"),
            ("estimate", "sc-estimate"),
            ("workflow", "sc-workflow"),
            ("git", "sc-git"),
        ]

        for keyword, skill_id in command_patterns:
            if keyword in task_lower:
                skill = self.get_skill(skill_id)
                if skill:
                    return skill

        # Try search-based matching
        results = self.index.search(task)
        if results:
            best_id, _ = results[0]
            return self.index.skills.get(best_id)

        # Default to implement for general tasks
        return self.get_skill("sc-implement")

    def export_manifest(self) -> dict[str, Any]:
        """
        Export skill manifest for documentation.

        Returns:
            Dictionary containing skill metadata
        """
        if not self._discovered:
            self.discover()

        manifest = {
            "version": "1.0.0",
            "skills_dir": str(self.skills_dir),
            "stats": self.index.stats(),
            "skills": {},
        }

        for skill_id, skill in self.index.skills.items():
            manifest["skills"][skill_id] = {
                "name": skill.name,
                "description": skill.description,
                "type": skill.skill_type,
                "domain": skill.domain,
                "tools": skill.tools,
                "mcp_servers": skill.mcp_servers,
                "requires_evidence": skill.requires_evidence,
            }

        return manifest
