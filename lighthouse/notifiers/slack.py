"""
Slack notifier for Lighthouse (placeholder).
"""

from lighthouse.core import AlertDecision, Notifier
from lighthouse.registry import register_notifier


@register_notifier("slack")
class SlackNotifier(Notifier):
    """
    Sends notifications to Slack via webhook.

    TODO: Implement Slack formatting

    Config:
        webhook_url: Slack webhook URL
        channel: Optional channel override
        username: Optional bot username
    """

    def notify(self, alert: AlertDecision, watcher_name: str) -> bool:
        """Send notification to Slack (not yet implemented)."""
        raise NotImplementedError("Slack notifications not yet implemented")


# Export for dynamic importing
__all__ = ["SlackNotifier"]

