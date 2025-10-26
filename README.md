# Lighthouse

[![CI](https://gitea.notyourz.org/hall/lighthouse/actions/workflows/ci.yml/badge.svg)](https://gitea.notyourz.org/hall/lighthouse/actions)

A lightweight, plugin-driven monitoring daemon that watches logs and metrics and delivers alerts through Pushover, webhooks, or custom notifiers.

**Target Platform**: Linux (systemd-based distributions)

## Overview

Lighthouse runs as a long-lived daemon. Each *watcher* combines:

- an **observer** (what to collect),
- a **trigger** (when to check),
- an **evaluator** (whether to alert), and
- one or more **notifiers** (where to send the alert).

Configuration is declarative YAML validated by Pydantic, and the plugin registry makes it easy to extend Lighthouse with new components.

## Features

- **Flexible Watchers**: Mix and match observers, triggers, and evaluators for logs, metrics, and services.
- **Smart Alerting**: Built-in deduplication and rate limiting prevent notification spam.
- **Multiple Destinations**: Pushover, webhooks, console output, and placeholders for additional notifiers.
- **Extensible Plugins**: Simple registration decorators for custom observers, triggers, evaluators, and notifiers.
- **Config Validation**: Schema validation catches misconfigurations before the daemon starts.

## Installation

```bash
# (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install Lighthouse
python -m pip install .

# Or for development (editable install with extras)
python -m pip install -e .[dev]
```

## Configuration

Copy the example configuration and edit it to fit your environment:

```bash
cp config.yaml.example config.yaml
```

The configuration uses the plugin-based layout:

```yaml
watchers:
  - name: "Restic Backup Errors"
    observer:
      type: "log_pattern"
      config:
        log_file: "/var/log/restic-backup.log"
        patterns:
          - "ERROR"
          - "FATAL"
    trigger:
      type: "file_event"
      config:
        path: "/var/log/restic-backup.log"
        events: ["modified"]
    evaluator:
      type: "pattern_match"
      config:
        severity: "high"

notifiers:
  - type: "pushover"
    config:
      user_key: "your-user-key"
      api_token: "your-api-token"
  - type: "console"
    config: {}

rate_limiting:
  cooldown_seconds: 3600
  max_per_hour: 10

state_dir: "/var/lib/lighthouse"
```

See `config.yaml.example` for additional watcher scenarios including metrics, service checks, and scheduled triggers.

## Webhook Triggers

Lighthouse supports webhook triggers for external systems (CI/CD, backup scripts, etc.) to initiate monitoring checks.

### Setup

1. Generate an API key:
   ```bash
   lighthouse api-key generate -o /etc/lighthouse/webhook-api-keys.txt
   ```

2. Configure webhook trigger:
   ```yaml
   watchers:
     - name: "backup-check"
       trigger:
         type: "webhook"
         config:
           port: 8888
           api_key_file: "/etc/lighthouse/webhook-api-keys.txt"
           host: "127.0.0.1"  # Localhost only
   ```

3. Trigger from external system:
   ```bash
   curl -X POST http://127.0.0.1:8888/api \
     -H "Authorization: Bearer your-generated-key" \
     -H "Content-Type: application/json" \
     -d '{"target": "backup-check", "timestamp": "2025-10-26T12:00:00Z"}'
   ```

**Note**: The connection will be reset immediately (TCP RST) - this is normal! The webhook processes requests asynchronously.

### TLS/HTTPS with Reverse Proxy

For external webhooks, use a reverse proxy (nginx, caddy) for TLS termination:

**Nginx Example**:
```nginx
# /etc/nginx/sites-available/lighthouse-webhook
server {
    listen 443 ssl http2;
    server_name webhook.example.com;

    ssl_certificate /etc/letsencrypt/live/webhook.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/webhook.example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location /api {
        proxy_pass http://127.0.0.1:8888/api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Handle connection resets gracefully
        proxy_ignore_client_abort on;
    }
}
```

**Caddy Example**:
```
webhook.example.com {
    reverse_proxy /api localhost:8888
}
```

## Running the Daemon

```bash
# Run in the foreground for quick smoke tests
python -m lighthouse.daemon --config config.yaml --foreground
```

For a permanent deployment, create a systemd unit that executes the same command and points to your configuration file. Example unit files can be modelled on the snippets under `systemd/`.
An example unit might look like:

```ini
[Unit]
Description=Lighthouse monitoring daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/env python -m lighthouse.daemon --config /etc/lighthouse/config.yaml --foreground
WorkingDirectory=/etc/lighthouse
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Command Line Interface

The `lighthouse` CLI provides commands for managing the daemon, configuration, API keys, watchers, and sending manual notifications:

```bash
# Validate configuration
lighthouse config validate

# Generate API keys for webhook triggers
lighthouse api-key generate -o /etc/lighthouse/webhook-api-keys.txt

# Start the daemon
lighthouse daemon start

# List all configured watchers
lighthouse watcher list

# Manually trigger a specific watcher
lighthouse watcher trigger "Watcher Name"

# Send manual notification
lighthouse notify "Title" "Message" --severity high
```

## Architecture

- **`lighthouse.daemon`**: Entry point that loads configuration, wires watchers, and runs the main loop.
- **`lighthouse.coordinator`**: Orchestrates observer/trigger/evaluator combinations and captures observation history.
- **`lighthouse.plugins`**: Imports all built-in plugins and exposes factory helpers.
- **`lighthouse.state`**: Persists rate-limiting state between runs.
- **`lighthouse.notifiers` / `observers` / `triggers` / `evaluators`**: Built-in plugin implementations.
- **`config.yaml`**: Declarative configuration validated by `lighthouse.config.Config`.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e .[dev]

ruff check .
pytest
mypy lighthouse
```

The daemon can be started with `python -m lighthouse.daemon --config config.yaml --foreground` for iterative testing.

## License

Apache License 2.0 - see `LICENSE` for details.

## Known Limitations

### File System Event Throttling

The `watchdog` library only watches directories, not individual files. This means every filesystem event in a watched directory triggers our handler, even during throttle periods. We use timestamp checks to avoid expensive file I/O, but we still process every event.

In high-activity environments (busy directories, network drives, millions of events/sec), this creates significant overhead from watchdog's event queue + our filtering + timestamp checks.

**TODO**: Implement true per-file watching to eliminate event processing during throttle periods. Options: fork watchdog, use platform-specific APIs (inotify/FSEvents/ReadDirectoryChangesW), or find/create alternative library.

## Contributing

Contributions welcome! Please open an issue or pull request.
