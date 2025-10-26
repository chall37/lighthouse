"""
Tests for state management and rate limiting.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from lighthouse.state import AlertState, StateManager


class TestAlertState:
    """Tests for AlertState dataclass."""

    def test_alert_state_creation(self) -> None:
        """Test creating an AlertState instance."""
        now = datetime.now()
        state = AlertState(last_sent=now, count_this_hour=5, hour_start=now)

        assert state.last_sent == now
        assert state.count_this_hour == 5
        assert state.hour_start == now

    def test_alert_state_defaults(self) -> None:
        """Test AlertState default values."""
        now = datetime.now()
        state = AlertState(last_sent=now)

        assert state.last_sent == now
        assert state.count_this_hour == 0
        assert isinstance(state.hour_start, datetime)


class TestStateManager:
    """Tests for StateManager."""

    def test_init_creates_state_file_dir(self, tmp_path: Path) -> None:
        """Test that initialization creates state file directory."""
        state_file = tmp_path / "subdir" / "state.json"

        manager = StateManager(state_file)

        assert state_file.parent.exists()
        assert manager.state_file == state_file

    def test_init_with_existing_state(self, tmp_path: Path) -> None:
        """Test initialization with existing state file."""
        state_file = tmp_path / "state.json"

        # Create initial state
        now = datetime.now()
        data = {
            "alerts": {
                "watcher1:pattern1": {
                    "last_sent": now.isoformat(),
                    "count_this_hour": 3,
                    "hour_start": now.isoformat()
                }
            }
        }

        with state_file.open("w", encoding="utf-8") as f:
            json.dump(data, f)

        # Load state
        manager = StateManager(state_file)

        assert "watcher1:pattern1" in manager.alerts
        assert manager.alerts["watcher1:pattern1"].count_this_hour == 3

    def test_init_with_corrupted_state(self, tmp_path: Path, caplog: Any) -> None:
        """Test initialization with corrupted state file."""
        state_file = tmp_path / "state.json"
        state_file.write_text("invalid json{]")

        manager = StateManager(state_file)

        # Should start with empty state
        assert len(manager.alerts) == 0

        # Should log warning
        assert "Could not load state file" in caplog.text

    def test_should_send_alert_first_time(self, tmp_path: Path) -> None:
        """Test that first alert for a pattern should be sent."""
        manager = StateManager(tmp_path / "state.json")

        should_send = manager.should_send_alert(
            "test_watcher",
            "test_pattern",
            cooldown_seconds=60,
            max_per_hour=10
        )

        assert should_send is True

    def test_should_send_alert_respects_cooldown(self, tmp_path: Path) -> None:
        """Test that cooldown period prevents rapid alerts."""
        manager = StateManager(tmp_path / "state.json")

        # First alert
        assert manager.should_send_alert("watcher", "pattern", cooldown_seconds=60, max_per_hour=0)
        manager.record_alert("watcher", "pattern")

        # Immediate second alert should be blocked
        should_send = manager.should_send_alert("watcher", "pattern", cooldown_seconds=60, max_per_hour=0)
        assert should_send is False

    def test_should_send_alert_after_cooldown_expires(self, tmp_path: Path) -> None:
        """Test that alerts can be sent after cooldown expires."""
        manager = StateManager(tmp_path / "state.json")

        # Record an alert in the past
        manager.record_alert("watcher", "pattern")
        manager.alerts["watcher:pattern"].last_sent = datetime.now() - timedelta(seconds=61)

        # Should be allowed now
        should_send = manager.should_send_alert("watcher", "pattern", cooldown_seconds=60, max_per_hour=0)
        assert should_send is True

    def test_should_send_alert_respects_hourly_limit(self, tmp_path: Path) -> None:
        """Test that hourly rate limit is enforced."""
        manager = StateManager(tmp_path / "state.json")

        # Send max_per_hour alerts
        for _i in range(3):
            assert manager.should_send_alert("watcher", "pattern", cooldown_seconds=0, max_per_hour=3)
            manager.record_alert("watcher", "pattern")
            time.sleep(0.01)  # Small delay to avoid cooldown

        # Next alert should be blocked
        should_send = manager.should_send_alert("watcher", "pattern", cooldown_seconds=0, max_per_hour=3)
        assert should_send is False

    def test_should_send_alert_hourly_limit_resets(self, tmp_path: Path) -> None:
        """Test that hourly limit resets after an hour."""
        manager = StateManager(tmp_path / "state.json")

        # Send max alerts
        for _i in range(3):
            assert manager.should_send_alert("watcher", "pattern", cooldown_seconds=0, max_per_hour=3)
            manager.record_alert("watcher", "pattern")

        # Move hour_start back
        manager.alerts["watcher:pattern"].hour_start = datetime.now() - timedelta(hours=2)

        # Should be allowed again
        should_send = manager.should_send_alert("watcher", "pattern", cooldown_seconds=0, max_per_hour=3)
        assert should_send is True

    def test_should_send_alert_unlimited_hourly(self, tmp_path: Path) -> None:
        """Test that max_per_hour=0 means unlimited."""
        manager = StateManager(tmp_path / "state.json")

        # Send many alerts
        for _i in range(100):
            manager.record_alert("watcher", "pattern")
            time.sleep(0.001)

        # Should still be allowed
        should_send = manager.should_send_alert("watcher", "pattern", cooldown_seconds=0, max_per_hour=0)
        assert should_send is True

    def test_record_alert_creates_state(self, tmp_path: Path) -> None:
        """Test that recording an alert creates state."""
        manager = StateManager(tmp_path / "state.json")

        manager.record_alert("watcher", "pattern")

        assert "watcher:pattern" in manager.alerts
        state = manager.alerts["watcher:pattern"]
        assert state.count_this_hour == 1
        assert isinstance(state.last_sent, datetime)
        assert isinstance(state.hour_start, datetime)

    def test_record_alert_increments_count(self, tmp_path: Path) -> None:
        """Test that recording alerts increments count."""
        manager = StateManager(tmp_path / "state.json")

        manager.record_alert("watcher", "pattern")
        manager.record_alert("watcher", "pattern")
        manager.record_alert("watcher", "pattern")

        assert manager.alerts["watcher:pattern"].count_this_hour == 3

    def test_record_alert_resets_hourly_count(self, tmp_path: Path) -> None:
        """Test that count resets after an hour."""
        manager = StateManager(tmp_path / "state.json")

        manager.record_alert("watcher", "pattern")
        manager.record_alert("watcher", "pattern")

        # Move hour_start back
        manager.alerts["watcher:pattern"].hour_start = datetime.now() - timedelta(hours=2)

        # Record another alert
        manager.record_alert("watcher", "pattern")

        # Count should have reset
        assert manager.alerts["watcher:pattern"].count_this_hour == 1

    def test_record_alert_saves_to_disk(self, tmp_path: Path) -> None:
        """Test that recording an alert persists to disk."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)

        manager.record_alert("watcher", "pattern")

        # Verify file was written
        assert state_file.exists()

        # Load in new manager
        manager2 = StateManager(state_file)
        assert "watcher:pattern" in manager2.alerts

    def test_multiple_watchers_isolated(self, tmp_path: Path) -> None:
        """Test that different watchers have isolated state."""
        manager = StateManager(tmp_path / "state.json")

        # Record alerts for different watchers
        manager.record_alert("watcher1", "pattern1")
        manager.record_alert("watcher2", "pattern2")

        assert "watcher1:pattern1" in manager.alerts
        assert "watcher2:pattern2" in manager.alerts
        assert manager.alerts["watcher1:pattern1"].count_this_hour == 1
        assert manager.alerts["watcher2:pattern2"].count_this_hour == 1

    def test_multiple_patterns_isolated(self, tmp_path: Path) -> None:
        """Test that different patterns for same watcher are isolated."""
        manager = StateManager(tmp_path / "state.json")

        manager.record_alert("watcher", "pattern1")
        manager.record_alert("watcher", "pattern2")

        assert "watcher:pattern1" in manager.alerts
        assert "watcher:pattern2" in manager.alerts

    def test_state_persistence(self, tmp_path: Path) -> None:
        """Test that state persists across manager instances."""
        state_file = tmp_path / "state.json"

        # Create and use first manager
        manager1 = StateManager(state_file)
        manager1.record_alert("watcher", "pattern")
        manager1.record_alert("watcher", "pattern")

        # Create second manager
        manager2 = StateManager(state_file)

        # Should have loaded previous state
        assert manager2.alerts["watcher:pattern"].count_this_hour == 2

    def test_json_serialization_format(self, tmp_path: Path) -> None:
        """Test that state file is valid JSON with correct structure."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)

        manager.record_alert("test_watcher", "test_pattern")

        # Read raw JSON
        with state_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert "alerts" in data
        assert "test_watcher:test_pattern" in data["alerts"]
        alert_data = data["alerts"]["test_watcher:test_pattern"]
        assert "last_sent" in alert_data
        assert "count_this_hour" in alert_data
        assert "hour_start" in alert_data
