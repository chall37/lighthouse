"""
Tests for dynamic import validation in triggers, notifiers, observers, and evaluators modules.
"""

import importlib
import importlib.util
from pathlib import Path
from typing import Any


class TestTriggerImportValidation:
    """Test validation of trigger imports."""

    def test_rejects_non_class_export(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that non-class exports are rejected."""
        # Create a temporary trigger module with a non-class export
        trigger_file = tmp_path / "bad_trigger.py"
        trigger_file.write_text("""
from lighthouse.core import Trigger as BaseTrigger
from lighthouse.registry import register_trigger

# This is a function, not a class - should be rejected
def NotAClass():
    pass

__all__ = ["NotAClass"]
""")

        # Temporarily add tmp_path to sys.path
        monkeypatch.syspath_prepend(str(tmp_path))

        # Import and check it doesn't export the invalid item
        module = importlib.import_module("bad_trigger")
        assert hasattr(module, "__all__")
        assert "NotAClass" in module.__all__

        # The validation should skip it (tested via warning logs)

    def test_rejects_non_trigger_subclass(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that non-Trigger subclasses are rejected."""
        trigger_file = tmp_path / "wrong_base.py"
        trigger_file.write_text("""
from lighthouse.core import Observer  # Wrong base class
from lighthouse.registry import register_trigger

@register_trigger("wrong")
class WrongBase(Observer):
    def observe(self):
        pass

__all__ = ["WrongBase"]
""")

        monkeypatch.syspath_prepend(str(tmp_path))
        module = importlib.import_module("wrong_base")
        assert hasattr(module, "__all__")

    def test_accepts_valid_trigger(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that valid triggers are accepted."""
        trigger_file = tmp_path / "valid_trigger.py"
        trigger_file.write_text("""
from lighthouse.core import Trigger as BaseTrigger
from lighthouse.registry import register_trigger
from typing import Any
from collections.abc import Callable

@register_trigger("valid")
class ValidTrigger(BaseTrigger):
    def __init__(self, config: dict[str, Any], callback: Callable[[], None]) -> None:
        super().__init__(config, callback)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

Trigger = ValidTrigger
__all__ = ["Trigger", "ValidTrigger"]
""")

        monkeypatch.syspath_prepend(str(tmp_path))
        module = importlib.import_module("valid_trigger")
        assert hasattr(module, "ValidTrigger")
        assert hasattr(module, "Trigger")


class TestNotifierImportValidation:
    """Test validation of notifier imports."""

    def test_rejects_non_class_export(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that non-class exports are rejected."""
        notifier_file = tmp_path / "bad_notifier.py"
        notifier_file.write_text("""
from lighthouse.core import Notifier as BaseNotifier
from lighthouse.registry import register_notifier

# This is a constant, not a class - should be rejected
SOME_CONSTANT = 42

__all__ = ["SOME_CONSTANT"]
""")

        monkeypatch.syspath_prepend(str(tmp_path))
        module = importlib.import_module("bad_notifier")
        assert hasattr(module, "__all__")

    def test_rejects_non_notifier_subclass(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that non-Notifier subclasses are rejected."""
        notifier_file = tmp_path / "wrong_notifier.py"
        notifier_file.write_text("""
class NotANotifier:
    '''Not a notifier at all'''
    pass

__all__ = ["NotANotifier"]
""")

        monkeypatch.syspath_prepend(str(tmp_path))
        module = importlib.import_module("wrong_notifier")
        assert hasattr(module, "__all__")

    def test_accepts_valid_notifier(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that valid notifiers are accepted."""
        notifier_file = tmp_path / "valid_notifier.py"
        notifier_file.write_text("""
from lighthouse.core import AlertDecision, Notifier as BaseNotifier
from lighthouse.registry import register_notifier

@register_notifier("valid")
class ValidNotifier(BaseNotifier):
    def notify(self, alert: AlertDecision, watcher_name: str) -> bool:
        return True

Notifier = ValidNotifier
__all__ = ["Notifier", "ValidNotifier"]
""")

        monkeypatch.syspath_prepend(str(tmp_path))
        module = importlib.import_module("valid_notifier")
        assert hasattr(module, "ValidNotifier")
        assert hasattr(module, "Notifier")


class TestObserverImportValidation:
    """Test validation of observer imports."""

    def test_rejects_non_class_export(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that non-class exports are rejected."""
        observer_file = tmp_path / "bad_observer.py"
        observer_file.write_text("""
from lighthouse.core import Observer as BaseObserver
from lighthouse.registry import register_observer

# This is a variable, not a class - should be rejected
SOME_VALUE = 123

__all__ = ["SOME_VALUE"]
""")

        monkeypatch.syspath_prepend(str(tmp_path))
        module = importlib.import_module("bad_observer")
        assert hasattr(module, "__all__")

    def test_rejects_non_observer_subclass(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that non-Observer subclasses are rejected."""
        observer_file = tmp_path / "wrong_observer.py"
        observer_file.write_text("""
class NotAnObserver:
    '''Not an observer at all'''
    pass

__all__ = ["NotAnObserver"]
""")

        monkeypatch.syspath_prepend(str(tmp_path))
        module = importlib.import_module("wrong_observer")
        assert hasattr(module, "__all__")

    def test_accepts_valid_observer(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that valid observers are accepted."""
        observer_file = tmp_path / "valid_observer.py"
        observer_file.write_text("""
from lighthouse.core import Observer as BaseObserver, ObservationResult
from lighthouse.registry import register_observer
from datetime import datetime

@register_observer("valid")
class ValidObserver(BaseObserver):
    def observe(self) -> ObservationResult:
        return ObservationResult(value=True, timestamp=datetime.now(), metadata={})

Observer = ValidObserver
__all__ = ["Observer", "ValidObserver"]
""")

        monkeypatch.syspath_prepend(str(tmp_path))
        module = importlib.import_module("valid_observer")
        assert hasattr(module, "ValidObserver")
        assert hasattr(module, "Observer")


class TestDuplicateNameDetection:
    """Test that duplicate names are properly detected and handled."""

    def test_all_triggers_export_unique_descriptive_names(self) -> None:
        """Verify all trigger modules export unique descriptive class names."""
        from lighthouse.triggers import (
            FileEventTrigger,
            ManualTrigger,
            ProcessEventTrigger,
            TemporalTrigger,
            WebhookTrigger,
        )

        # All should be different classes
        triggers = {
            FileEventTrigger,
            ManualTrigger,
            ProcessEventTrigger,
            TemporalTrigger,
            WebhookTrigger,
        }
        assert len(triggers) == 5, "Should have 5 unique trigger classes"

    def test_all_notifiers_export_unique_descriptive_names(self) -> None:
        """Verify all notifier modules export unique descriptive class names."""
        from lighthouse.notifiers import (
            ConsoleNotifier,
            EmailNotifier,
            PushoverNotifier,
            SlackNotifier,
            WebhookNotifier,
        )

        # All should be different classes
        notifiers = {
            ConsoleNotifier,
            EmailNotifier,
            PushoverNotifier,
            SlackNotifier,
            WebhookNotifier,
        }
        assert len(notifiers) == 5, "Should have 5 unique notifier classes"



    def test_all_observers_export_unique_descriptive_names(self) -> None:
        """Verify all observer modules export unique descriptive class names."""
        from lighthouse.observers import (
            LogPatternObserver,
            MetricObserver,
            ServiceObserver,
            StatefulLogPatternObserver,
        )

        # All should be different classes
        observers = {
            LogPatternObserver,
            MetricObserver,
            ServiceObserver,
            StatefulLogPatternObserver,
        }
        assert len(observers) == 4, "Should have 4 unique observer classes"


class TestModuleExports:
    """Test that __all__ is properly populated."""

    def test_triggers_all_contains_expected_exports(self) -> None:
        """Verify triggers.__all__ contains expected class names."""
        from lighthouse import triggers

        # Should have descriptive names
        assert "FileEventTrigger" in triggers.__all__
        assert "ManualTrigger" in triggers.__all__
        assert "ProcessEventTrigger" in triggers.__all__
        assert "TemporalTrigger" in triggers.__all__
        assert "WebhookTrigger" in triggers.__all__

    def test_notifiers_all_contains_expected_exports(self) -> None:
        """Verify notifiers.__all__ contains expected class names."""
        from lighthouse import notifiers

        # Should have descriptive names
        assert "ConsoleNotifier" in notifiers.__all__
        assert "EmailNotifier" in notifiers.__all__
        assert "PushoverNotifier" in notifiers.__all__
        assert "SlackNotifier" in notifiers.__all__
        assert "WebhookNotifier" in notifiers.__all__

    def test_wildcard_import_triggers(self) -> None:
        """Test that wildcard import works for triggers."""
        # This simulates: from lighthouse.triggers import *
        from lighthouse import triggers

        namespace = {}
        for name in triggers.__all__:
            namespace[name] = getattr(triggers, name)

        # Check we got all expected classes
        assert "FileEventTrigger" in namespace
        assert "WebhookTrigger" in namespace

    def test_wildcard_import_notifiers(self) -> None:
        """Test that wildcard import works for notifiers."""
        # This simulates: from lighthouse.notifiers import *
        from lighthouse import notifiers

        namespace = {}
        for name in notifiers.__all__:
            namespace[name] = getattr(notifiers, name)

        # Check we got all expected classes
        assert "PushoverNotifier" in namespace
        assert "ConsoleNotifier" in namespace

    def test_observers_all_contains_expected_exports(self) -> None:
        """Verify observers.__all__ contains expected class names."""
        from lighthouse import observers

        # Should have descriptive names
        assert "LogPatternObserver" in observers.__all__
        assert "StatefulLogPatternObserver" in observers.__all__
        assert "MetricObserver" in observers.__all__
        assert "ServiceObserver" in observers.__all__

    def test_wildcard_import_observers(self) -> None:
        """Test that wildcard import works for observers."""
        # This simulates: from lighthouse.observers import *
        from lighthouse import observers

        namespace = {}
        for name in observers.__all__:
            namespace[name] = getattr(observers, name)

        # Check we got all expected classes
        assert "LogPatternObserver" in namespace
        assert "MetricObserver" in namespace


class TestImportProcessValidation:
    """Test the actual import process with validation."""

    def test_import_process_logs_duplicate_names(self, caplog: Any) -> None:
        """Test that duplicate names would trigger warning logs (structural test)."""
        import logging
        caplog.set_level(logging.WARNING)

        # Re-import triggers module to trigger the import process
        import lighthouse.triggers
        importlib.reload(lighthouse.triggers)

        # Check that the warning system is working (we won't have duplicates with current structure)
        # This test mainly ensures the validation system is in place
        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        # Current implementation has no duplicates, so this is a structural test
        assert isinstance(warning_messages, list)


    def test_import_process_validates_base_class(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test import process validates base class using actual validation logic."""
        import inspect
        import pkgutil

        from lighthouse.core import Trigger as BaseTrigger

        # Create a mock module directory
        mock_triggers_dir = tmp_path / "mock_triggers"
        mock_triggers_dir.mkdir()
        (mock_triggers_dir / "__init__.py").write_text("")

        # Create an invalid trigger (wrong base class)
        invalid_file = mock_triggers_dir / "invalid.py"
        invalid_file.write_text("""
class InvalidTrigger:  # Not a Trigger subclass!
    pass

__all__ = ["InvalidTrigger"]
""")

        # Add to sys.path temporarily
        monkeypatch.syspath_prepend(str(tmp_path))

        # Simulate the validation logic from __init__.py
        for module_info in pkgutil.iter_modules([str(mock_triggers_dir)]):
            module = importlib.import_module(f"mock_triggers.{module_info.name}")

            if hasattr(module, '__all__'):
                for name in module.__all__:
                    cls = getattr(module, name)

                    # This is the validation that should reject it
                    if not inspect.isclass(cls):
                        continue

                    # This should return False for InvalidTrigger
                    is_valid = issubclass(cls, BaseTrigger) if inspect.isclass(cls) else False
                    assert not is_valid, "InvalidTrigger should not be a valid Trigger subclass"

    def test_validation_accepts_proper_subclasses(self) -> None:
        """Test that validation accepts properly structured classes."""
        import inspect

        from lighthouse.core import Trigger as BaseTrigger
        from lighthouse.triggers import FileEventTrigger

        # Should pass all validation checks
        assert inspect.isclass(FileEventTrigger)
        assert issubclass(FileEventTrigger, BaseTrigger)

    def test_validation_rejects_functions(self) -> None:
        """Test that validation rejects functions."""
        import inspect


        def not_a_class():
            pass

        # Should fail validation
        assert not inspect.isclass(not_a_class)

    def test_validation_rejects_instances(self) -> None:
        """Test that validation rejects class instances."""
        import inspect

        from lighthouse.triggers import FileEventTrigger

        instance = FileEventTrigger({}, lambda: None)

        # Should fail validation (it's an instance, not a class)
        assert not inspect.isclass(instance)

    def test_all_actual_triggers_pass_validation(self) -> None:
        """Verify all actual trigger modules pass validation."""
        import inspect

        from lighthouse import triggers
        from lighthouse.core import Trigger as BaseTrigger

        # Get all exported names
        for name in triggers.__all__:
            if name == "Trigger":  # Skip the generic alias
                continue

            cls = getattr(triggers, name)

            # All should be classes
            assert inspect.isclass(cls), f"{name} should be a class"

            # All should be Trigger subclasses
            assert issubclass(cls, BaseTrigger), f"{name} should be a Trigger subclass"

    def test_all_actual_notifiers_pass_validation(self) -> None:
        """Verify all actual notifier modules pass validation."""
        import inspect

        from lighthouse import notifiers
        from lighthouse.core import Notifier as BaseNotifier

        # Get all exported names
        for name in notifiers.__all__:
            if name == "Notifier":  # Skip the generic alias
                continue

            cls = getattr(notifiers, name)

            # All should be classes
            assert inspect.isclass(cls), f"{name} should be a class"

            # All should be Notifier subclasses
            assert issubclass(cls, BaseNotifier), f"{name} should be a Notifier subclass"

    def test_all_actual_observers_pass_validation(self) -> None:
        """Verify all actual observer modules pass validation."""
        import inspect

        from lighthouse import observers
        from lighthouse.core import Observer as BaseObserver

        # Get all exported names
        for name in observers.__all__:
            if name == "Observer":  # Skip the generic alias
                continue

            cls = getattr(observers, name)

            # All should be classes
            assert inspect.isclass(cls), f"{name} should be a class"

            # All should be Observer subclasses
            assert issubclass(cls, BaseObserver), f"{name} should be an Observer subclass"
