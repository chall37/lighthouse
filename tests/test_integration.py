"""
Integration tests for the full Lighthouse daemon workflow.
"""

from pathlib import Path
from unittest.mock import patch

from lighthouse.daemon import LighthouseDaemon


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_daemon_init_and_config_loading(self, tmp_path: Path) -> None:
        """Test daemon initialization with config."""
        config_file = tmp_path / "config.yaml"
        state_dir = str(tmp_path / "state")
        config_file.write_text(f"""
watchers:
  - name: "Test Watcher"
    observer:
      type: "log_pattern"
      config:
        log_file: "/tmp/test.log"
        patterns: ["ERROR"]
    trigger:
      type: "file_event"
      config:
        path: "/tmp/test.log"
        events: ["modified"]
    evaluator:
      type: "pattern_match"
      config:
        severity: "medium"

notifiers:
  - type: "console"
    config: {{}}

state_dir: "{state_dir}"
""")

        daemon = LighthouseDaemon(str(config_file))

        assert len(daemon.config.watchers) == 1
        assert len(daemon.notifiers) == 1
        assert daemon.state_dir == tmp_path / "state"

    def test_log_pattern_to_notification_workflow(self, tmp_path: Path) -> None:
        """Test full workflow: log pattern → observation → evaluation → notification."""
        log_file = tmp_path / "test.log"
        log_file.write_text("INFO: Starting\n")

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
watchers:
  - name: "Error Detector"
    observer:
      type: "log_pattern"
      config:
        log_file: "{log_file}"
        patterns: ["ERROR"]
    trigger:
      type: "manual"
      config: {{}}
    evaluator:
      type: "pattern_match"
      config:
        severity: "high"

notifiers:
  - type: "console"
    config: {{}}

state_dir: "{state_dir}"
""".format(log_file=str(log_file), state_dir=str(tmp_path / "state")))

        daemon = LighthouseDaemon(str(config_file))
        daemon.setup_watchers()

        # Manually trigger observation - no error yet
        coordinator = daemon.coordinators[0]
        decision = coordinator.check()
        assert decision is None  # No alert

        # Add error to log
        log_file.write_text("INFO: Starting\nERROR: Something broke\n")

        # Trigger again
        decision = coordinator.check()
        assert decision is not None
        assert decision.should_alert is True
        assert decision.severity == "high"

    def test_metric_sequential_growth_workflow(self, tmp_path: Path) -> None:
        """Test metric observation with sequential growth evaluator."""
        error_file = tmp_path / "errors.log"
        error_file.write_text("[FAILED] File 1\n[FAILED] File 2\n")

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
watchers:
  - name: "Persistent Errors"
    observer:
      type: "metric"
      config:
        extractor:
          type: "line_count"
          source: "{error_file}"
          pattern: "\\\\[FAILED\\\\]"
    trigger:
      type: "manual"
      config: {{}}
    evaluator:
      type: "sequential_growth"
      config:
        severity: "medium"

notifiers:
  - type: "console"
    config: {{}}

state_dir: "{state_dir}"
""".format(error_file=str(error_file), state_dir=str(tmp_path / "state")))

        daemon = LighthouseDaemon(str(config_file))
        daemon.setup_watchers()
        coordinator = daemon.coordinators[0]

        # First observation - establishes baseline
        decision1 = coordinator.check()
        assert decision1 is None  # No alert (first observation)

        # Second observation - same count (should alert)
        decision2 = coordinator.check()
        assert decision2 is not None
        assert decision2.should_alert is True
        assert "2 errors" in decision2.message

        # Add one more error
        error_file.write_text("[FAILED] File 1\n[FAILED] File 2\n[FAILED] File 3\n")

        # Third observation - increased (should alert)
        decision3 = coordinator.check()
        assert decision3 is not None
        assert decision3.should_alert is True
        assert "3 errors" in decision3.message

        # Fix some errors
        error_file.write_text("[FAILED] File 1\n")

        # Fourth observation - decreased (no alert, improving!)
        decision4 = coordinator.check()
        assert decision4 is None  # No alert when improving

    def test_rate_limiting_works(self, tmp_path: Path) -> None:
        """Test that rate limiting prevents alert spam."""
        log_file = tmp_path / "test.log"
        log_file.write_text("ERROR: Problem\n")

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
watchers:
  - name: "Test"
    observer:
      type: "log_pattern"
      config:
        log_file: "{log_file}"
        patterns: ["ERROR"]
    trigger:
      type: "manual"
      config: {{}}
    evaluator:
      type: "pattern_match"
      config: {{}}

notifiers:
  - type: "console"
    config: {{}}

rate_limiting:
  cooldown_seconds: 60
  max_per_hour: 5

state_dir: "{state_dir}"
""".format(log_file=str(log_file), state_dir=str(tmp_path / "state")))

        daemon = LighthouseDaemon(str(config_file))
        daemon.setup_watchers()

        # Mock the notifier to track calls
        with patch.object(daemon.notifiers[0], 'notify', return_value=True) as mock_notify:
            coordinator = daemon.coordinators[0]

            # First alert should go through
            decision1 = coordinator.check()
            assert decision1 is not None
            daemon._handle_alert("Test", decision1, None)
            assert mock_notify.call_count == 1

            # Second alert should be rate limited
            decision2 = coordinator.check()
            assert decision2 is not None
            daemon._handle_alert("Test", decision2, None)
            assert mock_notify.call_count == 1  # Still 1, not 2

    def test_multiple_notifiers(self, tmp_path: Path) -> None:
        """Test that alerts are sent to all notifiers."""
        log_file = tmp_path / "test.log"
        log_file.write_text("ERROR: Problem\n")

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
watchers:
  - name: "Test"
    observer:
      type: "log_pattern"
      config:
        log_file: "{log_file}"
        patterns: ["ERROR"]
    trigger:
      type: "manual"
      config: {{}}
    evaluator:
      type: "pattern_match"
      config: {{}}

notifiers:
  - type: "console"
    config: {{}}
  - type: "console"
    config: {{}}

rate_limiting:
  cooldown_seconds: 0
  max_per_hour: 100

state_dir: "{state_dir}"
""".format(log_file=str(log_file), state_dir=str(tmp_path / "state")))

        daemon = LighthouseDaemon(str(config_file))
        daemon.setup_watchers()

        # Mock both notifiers
        with patch.object(daemon.notifiers[0], 'notify', return_value=True) as mock1, \
             patch.object(daemon.notifiers[1], 'notify', return_value=True) as mock2:

            coordinator = daemon.coordinators[0]
            decision = coordinator.check()
            assert decision is not None
            daemon._handle_alert("Test", decision, None)

            # Both notifiers should be called
            assert mock1.call_count == 1
            assert mock2.call_count == 1

    def test_observation_history_persistence(self, tmp_path: Path) -> None:
        """Test that observation history is saved and loaded."""
        error_file = tmp_path / "errors.log"
        error_file.write_text("[FAILED] File 1\n")

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
watchers:
  - name: "Errors"
    observer:
      type: "metric"
      config:
        extractor:
          type: "line_count"
          source: "{error_file}"
          pattern: "\\\\[FAILED\\\\]"
    trigger:
      type: "manual"
      config: {{}}
    evaluator:
      type: "sequential_growth"
      config: {{}}

notifiers:
  - type: "console"
    config: {{}}

state_dir: "{state_dir}"
""".format(error_file=str(error_file), state_dir=str(tmp_path / "state")))

        # First daemon instance
        daemon1 = LighthouseDaemon(str(config_file))
        daemon1.setup_watchers()
        coordinator1 = daemon1.coordinators[0]

        # Make some observations
        coordinator1.check()  # First observation
        coordinator1.check()  # Second observation

        assert len(coordinator1.history) == 2

        # Create new daemon instance (simulating restart)
        daemon2 = LighthouseDaemon(str(config_file))
        daemon2.setup_watchers()
        coordinator2 = daemon2.coordinators[0]

        # History should be loaded
        assert len(coordinator2.history) == 2
        assert coordinator2.history[0].value == 1
        assert coordinator2.history[1].value == 1

    def test_state_change_evaluator_service_monitoring(self, tmp_path: Path) -> None:
        """Test state change evaluator for service monitoring."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
watchers:
  - name: "Service Monitor"
    observer:
      type: "service"
      config:
        check_type: "process"
        service_name: "launchd"
    trigger:
      type: "manual"
      config: {{}}
    evaluator:
      type: "state_change"
      config:
        alert_on: "true_to_false"
        severity: "critical"

notifiers:
  - type: "console"
    config: {{}}

state_dir: "{state_dir}"
""".format(state_dir=str(tmp_path / "state")))

        daemon = LighthouseDaemon(str(config_file))
        daemon.setup_watchers()
        coordinator = daemon.coordinators[0]

        # First check - service is running
        decision1 = coordinator.check()
        assert decision1 is None  # No alert (first observation)

        # Second check - service still running
        decision2 = coordinator.check()
        assert decision2 is None  # No alert (no change)

        # Note: We can't easily test service going down without actually stopping a process
        # This test just verifies the wiring works
