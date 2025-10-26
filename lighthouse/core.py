"""
Core interfaces and data structures for Lighthouse monitoring system.

This module defines the plugin architecture with four main categories:
- Observers: What to measure
- Triggers: When to check
- Evaluators: Should we alert
- Notifiers: How to alert
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ObservationResult:
    """Result from an observer."""
    value: Any  # The observed value (could be bool, int, str, dict, etc.)
    timestamp: datetime
    metadata: dict[str, Any]  # Additional context about the observation


@dataclass
class AlertDecision:
    """Decision from an evaluator about whether to alert."""
    should_alert: bool
    severity: str  # "low", "medium", "high", "critical"
    message: str
    context: dict[str, Any]  # Additional context for the alert


class Observer(ABC):
    """
    Base class for all observers.

    Observers extract data from the system to be evaluated.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the observer with configuration.

        Args:
            config: Type-specific configuration dictionary
        """
        self.config = config

    @abstractmethod
    def observe(self) -> ObservationResult:
        """
        Perform an observation and return the result.

        Returns:
            ObservationResult containing the observed value and metadata
        """
        raise NotImplementedError


class Trigger(ABC):
    """
    Base class for all triggers.

    Triggers determine when to run observers.
    """

    def __init__(self, config: dict[str, Any], callback: Callable[[], None]):
        """
        Initialize the trigger with configuration and callback.

        Args:
            config: Type-specific configuration dictionary
            callback: Function to call when trigger fires
        """
        self.config = config
        self.callback = callback

    @abstractmethod
    def start(self) -> None:
        """Start listening for trigger events."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stop listening for trigger events."""
        raise NotImplementedError


class Evaluator(ABC):
    """
    Base class for all evaluators.

    Evaluators decide whether an observation warrants an alert.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the evaluator with configuration.

        Args:
            config: Type-specific configuration dictionary
        """
        self.config = config

    @abstractmethod
    def evaluate(
        self,
        current: ObservationResult,
        history: list[ObservationResult]
    ) -> AlertDecision:
        """
        Evaluate whether to alert based on current and historical observations.

        Args:
            current: The current observation
            history: Previous observations (may be empty)

        Returns:
            AlertDecision indicating whether to alert and with what message
        """
        raise NotImplementedError


class Notifier(ABC):
    """
    Base class for all notifiers.

    Notifiers send alerts to external destinations.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the notifier with configuration.

        Args:
            config: Type-specific configuration dictionary
        """
        self.config = config

    @abstractmethod
    def notify(self, alert: AlertDecision, watcher_name: str) -> bool:
        """
        Send a notification about an alert.

        Args:
            alert: The alert decision to notify about
            watcher_name: Name of the watcher that triggered the alert

        Returns:
            True if notification was sent successfully, False otherwise
        """
        raise NotImplementedError
