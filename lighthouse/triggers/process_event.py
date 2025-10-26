"""
Process event trigger (placeholder - not yet implemented).
"""

from collections.abc import Callable
from typing import Any

from lighthouse.core import Trigger as BaseTrigger
from lighthouse.registry import register_trigger


@register_trigger("process_event")
class Trigger(BaseTrigger):
    """
    Triggers on process start/stop/exit events.

    TODO: Implement process monitoring

    Config:
        process_name: Name of process to monitor
        events: List of events ("start", "stop", "exit")
    """

    def __init__(self, config: dict[str, Any], callback: Callable[[], None]) -> None:
        super().__init__(config, callback)

    def start(self) -> None:
        """Start monitoring process (not yet implemented)."""
        raise NotImplementedError("Process event triggers not yet implemented")

    def stop(self) -> None:
        """Stop monitoring process."""
        raise NotImplementedError("Process event triggers not yet implemented")


# Export with descriptive name for imports
ProcessEventTrigger = Trigger
__all__ = ["ProcessEventTrigger"]
