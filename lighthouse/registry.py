"""
Plugin registry and factory system for Lighthouse.

This module provides a centralized registry for all plugin types and
factory functions to instantiate them from configuration.
"""

from collections.abc import Callable
from typing import Any

from lighthouse.core import Evaluator, Notifier, Observer, Trigger


class PluginRegistry:
    """
    Central registry for all plugin types.

    Each category (observers, triggers, evaluators, notifiers) maintains
    a mapping of type names to implementation classes.
    """

    def __init__(self) -> None:
        self._observers: dict[str, type[Observer]] = {}
        self._triggers: dict[str, type[Trigger]] = {}
        self._evaluators: dict[str, type[Evaluator]] = {}
        self._notifiers: dict[str, type[Notifier]] = {}

    # Observer registration
    def register_observer(self, type_name: str, cls: type[Observer]) -> None:
        """Register an observer implementation."""
        self._observers[type_name] = cls

    def get_observer(self, type_name: str) -> type[Observer]:
        """Get an observer class by type name."""
        if type_name not in self._observers:
            raise ValueError(f"Unknown observer type: {type_name}")
        return self._observers[type_name]

    # Trigger registration
    def register_trigger(self, type_name: str, cls: type[Trigger]) -> None:
        """Register a trigger implementation."""
        self._triggers[type_name] = cls

    def get_trigger(self, type_name: str) -> type[Trigger]:
        """Get a trigger class by type name."""
        if type_name not in self._triggers:
            raise ValueError(f"Unknown trigger type: {type_name}")
        return self._triggers[type_name]

    # Evaluator registration
    def register_evaluator(self, type_name: str, cls: type[Evaluator]) -> None:
        """Register an evaluator implementation."""
        self._evaluators[type_name] = cls

    def get_evaluator(self, type_name: str) -> type[Evaluator]:
        """Get an evaluator class by type name."""
        if type_name not in self._evaluators:
            raise ValueError(f"Unknown evaluator type: {type_name}")
        return self._evaluators[type_name]

    # Notifier registration
    def register_notifier(self, type_name: str, cls: type[Notifier]) -> None:
        """Register a notifier implementation."""
        self._notifiers[type_name] = cls

    def get_notifier(self, type_name: str) -> type[Notifier]:
        """Get a notifier class by type name."""
        if type_name not in self._notifiers:
            raise ValueError(f"Unknown notifier type: {type_name}")
        return self._notifiers[type_name]

    def list_plugins(self) -> dict[str, list[str]]:
        """List all registered plugins by category."""
        return {
            "observers": list(self._observers.keys()),
            "triggers": list(self._triggers.keys()),
            "evaluators": list(self._evaluators.keys()),
            "notifiers": list(self._notifiers.keys()),
        }


# Global registry instance
_registry = PluginRegistry()


# Factory functions
def create_observer(type_name: str, config: dict[str, Any]) -> Observer:
    """Create an observer instance from configuration."""
    cls = _registry.get_observer(type_name)
    return cls(config)


def create_trigger(type_name: str, config: dict[str, Any], callback: Callable[[], None]) -> Trigger:
    """Create a trigger instance from configuration."""
    cls = _registry.get_trigger(type_name)
    return cls(config, callback)


def create_evaluator(type_name: str, config: dict[str, Any]) -> Evaluator:
    """Create an evaluator instance from configuration."""
    cls = _registry.get_evaluator(type_name)
    return cls(config)


def create_notifier(type_name: str, config: dict[str, Any]) -> Notifier:
    """Create a notifier instance from configuration."""
    cls = _registry.get_notifier(type_name)
    return cls(config)


# Decorator for easy registration
def register_observer(type_name: str) -> Callable[[type[Observer]], type[Observer]]:
    """Decorator to register an observer class."""
    def decorator(cls: type[Observer]) -> type[Observer]:
        _registry.register_observer(type_name, cls)
        return cls
    return decorator


def register_trigger(type_name: str) -> Callable[[type[Trigger]], type[Trigger]]:
    """Decorator to register a trigger class."""
    def decorator(cls: type[Trigger]) -> type[Trigger]:
        _registry.register_trigger(type_name, cls)
        return cls
    return decorator


def register_evaluator(type_name: str) -> Callable[[type[Evaluator]], type[Evaluator]]:
    """Decorator to register an evaluator class."""
    def decorator(cls: type[Evaluator]) -> type[Evaluator]:
        _registry.register_evaluator(type_name, cls)
        return cls
    return decorator


def register_notifier(type_name: str) -> Callable[[type[Notifier]], type[Notifier]]:
    """Decorator to register a notifier class."""
    def decorator(cls: type[Notifier]) -> type[Notifier]:
        _registry.register_notifier(type_name, cls)
        return cls
    return decorator


def get_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    return _registry
