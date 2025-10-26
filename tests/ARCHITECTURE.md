# Lighthouse Plugin Architecture

## Overview

Lighthouse has been refactored into a flexible, plugin-based monitoring system with four core categories:

1. **Observers** - What to measure
2. **Triggers** - When to check
3. **Evaluators** - Should we alert
4. **Notifiers** - How to alert

## Architecture

### Core Components

- `lighthouse/core.py` - Base classes and data structures
- `lighthouse/registry.py` - Plugin registry and factory functions
- `lighthouse/plugins.py` - Plugin initialization module
- `lighthouse/coordinator.py` - Wires together observer + trigger + evaluator
- `lighthouse/daemon.py` - Main daemon that coordinates everything

### Plugins

#### Observers (`lighthouse/observers.py`)
- `log_pattern` - Match regex patterns in log files
- `metric` - Extract numeric values (line counts, regex captures, commands)
- `service` - Check systemd/process status

#### Triggers (`lighthouse/triggers.py`)
- `file_event` - Watchdog-based file monitoring
- `temporal` - Interval-based scheduling
- `manual` - Explicit CLI trigger
- `webhook` - HTTP webhook (stubbed)
- `process_event` - Process monitoring (stubbed)

#### Evaluators (`lighthouse/evaluators.py`)
- `pattern_match` - Alert when pattern found
- `threshold` - Alert when value crosses threshold
- `sequential_growth` - Alert when value doesn't improve over time
- `state_change` - Alert on boolean state changes

#### Notifiers (`lighthouse/notifiers.py`)
- `pushover` - Pushover API notifications
- `console` - Console/stdout notifications  
- `webhook` - HTTP webhook notifications
- `email` - Email notifications (stubbed)
- `slack` - Slack notifications (stubbed)

## Configuration

Example configuration:

```yaml
watchers:
  - name: "iDrive Persistent Failures"
    observer:
      type: "metric"
      config:
        extractor:
          type: "line_count"
          source: "/path/to/ERROR/permissionError.txt"
          pattern: "\\[FAILED\\]"
    trigger:
      type: "file_event"
      config:
        path: "/path/to/ERROR/permissionError.txt"
        events: ["modified"]
    evaluator:
      type: "sequential_growth"
      config:
        severity: "medium"

notifiers:
  - type: "pushover"
    config:
      user_key: "your-key"
      api_token: "your-token"

state_dir: "/var/lib/lighthouse"
```

## State Storage

- Location: `/var/lib/lighthouse/` (configurable via `state_dir`)
- Alert state: `alerts.json` - Rate limiting and deduplication
- Observation history: `{watcher_name}.history.json` - Per-watcher observation history

## Testing Status

✓ Config loading tests (7/7 passing)
- State manager tests (reuse old tests - unchanged)
- Observer tests (TODO)
- Trigger tests (TODO)
- Evaluator tests (TODO)  
- Notifier tests (reuse old Pushover tests)
- Coordinator tests (TODO)
- Daemon tests (TODO)
- Integration tests (TODO)

## Next Steps

1. Run state manager tests (should pass unchanged)
2. Create observer/trigger/evaluator unit tests
3. Create integration tests
4. Test with real iDrive monitoring
5. Update documentation
