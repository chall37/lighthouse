"""
Main daemon entry point for Lighthouse (new architecture).
"""

import argparse
import signal
import sys
import time
from pathlib import Path
from typing import Any

from lighthouse.config import load_config
from lighthouse.coordinator import WatcherCoordinator, create_watcher_coordinator
from lighthouse.core import AlertDecision
from lighthouse.logging_config import get_logger, setup_logging
from lighthouse.plugins import create_notifier
from lighthouse.state import StateManager

logger = get_logger(__name__)


class LighthouseDaemon:
    """Main daemon class that coordinates watchers and notifications."""

    def __init__(self, config_path: str) -> None:
        """
        Initialize the daemon.

        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.state_dir = Path(self.config.state_dir)

        # Initialize state manager for rate limiting
        state_file = self.state_dir / "alerts.json"
        self.state = StateManager(str(state_file))

        # Initialize notifiers
        self.notifiers = [
            create_notifier(n.type, n.config)
            for n in self.config.notifiers
        ]

        # Watcher coordinators
        self.coordinators: list[WatcherCoordinator] = []
        self.running = False

    def _handle_alert(
        self,
        watcher_name: str,
        decision: AlertDecision,
        _priority: int | None
    ) -> None:
        """
        Handle an alert decision from a watcher.

        Args:
            watcher_name: Name of the watcher that triggered
            decision: The alert decision
            _priority: Optional priority override (unused currently)
        """
        # Check rate limiting
        # Use decision.message as the "pattern" for rate limiting purposes
        should_send = self.state.should_send_alert(
            watcher_name=watcher_name,
            pattern=decision.message[:100],  # Use first 100 chars as key
            cooldown_seconds=self.config.rate_limiting.cooldown_seconds,
            max_per_hour=self.config.rate_limiting.max_per_hour
        )

        if not should_send:
            logger.info("Alert rate limited for watcher '%s'", watcher_name)
            return

        # Send to all notifiers
        for notifier in self.notifiers:
            try:
                success = notifier.notify(decision, watcher_name)
                # Notifiers already log their own success/failure
                if not success:
                    logger.warning(
                        "Notifier %s returned False for watcher '%s'",
                        notifier.__class__.__name__,
                        watcher_name
                    )
            except Exception:
                logger.error(
                    "Error sending notification via %s for watcher '%s'",
                    notifier.__class__.__name__,
                    watcher_name,
                    exc_info=True
                )

        # Record alert in state
        self.state.record_alert(watcher_name, decision.message[:100])

    def setup_watchers(self) -> None:
        """Set up all watcher coordinators from configuration."""
        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

        for watcher_config in self.config.watchers:
            coordinator = create_watcher_coordinator(
                watcher_config=watcher_config,
                state_dir=str(self.state_dir),
                on_alert=self._handle_alert,
            )
            self.coordinators.append(coordinator)

        logger.info("Configured %s watcher(s)", len(self.coordinators))

    def start(self) -> None:
        """Start the daemon."""
        logger.info("Starting Lighthouse daemon")

        self.setup_watchers()

        # Start all coordinators
        for coordinator in self.coordinators:
            coordinator.start()
            logger.info("Started watcher '%s'", coordinator.name)

        self.running = True
        logger.info("Lighthouse daemon running")

        # Keep the main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
            self.stop()

    def stop(self) -> None:
        """Stop the daemon."""
        logger.info("Stopping Lighthouse daemon")
        self.running = False

        # Stop all coordinators
        for coordinator in self.coordinators:
            coordinator.stop()
            logger.info("Stopped watcher '%s'", coordinator.name)

        logger.info("Lighthouse daemon stopped")


def main() -> None:
    """Entry point for the daemon."""
    parser = argparse.ArgumentParser(description="Lighthouse monitoring daemon")
    parser.add_argument(
        '--config',
        default='/etc/lighthouse/config.yaml',
        help='Path to configuration file (default: /etc/lighthouse/config.yaml)'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Log level (default: INFO)'
    )
    parser.add_argument(
        '--log-file',
        help='Optional log file path (logs to console if not specified)'
    )
    args = parser.parse_args()

    # Initialize logging
    setup_logging(level=args.log_level, log_file=args.log_file)

    daemon = LighthouseDaemon(args.config)

    # Set up signal handlers
    def signal_handler(_sig: int, _frame: Any) -> None:
        logger.info("Shutdown signal received")
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        daemon.start()
    except Exception:
        logger.critical("Fatal error", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
