"""
Observes log files for pattern matches by tailing the file.

This observer is robust against log rotation and truncation.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from lighthouse.core import ObservationResult
from lighthouse.core import Observer as BaseObserver
from lighthouse.logging_config import get_logger
from lighthouse.platform import get_file_fingerprint
from lighthouse.registry import register_observer

logger = get_logger(__name__)


class RotationHandler:
    """Base class for handling specific rotation scenarios."""

    def handle(self, log_file: Path, state: dict[str, Any]) -> int:
        """
        Handle rotation and return the offset to use.

        Args:
            log_file: Path to the main log file
            state: Current state dictionary (may be modified)

        Returns:
            Offset to use for reading
        """
        raise NotImplementedError


class NoRotationHandler(RotationHandler):
    """Handler for when no rotation has occurred."""

    def handle(self, log_file: Path, state: dict[str, Any]) -> int:
        """Continue from stored offset."""
        offset: int = state.get("offset", 0)

        # Safety check: detect file size regression
        try:
            file_size = log_file.stat().st_size
            if file_size < offset:
                logger.info(
                    "File size regression detected for %s. Resetting offset.",
                    log_file
                )
                return 0
        except FileNotFoundError:
            return 0

        return offset


class CopytruncateRotationHandler(RotationHandler):
    """Handler for copytruncate rotation (inode unchanged, .log.1 changed)."""

    def handle(self, log_file: Path, _state: dict[str, Any]) -> int:
        """Reset offset to start of file."""
        logger.info("Copytruncate rotation detected for %s. Resetting offset.", log_file)
        return 0


class MoveCreateRotationHandler(RotationHandler):
    """Handler for move/create rotation (inode changed)."""

    def handle(self, log_file: Path, state: dict[str, Any]) -> int:
        """Reset offset and update fingerprint."""
        logger.info("Move/create rotation detected for %s. Resetting offset.", log_file)
        current_fingerprint = get_file_fingerprint(str(log_file))
        state["fingerprint"] = current_fingerprint
        return 0


class RotationDetector:
    """Detects log rotation and delegates to appropriate handler."""

    def __init__(self) -> None:
        self.no_rotation_handler = NoRotationHandler()
        self.copytruncate_handler = CopytruncateRotationHandler()
        self.move_create_handler = MoveCreateRotationHandler()

    def detect_and_handle(
        self,
        log_file: Path,
        rotated_log_file: Path,
        state: dict[str, Any]
    ) -> int:
        """
        Detect rotation type and return offset to use.

        Args:
            log_file: Path to the main log file
            rotated_log_file: Path to the rotated log file (.log.1)
            state: Current state dictionary

        Returns:
            Offset to use for reading
        """
        current_fingerprint = get_file_fingerprint(str(log_file))
        stored_fingerprint = state.get("fingerprint")
        stored_rotated_fingerprint = state.get("rotated_fingerprint")

        # Get fingerprint of rotated log file (if exists)
        current_rotated_fingerprint = None
        if rotated_log_file.exists():
            current_rotated_fingerprint = get_file_fingerprint(str(rotated_log_file))

        # Store current rotated fingerprint for next iteration
        state["rotated_fingerprint"] = current_rotated_fingerprint

        # Determine rotation type and delegate to handler
        if stored_fingerprint == current_fingerprint:
            # .log fingerprint unchanged
            if stored_rotated_fingerprint != current_rotated_fingerprint:
                # .log.1 changed - copytruncate rotation
                return self.copytruncate_handler.handle(log_file, state)
            # No rotation
            return self.no_rotation_handler.handle(log_file, state)

        # .log fingerprint changed - move/create rotation
        return self.move_create_handler.handle(log_file, state)


@register_observer("stateful_log_pattern")
class Observer(BaseObserver):
    """
    Observes log files for pattern matches by tailing the file.

    This observer is robust against log rotation and truncation.

    Config:
        log_file: Path to the log file to watch
        patterns: List of regex patterns to match
    """
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.log_file = Path(self.config["log_file"])
        self.patterns = self.config["patterns"]
        self.state_file = Path(self.config["state_dir"]) / f'{self.config["name"]}.state.json'
        self.state = self._load_state()
        # Derive rotated log path (TODO: support multiple rotation schemes)
        self.rotated_log_file = Path(str(self.log_file) + ".1")
        self.rotation_detector = RotationDetector()

    def _load_state(self) -> dict[str, Any]:
        """Load observer state from disk."""
        if not self.state_file.exists():
            return {"fingerprint": None, "offset": 0, "rotated_fingerprint": None}
        try:
            with self.state_file.open('r', encoding='utf-8') as f:
                state: dict[str, Any] = json.load(f)
                # Ensure rotated_fingerprint exists for backward compatibility
                if "rotated_fingerprint" not in state:
                    state["rotated_fingerprint"] = None
                return state
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "Could not load state file for %s: %s. Starting fresh.",
                self.config['name'], e
            )
            return {"fingerprint": None, "offset": 0, "rotated_fingerprint": None}

    def _save_state(self) -> None:
        """Save observer state to disk."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with self.state_file.open('w', encoding='utf-8') as f:
                json.dump(self.state, f)
        except Exception as e:
            logger.error("Error saving state for %s: %s", self.config['name'], e)

    def observe(self) -> ObservationResult:
        """Tails the log file and checks for pattern matches in new lines."""
        if not self.log_file.exists():
            logger.debug("Log file not found: %s", self.log_file)
            return ObservationResult(
                value=False,
                timestamp=datetime.now(),
                metadata={"status": "file not found"}
            )

        # Detect rotation and get offset to use
        offset = self.rotation_detector.detect_and_handle(
            self.log_file,
            self.rotated_log_file,
            self.state
        )

        # Read new lines
        lines = []
        try:
            with self.log_file.open('r', encoding='utf-8', errors='ignore') as f:
                f.seek(offset)
                lines = f.readlines()
                new_offset = f.tell()
        except Exception as e:
            logger.error("Error reading log file %s: %s", self.log_file, e)
            return ObservationResult(
                value=False,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )

        # Search for patterns
        matched_lines = []
        for line in lines:
            for pattern in self.patterns:
                if re.search(pattern, line):
                    matched_lines.append(line.strip())
                    break # Don't match same line against multiple patterns

        self.state["offset"] = new_offset
        self._save_state()

        if matched_lines:
            logger.info(
                "Found %d pattern match(es) in %s",
                len(matched_lines), self.log_file
            )
            return ObservationResult(
                value=True,
                timestamp=datetime.now(),
                metadata={
                    "matched_lines": matched_lines,
                    "log_file": str(self.log_file)
                }
            )

        return ObservationResult(
            value=False,
            timestamp=datetime.now(),
            metadata={"lines_read": len(lines)}
        )


# Export for dynamic importing
StatefulLogPatternObserver = Observer
__all__ = ["StatefulLogPatternObserver"]
