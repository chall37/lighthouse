"""
Email notifier for Lighthouse (placeholder).
"""

from lighthouse.core import AlertDecision, Notifier
from lighthouse.registry import register_notifier


@register_notifier("email")
class EmailNotifier(Notifier):
    """
    Sends notifications via email.

    TODO: Implement email sending

    Config:
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port
        from_addr: Sender email address
        to_addr: Recipient email address
        username: SMTP username (optional)
        password: SMTP password (optional)
    """

    def notify(self, alert: AlertDecision, watcher_name: str) -> bool:
        """Send notification via email (not yet implemented)."""
        raise NotImplementedError("Email notifications not yet implemented")


# Export for dynamic importing
__all__ = ["EmailNotifier"]

