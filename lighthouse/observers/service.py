"""
Observes systemd service or process status.
"""

import subprocess  # nosec B404 - Required for system monitoring (services)
from datetime import datetime

from lighthouse.core import ObservationResult
from lighthouse.core import Observer as BaseObserver
from lighthouse.logging_config import get_logger
from lighthouse.registry import register_observer

logger = get_logger(__name__)


@register_observer("service")
class Observer(BaseObserver):
    """
    Observes systemd service or process status.

    Config:
        check_type: "systemd" or "process"
        service_name: Name of service/process to check
    """

    def observe(self) -> ObservationResult:
        """Check if service/process is running."""
        check_type = self.config["check_type"]
        service_name = self.config["service_name"]

        try:
            if check_type == "systemd":
                is_active = self._check_systemd(service_name)
            elif check_type == "process":
                is_active = self._check_process(service_name)
            else:
                raise ValueError(f"Unknown check_type: {check_type}")

            status = "running" if is_active else "not running"
            logger.info("Checked service %s: %s", service_name, status)

            return ObservationResult(
                value=is_active,
                timestamp=datetime.now(),
                metadata={
                    "check_type": check_type,
                    "service_name": service_name
                }
            )
        except Exception as e:
            logger.error("Error checking service %s: %s", service_name, e)
            return ObservationResult(
                value=False,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )

    def _check_systemd(self, service_name: str) -> bool:
        """Check if systemd service is active."""
        result = subprocess.run(
            ["systemctl", "is-active", service_name],  # nosec B603 B607 - Standard systemd utility
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0

    def _check_process(self, process_name: str) -> bool:
        """Check if process is running by name (substring match)."""
        # Use ps and check if process_name appears in output
        result = subprocess.run(
            ["ps", "ax", "-o", "comm"],  # nosec B603 B607 - Standard ps utility
            capture_output=True,
            text=True,
            check=False
        )
        return process_name in result.stdout


# Export for dynamic importing
ServiceObserver = Observer
__all__ = ["ServiceObserver"]
