"""
Temporal (scheduled/interval-based) trigger.
"""

import threading
from collections.abc import Callable
from typing import Any

from lighthouse.core import Trigger as BaseTrigger
from lighthouse.registry import register_trigger


@register_trigger("temporal")
class Trigger(BaseTrigger):
    """
    Triggers on a schedule (cron-like).

    Config:
        interval_seconds: How often to trigger (simple interval for now)

    TODO: Add cron expression support
    """

    def __init__(self, config: dict[str, Any], callback: Callable[[], None]) -> None:
        super().__init__(config, callback)
        self.thread: threading.Thread | None = None
        self.stop_event: threading.Event = threading.Event()

    def start(self) -> None:
        """Start the scheduled trigger."""
        interval = self.config["interval_seconds"]

        def run() -> None:
            while not self.stop_event.is_set():
                self.callback()
                self.stop_event.wait(interval)

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop the scheduled trigger."""
        if self.thread:
            self.stop_event.set()
            self.thread.join(timeout=5)


# Export with descriptive name for imports
TemporalTrigger = Trigger
__all__ = ["TemporalTrigger"]
