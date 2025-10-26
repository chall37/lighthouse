"""
Live integration tests for Pushover notifications.

These tests require real Pushover API credentials set in environment variables:
- PUSHOVER_USER_KEY
- PUSHOVER_API_TOKEN

Tests will be skipped if credentials are not provided.
"""

import os

import pytest

from lighthouse.core import AlertDecision
from lighthouse.notifiers import PushoverNotifier

# Check if Pushover credentials are available
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")

skip_if_no_credentials = pytest.mark.skipif(
    not PUSHOVER_USER_KEY or not PUSHOVER_API_TOKEN,
    reason="Pushover credentials not set (PUSHOVER_USER_KEY, PUSHOVER_API_TOKEN)"
)


@skip_if_no_credentials
class TestPushoverLive:
    """Live tests for Pushover notifier (requires API credentials)."""

    def test_send_basic_notification(self) -> None:
        """Test sending a basic notification."""
        notifier = PushoverNotifier({
            "user_key": PUSHOVER_USER_KEY,
            "api_token": PUSHOVER_API_TOKEN
        })

        alert = AlertDecision(
            should_alert=True,
            severity="low",
            message="Test notification from Lighthouse test suite",
            context={"test": "basic_notification"}
        )

        result = notifier.notify(alert, "Live Test")

        assert result is True, "Notification should be sent successfully"

    def test_send_with_different_priorities(self) -> None:
        """Test sending notifications with different severity levels."""
        notifier = PushoverNotifier({
            "user_key": PUSHOVER_USER_KEY,
            "api_token": PUSHOVER_API_TOKEN
        })

        severities = ["low", "medium", "high", "critical"]

        for severity in severities:
            alert = AlertDecision(
                should_alert=True,
                severity=severity,
                message=f"Test {severity} priority notification",
                context={"severity_test": severity}
            )

            result = notifier.notify(alert, f"Priority Test ({severity})")
            assert result is True, f"Should send {severity} notification"

    def test_send_with_rich_context(self) -> None:
        """Test sending notification with rich context information."""
        notifier = PushoverNotifier({
            "user_key": PUSHOVER_USER_KEY,
            "api_token": PUSHOVER_API_TOKEN
        })

        alert = AlertDecision(
            should_alert=True,
            severity="medium",
            message="Error detected in backup process",
            context={
                "error_count": 5,
                "service": "backup",
                "host": "server-01",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        )

        result = notifier.notify(alert, "Backup Monitor")

        assert result is True, "Rich context notification should be sent"
