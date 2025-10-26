# Lighthouse

## Project Overview

Lighthouse is a lightweight, flexible notification daemon for monitoring system logs and sending alerts via Pushover. It is written in Python and designed to run as a systemd service on Linux.

The core functionality involves watching specified log files for configured error patterns. When a pattern is matched, Lighthouse sends a notification through Pushover. It includes features like rate limiting and deduplication to avoid alert spam.

The project is structured as follows:

-   `lighthouse/daemon.py`: The main entry point for the daemon, containing the core logic for watching logs and sending notifications.
-   `lighthouse/cli.py`: A command-line interface for sending manual notifications (currently a placeholder).
-   `lighthouse/config.py`: Handles loading the YAML configuration.
-   `lighthouse/notifier.py`: Manages sending notifications via Pushover.
-   `lighthouse/state.py`: Tracks sent notifications for deduplication and rate limiting.
-   `lighthouse/watcher.py`: Contains the log watching logic.
-   `pyproject.toml`: Defines project metadata, dependencies, and entry points.
-   `config.yaml.example`: An example configuration file.
-   `tests/`: Contains the project's tests.

## Building and Running

### Dependencies

The project's dependencies are listed in `pyproject.toml` and can be installed using pip:

```bash
pip install -r requirements.txt
```

### Running the Daemon

To run the daemon in the foreground for development:

```bash
python lighthouse/daemon.py --config config.yaml
```

To run as a systemd service:

1.  Copy the service file: `sudo cp systemd/lighthouse.service /etc/systemd/system/`
2.  Reload systemd: `sudo systemctl daemon-reload`
3.  Enable and start the service:
    ```bash
    sudo systemctl enable lighthouse
    sudo systemctl start lighthouse
    ```

### Running Tests

Tests are located in the `tests/` directory and can be run using pytest:

```bash
python -m pytest tests/
```

## Development Conventions

-   The project uses `ruff` for linting and `mypy` for type checking.
-   Configuration is managed through a `config.yaml` file.
-   The `lighthouse-notify` CLI is intended to communicate with the daemon via a Unix socket, but this is not yet implemented.
