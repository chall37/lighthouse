"""
Tests for trigger implementations.
"""

import time
from datetime import UTC
from pathlib import Path
from threading import Event

import pytest

from lighthouse.triggers import (
    FileEventTrigger,
    ManualTrigger,
    ProcessEventTrigger,
    TemporalTrigger,
    WebhookTrigger,
)


class TestFileEventTrigger:
    """Tests for FileEventTrigger."""

    def test_trigger_on_file_modified(self, tmp_path: Path) -> None:
        """Test triggering when a file is modified."""
        test_file = tmp_path / "test.log"
        test_file.write_text("initial content\n")

        triggered = Event()

        def callback() -> None:
            triggered.set()

        trigger = FileEventTrigger(
            {"path": str(test_file), "events": ["modified"]},
            callback
        )

        trigger.start()
        time.sleep(0.1)  # Let watchdog initialize

        # Modify the file
        test_file.write_text("modified content\n")

        # Wait for trigger
        assert triggered.wait(timeout=2), "Trigger should fire on file modification"

        trigger.stop()

    def test_trigger_on_file_created(self, tmp_path: Path) -> None:
        """Test triggering when a file is created."""
        test_file = tmp_path / "new_file.log"

        triggered = Event()

        def callback() -> None:
            triggered.set()

        trigger = FileEventTrigger(
            {"path": str(tmp_path), "events": ["created"], "recursive": False},
            callback
        )

        trigger.start()
        time.sleep(0.1)

        # Create a new file
        test_file.write_text("new content\n")

        assert triggered.wait(timeout=2), "Trigger should fire on file creation"

        trigger.stop()

    def test_trigger_on_file_deleted(self, tmp_path: Path) -> None:
        """Test triggering when a file is deleted."""
        test_file = tmp_path / "to_delete.log"
        test_file.write_text("content\n")

        triggered = Event()

        def callback() -> None:
            triggered.set()

        trigger = FileEventTrigger(
            {"path": str(tmp_path), "events": ["deleted"], "recursive": False},
            callback
        )

        trigger.start()
        time.sleep(0.1)

        # Delete the file
        test_file.unlink()

        assert triggered.wait(timeout=2), "Trigger should fire on file deletion"

        trigger.stop()

    def test_trigger_multiple_events(self, tmp_path: Path) -> None:
        """Test triggering on multiple event types."""
        test_file = tmp_path / "multi.log"
        test_file.write_text("initial\n")

        trigger_count = {"count": 0}

        def callback() -> None:
            trigger_count["count"] += 1

        trigger = FileEventTrigger(
            {"path": str(test_file), "events": ["modified", "deleted"]},
            callback
        )

        trigger.start()
        time.sleep(0.1)

        # Modify file
        test_file.write_text("modified\n")
        time.sleep(0.2)

        # Delete file
        test_file.unlink()
        time.sleep(0.2)

        trigger.stop()

        assert trigger_count["count"] >= 2, "Should trigger on both modification and deletion"

    def test_trigger_recursive_directory(self, tmp_path: Path) -> None:
        """Test recursive directory watching."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        triggered = Event()

        def callback() -> None:
            triggered.set()

        trigger = FileEventTrigger(
            {"path": str(tmp_path), "events": ["created"], "recursive": True},
            callback
        )

        trigger.start()
        time.sleep(0.1)

        # Create file in subdirectory
        test_file = subdir / "deep.log"
        test_file.write_text("deep content\n")

        assert triggered.wait(timeout=2), "Should trigger on file creation in subdirectory"

        trigger.stop()

    def test_trigger_non_recursive_config(self, tmp_path: Path) -> None:
        """Test non-recursive configuration is accepted."""
        triggered = Event()

        def callback() -> None:
            triggered.set()

        trigger = FileEventTrigger(
            {"path": str(tmp_path), "events": ["created"], "recursive": False},
            callback
        )

        trigger.start()
        time.sleep(0.1)

        # Create file in main directory (should trigger)
        test_file = tmp_path / "file.log"
        test_file.write_text("content\n")

        assert triggered.wait(timeout=1), "Should trigger on file creation in watched directory"

        trigger.stop()

    def test_stop_cleans_up_observer(self, tmp_path: Path) -> None:
        """Test that stopping the trigger cleans up the observer."""
        test_file = tmp_path / "test.log"
        test_file.write_text("initial\n")

        triggered = Event()

        def callback() -> None:
            triggered.set()

        trigger = FileEventTrigger(
            {"path": str(test_file), "events": ["modified"]},
            callback
        )

        trigger.start()
        assert trigger.observer is not None, "Observer should be created on start"

        time.sleep(0.1)

        # Verify it can trigger
        test_file.write_text("modification\n")
        assert triggered.wait(timeout=1), "Should trigger before stop"

        # Stop the trigger
        trigger.stop()

        # Observer should be stopped (we can't easily test no further triggers
        # due to race conditions with watchdog cleanup)


class TestTemporalTrigger:
    """Tests for TemporalTrigger."""

    def test_trigger_on_interval(self) -> None:
        """Test triggering at regular intervals."""
        trigger_times: list[float] = []

        def callback() -> None:
            trigger_times.append(time.time())

        trigger = TemporalTrigger(
            {"interval_seconds": 0.2},
            callback
        )

        trigger.start()
        time.sleep(0.7)  # Should get ~3 triggers
        trigger.stop()

        assert len(trigger_times) >= 3, f"Should trigger at least 3 times, got {len(trigger_times)}"

        # Check intervals are roughly correct
        if len(trigger_times) >= 2:
            intervals = [trigger_times[i+1] - trigger_times[i] for i in range(len(trigger_times)-1)]
            for interval in intervals:
                assert 0.15 <= interval <= 0.35, f"Interval should be ~0.2s, got {interval}"

    def test_stop_prevents_further_triggers(self) -> None:
        """Test that stopping prevents further triggers."""
        trigger_count = {"count": 0}

        def callback() -> None:
            trigger_count["count"] += 1

        trigger = TemporalTrigger(
            {"interval_seconds": 0.1},
            callback
        )

        trigger.start()
        time.sleep(0.35)  # Should get ~3 triggers
        trigger.stop()

        # Record count after stopping
        count_at_stop = trigger_count["count"]
        assert count_at_stop >= 3, "Should have triggered at least 3 times"

        # Wait and verify no more triggers
        time.sleep(0.3)
        assert trigger_count["count"] == count_at_stop, "Should not trigger after stop()"

    def test_immediate_trigger_on_start(self) -> None:
        """Test that trigger fires immediately on start."""
        triggered = Event()

        def callback() -> None:
            triggered.set()

        trigger = TemporalTrigger(
            {"interval_seconds": 10},  # Long interval
            callback
        )

        trigger.start()

        # Should trigger immediately
        assert triggered.wait(timeout=1), "Should trigger immediately on start"

        trigger.stop()


class TestManualTrigger:
    """Tests for ManualTrigger."""

    def test_manual_trigger_fires_callback(self) -> None:
        """Test that manually calling trigger() fires the callback."""
        triggered = Event()

        def callback() -> None:
            triggered.set()

        trigger = ManualTrigger({}, callback)

        # Start does nothing
        trigger.start()

        # Should not have triggered yet
        assert not triggered.is_set()

        # Manually trigger
        trigger.trigger()

        assert triggered.is_set(), "Should trigger when trigger() is called"

        trigger.stop()

    def test_manual_trigger_multiple_calls(self) -> None:
        """Test that manual trigger can be called multiple times."""
        trigger_count = {"count": 0}

        def callback() -> None:
            trigger_count["count"] += 1

        trigger = ManualTrigger({}, callback)
        trigger.start()

        # Trigger multiple times
        trigger.trigger()
        trigger.trigger()
        trigger.trigger()

        assert trigger_count["count"] == 3, "Should trigger exactly 3 times"

        trigger.stop()

    def test_start_and_stop_do_nothing(self) -> None:
        """Test that start() and stop() are no-ops for manual triggers."""
        trigger_count = {"count": 0}

        def callback() -> None:
            trigger_count["count"] += 1

        trigger = ManualTrigger({}, callback)

        # These should do nothing
        trigger.start()
        trigger.stop()
        trigger.start()

        # Should not have triggered
        assert trigger_count["count"] == 0


class TestWebhookTrigger:
    """Tests for WebhookTrigger with opaque API."""

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format."""
        from datetime import datetime
        return datetime.now(UTC).isoformat().replace('+00:00', 'Z')

    def test_webhook_server_starts_and_stops(self, tmp_path: Path) -> None:
        """Test that webhook server starts and stops cleanly."""
        api_key_file = tmp_path / "api_keys.txt"
        api_key_file.write_text("test-key-123\n")

        trigger = WebhookTrigger(
            {
                "port": 18888,
                "api_key_file": str(api_key_file),
                "host": "127.0.0.1"
            },
            lambda: None  # Dummy callback (not used with new API)
        )

        trigger.start()
        time.sleep(0.1)
        trigger.stop()

    def test_webhook_authenticated_request_triggers_callback(self, tmp_path: Path) -> None:
        """Test that authenticated webhook triggers registered watcher."""
        import http.client
        import json

        api_key_file = tmp_path / "api_keys.txt"
        api_key = "valid-api-key-456"
        api_key_file.write_text(f"{api_key}\n")

        callback_count = 0

        def callback() -> None:
            nonlocal callback_count
            callback_count += 1

        trigger = WebhookTrigger(
            {"port": 18889, "api_key_file": str(api_key_file)},
            lambda: None
        )
        trigger.register_watcher("test-watcher", callback)
        trigger.start()
        time.sleep(0.2)

        try:
            # Send authenticated POST to /api with JSON body
            conn = http.client.HTTPConnection("127.0.0.1", 18889, timeout=2)
            body = json.dumps({
                "target": "test-watcher",
                "timestamp": self._get_current_timestamp()
            })
            try:
                conn.request(
                    "POST",
                    "/api",
                    body=body,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                )
                # Server sends RST, so this will fail - that's expected
                conn.getresponse()
            except Exception:
                pass  # Connection reset is expected
            finally:
                conn.close()

            # Wait for async processing
            time.sleep(0.5)
            assert callback_count == 1
        finally:
            trigger.stop()

    def test_webhook_wrong_bearer_token_rejected(self, tmp_path: Path) -> None:
        """Test that wrong bearer token is rejected."""
        import http.client
        import json

        api_key_file = tmp_path / "api_keys.txt"
        api_key_file.write_text("valid-key\n")

        callback_count = 0

        def callback() -> None:
            nonlocal callback_count
            callback_count += 1

        trigger = WebhookTrigger(
            {"port": 18890, "api_key_file": str(api_key_file)},
            lambda: None
        )
        trigger.register_watcher("test-watcher", callback)
        trigger.start()
        time.sleep(0.2)

        try:
            conn = http.client.HTTPConnection("127.0.0.1", 18890, timeout=2)
            body = json.dumps({
                "target": "test-watcher",
                "timestamp": self._get_current_timestamp()
            })
            try:
                conn.request(
                    "POST",
                    "/api",
                    body=body,
                    headers={
                        "Authorization": "Bearer wrong-key",
                        "Content-Type": "application/json"
                    }
                )
                conn.getresponse()
            except Exception:
                pass
            finally:
                conn.close()

            time.sleep(0.5)
            assert callback_count == 0  # Not triggered
        finally:
            trigger.stop()

    def test_webhook_stale_timestamp_rejected(self, tmp_path: Path) -> None:
        """Test that stale timestamps are rejected (replay protection)."""
        import http.client
        import json
        from datetime import datetime, timedelta

        api_key_file = tmp_path / "api_keys.txt"
        api_key = "valid-key"
        api_key_file.write_text(f"{api_key}\n")

        callback_count = 0

        def callback() -> None:
            nonlocal callback_count
            callback_count += 1

        trigger = WebhookTrigger(
            {"port": 18891, "api_key_file": str(api_key_file)},
            lambda: None
        )
        trigger.register_watcher("test-watcher", callback)
        trigger.start()
        time.sleep(0.2)

        try:
            # Send request with old timestamp (> 5 min ago)
            old_time = datetime.now(UTC) - timedelta(minutes=10)
            old_timestamp = old_time.isoformat().replace('+00:00', 'Z')

            conn = http.client.HTTPConnection("127.0.0.1", 18891, timeout=2)
            body = json.dumps({
                "target": "test-watcher",
                "timestamp": old_timestamp
            })
            try:
                conn.request(
                    "POST",
                    "/api",
                    body=body,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                )
                conn.getresponse()
            except Exception:
                pass
            finally:
                conn.close()

            time.sleep(0.5)
            assert callback_count == 0  # Not triggered (stale)
        finally:
            trigger.stop()

    def test_webhook_wrong_path_rejected(self, tmp_path: Path) -> None:
        """Test that requests to wrong path are rejected."""
        import http.client
        import json

        api_key_file = tmp_path / "api_keys.txt"
        api_key = "valid-key"
        api_key_file.write_text(f"{api_key}\n")

        callback_count = 0

        def callback() -> None:
            nonlocal callback_count
            callback_count += 1

        trigger = WebhookTrigger(
            {"port": 18892, "api_key_file": str(api_key_file)},
            lambda: None
        )
        trigger.register_watcher("test-watcher", callback)
        trigger.start()
        time.sleep(0.2)

        try:
            # Send to wrong path
            conn = http.client.HTTPConnection("127.0.0.1", 18892, timeout=2)
            body = json.dumps({
                "target": "test-watcher",
                "timestamp": self._get_current_timestamp()
            })
            try:
                conn.request(
                    "POST",
                    "/wrong",  # Wrong path
                    body=body,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                )
                conn.getresponse()
            except Exception:
                pass
            finally:
                conn.close()

            time.sleep(0.5)
            assert callback_count == 0
        finally:
            trigger.stop()

    def test_webhook_get_request_rejected(self, tmp_path: Path) -> None:
        """Test that GET requests are rejected."""
        import http.client

        api_key_file = tmp_path / "api_keys.txt"
        api_key = "valid-key"
        api_key_file.write_text(f"{api_key}\n")

        callback_count = 0

        def callback() -> None:
            nonlocal callback_count
            callback_count += 1

        trigger = WebhookTrigger(
            {"port": 18893, "api_key_file": str(api_key_file)},
            lambda: None
        )
        trigger.register_watcher("test-watcher", callback)
        trigger.start()
        time.sleep(0.2)

        try:
            # Send GET request
            conn = http.client.HTTPConnection("127.0.0.1", 18893, timeout=2)
            try:
                conn.request("GET", "/api", headers={"Authorization": f"Bearer {api_key}"})
                conn.getresponse()
            except Exception:
                pass
            finally:
                conn.close()

            time.sleep(0.5)
            assert callback_count == 0
        finally:
            trigger.stop()

    def test_webhook_unknown_watcher_rejected(self, tmp_path: Path) -> None:
        """Test that requests for unknown watchers are rejected."""
        import http.client
        import json

        api_key_file = tmp_path / "api_keys.txt"
        api_key = "valid-key"
        api_key_file.write_text(f"{api_key}\n")

        callback_count = 0

        def callback() -> None:
            nonlocal callback_count
            callback_count += 1

        trigger = WebhookTrigger(
            {"port": 18894, "api_key_file": str(api_key_file)},
            lambda: None
        )
        trigger.register_watcher("known-watcher", callback)
        trigger.start()
        time.sleep(0.2)

        try:
            # Request unknown watcher
            conn = http.client.HTTPConnection("127.0.0.1", 18894, timeout=2)
            body = json.dumps({
                "target": "unknown-watcher",  # Not registered
                "timestamp": self._get_current_timestamp()
            })
            try:
                conn.request(
                    "POST",
                    "/api",
                    body=body,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                )
                conn.getresponse()
            except Exception:
                pass
            finally:
                conn.close()

            time.sleep(0.5)
            assert callback_count == 0
        finally:
            trigger.stop()


class TestProcessEventTrigger:
    """Tests for ProcessEventTrigger (not yet implemented)."""

    def test_process_event_raises_not_implemented(self) -> None:
        """Test that process event trigger raises NotImplementedError."""
        def callback() -> None:
            pass

        trigger = ProcessEventTrigger(
            {"process_name": "test", "events": ["start"]},
            callback
        )

        with pytest.raises(NotImplementedError, match="Process event triggers not yet implemented"):
            trigger.start()
