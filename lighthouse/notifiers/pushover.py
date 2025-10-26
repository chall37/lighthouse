"""
Pushover notifier for Lighthouse.
"""

from typing import ClassVar

import requests

from lighthouse.core import AlertDecision, Notifier
from lighthouse.logging_config import get_logger
from lighthouse.registry import register_notifier

logger = get_logger(__name__)


@register_notifier("pushover")
class PushoverNotifier(Notifier):
    """
    Sends notifications via Pushover API.

    Config:
        user_key: Pushover user key
        api_token: Pushover API token
        priority: Default priority (can be overridden by alert severity)
    """

    PUSHOVER_API_URL: ClassVar[str] = "https://api.pushover.net/1/messages.json"

    SEVERITY_TO_PRIORITY: ClassVar[dict[str, int]] = {
        "low": -1,
        "medium": 0,
        "high": 1,
        "critical": 2,
    }

    def notify(self, alert: AlertDecision, watcher_name: str) -> bool:
        """Send notification via Pushover."""
        user_key = self.config["user_key"]
        api_token = self.config["api_token"]
        default_priority = self.config.get("priority", 0)

        # Map severity to Pushover priority
        priority = self.SEVERITY_TO_PRIORITY.get(alert.severity, default_priority)

        # Build notification message
        title = f"Lighthouse: {watcher_name}"
        message = alert.message

        # Add context as additional details
        if alert.context:
            details = "\n\n".join([f"{k}: {v}" for k, v in alert.context.items()])
            message = f"{message}\n\n{details}"

        # Send to Pushover
        payload = {
            "token": api_token,
            "user": user_key,
            "title": title,
            "message": message,
            "priority": priority,
        }

        # Priority 2 (emergency) requires retry and expire parameters
        if priority == 2:
            payload["retry"] = 30  # Retry every 30 seconds
            payload["expire"] = 3600  # Give up after 1 hour

        try:
            response = requests.post(
                self.PUSHOVER_API_URL,
                data=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info("Pushover notification sent successfully for watcher '%s'", watcher_name)
            return True
        except requests.RequestException:
            logger.error(
                "Failed to send Pushover notification for watcher '%s'",
                watcher_name,
                exc_info=True
            )
            return False


# Export for dynamic importing
__all__ = ["PushoverNotifier"]

