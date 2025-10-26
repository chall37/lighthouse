# Lighthouse - Project Vision

## Purpose

Lighthouse is a notification daemon designed to solve a common problem in system administration: **knowing when something goes wrong without constantly monitoring logs**. It acts as a vigilant watcher, scanning system logs and alerting you only when it matters.

**Platform**: Currently designed for Linux environments with systemd. The architecture uses systemd services and Unix sockets, making it Linux-focused for now. Future versions could support macOS (launchd) and Windows (services), but the initial implementation targets Linux servers.

## Origin Story

This project was born from the need to monitor critical backup operations (restic and iDrive) on a home server running Docker services, GitLab, Plex, and other applications. The goal was to have a lightweight, configurable solution that could:

1. Watch backup logs for failures
2. Allow custom scripts to send notifications (e.g., "Plex is down")
3. Be smart about alerts (no spam, deduplication)
4. Use Pushover for reliable mobile notifications

Rather than using heavyweight monitoring solutions (Nagios, Prometheus, etc.) or cloud services (Healthchecks.io), we wanted something simple, self-hosted, and focused on notifications.

## Core Philosophy

### Simplicity First
- YAML configuration, not a complex UI
- One daemon, one CLI tool
- Clear, readable code
- Easy to extend

### Smart, Not Noisy
- Rate limiting prevents alert fatigue
- Deduplication avoids repeated notifications for the same error
- Configurable cooldown periods
- Optional max alerts per hour

### Flexibility
- Watch any log file
- Use regex patterns for matching
- Trigger from any script
- Extensible architecture for future notification backends

## Architecture

### Components

**1. Main Daemon (`lighthouse.py`)**
- Runs as a systemd service
- Uses `watchdog` library for efficient file monitoring
- Maintains state in `.lighthouse/state.json`
- Handles rate limiting and deduplication
- Sends notifications via Pushover API

**2. CLI Tool (`lighthouse-notify`)**
- Simple interface for manual notifications
- Communicates with daemon via Unix socket
- Used by custom monitoring scripts

**3. Configuration (`config.yaml`)**
- Defines Pushover credentials
- Lists log files to watch
- Specifies error patterns (regex)
- Sets rate limiting rules

### Design Decisions

**Why Python?**
- Excellent libraries for file watching (`watchdog`)
- Easy to read and maintain
- Good for system scripting
- Strong community support

**Why Pushover?**
- Reliable push notifications
- Simple API
- One-time payment, no subscription
- Mobile apps for iOS and Android

**Why YAML?**
- Human-readable configuration
- Easy to edit and version control
- Standard in DevOps tooling

**Why Unix Socket?**
- Fast local IPC
- Simple and secure
- No network exposure
- Standard Unix pattern

## Use Cases

### 1. Backup Monitoring
Watch backup logs for failure messages and alert immediately when backups fail.

```yaml
watchers:
  - name: "Restic Backup"
    log_file: "/var/log/restic-backup-docker.log"
    patterns:
      - "ERROR"
      - "Backup failed"
```

### 2. Service Health Checks
Custom scripts check if services are accessible and alert if down.

```bash
#!/bin/bash
# Check if Plex is accessible
if ! curl -s http://plex.example.com > /dev/null; then
    lighthouse-notify "Plex Down" "Plex is not accessible"
fi
```

### 3. Security Monitoring
Watch auth logs for suspicious activity.

```yaml
watchers:
  - name: "SSH Failures"
    log_file: "/var/log/auth.log"
    patterns:
      - "Failed password"
      - "Invalid user"
```

### 4. Application Errors
Monitor application logs for errors.

```yaml
watchers:
  - name: "GitLab Errors"
    log_file: "/var/log/gitlab/gitlab-rails/production.log"
    patterns:
      - "ERROR"
      - "FATAL"
```

## Future Enhancements

### Potential Features
- **Priority levels**: Different notification priorities (Pushover does support this via the `priority` parameter)
- **Multiple notification backends**: Email, Slack, Discord, webhooks
- **Regex capture groups**: Include matched patterns in notifications
- **Time-based rules**: Different alerts during/outside business hours
- **Dashboard**: Simple web UI to view alert history
- **Alert grouping**: Bundle related alerts into single notification
- **Metrics**: Track alert frequency, cooldown effectiveness
- **Health monitoring**: Self-monitoring with heartbeat checks

### Plugin System
Future architecture could support plugins for:
- Custom notification backends
- Custom log parsers
- Custom alert logic
- Integrations with external systems

## Development Guidelines

### Code Quality Standards

**ALL code must pass these checks before committing:**

1. **Type Checking (mypy)**
   - Run: `python -m mypy lighthouse/ --exclude lighthouse/watcher.py --exclude lighthouse/notifier.py`
   - ALL functions must have complete type annotations:
     - Parameters: `def foo(x: int, y: str) -> bool:`
     - Return types: `-> None`, `-> str`, `-> list[int]`, etc.
     - Class attributes: `self.coordinators: list[WatcherCoordinator] = []`
   - Use proper type imports: `from typing import Any, Callable, Type`
   - No `Any` types unless absolutely necessary (explain why in comment)

2. **Linting (ruff)**
   - Run: `python -m ruff check .`
   - Auto-fix when possible: `python -m ruff check . --fix`
   - Follow PEP 8 naming conventions:
     - Classes: `PascalCase` (e.g., `WatcherCoordinator`, `ObservationResult`)
     - Functions/variables: `snake_case` (e.g., `create_watcher`, `load_config`)
     - Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`)
   - Organize imports properly (ruff will auto-fix)

3. **Testing (pytest)**
   - Run: `python -m pytest tests/ -v`
   - ALL tests must pass
   - Write tests for new functionality
   - Aim for >80% code coverage

### Code Style
- PEP 8 compliant (enforced by ruff)
- Complete type annotations on ALL functions (enforced by mypy)
- Docstrings for all public functions and classes
- Keep functions small and focused (< 50 lines ideally)
- Prefer explicit over implicit
- Use descriptive variable names

### Testing
- Unit tests for core logic
- Integration tests for full workflows
- Mock external API calls (Pushover)
- Test rate limiting and deduplication
- Test error conditions and edge cases

### Documentation
- Keep README.md up to date
- Document all configuration options
- Provide example configs
- Write clear error messages

### Security
- Never log sensitive credentials
- Use proper file permissions (600) for config
- Validate all inputs
- Sanitize log patterns (prevent ReDoS)

## Contributing

We welcome contributions! Areas where help is especially appreciated:

1. **Additional notification backends** (email, Slack, etc.)
2. **Improved log parsing** (structured logs, JSON, etc.)
3. **Better error handling** (retry logic, fallback notifications)
4. **Performance optimization** (handling very large log files)
5. **Documentation** (examples, tutorials, troubleshooting)

## License

Apache License 2.0 - Free to use, modify, and distribute with attribution.

## Contact

Issues and pull requests welcome on GitHub.

---

*Lighthouse: Guiding you to problems before they become disasters.*
