"""
Tests for plugin registry and factory system.
"""

from datetime import datetime

import pytest

# Import plugin modules to trigger decorator registration
# pylint: disable=unused-import
# ruff: noqa: F401
import lighthouse.evaluators
import lighthouse.notifiers
import lighthouse.observers
import lighthouse.triggers
from lighthouse.core import AlertDecision, Evaluator, Notifier, ObservationResult, Observer, Trigger
from lighthouse.registry import (
    PluginRegistry,
    create_evaluator,
    create_notifier,
    create_observer,
    create_trigger,
    get_registry,
    register_observer,
)


class TestPluginRegistry:
    """Tests for PluginRegistry class."""

    def test_register_and_get_observer(self) -> None:
        """Test registering and retrieving an observer."""
        registry = PluginRegistry()

        class TestObserver(Observer):
            def observe(self) -> ObservationResult:
                return ObservationResult(value=True, timestamp=datetime.now(), metadata={})

        registry.register_observer("test", TestObserver)
        retrieved = registry.get_observer("test")

        assert retrieved is TestObserver

    def test_register_and_get_trigger(self) -> None:
        """Test registering and retrieving a trigger."""
        registry = PluginRegistry()

        class TestTrigger(Trigger):
            def start(self) -> None:
                pass
            def stop(self) -> None:
                pass

        registry.register_trigger("test", TestTrigger)
        retrieved = registry.get_trigger("test")

        assert retrieved is TestTrigger

    def test_register_and_get_evaluator(self) -> None:
        """Test registering and retrieving an evaluator."""
        registry = PluginRegistry()

        class TestEvaluator(Evaluator):
            def evaluate(
                self,
                current: ObservationResult,
                history: list[ObservationResult]
            ) -> AlertDecision:
                return AlertDecision(should_alert=False, severity="low", message="test", context={})

        registry.register_evaluator("test", TestEvaluator)
        retrieved = registry.get_evaluator("test")

        assert retrieved is TestEvaluator

    def test_register_and_get_notifier(self) -> None:
        """Test registering and retrieving a notifier."""
        registry = PluginRegistry()

        class TestNotifier(Notifier):
            def notify(self, alert: AlertDecision, watcher_name: str) -> bool:
                return True

        registry.register_notifier("test", TestNotifier)
        retrieved = registry.get_notifier("test")

        assert retrieved is TestNotifier

    def test_get_unknown_observer_raises_error(self) -> None:
        """Test that getting an unknown observer raises ValueError."""
        registry = PluginRegistry()

        with pytest.raises(ValueError, match="Unknown observer type: nonexistent"):
            registry.get_observer("nonexistent")

    def test_get_unknown_trigger_raises_error(self) -> None:
        """Test that getting an unknown trigger raises ValueError."""
        registry = PluginRegistry()

        with pytest.raises(ValueError, match="Unknown trigger type: nonexistent"):
            registry.get_trigger("nonexistent")

    def test_get_unknown_evaluator_raises_error(self) -> None:
        """Test that getting an unknown evaluator raises ValueError."""
        registry = PluginRegistry()

        with pytest.raises(ValueError, match="Unknown evaluator type: nonexistent"):
            registry.get_evaluator("nonexistent")

    def test_get_unknown_notifier_raises_error(self) -> None:
        """Test that getting an unknown notifier raises ValueError."""
        registry = PluginRegistry()

        with pytest.raises(ValueError, match="Unknown notifier type: nonexistent"):
            registry.get_notifier("nonexistent")

    def test_list_plugins_empty(self) -> None:
        """Test listing plugins in an empty registry."""
        registry = PluginRegistry()

        plugins = registry.list_plugins()

        assert plugins == {
            "observers": [],
            "triggers": [],
            "evaluators": [],
            "notifiers": []
        }

    def test_list_plugins_with_registrations(self) -> None:
        """Test listing plugins after registration."""
        registry = PluginRegistry()

        class DummyObserver(Observer):
            def observe(self) -> ObservationResult:
                return ObservationResult(value=None, timestamp=datetime.now(), metadata={})

        class DummyTrigger(Trigger):
            def start(self) -> None:
                pass
            def stop(self) -> None:
                pass

        registry.register_observer("obs1", DummyObserver)
        registry.register_observer("obs2", DummyObserver)
        registry.register_trigger("trig1", DummyTrigger)

        plugins = registry.list_plugins()

        assert "obs1" in plugins["observers"]
        assert "obs2" in plugins["observers"]
        assert "trig1" in plugins["triggers"]
        assert len(plugins["evaluators"]) == 0
        assert len(plugins["notifiers"]) == 0

    def test_overwrite_registration(self) -> None:
        """Test that registering the same type name overwrites previous registration."""
        registry = PluginRegistry()

        class FirstObserver(Observer):
            def observe(self) -> ObservationResult:
                return ObservationResult(value=1, timestamp=datetime.now(), metadata={})

        class SecondObserver(Observer):
            def observe(self) -> ObservationResult:
                return ObservationResult(value=2, timestamp=datetime.now(), metadata={})

        registry.register_observer("test", FirstObserver)
        registry.register_observer("test", SecondObserver)

        retrieved = registry.get_observer("test")
        assert retrieved is SecondObserver


class TestDecoratorRegistration:
    """Tests for decorator-based registration."""

    def test_register_observer_decorator(self) -> None:
        """Test @register_observer decorator."""
        # Create a fresh registry for this test
        PluginRegistry()

        # Use decorator
        @register_observer("decorator_test")
        class DecoratorObserver(Observer):
            def observe(self) -> ObservationResult:
                return ObservationResult(value=True, timestamp=datetime.now(), metadata={})

        # The decorator should register with the global registry, not our test registry
        # So let's just verify the class is returned unchanged
        assert DecoratorObserver is not None
        assert hasattr(DecoratorObserver, 'observe')

    def test_decorator_returns_original_class(self) -> None:
        """Test that decorators return the original class."""
        @register_observer("original_test")
        class OriginalObserver(Observer):
            custom_attr = "test"
            def observe(self) -> ObservationResult:
                return ObservationResult(value=None, timestamp=datetime.now(), metadata={})

        # Should preserve the class and its attributes
        assert OriginalObserver.custom_attr == "test"
        assert hasattr(OriginalObserver, 'observe')


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_observer_from_config(self) -> None:
        """Test creating observer instance from config."""
        # Use a built-in observer type that's already registered
        observer = create_observer("log_pattern", {
            "log_file": "/tmp/test.log",
            "patterns": ["ERROR"]
        })

        assert observer is not None
        assert hasattr(observer, 'observe')
        assert observer.config["log_file"] == "/tmp/test.log"

    def test_create_trigger_from_config(self) -> None:
        """Test creating trigger instance from config."""
        callback_called = {"called": False}

        def test_callback() -> None:
            callback_called["called"] = True

        # Use a built-in trigger type
        trigger = create_trigger("manual", {}, test_callback)

        assert trigger is not None
        assert hasattr(trigger, 'start')
        assert hasattr(trigger, 'stop')

    def test_create_evaluator_from_config(self) -> None:
        """Test creating evaluator instance from config."""
        evaluator = create_evaluator("threshold", {
            "operator": "gt",
            "value": 10
        })

        assert evaluator is not None
        assert hasattr(evaluator, 'evaluate')
        assert evaluator.config["operator"] == "gt"
        assert evaluator.config["value"] == 10

    def test_create_notifier_from_config(self) -> None:
        """Test creating notifier instance from config."""
        notifier = create_notifier("console", {})

        assert notifier is not None
        assert hasattr(notifier, 'notify')

    def test_create_unknown_observer_raises_error(self) -> None:
        """Test that creating unknown observer raises ValueError."""
        with pytest.raises(ValueError, match="Unknown observer type"):
            create_observer("nonexistent_type", {})

    def test_create_unknown_trigger_raises_error(self) -> None:
        """Test that creating unknown trigger raises ValueError."""
        with pytest.raises(ValueError, match="Unknown trigger type"):
            create_trigger("nonexistent_type", {}, lambda: None)

    def test_create_unknown_evaluator_raises_error(self) -> None:
        """Test that creating unknown evaluator raises ValueError."""
        with pytest.raises(ValueError, match="Unknown evaluator type"):
            create_evaluator("nonexistent_type", {})

    def test_create_unknown_notifier_raises_error(self) -> None:
        """Test that creating unknown notifier raises ValueError."""
        with pytest.raises(ValueError, match="Unknown notifier type"):
            create_notifier("nonexistent_type", {})


class TestGlobalRegistry:
    """Tests for global registry access."""

    def test_get_registry_returns_singleton(self) -> None:
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_global_registry_has_builtin_plugins(self) -> None:
        """Test that global registry has all built-in plugins registered."""
        registry = get_registry()
        plugins = registry.list_plugins()

        # Check for built-in observers
        assert "log_pattern" in plugins["observers"]
        assert "metric" in plugins["observers"]
        assert "service" in plugins["observers"]

        # Check for built-in triggers
        assert "file_event" in plugins["triggers"]
        assert "temporal" in plugins["triggers"]
        assert "manual" in plugins["triggers"]

        # Check for built-in evaluators
        assert "pattern_match" in plugins["evaluators"]
        assert "threshold" in plugins["evaluators"]
        assert "sequential_growth" in plugins["evaluators"]
        assert "state_change" in plugins["evaluators"]

        # Check for built-in notifiers
        assert "pushover" in plugins["notifiers"]
        assert "webhook" in plugins["notifiers"]
        assert "console" in plugins["notifiers"]

    def test_factory_uses_global_registry(self) -> None:
        """Test that factory functions use the global registry."""
        # Should be able to create built-in types without manual registration
        observer = create_observer("log_pattern", {
            "log_file": "/tmp/test.log",
            "patterns": []
        })

        evaluator = create_evaluator("pattern_match", {})

        assert observer is not None
        assert evaluator is not None
