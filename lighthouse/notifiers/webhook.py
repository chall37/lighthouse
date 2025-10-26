"""
Webhook notifier for Lighthouse.
"""

import requests

from lighthouse.core import AlertDecision, Notifier
from lighthouse.logging_config import get_logger
from lighthouse.registry import register_notifier

logger = get_logger(__name__)


@register_notifier("webhook")
class WebhookNotifier(Notifier):
    """
    Sends notifications via HTTP webhook.

    Config:
        url: Webhook URL to POST to
        method: HTTP method (default: POST)
        headers: Optional HTTP headers
        auth: Optional authentication config
    """

    def notify(self, alert: AlertDecision, watcher_name: str) -> bool:
        """Send notification via webhook."""
        url = self.config["url"]
        method = self.config.get("method", "POST").upper()
        headers = self.config.get("headers", {})

        # Build payload
        payload = {
            "watcher": watcher_name,
            "severity": alert.severity,
            "message": alert.message,
            "context": alert.context,
            "timestamp": alert.context.get("timestamp"),  # If available
        }

        try:
            if method == "POST":
                response = requests.post(url, json=payload, headers=headers, timeout=10)
            elif method == "PUT":
                response = requests.put(url, json=payload, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            logger.info(
                "Webhook notification sent successfully for watcher '%s' to %s",
                watcher_name,
                url
            )
            return True
        except requests.RequestException:
            logger.error(
                "Failed to send webhook notification for watcher '%s'",
                watcher_name,
                exc_info=True
            )
            return False


# Export for dynamic importing
__all__ = ["WebhookNotifier"]

