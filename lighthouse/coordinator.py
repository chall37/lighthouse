"""
Watcher coordinator that wires together observers, triggers, and evaluators.
"""

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from lighthouse.config import WatcherConfig
from lighthouse.core import AlertDecision, Evaluator, ObservationResult, Observer, Trigger
from lighthouse.logging_config import get_logger
from lighthouse.plugins import create_evaluator, create_observer, create_trigger

logger = get_logger(__name__)


class WatcherCoordinator:
    """
    Coordinates a single watcher's observer, trigger, and evaluator.

    This class wires together the three components and manages observation history.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        name: str,
        observer: Observer,
        trigger: Trigger | None,
        evaluator: Evaluator,
        state_dir: str,
        priority: int | None = None
    ):
        """
        Initialize the coordinator.

        Args:
            name: Watcher name
            observer: Observer instance
            trigger: Trigger instance
            evaluator: Evaluator instance
            state_dir: Directory for storing observation history
            priority: Optional priority level
        """
        self.name = name
        self.observer = observer
        self.trigger = trigger
        self.evaluator = evaluator
        self.state_dir = Path(state_dir)
        self.priority = priority
        self.history: list[ObservationResult] = []
        self._load_history()

    def _load_history(self) -> None:
        """Load observation history from disk."""
        history_file = self.state_dir / f"{self.name}.history.json"
        if not history_file.exists():
            logger.debug("No history file found for watcher '%s'", self.name)
            return

        try:
            with open(history_file, encoding='utf-8') as f:
                data = json.load(f)

            # Reconstruct ObservationResult objects from JSON
            self.history = [
                ObservationResult(
                    value=item['value'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    metadata=item['metadata']
                )
                for item in data
            ]
            logger.debug(
                "Loaded %s observation(s) from history for watcher '%s'",
                len(self.history),
                self.name
            )
        except Exception:
            logger.warning("Failed to load history for watcher '%s'", self.name, exc_info=True)
            self.history = []

    def _save_history(self) -> None:
        """Save observation history to disk."""
        # Create state directory if it doesn't exist
        self.state_dir.mkdir(parents=True, exist_ok=True)

        history_file = self.state_dir / f"{self.name}.history.json"

        # Keep only last 100 observations to prevent unbounded growth
        recent_history = self.history[-100:]

        # Serialize to JSON
        data = [
            {
                'value': item.value,
                'timestamp': item.timestamp.isoformat(),
                'metadata': item.metadata
            }
            for item in recent_history
        ]

        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            logger.warning("Failed to save history for watcher '%s'", self.name, exc_info=True)

    def check(self) -> AlertDecision | None:
        """
        Run one check cycle: observe → evaluate → decide.

        Returns:
            AlertDecision if evaluation determines an alert should be sent,
            None otherwise
        """
        # Observe
        observation = self.observer.observe()

        # Evaluate
        decision = self.evaluator.evaluate(observation, self.history)

        # Update history
        self.history.append(observation)
        self._save_history()

        # Return decision if we should alert
        if decision.should_alert:
            return decision
        return None

    def start(self) -> None:
        """Start the trigger."""
        if self.trigger:
            self.trigger.start()

    def stop(self) -> None:
        """Stop the trigger."""
        if self.trigger:
            self.trigger.stop()


def create_watcher_coordinator(
    watcher_config: WatcherConfig,
    state_dir: str,
    on_alert: Callable[[str, AlertDecision, int | None], None],
) -> WatcherCoordinator:
    """
    Factory function to create a watcher coordinator from configuration.

    Args:
        watcher_config: The configuration object for the watcher.
        state_dir: Directory for state storage
        on_alert: Callback to invoke when alert decision is made

    Returns:
        WatcherCoordinator instance
    """
    # Add watcher-specific info to the observer's config
    watcher_config.observer.config['name'] = watcher_config.name
    watcher_config.observer.config['state_dir'] = state_dir

    # Create components
    observer = create_observer(
        watcher_config.observer.type, watcher_config.observer.config
    )

    evaluator = create_evaluator(
        watcher_config.evaluator.type, watcher_config.evaluator.config
    )

    # Create the coordinator instance that will be used by the trigger
    coordinator = WatcherCoordinator(
        name=watcher_config.name,
        observer=observer,
        trigger=None,  # Trigger will be set later
        evaluator=evaluator,
        state_dir=state_dir,
        priority=watcher_config.priority,
    )

    # Define the callback for the trigger
    def trigger_callback() -> None:
        decision = coordinator.check()
        if decision:
            on_alert(watcher_config.name, decision, watcher_config.priority)

    # Create the trigger with the callback
    trigger = create_trigger(
        watcher_config.trigger.type,
        watcher_config.trigger.config,
        trigger_callback
    )

    # Assign the trigger to the coordinator
    coordinator.trigger = trigger

    return coordinator
