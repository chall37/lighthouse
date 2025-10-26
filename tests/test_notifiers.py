"""
Tests for notifier implementations.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from lighthouse.core import AlertDecision
from lighthouse.notifiers import (
    ConsoleNotifier,
    EmailNotifier,
    PushoverNotifier,
    SlackNotifier,
    WebhookNotifier,
)


class TestPushoverNotifier:
    """Tests for PushoverNotifier."""

    def test_notify_success(self) -> None:
        """Test successful Pushover notification."""
        notifier = PushoverNotifier({
            "user_key": "test_user",
            "api_token": "test_token"
        })

        alert = AlertDecision(
            should_alert=True,
            severity="medium",
            message="Test alert",
            context={"details": "Test details"}
        )

        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = notifier.notify(alert, "test_watcher")

            assert result is True
            mock_post.assert_called_once()

            # Verify payload
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://api.pushover.net/1/messages.json"
            payload = call_args[1]["data"]
            assert payload["user"] == "test_user"
            assert payload["token"] == "test_token"
            assert "test_watcher" in payload["title"]
            assert "Test alert" in payload["message"]

    def test_notify_with_priority_mapping(self) -> None:
        """Test priority mapping from severity levels."""
        notifier = PushoverNotifier({
            "user_key": "test_user",
            "api_token": "test_token"
        })

        severities_to_priorities = {
            "low": -1,
            "medium": 0,
            "high": 1,
            "critical": 2
        }

        for severity, expected_priority in severities_to_priorities.items():
            alert = AlertDecision(
                should_alert=True,
                severity=severity,
                message="Test",
                context={}
            )

            with patch('requests.post') as mock_post:
                mock_response = MagicMock()
                mock_response.raise_for_status = MagicMock()
                mock_post.return_value = mock_response

                notifier.notify(alert, "test")

                payload = mock_post.call_args[1]["data"]
                assert payload["priority"] == expected_priority

    def test_notify_includes_context(self) -> None:
        """Test that context is included in notification message."""
        notifier = PushoverNotifier({
            "user_key": "test_user",
            "api_token": "test_token"
        })

        alert = AlertDecision(
            should_alert=True,
            severity="high",
            message="Error occurred",
            context={
                "error_count": 5,
                "service": "backup"
            }
        )

        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            notifier.notify(alert, "backup_watcher")

            payload = mock_post.call_args[1]["data"]
            message = payload["message"]
            assert "Error occurred" in message
            assert "error_count: 5" in message
            assert "service: backup" in message

    def test_notify_handles_request_failure(self) -> None:
        """Test handling of request failures."""
        notifier = PushoverNotifier({
            "user_key": "test_user",
            "api_token": "test_token"
        })

        alert = AlertDecision(
            should_alert=True,
            severity="medium",
            message="Test",
            context={}
        )

        with patch('requests.post', side_effect=requests.RequestException("Network error")):
            result = notifier.notify(alert, "test")

            assert result is False

    def test_notify_handles_http_error(self) -> None:
        """Test handling of HTTP errors."""
        notifier = PushoverNotifier({
            "user_key": "test_user",
            "api_token": "test_token"
        })

        alert = AlertDecision(
            should_alert=True,
            severity="medium",
            message="Test",
            context={}
        )

        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = requests.HTTPError("400 Bad Request")
            mock_post.return_value = mock_response

            result = notifier.notify(alert, "test")

            assert result is False


class TestWebhookNotifier:
    """Tests for WebhookNotifier."""

    def test_notify_post_success(self) -> None:
        """Test successful webhook POST."""
        notifier = WebhookNotifier({
            "url": "https://example.com/webhook"
        })

        alert = AlertDecision(
            should_alert=True,
            severity="high",
            message="Alert message",
            context={"key": "value"}
        )

        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = notifier.notify(alert, "webhook_test")

            assert result is True
            mock_post.assert_called_once()

            # Verify payload structure
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://example.com/webhook"
            payload = call_args[1]["json"]
            assert payload["watcher"] == "webhook_test"
            assert payload["severity"] == "high"
            assert payload["message"] == "Alert message"
            assert payload["context"]["key"] == "value"

    def test_notify_put_method(self) -> None:
        """Test webhook with PUT method."""
        notifier = WebhookNotifier({
            "url": "https://example.com/webhook",
            "method": "PUT"
        })

        alert = AlertDecision(
            should_alert=True,
            severity="medium",
            message="Test",
            context={}
        )

        with patch('requests.put') as mock_put:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_put.return_value = mock_response

            result = notifier.notify(alert, "test")

            assert result is True
            mock_put.assert_called_once()

    def test_notify_with_custom_headers(self) -> None:
        """Test webhook with custom headers."""
        notifier = WebhookNotifier({
            "url": "https://example.com/webhook",
            "headers": {
                "Authorization": "Bearer token123",
                "X-Custom": "value"
            }
        })

        alert = AlertDecision(
            should_alert=True,
            severity="medium",
            message="Test",
            context={}
        )

        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            notifier.notify(alert, "test")

            headers = mock_post.call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer token123"
            assert headers["X-Custom"] == "value"

    def test_notify_handles_request_failure(self) -> None:
        """Test handling of request failures."""
        notifier = WebhookNotifier({
            "url": "https://example.com/webhook"
        })

        alert = AlertDecision(
            should_alert=True,
            severity="medium",
            message="Test",
            context={}
        )

        with patch('requests.post', side_effect=requests.RequestException("Connection error")):
            result = notifier.notify(alert, "test")

            assert result is False

    def test_notify_unsupported_method(self) -> None:
        """Test that unsupported HTTP methods raise ValueError."""
        notifier = WebhookNotifier({
            "url": "https://example.com/webhook",
            "method": "DELETE"
        })

        alert = AlertDecision(
            should_alert=True,
            severity="medium",
            message="Test",
            context={}
        )

        with pytest.raises(ValueError, match="Unsupported HTTP method: DELETE"):
            notifier.notify(alert, "test")


class TestConsoleNotifier:
    """Tests for ConsoleNotifier."""

    def test_notify_prints_alert(self, capsys: Any) -> None:
        """Test that console notifier prints alert details."""
        notifier = ConsoleNotifier({})

        alert = AlertDecision(
            should_alert=True,
            severity="high",
            message="Critical error occurred",
            context={"error_code": 500}
        )

        result = notifier.notify(alert, "critical_watcher")

        assert result is True

        # Check output
        captured = capsys.readouterr()
        assert "ALERT: critical_watcher" in captured.out
        assert "Severity: high" in captured.out
        assert "Message: Critical error occurred" in captured.out
        assert "error_code: 500" in captured.out

    def test_notify_without_context(self, capsys: Any) -> None:
        """Test console notifier with no context."""
        notifier = ConsoleNotifier({})

        alert = AlertDecision(
            should_alert=True,
            severity="low",
            message="Simple alert",
            context={}
        )

        result = notifier.notify(alert, "simple_watcher")

        assert result is True

        captured = capsys.readouterr()
        assert "Simple alert" in captured.out
        assert "Severity: low" in captured.out

    def test_notify_always_succeeds(self) -> None:
        """Test that console notifier always returns True."""
        notifier = ConsoleNotifier({})

        alert = AlertDecision(
            should_alert=True,
            severity="medium",
            message="Test",
            context={}
        )

        # Should never fail
        for _ in range(5):
            result = notifier.notify(alert, "test")
            assert result is True


class TestEmailNotifier:
    """Tests for EmailNotifier (not yet implemented)."""

    def test_email_raises_not_implemented(self) -> None:
        """Test that email notifier raises NotImplementedError."""
        notifier = EmailNotifier({
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "from_addr": "lighthouse@example.com",
            "to_addr": "admin@example.com"
        })

        alert = AlertDecision(
            should_alert=True,
            severity="medium",
            message="Test",
            context={}
        )

        with pytest.raises(NotImplementedError, match="Email notifications not yet implemented"):
            notifier.notify(alert, "test")


class TestSlackNotifier:
    """Tests for SlackNotifier (not yet implemented)."""

    def test_slack_raises_not_implemented(self) -> None:
        """Test that Slack notifier raises NotImplementedError."""
        notifier = SlackNotifier({
            "webhook_url": "https://hooks.slack.com/services/XXX/YYY/ZZZ"
        })

        alert = AlertDecision(
            should_alert=True,
            severity="medium",
            message="Test",
            context={}
        )

        with pytest.raises(NotImplementedError, match="Slack notifications not yet implemented"):
            notifier.notify(alert, "test")
