"""
Plugin initialization for Lighthouse.

This module imports all built-in plugins to register them with the registry.
Import this module to ensure all plugins are available.
"""

# Import all plugin modules to trigger registration decorators
# pylint: disable=unused-import
# ruff: noqa: F401
from lighthouse import evaluators, notifiers, observers, triggers

# Re-export registry functions for convenience
from lighthouse.registry import (
    create_evaluator,
    create_notifier,
    create_observer,
    create_trigger,
    get_registry,
)

__all__ = [
    "create_evaluator",
    "create_notifier",
    "create_observer",
    "create_trigger",
    "get_registry",
]
