"""
Pytest configuration and fixtures for Lighthouse tests.
"""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_path(tmp_path: Path) -> Path:
    """
    Provide a temporary directory for tests.

    This is a built-in pytest fixture that we're re-exposing.
    """
    return tmp_path
