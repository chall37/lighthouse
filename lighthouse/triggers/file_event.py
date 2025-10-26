"""
File system event trigger using watchdog.
"""

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer as WatchdogObserver

from lighthouse.core import Trigger as BaseTrigger
from lighthouse.registry import register_trigger

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver


@register_trigger("file_event")
class Trigger(BaseTrigger):
    """
    Triggers on file system events using watchdog.

    Config:
        path: File or directory to watch
        events: List of events to trigger on ("modified", "created", "deleted", "moved")
        recursive: Whether to watch subdirectories (default: False)
    """

    def __init__(self, config: dict[str, Any], callback: Callable[[], None]) -> None:
        super().__init__(config, callback)
        self.observer: BaseObserver | None = None
        self.event_handler: FileSystemEventHandler | None = None

    def start(self) -> None:
        """Start watching for file events."""
        path = Path(self.config["path"])
        events = self.config.get("events", ["modified"])
        recursive = self.config.get("recursive", False)

        # Create event handler
        self.event_handler = self._create_event_handler(events)

        # Start watchdog observer
        self.observer = WatchdogObserver()
        self.observer.schedule(
            self.event_handler,
            str(path.parent if path.is_file() else path),
            recursive=recursive
        )
        self.observer.start()

    def stop(self) -> None:
        """Stop watching for file events."""
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def _create_event_handler(self, events: list[str]) -> FileSystemEventHandler:
        """Create a watchdog event handler that calls our callback."""
        callback = self.callback
        watch_path = Path(self.config["path"])

        class Handler(FileSystemEventHandler):
            """Custom event handler for file system events."""

            def _should_trigger(self, event: FileSystemEvent) -> bool:
                """Check if this event should trigger the callback."""
                # If watching a specific file, only trigger for that file
                if isinstance(event.src_path, str):
                    event_path = event.src_path
                else:
                    event_path = event.src_path.decode()
                if watch_path.is_file() and Path(event_path) != watch_path:
                    return False
                return True

            def on_modified(self, event: FileSystemEvent) -> None:
                if "modified" in events and self._should_trigger(event):
                    callback()

            def on_created(self, event: FileSystemEvent) -> None:
                if "created" in events and self._should_trigger(event):
                    callback()

            def on_deleted(self, event: FileSystemEvent) -> None:
                if "deleted" in events and self._should_trigger(event):
                    callback()

            def on_moved(self, event: FileSystemEvent) -> None:
                if "moved" in events and self._should_trigger(event):
                    callback()

        return Handler()


# Export with descriptive name for imports
FileEventTrigger = Trigger
__all__ = ["FileEventTrigger"]
