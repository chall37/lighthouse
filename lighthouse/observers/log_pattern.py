"""
Observes log files for pattern matches by reading the entire file.
"""

import re
from datetime import datetime
from pathlib import Path

from lighthouse.core import ObservationResult
from lighthouse.core import Observer as BaseObserver
from lighthouse.logging_config import get_logger
from lighthouse.registry import register_observer

logger = get_logger(__name__)


@register_observer("log_pattern")
class Observer(BaseObserver):
    """
    Observes log files for pattern matches by reading the entire file.

    Config:
        log_file: Path to the log file to watch
        patterns: List of regex patterns to match
    """

    def observe(self) -> ObservationResult:
        """Check if any patterns match in the log file."""
        log_file = Path(self.config["log_file"])
        patterns = self.config["patterns"]

        if not log_file.exists():
            logger.warning("Log file not found: %s", log_file)
            return ObservationResult(
                value=False,
                timestamp=datetime.now(),
                metadata={"error": f"Log file not found: {log_file}"}
            )

        # Read the file and check for pattern matches
        try:
            with open(log_file, encoding='utf-8', errors='ignore') as f:
                content = f.read()

            matches = []
            for pattern in patterns:
                if re.search(pattern, content):
                    matches.append(pattern)

            if matches:
                logger.info(
                    "Found %d pattern match(es) in %s: %s",
                    len(matches), log_file, matches
                )
            else:
                logger.info("Checked %s: no pattern matches", log_file)

            return ObservationResult(
                value=len(matches) > 0,
                timestamp=datetime.now(),
                metadata={
                    "matched_patterns": matches,
                    "total_patterns": len(patterns),
                    "log_file": str(log_file)
                }
            )
        except Exception as e:
            logger.error("Error reading log file %s: %s", log_file, e)
            return ObservationResult(
                value=False,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )


# Export for dynamic importing
LogPatternObserver = Observer
__all__ = ["LogPatternObserver"]
