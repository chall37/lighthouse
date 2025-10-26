"""
Configuration loading and validation for Lighthouse.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError


class PushoverConfig(BaseModel):
    """Pushover API configuration."""
    user_key: str = Field(..., min_length=1)
    api_token: str = Field(..., min_length=1)
    priority: int = 0


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    cooldown_seconds: int = 3600
    max_per_hour: int = 10


class ObserverConfig(BaseModel):
    """Configuration for what to observe."""
    type: str  # "log_pattern", "metric", "service", etc.
    config: dict[str, Any]  # Type-specific configuration


class TriggerConfig(BaseModel):
    """Configuration for when to check."""
    type: str  # "file_event", "temporal", "webhook", "process_event", etc.
    config: dict[str, Any] = Field(default_factory=dict)  # Type-specific configuration


class EvaluatorConfig(BaseModel):
    """Configuration for alert evaluation logic."""
    type: str  # "pattern_match", "threshold", "sequential_growth", "state_change", etc.
    config: dict[str, Any] = Field(default_factory=dict)  # Type-specific configuration


class WatcherConfig(BaseModel):
    """Configuration for a watcher."""
    name: str
    observer: ObserverConfig
    trigger: TriggerConfig
    evaluator: EvaluatorConfig
    priority: int | None = None


class NotifierConfig(BaseModel):
    """Configuration for notification destinations."""
    type: str  # "pushover", "webhook", "email", "slack", etc.
    config: dict[str, Any]  # Type-specific configuration


class Config(BaseModel):
    """Main configuration for Lighthouse."""
    watchers: list[WatcherConfig] = Field(..., min_length=1)
    notifiers: list[NotifierConfig] = Field(..., min_length=1)
    rate_limiting: RateLimitConfig = Field(default_factory=RateLimitConfig)
    state_dir: str = "/var/lib/lighthouse"  # Directory for state storage


def load_config(config_path: str | Path) -> Config:
    """
    Load and validate configuration from YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Validated Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
        yaml.YAMLError: If YAML parsing fails
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with path.open('r', encoding='utf-8') as f:
        raw_config: dict[str, Any] = yaml.safe_load(f)

    try:
        return Config.model_validate(raw_config)
    except ValidationError as e:
        raise ValueError(f"Configuration validation error: {e}") from e
