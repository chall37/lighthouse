"""
Console notifier for Lighthouse.
"""

from lighthouse.core import AlertDecision, Notifier
from lighthouse.logging_config import get_logger
from lighthouse.registry import register_notifier

logger = get_logger(__name__)


@register_notifier("console")
class ConsoleNotifier(Notifier):
    """
    Prints notifications to console/stdout.

    Useful for testing and debugging.

    Config:
        (none required)
    """

    def notify(self, alert: AlertDecision, watcher_name: str) -> bool:
        """Print notification to console."""
        logger.info("Console alert for watcher '%s': {alert.message}", watcher_name)

        print(f"\n{'=' * 60}")
        print(f"ALERT: {watcher_name}")
        print(f"Severity: {alert.severity}")
        print(f"Message: {alert.message}")
        if alert.context:
            print("\nContext:")
            for key, value in alert.context.items():
                print(f"  {key}: {value}")
        print(f"{'=' * 60}\n")
        return True


# Export for dynamic importing
__all__ = ["ConsoleNotifier"]

