"""
Dynamic Loading System for SuperClaude Framework

Provides intelligent, context-aware component loading to minimize token usage
and maximize performance through strategic caching and lazy loading.
"""

from .context_manager import DynamicContextManager, LoadedComponent, TriggerRule

__all__ = [
    'DynamicContextManager',
    'LoadedComponent',
    'TriggerRule'
]

__version__ = '1.0.0'