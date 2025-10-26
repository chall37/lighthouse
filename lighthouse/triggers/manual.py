"""
Manual trigger for CLI-triggered checks.
"""

from collections.abc import Callable
from typing import Any

from lighthouse.core import Trigger as BaseTrigger
from lighthouse.registry import register_trigger


@register_trigger("manual")
class Trigger(BaseTrigger):
    """
    Trigger that must be explicitly called.

    This is useful for CLI-triggered checks or external integrations.
    """

    def __init__(self, config: dict[str, Any], callback: Callable[[], None]) -> None:
        super().__init__(config, callback)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def trigger(self) -> None:
        """Manually trigger the callback."""
        self.callback()


# Export with descriptive name for imports
ManualTrigger = Trigger
__all__ = ["ManualTrigger"]
