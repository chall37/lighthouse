"""
Opaque webhook trigger with constant-time response.
"""

import http.server
import json
import socket
import socketserver
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from lighthouse.core import Trigger as BaseTrigger
from lighthouse.logging_config import get_logger
from lighthouse.registry import register_trigger

logger = get_logger(__name__)


@register_trigger("webhook")
class Trigger(BaseTrigger):
    """
    Opaque webhook trigger with constant-time response.

    Security design:
    - Single opaque endpoint: POST /api (never varies)
    - Immediate TCP RST on all requests (constant timing)
    - Background async processing (no timing side-channels)
    - Bearer token authentication
    - Timestamp-based replay protection (±5 min tolerance)
    - Rate-limited failure logging

    Config:
        port: Port to listen on (default: 8888)
        api_key_file: Path to file containing valid API keys (one per line)
        host: Host to bind to (default: "127.0.0.1" for localhost only)
        watcher_map: Dict mapping watcher names to callbacks

    Request format:
        POST /api
        Authorization: Bearer <token>
        Content-Type: application/json

        {"target": "watcher-name", "timestamp": "2025-10-26T12:00:00Z"}
    """

    def __init__(self, config: dict[str, Any], callback: Callable[[], None]) -> None:
        super().__init__(config, callback)
        self.server: socketserver.TCPServer | None = None
        self.server_thread: threading.Thread | None = None
        self.watcher_callbacks: dict[str, Callable[[], None]] = {}

        # Track failed auth attempts for rate-limited logging
        self.failed_attempts: dict[str, int] = defaultdict(int)
        self.last_log_time = time.time()
        self.log_interval = 60  # Log summary every 60 seconds
        self.timestamp_tolerance = timedelta(minutes=5)

    def register_watcher(self, name: str, callback: Callable[[], None]) -> None:
        """Register a watcher that can be triggered via webhook."""
        self.watcher_callbacks[name] = callback

    def _load_api_keys(self) -> set[str]:
        """Load valid API keys from file."""
        api_key_file = self.config.get("api_key_file")
        if not api_key_file:
            logger.warning("No api_key_file configured for webhook trigger")
            return set()

        key_path = Path(api_key_file)
        if not key_path.exists():
            logger.error("API key file not found: %s", api_key_file)
            return set()

        try:
            keys = set()
            for line in key_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    keys.add(line)
            logger.info("Loaded %d API key(s) from %s", len(keys), api_key_file)
            return keys
        except Exception:
            logger.error("Failed to load API keys from %s", api_key_file, exc_info=True)
            return set()

    def _log_failed_attempts(self, force: bool = False) -> None:
        """Log summary of failed attempts (rate-limited)."""
        current_time = time.time()

        if not force and current_time - self.last_log_time < self.log_interval:
            return

        if self.failed_attempts:
            total_failures = sum(self.failed_attempts.values())
            logger.warning(
                "Webhook failures in last %ds: %d total from %d IP(s)",
                int(current_time - self.last_log_time),
                total_failures,
                len(self.failed_attempts)
            )
            top_offenders = sorted(
                self.failed_attempts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            for ip, count in top_offenders:
                logger.warning("  %s: %d attempts", ip, count)

            self.failed_attempts.clear()

        self.last_log_time = current_time

    def _validate_timestamp(self, timestamp_str: str) -> bool:
        """Validate timestamp is within tolerance window."""
        try:
            request_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.now(UTC)
            delta = abs(now - request_time)
            return delta <= self.timestamp_tolerance
        except Exception:
            return False

    def _process_request_async(
        self,
        client_ip: str,
        auth_header: str,
        body: bytes,
        valid_api_keys: set[str]
    ) -> None:
        """Process webhook request asynchronously after sending RST."""
        # Validate Authorization header
        if not auth_header.startswith("Bearer "):
            self.failed_attempts[client_ip] += 1
            self._log_failed_attempts()
            return

        token = auth_header[7:]  # Remove "Bearer " prefix
        if token not in valid_api_keys:
            self.failed_attempts[client_ip] += 1
            self._log_failed_attempts()
            return

        # Parse JSON body
        try:
            data = json.loads(body)
            target = data.get("target")
            timestamp = data.get("timestamp")

            if not target or not timestamp:
                self.failed_attempts[client_ip] += 1
                self._log_failed_attempts()
                return

        except Exception:
            self.failed_attempts[client_ip] += 1
            self._log_failed_attempts()
            return

        # Validate timestamp (replay protection)
        if not self._validate_timestamp(timestamp):
            self.failed_attempts[client_ip] += 1
            self._log_failed_attempts()
            return

        # Find and trigger watcher
        callback = self.watcher_callbacks.get(target)
        if not callback:
            self.failed_attempts[client_ip] += 1
            self._log_failed_attempts()
            return

        # Valid request - trigger callback
        try:
            callback()
            logger.info("Webhook triggered watcher: %s", target)
        except Exception:
            logger.error("Error executing webhook callback for %s", target, exc_info=True)

    def start(self) -> None:
        """Start HTTP webhook server."""
        port = self.config.get("port", 8888)
        host = self.config.get("host", "127.0.0.1")

        valid_api_keys = self._load_api_keys()
        process_request_async = self._process_request_async
        failed_attempts = self.failed_attempts
        log_failed_attempts = self._log_failed_attempts

        class WebhookHandler(http.server.BaseHTTPRequestHandler):
            """Opaque webhook handler with constant-time response."""

            def log_message(self, format: str, *args: Any) -> None:
                """Suppress default request logging."""
                ...

            def do_POST(self) -> None:
                """Handle POST requests with immediate RST."""
                client_ip = self.client_address[0]

                # Read request data first
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length) if content_length > 0 else b''
                auth_header = self.headers.get('Authorization', '')
                path = self.path

                # IMMEDIATELY send TCP RST (constant-time response)
                try:
                    # Set SO_LINGER to 0 for immediate RST
                    self.request.setsockopt(
                        socket.SOL_SOCKET,
                        socket.SO_LINGER,
                        b'\x01\x00\x00\x00\x00\x00\x00\x00'  # struct linger {1, 0}
                    )
                    self.request.close()
                except Exception:
                    pass

                # Process request asynchronously in background
                if path == "/api":
                    threading.Thread(
                        target=process_request_async,
                        args=(client_ip, auth_header, body, valid_api_keys),
                        daemon=True
                    ).start()
                else:
                    # Wrong path - track as failed attempt
                    failed_attempts[client_ip] += 1
                    log_failed_attempts()

            def do_GET(self) -> None:
                """Reject GET requests with immediate RST."""
                client_ip = self.client_address[0]

                # IMMEDIATELY send TCP RST
                try:
                    self.request.setsockopt(
                        socket.SOL_SOCKET,
                        socket.SO_LINGER,
                        b'\x01\x00\x00\x00\x00\x00\x00\x00'
                    )
                    self.request.close()
                except Exception:
                    pass

                # Track as failed attempt (wrong method)
                failed_attempts[client_ip] += 1
                log_failed_attempts()

        # Create server with address reuse
        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer((host, port), WebhookHandler)

        # Start server in background thread
        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True
        )
        self.server_thread.start()

        logger.info("Webhook server started on %s:%d/api", host, port)

    def stop(self) -> None:
        """Stop HTTP webhook server."""
        if self.server:
            self._log_failed_attempts(force=True)
            self.server.shutdown()
            self.server.server_close()

            if self.server_thread:
                self.server_thread.join(timeout=5)

            logger.info("Webhook server stopped")


# Export with descriptive name for imports
WebhookTrigger = Trigger
__all__ = ["WebhookTrigger"]
