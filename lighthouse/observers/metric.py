"""
Observes metrics extracted from files or commands.
"""

import re
import subprocess  # nosec B404 - Required for system monitoring (metrics)
from datetime import datetime
from pathlib import Path
from typing import Any

from lighthouse.core import ObservationResult
from lighthouse.core import Observer as BaseObserver
from lighthouse.logging_config import get_logger
from lighthouse.registry import register_observer

logger = get_logger(__name__)


@register_observer("metric")
class Observer(BaseObserver):
    """
    Observes metrics extracted from files or commands.

    Config:
        extractor: Configuration for how to extract the metric
            type: "line_count", "regex_capture", "json_path", "command"
            (type-specific config)
    """

    def observe(self) -> ObservationResult:
        """Extract and return the metric value."""
        extractor_config = self.config["extractor"]
        extractor_type = extractor_config["type"]

        try:
            value: Any
            if extractor_type == "line_count":
                value = self._extract_line_count(extractor_config)
            elif extractor_type == "regex_capture":
                value = self._extract_regex_capture(extractor_config)
            elif extractor_type == "json_path":
                value = self._extract_json_path(extractor_config)
            elif extractor_type == "command":
                value = self._extract_command(extractor_config)
            else:
                raise ValueError(f"Unknown extractor type: {extractor_type}")

            logger.info("Extracted metric (%s): %s", extractor_type, value)

            return ObservationResult(
                value=value,
                timestamp=datetime.now(),
                metadata={"extractor_type": extractor_type}
            )
        except Exception as e:
            logger.error("Error extracting metric (%s): %s", extractor_type, e)
            return ObservationResult(
                value=None,
                timestamp=datetime.now(),
                metadata={"error": str(e), "extractor_type": extractor_type}
            )

    def _extract_line_count(self, config: dict[str, Any]) -> int:
        """Count lines matching a pattern in a file."""
        file_path = Path(config["source"])
        pattern = config["pattern"]

        if not file_path.exists():
            return 0

        count = 0
        with open(file_path, encoding='utf-8', errors='ignore') as f:
            for line in f:
                if re.search(pattern, line):
                    count += 1

        return count

    def _extract_regex_capture(self, config: dict[str, Any]) -> str | int | float | None:
        """Extract a value using regex capture group."""
        file_path = Path(config["source"])
        pattern = config["pattern"]
        group = config.get("group", 1)
        data_type = config.get("data_type", "str")  # str, int, float

        if not file_path.exists():
            return None

        with open(file_path, encoding='utf-8', errors='ignore') as f:
            content = f.read()

        match = re.search(pattern, content)
        if not match:
            return None

        value_str: str = match.group(group)

        # Convert to appropriate type
        if data_type == "int":
            return int(value_str)
        if data_type == "float":
            return float(value_str)
        return value_str

    def _extract_json_path(self, config: dict[str, Any]) -> Any:
        """Extract a value from JSON using JSONPath."""
        # TODO: Implement JSONPath extraction
        # Will need to add jsonpath dependency
        raise NotImplementedError("JSON path extraction not yet implemented")

    def _extract_command(self, config: dict[str, Any]) -> str:
        """Extract a value by running a command."""
        command = config["command"]
        timeout = config.get("timeout", 30)

        result = subprocess.run(
            command,
            shell=True,  # nosec B602 - Intentional for command extractor metric type
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False  # nosec B603 - Return code checked by caller if needed
        )

        return result.stdout.strip()


# Export for dynamic importing
MetricObserver = Observer
__all__ = ["MetricObserver"]
