"""
Tests for observer implementations.
"""

import shutil
from datetime import datetime
from pathlib import Path

from lighthouse.observers import (
    LogPatternObserver,
    MetricObserver,
    ServiceObserver,
    StatefulLogPatternObserver,
)


class TestLogPatternObserver:
    """Tests for LogPatternObserver."""

    def test_observe_pattern_match(self, tmp_path: Path) -> None:
        """Test observing a file with matching pattern."""
        log_file = tmp_path / "test.log"
        log_file.write_text("INFO: Starting\nERROR: Something failed\nINFO: Done\n")

        observer = LogPatternObserver({
            "log_file": str(log_file),
            "patterns": ["ERROR"]
        })

        result = observer.observe()

        assert result.value is True
        assert "ERROR" in result.metadata["matched_patterns"]
        assert result.metadata["total_patterns"] == 1
        assert isinstance(result.timestamp, datetime)

    def test_observe_no_match(self, tmp_path: Path) -> None:
        """Test observing a file with no matching pattern."""
        log_file = tmp_path / "test.log"
        log_file.write_text("INFO: Starting\nINFO: Done\n")

        observer = LogPatternObserver({
            "log_file": str(log_file),
            "patterns": ["ERROR", "FATAL"]
        })

        result = observer.observe()

        assert result.value is False
        assert result.metadata["matched_patterns"] == []

    def test_observe_multiple_patterns(self, tmp_path: Path) -> None:
        """Test observing with multiple patterns."""
        log_file = tmp_path / "test.log"
        log_file.write_text("ERROR: First error\nWARNING: A warning\nFATAL: Critical\n")

        observer = LogPatternObserver({
            "log_file": str(log_file),
            "patterns": ["ERROR", "FATAL", "CRITICAL"]
        })

        result = observer.observe()

        assert result.value is True
        assert "ERROR" in result.metadata["matched_patterns"]
        assert "FATAL" in result.metadata["matched_patterns"]
        assert len(result.metadata["matched_patterns"]) == 2

    def test_observe_nonexistent_file(self, tmp_path: Path) -> None:
        """Test observing a nonexistent file."""
        observer = LogPatternObserver({
            "log_file": str(tmp_path / "nonexistent.log"),
            "patterns": ["ERROR"]
        })

        result = observer.observe()

        assert result.value is False
        assert "error" in result.metadata
        assert "not found" in result.metadata["error"].lower()

    def test_observe_regex_pattern(self, tmp_path: Path) -> None:
        """Test observing with regex patterns."""
        log_file = tmp_path / "test.log"
        log_file.write_text("Error code: 500\nError code: 404\nSuccess: 200\n")

        observer = LogPatternObserver({
            "log_file": str(log_file),
            "patterns": [r"Error code: \d+"]
        })

        result = observer.observe()

        assert result.value is True


class TestStatefulLogPatternObserver:
    """Tests for StatefulLogPatternObserver."""

    def test_initial_read(self, tmp_path: Path) -> None:
        """Test that the first read processes the whole file."""
        log_file = tmp_path / "test.log"
        log_file.write_text("line 1\nERROR: line 2\nline 3\n")

        observer = StatefulLogPatternObserver({
            "name": "test_initial_read",
            "state_dir": str(tmp_path),
            "log_file": str(log_file),
            "patterns": ["ERROR"]
        })

        result = observer.observe()

        assert result.value is True
        assert "ERROR: line 2" in result.metadata["matched_lines"]
        assert observer.state["offset"] > 0

    def test_tailing_logic(self, tmp_path: Path) -> None:
        """Test that subsequent reads only process new lines."""
        log_file = tmp_path / "test.log"
        state_dir = tmp_path / "state"

        observer = StatefulLogPatternObserver({
            "name": "test_tailing_logic",
            "state_dir": str(state_dir),
            "log_file": str(log_file),
            "patterns": ["ERROR"]
        })

        # First run
        log_file.write_text("line 1\n")
        result1 = observer.observe()
        assert result1.value is False

        # Second run
        with log_file.open("a") as f:
            f.write("ERROR: new line\n")

        result2 = observer.observe()
        assert result2.value is True
        assert "ERROR: new line" in result2.metadata["matched_lines"]

        # Third run (no new error lines)
        with log_file.open("a") as f:
            f.write("another line\n")

        result3 = observer.observe()
        assert result3.value is False

    def test_standard_rotation(self, tmp_path: Path) -> None:
        """Test that the observer handles standard log rotation (rename)."""
        log_file = tmp_path / "test.log"
        state_dir = tmp_path / "state"

        observer = StatefulLogPatternObserver({
            "name": "test_standard_rotation",
            "state_dir": str(state_dir),
            "log_file": str(log_file),
            "patterns": ["ERROR"]
        })

        # Initial file
        log_file.write_text("initial line\n")
        observer.observe()
        initial_fingerprint = observer.state["fingerprint"]

        # Rotate the log
        rotated_log = tmp_path / "test.log.1"
        log_file.rename(rotated_log)
        log_file.write_text("new file line\nERROR: after rotation\n")

        # Observe again
        result = observer.observe()

        assert result.value is True
        assert "ERROR: after rotation" in result.metadata["matched_lines"]

        # Check that the fingerprint has changed
        new_fingerprint = observer.state["fingerprint"]
        assert new_fingerprint is not None
        assert new_fingerprint != initial_fingerprint

    def test_copytruncate_rotation(self, tmp_path: Path) -> None:
        """Test that the observer handles copy-truncate rotation."""
        log_file = tmp_path / "test.log"
        state_dir = tmp_path / "state"

        observer = StatefulLogPatternObserver({
            "name": "test_copytruncate_rotation",
            "state_dir": str(state_dir),
            "log_file": str(log_file),
            "patterns": ["ERROR"]
        })

        # Initial file - make it longer so truncation is detected
        log_file.write_text("initial line 1\ninitial line 2\ninitial line 3\n")
        observer.observe()
        initial_fingerprint = observer.state["fingerprint"]
        initial_offset = observer.state["offset"]
        assert initial_offset > 0

        # Simulate copy-truncate - copy then truncate and write new (smaller) content
        shutil.copy(log_file, tmp_path / "test.log.bak")
        with log_file.open("w") as f:
            f.truncate(0)

        # Write to the now-truncated file (shorter than before to trigger detection)
        log_file.write_text("ERROR: new\n")

        # Observe again
        result = observer.observe()

        assert result.value is True, f"Expected match but got: {result}"
        assert "ERROR: new" in result.metadata.get("matched_lines", [])

        # After copytruncate, the fingerprint stays the same (same inode)
        # but offset should be reset to 0 when truncation is detected
        new_fingerprint = observer.state["fingerprint"]
        assert new_fingerprint == initial_fingerprint, "Fingerprint should not change on copytruncate"

    def test_state_file_creation(self, tmp_path: Path) -> None:
        """Test that a state file is created."""
        log_file = tmp_path / "test.log"
        state_dir = tmp_path / "state"
        log_file.write_text("some data\n")

        observer = StatefulLogPatternObserver({
            "name": "test_state_file_creation",
            "state_dir": str(state_dir),
            "log_file": str(log_file),
            "patterns": ["ERROR"]
        })

        observer.observe()

        state_file = state_dir / "test_state_file_creation.state.json"
        assert state_file.exists()
        assert state_file.stat().st_size > 0

    def test_file_size_regression(self, tmp_path: Path) -> None:
        """Test that file size regression (file smaller than offset) is handled."""
        log_file = tmp_path / "test.log"
        state_dir = tmp_path / "state"

        observer = StatefulLogPatternObserver({
            "name": "test_file_size_regression",
            "state_dir": str(state_dir),
            "log_file": str(log_file),
            "patterns": ["ERROR"]
        })

        # Initial file with content
        log_file.write_text("line 1\nline 2\nline 3\nline 4\n")
        observer.observe()
        initial_offset = observer.state["offset"]
        assert initial_offset > 0

        # Simulate file being truncated (race condition or manual truncation)
        # File is now smaller than the stored offset
        log_file.write_text("ERROR: new\n")

        # Observer should detect size regression and reset offset to 0
        result = observer.observe()

        assert result.value is True
        assert "ERROR: new" in result.metadata.get("matched_lines", [])
        # Offset should be updated to new position after reading from 0
        assert observer.state["offset"] > 0
        assert observer.state["offset"] < initial_offset

    def test_file_deleted_during_observation(self, tmp_path: Path) -> None:
        """Test that file deletion during observation is handled gracefully."""
        log_file = tmp_path / "test.log"
        state_dir = tmp_path / "state"

        observer = StatefulLogPatternObserver({
            "name": "test_file_deleted",
            "state_dir": str(state_dir),
            "log_file": str(log_file),
            "patterns": ["ERROR"]
        })

        # Initial observation with file present
        log_file.write_text("initial content\n")
        result1 = observer.observe()
        assert result1.value is False

        # Delete the file (simulating race condition or external deletion)
        log_file.unlink()

        # Observer should handle missing file gracefully
        result2 = observer.observe()
        assert result2.value is False
        assert result2.metadata.get("status") == "file not found"

    def test_copytruncate_with_log1_appearing(self, tmp_path: Path) -> None:
        """Test copytruncate detection when .log.1 suddenly appears."""
        log_file = tmp_path / "test.log"
        rotated_log = tmp_path / "test.log.1"
        state_dir = tmp_path / "state"

        observer = StatefulLogPatternObserver({
            "name": "test_copytruncate_log1_appears",
            "state_dir": str(state_dir),
            "log_file": str(log_file),
            "patterns": ["ERROR"]
        })

        # Initial observation - no .log.1 exists
        log_file.write_text("initial line 1\ninitial line 2\n")
        observer.observe()
        initial_fingerprint = observer.state["fingerprint"]
        assert observer.state.get("rotated_fingerprint") is None

        # Simulate copytruncate rotation - .log.1 appears
        shutil.copy(log_file, rotated_log)
        with log_file.open("w") as f:
            f.truncate(0)
        log_file.write_text("ERROR: after rotation\n")

        # Observer should detect .log.1 appeared and reset offset
        result = observer.observe()

        assert result.value is True
        assert "ERROR: after rotation" in result.metadata.get("matched_lines", [])
        # Fingerprint should not change (same inode)
        assert observer.state["fingerprint"] == initial_fingerprint
        # rotated_fingerprint should now be set
        assert observer.state.get("rotated_fingerprint") is not None

    def test_offset_beyond_file_end_race_condition(self, tmp_path: Path) -> None:
        """Test handling when offset is beyond file end (edge case race condition)."""
        log_file = tmp_path / "test.log"
        state_dir = tmp_path / "state"

        observer = StatefulLogPatternObserver({
            "name": "test_offset_beyond_end",
            "state_dir": str(state_dir),
            "log_file": str(log_file),
            "patterns": ["ERROR"]
        })

        # Initial file
        log_file.write_text("line 1\nline 2\nline 3\n")
        observer.observe()
        stored_offset = observer.state["offset"]

        # Manually manipulate state to simulate race condition
        # where offset is beyond file end
        observer.state["offset"] = stored_offset + 1000

        # File gets new content but is still smaller than offset
        log_file.write_text("ERROR: short\n")

        # Should detect size regression and reset
        result = observer.observe()

        assert result.value is True
        assert "ERROR: short" in result.metadata.get("matched_lines", [])

    def test_copytruncate_detection_without_size_regression(self, tmp_path: Path) -> None:
        """
        Test that copytruncate is detected purely by .log.1 inode change,
        even when file_size >= offset (no size regression).

        This proves the two-file fingerprint comparison works independently
        of the file size check.
        """
        log_file = tmp_path / "test.log"
        rotated_log = tmp_path / "test.log.1"
        state_dir = tmp_path / "state"

        observer = StatefulLogPatternObserver({
            "name": "test_copytruncate_no_size_regression",
            "state_dir": str(state_dir),
            "log_file": str(log_file),
            "patterns": ["ERROR"]
        })

        # Initial file - start with some content
        initial_content = "line 1\nline 2\nline 3\n"
        log_file.write_text(initial_content)
        observer.observe()
        initial_fingerprint = observer.state["fingerprint"]
        initial_offset = observer.state["offset"]

        # First rotation - create .log.1
        shutil.copy(log_file, rotated_log)
        observer.observe()  # This sets rotated_fingerprint
        stored_rotated_fingerprint = observer.state["rotated_fingerprint"]

        # Now simulate copytruncate rotation where new file is LARGER than offset
        # This ensures file_size >= offset, so size regression check won't trigger

        # Step 1: Copy current .log to a new temp file, then rename it to .log.1
        # This is more robust in ensuring the inode for .log.1 actually changes.
        temp_rotated_log = tmp_path / "test.log.1.tmp"
        shutil.copy(log_file, temp_rotated_log)
        rotated_log.unlink()  # Remove old .log.1
        temp_rotated_log.rename(rotated_log)  # Move new file into place

        # Step 2: Truncate and write NEW content to .log that is LONGER than before
        # This ensures new file size > initial_offset
        new_content = "ERROR: new line 1\nERROR: new line 2\nERROR: new line 3\nERROR: new line 4\n"
        assert len(new_content) > initial_offset, "New content must be larger than offset"

        with log_file.open("w") as f:
            f.truncate(0)
            f.write(new_content)

        # Verify our test setup: file size should be >= offset
        current_size = log_file.stat().st_size
        assert current_size >= initial_offset, "Test setup error: need file_size >= offset"

        # Observer should detect rotation ONLY by .log.1 fingerprint change
        result = observer.observe()

        # Should find the ERROR lines because rotation was detected
        assert result.value is True
        assert len(result.metadata.get("matched_lines", [])) == 4

        # Fingerprint should not change (copytruncate keeps same inode)
        assert observer.state["fingerprint"] == initial_fingerprint

        # rotated_fingerprint should have changed
        assert observer.state["rotated_fingerprint"] != stored_rotated_fingerprint
        assert observer.state["rotated_fingerprint"] is not None


class TestMetricObserver:
    """Tests for MetricObserver."""

    def test_line_count_extractor(self, tmp_path: Path) -> None:
        """Test extracting line count metric."""
        log_file = tmp_path / "errors.log"
        log_file.write_text("[FAILED] File 1\n[FAILED] File 2\n[SUCCESS] File 3\n[FAILED] File 4\n")

        observer = MetricObserver({
            "extractor": {
                "type": "line_count",
                "source": str(log_file),
                "pattern": r"\[FAILED\]"
            }
        })

        result = observer.observe()

        assert result.value == 3
        assert result.metadata["extractor_type"] == "line_count"

    def test_line_count_no_matches(self, tmp_path: Path) -> None:
        """Test line count with no matches."""
        log_file = tmp_path / "errors.log"
        log_file.write_text("[SUCCESS] File 1\n[SUCCESS] File 2\n")

        observer = MetricObserver({
            "extractor": {
                "type": "line_count",
                "source": str(log_file),
                "pattern": r"\[FAILED\]"
            }
        })

        result = observer.observe()

        assert result.value == 0

    def test_line_count_nonexistent_file(self, tmp_path: Path) -> None:
        """Test line count with nonexistent file."""
        observer = MetricObserver({
            "extractor": {
                "type": "line_count",
                "source": str(tmp_path / "nonexistent.log"),
                "pattern": r"\[FAILED\]"
            }
        })

        result = observer.observe()

        assert result.value == 0

    def test_regex_capture_extractor_int(self, tmp_path: Path) -> None:
        """Test extracting value via regex capture group as integer."""
        log_file = tmp_path / "stats.log"
        log_file.write_text("Failed files( % ): 15\nTotal files: 100\n")

        observer = MetricObserver({
            "extractor": {
                "type": "regex_capture",
                "source": str(log_file),
                "pattern": r"Failed files\( % \): (\d+)",
                "group": 1,
                "data_type": "int"
            }
        })

        result = observer.observe()

        assert result.value == 15
        assert isinstance(result.value, int)

    def test_regex_capture_extractor_str(self, tmp_path: Path) -> None:
        """Test extracting value via regex capture group as string."""
        log_file = tmp_path / "status.log"
        log_file.write_text("Status: running\nUptime: 3600\n")

        observer = MetricObserver({
            "extractor": {
                "type": "regex_capture",
                "source": str(log_file),
                "pattern": r"Status: (\w+)",
                "group": 1
            }
        })

        result = observer.observe()

        assert result.value == "running"

    def test_regex_capture_no_match(self, tmp_path: Path) -> None:
        """Test regex capture with no match."""
        log_file = tmp_path / "status.log"
        log_file.write_text("No status here\n")

        observer = MetricObserver({
            "extractor": {
                "type": "regex_capture",
                "source": str(log_file),
                "pattern": r"Status: (\w+)",
                "group": 1
            }
        })

        result = observer.observe()

        assert result.value is None

    def test_command_extractor(self) -> None:
        """Test extracting value from command."""
        observer = MetricObserver({
            "extractor": {
                "type": "command",
                "command": "echo 42"
            }
        })

        result = observer.observe()

        assert result.value == "42"
        assert result.metadata["extractor_type"] == "command"

    def test_unknown_extractor_type(self) -> None:
        """Test that unknown extractor type raises error."""
        observer = MetricObserver({
            "extractor": {
                "type": "unknown_type"
            }
        })

        result = observer.observe()

        assert result.value is None
        assert "error" in result.metadata


class TestServiceObserver:
    """Tests for ServiceObserver."""

    def test_check_process_running(self) -> None:
        """Test checking if a process is running."""
        # Use 'python' - guaranteed to be running since we're in a Python test
        observer = ServiceObserver({
            "check_type": "process",
            "service_name": "python"
        })

        result = observer.observe()

        assert result.value is True
        assert result.metadata["check_type"] == "process"
        assert result.metadata["service_name"] == "python"

    def test_check_process_not_running(self) -> None:
        """Test checking if a process is not running."""
        observer = ServiceObserver({
            "check_type": "process",
            "service_name": "definitely_not_running_process_12345"
        })

        result = observer.observe()

        assert result.value is False

    def test_unknown_check_type(self) -> None:
        """Test that unknown check type returns error."""
        observer = ServiceObserver({
            "check_type": "unknown",
            "service_name": "test"
        })

        result = observer.observe()

        assert result.value is False
        assert "error" in result.metadata
