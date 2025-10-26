"""
Dynamic Loading Context Manager for SuperClaude Framework

Manages intelligent, context-aware loading and unloading of components
based on triggers, thresholds, and resource constraints.
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib


@dataclass
class LoadedComponent:
    """Represents a loaded component with metadata."""

    name: str
    component_type: str  # 'agent', 'mode', 'command', 'mcp'
    loaded_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_kb: float = 0.0
    priority: int = 0
    ttl_seconds: int = 3600  # 1 hour default
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerRule:
    """Represents a trigger rule for dynamic loading."""

    pattern: str
    component_type: str
    components: List[str]
    threshold: float = 0.8
    regex: bool = False
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DynamicContextManager:
    """
    Manages dynamic loading and unloading of framework components.

    Features:
    - Context-aware trigger detection
    - LRU cache with TTL support
    - Resource constraint management
    - Performance optimization
    - Lazy loading patterns
    """

    # Configuration constants
    MAX_CACHE_SIZE = 10  # Maximum cached components
    DEFAULT_TTL = 3600  # 1 hour in seconds
    MIN_SCORE_THRESHOLD = 0.5
    LOAD_TIME_TARGET = 0.1  # 100ms target

    def __init__(self, triggers_path: Optional[str] = None):
        """
        Initialize the dynamic context manager.

        Args:
            triggers_path: Path to TRIGGERS.json file
        """
        self.logger = logging.getLogger(__name__)

        # Component cache (LRU with TTL)
        self.cache: OrderedDict[str, LoadedComponent] = OrderedDict()
        self.cache_hits = 0
        self.cache_misses = 0

        # Trigger rules
        self.triggers: List[TriggerRule] = []
        self.trigger_index: Dict[str, List[TriggerRule]] = defaultdict(list)

        # Loading metrics
        self.metrics = {
            'total_loads': 0,
            'total_unloads': 0,
            'average_load_time': 0.0,
            'total_load_time': 0.0,
            'cache_hit_rate': 0.0,
            'memory_saved_kb': 0.0,
            'token_reduction': 0.0
        }

        # Resource tracking
        self.resource_usage = {
            'memory_kb': 0.0,
            'token_count': 0,
            'component_count': 0
        }

        # Load triggers if path provided
        if triggers_path:
            self.load_triggers(triggers_path)

    def load_triggers(self, triggers_path: str) -> bool:
        """
        Load trigger rules from configuration file.

        Args:
            triggers_path: Path to triggers configuration

        Returns:
            True if successful
        """
        try:
            path = Path(triggers_path)
            if not path.exists():
                self.logger.warning(f"Triggers file not found: {triggers_path}")
                return False

            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Parse trigger rules
            for trigger_config in config.get('triggers', []):
                rule = TriggerRule(
                    pattern=trigger_config['pattern'],
                    component_type=trigger_config.get('type', 'agent'),
                    components=trigger_config.get('components', []),
                    threshold=trigger_config.get('threshold', 0.8),
                    regex=trigger_config.get('regex', False),
                    priority=trigger_config.get('priority', 0),
                    metadata=trigger_config.get('metadata', {})
                )
                self.triggers.append(rule)

                # Build index for faster lookup
                if not rule.regex:
                    # Index by first word for simple patterns
                    first_word = rule.pattern.split()[0] if rule.pattern else ''
                    if first_word:
                        self.trigger_index[first_word.lower()].append(rule)

            # Sort by priority
            self.triggers.sort(key=lambda x: x.priority, reverse=True)

            self.logger.info(f"Loaded {len(self.triggers)} trigger rules")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load triggers: {e}")
            return False

    def analyze_context(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Analyze context and determine components to load.

        Args:
            context: Execution context

        Returns:
            Dictionary of component names with confidence scores
        """
        components_to_load = {}

        # Extract text from context
        text_content = self._extract_text_from_context(context)

        # Check each trigger rule
        for rule in self.triggers:
            score = self._evaluate_trigger(rule, text_content, context)

            if score >= rule.threshold:
                for component in rule.components:
                    # Take maximum score if component appears in multiple rules
                    current_score = components_to_load.get(component, 0)
                    components_to_load[component] = max(current_score, score)

        # Check tool invocations
        tool_components = self._detect_tool_invocations(context)
        components_to_load.update(tool_components)

        # Check explicit flags
        flag_components = self._detect_flags(context)
        components_to_load.update(flag_components)

        return components_to_load

    def load_component(
        self,
        name: str,
        component_type: str,
        loader_func: Optional[Callable] = None,
        priority: int = 0
    ) -> Optional[Any]:
        """
        Load a component with caching.

        Args:
            name: Component name
            component_type: Type of component
            loader_func: Function to load the component
            priority: Component priority

        Returns:
            Loaded component or None
        """
        start_time = time.time()

        # Check cache first
        if name in self.cache:
            component = self.cache[name]

            # Check TTL
            if self._is_component_valid(component):
                # Update access time and count
                component.last_accessed = datetime.now()
                component.access_count += 1

                # Move to end (LRU)
                self.cache.move_to_end(name)

                self.cache_hits += 1
                self._update_cache_metrics()

                self.logger.debug(f"Cache hit for component: {name}")
                return component.metadata.get('instance')

            else:
                # TTL expired, remove from cache
                self._unload_component(name)

        # Cache miss
        self.cache_misses += 1

        # Load component
        if loader_func:
            try:
                instance = loader_func(name)

                # Estimate size (simplified)
                size_kb = len(str(instance)) / 1024 if instance else 0

                # Create component entry
                component = LoadedComponent(
                    name=name,
                    component_type=component_type,
                    loaded_at=datetime.now(),
                    last_accessed=datetime.now(),
                    access_count=1,
                    size_kb=size_kb,
                    priority=priority,
                    metadata={'instance': instance}
                )

                # Add to cache with eviction if needed
                self._add_to_cache(name, component)

                # Update metrics
                load_time = time.time() - start_time
                self._update_load_metrics(load_time, size_kb)

                self.logger.info(f"Loaded component: {name} ({load_time:.3f}s)")
                return instance

            except Exception as e:
                self.logger.error(f"Failed to load component {name}: {e}")
                return None

        return None

    def unload_component(self, name: str) -> bool:
        """
        Unload a component from cache.

        Args:
            name: Component name

        Returns:
            True if unloaded
        """
        return self._unload_component(name)

    def get_loaded_components(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about loaded components.

        Returns:
            Dictionary of loaded components
        """
        return {
            name: {
                'type': comp.component_type,
                'loaded_at': comp.loaded_at.isoformat(),
                'last_accessed': comp.last_accessed.isoformat(),
                'access_count': comp.access_count,
                'size_kb': comp.size_kb,
                'priority': comp.priority,
                'ttl_remaining': self._get_ttl_remaining(comp)
            }
            for name, comp in self.cache.items()
        }

    def optimize_for_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize component loading for given context.

        Args:
            context: Execution context

        Returns:
            Optimization recommendations
        """
        recommendations = {
            'load': [],
            'unload': [],
            'preload': [],
            'estimated_token_savings': 0,
            'estimated_memory_savings': 0
        }

        # Analyze what should be loaded
        components_needed = self.analyze_context(context)

        # Determine what to load
        for component, score in components_needed.items():
            if component not in self.cache and score >= self.MIN_SCORE_THRESHOLD:
                recommendations['load'].append({
                    'component': component,
                    'score': score,
                    'reason': 'High relevance to context'
                })

        # Determine what to unload
        current_time = datetime.now()
        for name, component in list(self.cache.items()):
            # Check if component is needed
            if name not in components_needed:
                # Check if it should be unloaded
                if not self._is_component_valid(component):
                    recommendations['unload'].append({
                        'component': name,
                        'reason': 'TTL expired'
                    })
                    recommendations['estimated_memory_savings'] += component.size_kb
                elif self._should_evict(component):
                    recommendations['unload'].append({
                        'component': name,
                        'reason': 'Low priority and not recently used'
                    })
                    recommendations['estimated_memory_savings'] += component.size_kb

        # Suggest preloading for likely next components
        preload_candidates = self._predict_next_components(context)
        for candidate in preload_candidates[:3]:  # Limit to top 3
            if candidate not in self.cache:
                recommendations['preload'].append(candidate)

        # Estimate token savings
        total_size = sum(c.size_kb for c in self.cache.values())
        recommendations['estimated_token_savings'] = int(total_size * 100)  # Rough estimate

        return recommendations

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.

        Returns:
            Dictionary of metrics
        """
        self._update_cache_metrics()

        return {
            **self.metrics,
            **self.resource_usage,
            'cache_size': len(self.cache),
            'cache_capacity': self.MAX_CACHE_SIZE,
            'trigger_rules': len(self.triggers)
        }

    def _extract_text_from_context(self, context: Dict[str, Any]) -> str:
        """Extract searchable text from context."""
        text_parts = []

        # Extract from common fields
        for field in ['task', 'description', 'query', 'question', 'prompt']:
            if field in context:
                text_parts.append(str(context[field]))

        # Extract from nested structures
        if 'messages' in context:
            for msg in context['messages']:
                if isinstance(msg, dict) and 'content' in msg:
                    text_parts.append(str(msg['content']))

        return ' '.join(text_parts).lower()

    def _evaluate_trigger(
        self,
        rule: TriggerRule,
        text: str,
        context: Dict[str, Any]
    ) -> float:
        """
        Evaluate trigger rule against context.

        Args:
            rule: Trigger rule
            text: Text content
            context: Full context

        Returns:
            Confidence score (0-1)
        """
        score = 0.0

        if rule.regex:
            # Regex pattern matching
            try:
                pattern = re.compile(rule.pattern, re.IGNORECASE)
                matches = pattern.findall(text)
                if matches:
                    # Score based on match count and position
                    score = min(1.0, len(matches) * 0.3)
                    # Boost if match is early in text
                    if pattern.search(text[:100]):
                        score = min(1.0, score * 1.5)
            except re.error:
                self.logger.error(f"Invalid regex pattern: {rule.pattern}")

        else:
            # Simple keyword matching
            pattern_lower = rule.pattern.lower()
            if pattern_lower in text:
                # Base score for presence
                score = 0.6

                # Boost for exact match
                if f' {pattern_lower} ' in f' {text} ':
                    score = 0.8

                # Boost for early occurrence
                index = text.find(pattern_lower)
                if index >= 0 and index < 100:
                    score = min(1.0, score * 1.2)

        # Apply context-specific adjustments
        if 'priority' in context and context['priority'] == 'high':
            score = min(1.0, score * 1.1)

        return score

    def _detect_tool_invocations(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Detect tool invocations that require specific components."""
        components = {}

        # Check for MCP tool patterns
        mcp_tools = {
            'mcp__zen': ['zen-mcp', 'consensus'],
        }

        text = str(context).lower()
        for tool_pattern, component_names in mcp_tools.items():
            if tool_pattern in text:
                for component in component_names:
                    components[component] = 1.0  # High confidence for explicit tool use

        return components

    def _detect_flags(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Detect command-line flags that trigger components."""
        components = {}

        flag_mappings = {
            '--brainstorm': 'brainstorming-mode',
            '--task-manage': 'task-management-mode',
            '--introspect': 'introspection-mode',
            '--uc': 'token-efficiency-mode',
            '--delegate': 'agent-coordination',
            '--zen': 'multi-model-support'
        }

        text = str(context).lower()
        for flag, component in flag_mappings.items():
            if flag in text:
                components[component] = 0.95  # High confidence for explicit flags

        return components

    def _is_component_valid(self, component: LoadedComponent) -> bool:
        """Check if component is still valid (TTL not expired)."""
        elapsed = (datetime.now() - component.loaded_at).total_seconds()
        return elapsed < component.ttl_seconds

    def _get_ttl_remaining(self, component: LoadedComponent) -> float:
        """Get remaining TTL in seconds."""
        elapsed = (datetime.now() - component.loaded_at).total_seconds()
        return max(0, component.ttl_seconds - elapsed)

    def _add_to_cache(self, name: str, component: LoadedComponent):
        """Add component to cache with LRU eviction."""
        # Check if eviction needed
        if len(self.cache) >= self.MAX_CACHE_SIZE:
            # Find component to evict
            evict_name = self._select_eviction_candidate()
            if evict_name:
                self._unload_component(evict_name)

        # Add to cache
        self.cache[name] = component
        self.resource_usage['component_count'] = len(self.cache)
        self.resource_usage['memory_kb'] += component.size_kb

    def _select_eviction_candidate(self) -> Optional[str]:
        """Select component to evict from cache."""
        current_time = datetime.now()
        candidates = []

        for name, component in self.cache.items():
            # Calculate eviction score (lower is better)
            time_since_access = (current_time - component.last_accessed).total_seconds()
            ttl_remaining = self._get_ttl_remaining(component)

            score = (
                time_since_access / 3600 +  # Hours since access
                (1 / (component.access_count + 1)) * 10 +  # Access frequency
                (1 - component.priority / 10) * 5 -  # Priority
                (ttl_remaining / 3600) * 2  # TTL remaining
            )

            candidates.append((name, score))

        # Sort by score and return lowest scoring (best to evict)
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def _should_evict(self, component: LoadedComponent) -> bool:
        """Determine if component should be evicted."""
        # Check various eviction criteria
        time_since_access = (datetime.now() - component.last_accessed).total_seconds()

        # Evict if not accessed recently and low priority
        if time_since_access > 1800 and component.priority < 5:  # 30 minutes
            return True

        # Evict if very low access count and not new
        time_since_load = (datetime.now() - component.loaded_at).total_seconds()
        if time_since_load > 600 and component.access_count < 2:  # 10 minutes
            return True

        return False

    def _unload_component(self, name: str) -> bool:
        """Unload component from cache."""
        if name in self.cache:
            component = self.cache[name]

            # Update resource usage
            self.resource_usage['memory_kb'] -= component.size_kb
            self.resource_usage['component_count'] = len(self.cache) - 1

            # Update metrics
            self.metrics['total_unloads'] += 1
            self.metrics['memory_saved_kb'] += component.size_kb

            # Remove from cache
            del self.cache[name]

            self.logger.debug(f"Unloaded component: {name}")
            return True

        return False

    def _predict_next_components(self, context: Dict[str, Any]) -> List[str]:
        """Predict likely next components based on patterns."""
        predictions = []

        # Simple prediction based on common sequences
        sequences = {
            'analysis': ['debugging', 'refactoring'],
            'implementation': ['testing', 'documentation'],
            'planning': ['architecture', 'design'],
            'debugging': ['performance', 'security']
        }

        # Find current context type
        text = self._extract_text_from_context(context)
        for context_type, next_components in sequences.items():
            if context_type in text:
                predictions.extend(next_components)

        return predictions[:5]  # Limit predictions

    def _update_load_metrics(self, load_time: float, size_kb: float):
        """Update loading metrics."""
        self.metrics['total_loads'] += 1
        self.metrics['total_load_time'] += load_time

        # Update average
        self.metrics['average_load_time'] = (
            self.metrics['total_load_time'] / self.metrics['total_loads']
        )

        # Estimate token reduction (rough approximation)
        self.metrics['token_reduction'] += size_kb * 100

    def _update_cache_metrics(self):
        """Update cache-related metrics."""
        total_requests = self.cache_hits + self.cache_misses
        if total_requests > 0:
            self.metrics['cache_hit_rate'] = self.cache_hits / total_requests

    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics = {
            'total_loads': 0,
            'total_unloads': 0,
            'average_load_time': 0.0,
            'total_load_time': 0.0,
            'cache_hit_rate': 0.0,
            'memory_saved_kb': 0.0,
            'token_reduction': 0.0
        }
        self.cache_hits = 0
        self.cache_misses = 0

    def clear_cache(self):
        """Clear all cached components."""
        for name in list(self.cache.keys()):
            self._unload_component(name)

        self.cache.clear()
        self.resource_usage = {
            'memory_kb': 0.0,
            'token_count': 0,
            'component_count': 0
        }
