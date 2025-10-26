"""
Cross-platform utilities for Lighthouse.
"""

import os
from pathlib import Path
from typing import Any

from lighthouse.logging_config import get_logger

# Conditional import for pywin32
if os.name == 'nt':
    try:
        import win32file
    except ImportError:
        win32file = None
else:
    win32file = None

logger = get_logger(__name__)


def get_file_fingerprint(path: str) -> tuple[Any, ...] | None:
    """
    Get a unique fingerprint for a file that is stable across renames.

    - On POSIX, this is (device, inode).
    - On Windows, this is (volume serial number, file index high, file index low).

    Args:
        path: The path to the file.

    Returns:
        A tuple representing the file fingerprint, or None if the file
        cannot be accessed or the platform is unsupported.
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return None

    try:
        if os.name == 'nt':  # Windows
            if not win32file:
                logger.warning("pywin32 is not installed, cannot get file fingerprint on Windows.")
                return None

            share_mode = (
                win32file.FILE_SHARE_READ |
                win32file.FILE_SHARE_WRITE |
                win32file.FILE_SHARE_DELETE
            )
            handle = win32file.CreateFile(
                path,
                win32file.GENERIC_READ,
                share_mode,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )
            info = win32file.GetFileInformationByHandle(handle)
            handle.Close()
            # (VolumeSerialNumber, nFileIndexHigh, nFileIndexLow)
            return (info[4], info[8], info[9])

        if os.name == 'posix':  # Linux, macOS, etc.
            stat_info = path_obj.stat()
            return (stat_info.st_dev, stat_info.st_ino)

        logger.warning("Unsupported OS for file fingerprinting: %s", os.name)
        return None
    except Exception as e:
        logger.error("Error getting fingerprint for file %s: %s", path, e)
        return None
