"""
Tests for configuration loading and validation.
"""

from pathlib import Path

import pytest

from lighthouse.config import load_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """Test loading a valid configuration file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
watchers:
  - name: "Test Watcher"
    observer:
      type: "log_pattern"
      config:
        log_file: "/var/log/test.log"
        patterns: ["ERROR"]
    trigger:
      type: "file_event"
      config:
        path: "/var/log/test.log"
        events: ["modified"]
    evaluator:
      type: "pattern_match"
      config:
        severity: "medium"

notifiers:
  - type: "pushover"
    config:
      user_key: "test_user_key"
      api_token: "test_api_token"

state_dir: "/var/lib/lighthouse"
""")

        config = load_config(config_file)

        assert len(config.watchers) == 1
        assert config.watchers[0].name == "Test Watcher"
        assert config.watchers[0].observer.type == "log_pattern"
        assert config.watchers[0].trigger.type == "file_event"
        assert config.watchers[0].evaluator.type == "pattern_match"
        assert len(config.notifiers) == 1
        assert config.notifiers[0].type == "pushover"
        assert config.state_dir == "/var/lib/lighthouse"

    def test_load_missing_file(self) -> None:
        """Test that loading a missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        """Test that invalid YAML raises an error."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(Exception):  # yaml.YAMLError
            load_config(config_file)

    def test_load_no_watchers(self, tmp_path: Path) -> None:
        """Test that config with no watchers is invalid."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
watchers: []
notifiers:
  - type: "console"
    config: {}
""")

        with pytest.raises(ValueError, match="validation error"):
            load_config(config_file)

    def test_load_no_notifiers(self, tmp_path: Path) -> None:
        """Test that config with no notifiers is invalid."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
watchers:
  - name: "Test"
    observer:
      type: "log_pattern"
      config:
        log_file: "/tmp/test.log"
        patterns: ["ERROR"]
    trigger:
      type: "file_event"
      config:
        path: "/tmp/test.log"
    evaluator:
      type: "pattern_match"
      config: {}
notifiers: []
""")

        with pytest.raises(ValueError, match="validation error"):
            load_config(config_file)

    def test_load_multiple_watchers(self, tmp_path: Path) -> None:
        """Test loading config with multiple watchers."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
watchers:
  - name: "Watcher 1"
    observer:
      type: "log_pattern"
      config:
        log_file: "/tmp/test1.log"
        patterns: ["ERROR"]
    trigger:
      type: "file_event"
      config:
        path: "/tmp/test1.log"
    evaluator:
      type: "pattern_match"
      config: {}

  - name: "Watcher 2"
    observer:
      type: "metric"
      config:
        extractor:
          type: "line_count"
          source: "/tmp/test2.log"
          pattern: "FAILED"
    trigger:
      type: "temporal"
      config:
        interval_seconds: 3600
    evaluator:
      type: "threshold"
      config:
        operator: "gt"
        value: 10

notifiers:
  - type: "console"
    config: {}
""")

        config = load_config(config_file)

        assert len(config.watchers) == 2
        assert config.watchers[0].name == "Watcher 1"
        assert config.watchers[1].name == "Watcher 2"

    def test_load_with_custom_state_dir(self, tmp_path: Path) -> None:
        """Test loading config with custom state directory."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
watchers:
  - name: "Test"
    observer:
      type: "log_pattern"
      config:
        log_file: "/tmp/test.log"
        patterns: ["ERROR"]
    trigger:
      type: "file_event"
      config:
        path: "/tmp/test.log"
    evaluator:
      type: "pattern_match"
      config: {}

notifiers:
  - type: "console"
    config: {}

state_dir: "/custom/state/path"
""")

        config = load_config(config_file)

        assert config.state_dir == "/custom/state/path"
