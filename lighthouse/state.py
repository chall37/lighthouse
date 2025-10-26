"""
State management for tracking sent notifications and rate limiting.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from lighthouse.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class AlertState:
    """State tracking for a single alert."""
    last_sent: datetime
    count_this_hour: int = 0
    hour_start: datetime = field(default_factory=datetime.now)


class StateManager:
    """
    Manages persistent state for deduplication and rate limiting.

    State is stored in JSON format with the following structure:
    {
        "alerts": {
            "watcher_name:pattern": {
                "last_sent": "2024-01-01T12:00:00",
                "count_this_hour": 3,
                "hour_start": "2024-01-01T12:00:00"
            }
        }
    }
    """

    def __init__(self, state_file: str | Path | None = None) -> None:
        """
        Initialize state manager.

        Args:
            state_file: Path to state file. If None, uses ~/.lighthouse/state.json
        """
        if state_file is None:
            state_file = Path.home() / '.lighthouse' / 'state.json'

        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        self.alerts: dict[str, AlertState] = {}
        self._load()

    def _load(self) -> None:
        """Load state from disk."""
        if not self.state_file.exists():
            return

        try:
            with self.state_file.open('r', encoding='utf-8') as f:
                data: dict[str, Any] = json.load(f)

            alerts_data = data.get('alerts', {})
            for key, alert_data in alerts_data.items():
                hour_start_str = alert_data.get('hour_start', alert_data['last_sent'])
                self.alerts[key] = AlertState(
                    last_sent=datetime.fromisoformat(alert_data['last_sent']),
                    count_this_hour=alert_data.get('count_this_hour', 0),
                    hour_start=datetime.fromisoformat(hour_start_str)
                )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If state file is corrupted, start fresh
            logger.warning("Could not load state file: %s", e)
            self.alerts = {}

    def _save(self) -> None:
        """Save state to disk."""
        data = {
            'alerts': {
                key: {
                    'last_sent': state.last_sent.isoformat(),
                    'count_this_hour': state.count_this_hour,
                    'hour_start': state.hour_start.isoformat()
                }
                for key, state in self.alerts.items()
            }
        }

        with self.state_file.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def should_send_alert(
        self,
        watcher_name: str,
        pattern: str,
        cooldown_seconds: int,
        max_per_hour: int
    ) -> bool:
        """
        Check if an alert should be sent based on rate limiting rules.

        Args:
            watcher_name: Name of the watcher
            pattern: Matched pattern
            cooldown_seconds: Minimum seconds between duplicate alerts
            max_per_hour: Maximum alerts per hour (0 = unlimited)

        Returns:
            True if the alert should be sent
        """
        key = f"{watcher_name}:{pattern}"
        now = datetime.now()

        if key not in self.alerts:
            return True

        state = self.alerts[key]

        # Check cooldown period
        time_since_last = now - state.last_sent
        if time_since_last.total_seconds() < cooldown_seconds:
            return False

        # Check hourly rate limit
        if max_per_hour > 0:
            # Reset hourly counter if an hour has passed
            if now - state.hour_start >= timedelta(hours=1):
                state.count_this_hour = 0
                state.hour_start = now

            if state.count_this_hour >= max_per_hour:
                return False

        return True

    def record_alert(self, watcher_name: str, pattern: str) -> None:
        """
        Record that an alert was sent.

        Args:
            watcher_name: Name of the watcher
            pattern: Matched pattern
        """
        key = f"{watcher_name}:{pattern}"
        now = datetime.now()

        if key in self.alerts:
            state = self.alerts[key]

            # Reset hourly counter if needed
            if now - state.hour_start >= timedelta(hours=1):
                state.count_this_hour = 0
                state.hour_start = now

            state.last_sent = now
            state.count_this_hour += 1
        else:
            self.alerts[key] = AlertState(
                last_sent=now,
                count_this_hour=1,
                hour_start=now
            )

        self._save()
