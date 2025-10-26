# Lighthouse Tests

This directory contains the test suite for Lighthouse.

## Test Structure

- `test_config.py` - Configuration loading and validation tests
- `test_state.py` - State management and rate limiting tests
- `test_notifier.py` - Pushover notification integration tests
- `test_watcher.py` - Log file watching and pattern matching tests
- `test_daemon.py` - Main daemon orchestration tests
- `test_integration.py` - End-to-end integration tests

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=lighthouse --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run specific test
pytest tests/test_config.py::TestLoadConfig::test_load_valid_config

# Run with verbose output
pytest -v

# Run only integration tests
pytest tests/test_integration.py

# Run only unit tests (exclude integration)
pytest --ignore=tests/test_integration.py
```

## Test Coverage

The test suite aims for high coverage of:
- Configuration validation
- State persistence and rate limiting logic
- Notification sending and error handling
- Log file watching and pattern matching
- End-to-end system integration

## Writing Tests

When adding new features:
1. Write unit tests for individual components
2. Write integration tests for end-to-end workflows
3. Use mocks for external dependencies (Pushover API, file system events)
4. Use temporary directories (`tmp_path` fixture) for file operations
