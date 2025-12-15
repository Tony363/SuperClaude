"""
Extended Agent Loader for SuperClaude Framework

This module provides dynamic loading and management of 116 specialized agents
with lazy loading, intelligent caching, and category-based organization.
"""

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # Optional dependency for YAML registry parsing
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on optional extras
    yaml = None  # type: ignore

from . import usage_tracker
from .base import BaseAgent
from .registry import AgentRegistry


class AgentCategory(Enum):
    """Agent category enumeration matching the 10 defined categories."""

    CORE_DEVELOPMENT = "01-core-development"
    LANGUAGE_SPECIALISTS = "02-language-specialists"
    INFRASTRUCTURE = "03-infrastructure"
    QUALITY_SECURITY = "04-quality-security"
    DATA_AI = "05-data-ai"
    DEVELOPER_EXPERIENCE = "06-developer-experience"
    SPECIALIZED_DOMAINS = "07-specialized-domains"
    BUSINESS_PRODUCT = "08-business-product"
    META_ORCHESTRATION = "09-meta-orchestration"
    RESEARCH_ANALYSIS = "10-research-analysis"


@dataclass
class AgentMetadata:
    """Metadata for agent capabilities and matching."""

    id: str
    name: str
    category: AgentCategory
    priority: int
    domains: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    file_patterns: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    description: str = ""
    path: Optional[Path] = None
    is_loaded: bool = False
    load_count: int = 0
    last_accessed: float = 0.0


@dataclass
class MatchScore:
    """Detailed scoring for agent matching."""

    agent_id: str
    total_score: float
    breakdown: Dict[str, float] = field(default_factory=dict)
    matched_criteria: List[str] = field(default_factory=list)
    confidence: str = "low"  # low, medium, high, excellent


class ExtendedAgentLoader:
    """
    Advanced agent loader for 131-agent system with intelligent selection.

    Features:
    - Lazy loading of agent definitions from YAML
    - LRU cache with TTL for frequently used agents
    - Category-based organization
    - Intelligent agent selection with confidence scoring
    - Capability matching (domains, languages, file patterns, imports)
    - Access pattern analysis and optimization
    """

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        cache_size: int = 20,
        ttl_seconds: int = 1800,  # 30 minutes
        registry_path: Optional[Path] = None,
    ):
        """
        Initialize the extended agent loader.

        Args:
            registry: Agent registry instance
            cache_size: Maximum number of agents to cache in memory
            ttl_seconds: Time-to-live for cached agents
            registry_path: Path to agent_registry.yaml
        """
        self.registry = registry or AgentRegistry()
        self.cache_size = cache_size
        self.ttl = ttl_seconds
        self.logger = logging.getLogger("agent.extended_loader")

        # Determine registry path
        if registry_path is None:
            registry_path = (
                Path(__file__).parent.parent / "Core" / "agent_registry.yaml"
            )
        self.registry_path = registry_path

        # Agent metadata index (lightweight, always loaded)
        self._agent_metadata: Dict[str, AgentMetadata] = {}
        self._category_index: Dict[AgentCategory, List[str]] = {
            cat: [] for cat in AgentCategory
        }

        # LRU cache for loaded agents
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

        # Statistics
        self._stats = {
            "metadata_loads": 0,
            "agent_loads": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "evictions": 0,
            "total_load_time": 0.0,
            "selection_queries": 0,
        }

        # Access patterns for optimization
        self._access_history: List[str] = []
        self._access_frequency: Dict[str, int] = {}

        # Load metadata index
        self._load_metadata_index()

    def _load_metadata_index(self):
        """Load lightweight metadata index for all agents."""
        start_time = time.time()

        if not self.registry_path.exists():
            self.logger.warning(f"Registry file not found: {self.registry_path}")
            return

        if yaml is None:
            self.logger.debug("PyYAML not available; skipping metadata index load")
            return

        try:
            with open(self.registry_path) as f:
                data = yaml.safe_load(f)

            if not data or "registry" not in data:
                self.logger.error("Invalid registry format")
                return

            registry = data["registry"]

            # Load all agent categories
            for category_key in registry:
                if category_key in ["core"]:
                    category = None  # Core agents don't map to AgentCategory enum
                else:
                    # Map category key to enum
                    category = self._map_category_key(category_key)

                agents = registry[category_key]

                for agent_data in agents:
                    agent_id = agent_data.get("id")
                    if not agent_id:
                        continue

                    # Create metadata entry
                    metadata = AgentMetadata(
                        id=agent_id,
                        name=agent_data.get("name", agent_id),
                        category=category
                        if category
                        else AgentCategory.CORE_DEVELOPMENT,
                        priority=agent_data.get("priority", 3),
                        domains=agent_data.get("domains", []),
                        languages=agent_data.get("languages", []),
                        keywords=agent_data.get("keywords", []),
                        file_patterns=agent_data.get("file_patterns", []),
                        imports=agent_data.get("imports", []),
                        description=agent_data.get("description", ""),
                    )

                    self._agent_metadata[agent_id] = metadata

                    # Update category index
                    if category:
                        self._category_index[category].append(agent_id)

            load_time = time.time() - start_time
            self._stats["metadata_loads"] += 1

            self.logger.info(
                f"Loaded metadata for {len(self._agent_metadata)} agents "
                f"in {load_time:.3f}s"
            )

        except Exception as e:
            self.logger.error(f"Failed to load metadata index: {e}")

    def _map_category_key(self, key: str) -> Optional[AgentCategory]:
        """Map registry category key to AgentCategory enum."""
        mapping = {
            "extended_core_development": AgentCategory.CORE_DEVELOPMENT,
            "extended_language_specialists": AgentCategory.LANGUAGE_SPECIALISTS,
            "extended_infrastructure": AgentCategory.INFRASTRUCTURE,
            "extended_quality_security": AgentCategory.QUALITY_SECURITY,
            "extended_data_ai": AgentCategory.DATA_AI,
            "extended_developer_experience": AgentCategory.DEVELOPER_EXPERIENCE,
            "extended_specialized": AgentCategory.SPECIALIZED_DOMAINS,
            "extended_business_product": AgentCategory.BUSINESS_PRODUCT,
            "extended_meta_orchestration": AgentCategory.META_ORCHESTRATION,
            "extended_research_analysis": AgentCategory.RESEARCH_ANALYSIS,
        }
        return mapping.get(key)

    def load_agent(
        self, agent_id: str, force_reload: bool = False
    ) -> Optional[BaseAgent]:
        """
        Load an agent by ID with caching.

        Args:
            agent_id: Agent identifier
            force_reload: Force reload even if cached

        Returns:
            Agent instance or None
        """
        self._stats["agent_loads"] += 1
        start_time = time.time()

        # Update access tracking
        self._track_access(agent_id)
        config = self.registry.get_agent_config(agent_id) if self.registry else None
        source = "core" if config and config.get("is_core") else "extended"

        # Check cache first
        if not force_reload and agent_id in self._cache:
            cache_entry = self._cache[agent_id]

            # Check TTL
            if time.time() - cache_entry["timestamp"] < self.ttl:
                # Move to end (most recently used)
                self._cache.move_to_end(agent_id)
                self._stats["cache_hits"] += 1

                # Update metadata
                if agent_id in self._agent_metadata:
                    metadata = self._agent_metadata[agent_id]
                    metadata.last_accessed = time.time()
                    metadata.load_count += 1

                usage_tracker.record_load(agent_id, source=source)
                load_time = time.time() - start_time
                self._stats["total_load_time"] += load_time

                self.logger.debug(f"Cache hit for agent: {agent_id}")
                return cache_entry["agent"]
            else:
                # Expired
                del self._cache[agent_id]
                self.logger.debug(f"Cache expired for agent: {agent_id}")

        # Cache miss - load from registry
        self._stats["cache_misses"] += 1

        agent = self.registry.get_agent(agent_id)

        if agent:
            # Initialize agent
            if agent.initialize():
                # Add to cache
                self._add_to_cache(agent_id, agent)
                usage_tracker.record_load(agent_id, source=source)

                # Update metadata
                if agent_id in self._agent_metadata:
                    metadata = self._agent_metadata[agent_id]
                    metadata.is_loaded = True
                    metadata.last_accessed = time.time()
                    metadata.load_count += 1
            else:
                self.logger.warning(f"Failed to initialize agent: {agent_id}")
                agent = None

        load_time = time.time() - start_time
        self._stats["total_load_time"] += load_time

        if agent:
            self.logger.info(f"Loaded agent {agent_id} in {load_time:.3f}s")
        else:
            self.logger.error(f"Failed to load agent: {agent_id}")

        return agent

    def _add_to_cache(self, agent_id: str, agent: BaseAgent):
        """Add agent to LRU cache with eviction."""
        # Check if cache is full
        if len(self._cache) >= self.cache_size:
            # Evict least recently used
            evicted_id = next(iter(self._cache))
            evicted_entry = self._cache.pop(evicted_id)

            # Clean up evicted agent
            evicted_agent = evicted_entry["agent"]
            evicted_agent.reset()

            self._stats["evictions"] += 1
            self.logger.debug(f"Evicted agent from cache: {evicted_id}")

        # Add new entry
        self._cache[agent_id] = {"agent": agent, "timestamp": time.time()}
        self._cache.move_to_end(agent_id)

    def _track_access(self, agent_id: str):
        """Track agent access patterns."""
        self._access_history.append(agent_id)
        self._access_frequency[agent_id] = self._access_frequency.get(agent_id, 0) + 1

        # Limit history size
        if len(self._access_history) > 1000:
            self._access_history = self._access_history[-500:]

    def select_agent(
        self,
        context: Dict[str, Any],
        category_hint: Optional[AgentCategory] = None,
        top_n: int = 5,
        min_confidence: float = 0.3,
    ) -> List[MatchScore]:
        """
        Intelligent agent selection based on context.

        Args:
            context: Task context with keys:
                - task: Task description
                - files: List of file paths
                - languages: List of programming languages
                - domains: List of domain areas
                - keywords: List of keywords
            category_hint: Optional category preference
            top_n: Number of suggestions to return
            min_confidence: Minimum confidence threshold

        Returns:
            List of MatchScore objects, sorted by score
        """
        self._stats["selection_queries"] += 1

        scores = []

        for agent_id, metadata in self._agent_metadata.items():
            # Apply category filter if provided
            if category_hint and metadata.category != category_hint:
                continue

            # Calculate match score
            match = self._calculate_match_score(context, metadata)

            if match.total_score >= min_confidence:
                scores.append(match)

        # Sort by total score
        scores.sort(key=lambda x: x.total_score, reverse=True)

        return scores[:top_n]

    def _calculate_match_score(
        self, context: Dict[str, Any], metadata: AgentMetadata
    ) -> MatchScore:
        """
        Calculate detailed match score for an agent.

        Scoring components:
        - Keywords: 30% weight
        - Domains: 25% weight
        - Languages: 20% weight
        - File patterns: 15% weight
        - Import patterns: 10% weight
        - Priority bonus: Up to 10% bonus

        Args:
            context: Task context
            metadata: Agent metadata

        Returns:
            MatchScore object with breakdown
        """
        score = 0.0
        breakdown = {}
        matched_criteria = []

        # Extract context data
        task_text = context.get("task", "").lower()
        files = [f.lower() for f in context.get("files", [])]
        languages = [l.lower() for l in context.get("languages", [])]
        domains = [d.lower() for d in context.get("domains", [])]
        keywords = [k.lower() for k in context.get("keywords", [])]
        imports = [i.lower() for i in context.get("imports", [])]

        # 1. Keyword matching (30% weight)
        keyword_score = 0.0
        if metadata.keywords:
            matched_keywords = []
            for keyword in metadata.keywords:
                keyword_lower = keyword.lower()
                # Check in task description
                if keyword_lower in task_text:
                    keyword_score += 1.0
                    matched_keywords.append(keyword)
                # Check in provided keywords
                elif keyword_lower in keywords:
                    keyword_score += 0.8
                    matched_keywords.append(keyword)
                # Partial match
                elif any(kw in keyword_lower or keyword_lower in kw for kw in keywords):
                    keyword_score += 0.3

            keyword_score = min(keyword_score / len(metadata.keywords), 1.0)
            if matched_keywords:
                matched_criteria.append(f"keywords: {', '.join(matched_keywords[:3])}")

        breakdown["keywords"] = keyword_score * 0.30
        score += breakdown["keywords"]

        # 2. Domain matching (25% weight)
        domain_score = 0.0
        if metadata.domains:
            matched_domains = []
            for domain in metadata.domains:
                domain_lower = domain.lower()
                if domain_lower in task_text or domain_lower in domains:
                    domain_score += 1.0
                    matched_domains.append(domain)
                elif any(d in domain_lower or domain_lower in d for d in domains):
                    domain_score += 0.5

            domain_score = min(domain_score / len(metadata.domains), 1.0)
            if matched_domains:
                matched_criteria.append(f"domains: {', '.join(matched_domains)}")

        breakdown["domains"] = domain_score * 0.25
        score += breakdown["domains"]

        # 3. Language matching (20% weight)
        language_score = 0.0
        if metadata.languages and metadata.languages != ["any"]:
            matched_languages = []
            for lang in metadata.languages:
                lang_lower = lang.lower()
                if lang_lower in languages or lang_lower in task_text:
                    language_score += 1.0
                    matched_languages.append(lang)

            if metadata.languages:
                language_score = min(language_score / len(metadata.languages), 1.0)
            if matched_languages:
                matched_criteria.append(f"languages: {', '.join(matched_languages)}")
        elif metadata.languages == ["any"]:
            language_score = 0.3  # Neutral score for any-language agents

        breakdown["languages"] = language_score * 0.20
        score += breakdown["languages"]

        # 4. File pattern matching (15% weight)
        file_pattern_score = 0.0
        if metadata.file_patterns and files:
            matched_patterns = []
            for pattern in metadata.file_patterns:
                pattern_lower = pattern.lower()
                for file in files:
                    if pattern_lower in file or self._match_glob(pattern_lower, file):
                        file_pattern_score += 1.0
                        matched_patterns.append(pattern)
                        break

            if metadata.file_patterns:
                file_pattern_score = min(
                    file_pattern_score / len(metadata.file_patterns), 1.0
                )
            if matched_patterns:
                matched_criteria.append(f"files: {', '.join(matched_patterns[:3])}")

        breakdown["file_patterns"] = file_pattern_score * 0.15
        score += breakdown["file_patterns"]

        # 5. Import pattern matching (10% weight)
        import_score = 0.0
        if metadata.imports and imports:
            matched_imports = []
            for imp in metadata.imports:
                imp_lower = imp.lower()
                if any(imp_lower in i or i in imp_lower for i in imports):
                    import_score += 1.0
                    matched_imports.append(imp)

            if metadata.imports:
                import_score = min(import_score / len(metadata.imports), 1.0)
            if matched_imports:
                matched_criteria.append(f"imports: {', '.join(matched_imports[:2])}")

        breakdown["imports"] = import_score * 0.10
        score += breakdown["imports"]

        # 6. Priority bonus (up to 10%)
        priority_bonus = (
            (4 - metadata.priority) / 3 * 0.10
        )  # Priority 1 = 10%, 2 = 6.67%, 3 = 3.33%
        breakdown["priority"] = priority_bonus
        score += priority_bonus

        # Determine confidence level
        if score >= 0.8:
            confidence = "excellent"
        elif score >= 0.6:
            confidence = "high"
        elif score >= 0.4:
            confidence = "medium"
        else:
            confidence = "low"

        return MatchScore(
            agent_id=metadata.id,
            total_score=score,
            breakdown=breakdown,
            matched_criteria=matched_criteria,
            confidence=confidence,
        )

    def _match_glob(self, pattern: str, filename: str) -> bool:
        """Simple glob matching for file patterns."""
        import fnmatch

        return fnmatch.fnmatch(filename, pattern)

    def get_agents_by_category(self, category: AgentCategory) -> List[AgentMetadata]:
        """Get all agents in a category."""
        agent_ids = self._category_index.get(category, [])
        return [
            self._agent_metadata[aid]
            for aid in agent_ids
            if aid in self._agent_metadata
        ]

    def list_categories(self) -> Dict[AgentCategory, int]:
        """List all categories with agent counts."""
        return {cat: len(agents) for cat, agents in self._category_index.items()}

    def search_agents(
        self, query: str, search_fields: List[str] = None
    ) -> List[AgentMetadata]:
        """
        Search agents by query string.

        Args:
            query: Search query
            search_fields: Fields to search in (name, description, keywords, domains)

        Returns:
            List of matching agent metadata
        """
        if search_fields is None:
            search_fields = ["name", "description", "keywords", "domains"]

        query_lower = query.lower()
        matches = []

        for metadata in self._agent_metadata.values():
            # Search in specified fields
            if "name" in search_fields and query_lower in metadata.name.lower():
                matches.append(metadata)
                continue

            if (
                "description" in search_fields
                and query_lower in metadata.description.lower()
            ):
                matches.append(metadata)
                continue

            if "keywords" in search_fields:
                if any(query_lower in k.lower() for k in metadata.keywords):
                    matches.append(metadata)
                    continue

            if "domains" in search_fields:
                if any(query_lower in d.lower() for d in metadata.domains):
                    matches.append(metadata)
                    continue

        return matches

    def preload_top_agents(self, count: int = 10) -> int:
        """
        Preload most frequently accessed agents.

        Args:
            count: Number of agents to preload

        Returns:
            Number of agents successfully loaded
        """
        # Sort by access frequency
        sorted_agents = sorted(
            self._access_frequency.items(), key=lambda x: x[1], reverse=True
        )

        loaded = 0
        for agent_id, _ in sorted_agents[:count]:
            if self.load_agent(agent_id):
                loaded += 1

        self.logger.info(f"Preloaded {loaded}/{count} top agents")
        return loaded

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive loader statistics."""
        stats = self._stats.copy()

        # Calculate derived metrics
        if stats["agent_loads"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["agent_loads"]
            stats["avg_load_time"] = stats["total_load_time"] / stats["agent_loads"]
        else:
            stats["cache_hit_rate"] = 0.0
            stats["avg_load_time"] = 0.0

        stats["total_agents"] = len(self._agent_metadata)
        stats["cached_agents"] = len(self._cache)
        stats["max_cache_size"] = self.cache_size
        stats["category_distribution"] = {
            cat.value: len(agents) for cat, agents in self._category_index.items()
        }

        # Top accessed agents
        top_agents = sorted(
            self._access_frequency.items(), key=lambda x: x[1], reverse=True
        )[:10]
        stats["top_accessed_agents"] = dict(top_agents)

        return stats

    def load_all_agents(self) -> Dict[str, Any]:
        """Load all agents into memory and return a mapping of id->agent instance."""
        loaded: Dict[str, Any] = {}
        for agent_id in list(self._agent_metadata.keys()):
            agent = self.load_agent(agent_id)
            if agent:
                loaded[agent_id] = agent
        return loaded

    def explain_selection(
        self, agent_id: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Explain why an agent was selected.

        Args:
            agent_id: Selected agent ID
            context: Task context

        Returns:
            Detailed explanation with scoring breakdown
        """
        if agent_id not in self._agent_metadata:
            return {"error": f"Agent not found: {agent_id}"}

        metadata = self._agent_metadata[agent_id]
        match = self._calculate_match_score(context, metadata)

        return {
            "agent_id": agent_id,
            "agent_name": metadata.name,
            "category": metadata.category.value,
            "priority": metadata.priority,
            "confidence": match.confidence,
            "total_score": match.total_score,
            "breakdown": match.breakdown,
            "matched_criteria": match.matched_criteria,
            "metadata": {
                "domains": metadata.domains,
                "languages": metadata.languages,
                "keywords": metadata.keywords,
                "file_patterns": metadata.file_patterns,
            },
        }

    def clear_cache(self):
        """Clear the agent cache."""
        for entry in self._cache.values():
            entry["agent"].reset()

        self._cache.clear()
        self.logger.info("Agent cache cleared")

    def optimize_cache(self):
        """Optimize cache based on access patterns."""
        if not self._access_history:
            return

        # Analyze recent access patterns
        recent_accesses = self._access_history[-100:]
        frequency = {}
        for agent_id in recent_accesses:
            frequency[agent_id] = frequency.get(agent_id, 0) + 1

        # Preload frequently accessed agents
        sorted_agents = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
        top_agents = [aid for aid, _ in sorted_agents[: self.cache_size]]

        loaded = 0
        for agent_id in top_agents:
            if agent_id not in self._cache:
                if self.load_agent(agent_id):
                    loaded += 1

        self.logger.info(
            f"Cache optimized: preloaded {loaded} agents based on access patterns"
        )

    def __str__(self) -> str:
        """String representation."""
        return (
            f"ExtendedAgentLoader("
            f"agents={len(self._agent_metadata)}, "
            f"cached={len(self._cache)}/{self.cache_size}, "
            f"hit_rate={self.get_statistics()['cache_hit_rate']:.2%}"
            f")"
        )
