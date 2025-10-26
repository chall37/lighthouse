"""
Centralized logging configuration for Lighthouse.

Provides consistent logging setup across all modules with configurable
levels and formatting.
"""

import logging
import logging.handlers
import sys


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB default
    backup_count: int = 5
) -> None:
    """
    Configure logging for Lighthouse.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file (logs to console if not provided)
        max_bytes: Maximum bytes per log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter with timestamp, level, module, and message
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure root logger
    root_logger = logging.getLogger("lighthouse")
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (optional)
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Prevent propagation to root logger
    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    # Strip 'lighthouse.' prefix if present for cleaner names
    if name.startswith("lighthouse."):
        name = name[11:]

    return logging.getLogger(f"lighthouse.{name}")
