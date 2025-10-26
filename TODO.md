# Lighthouse TODO

## StatefulLogPatternObserver Enhancements

### Heuristic Detection of Log Rotation Naming Schemes
Currently hardcoded to check `.log.1` for rotation detection. Should support:
- Common patterns: `.log.1`, `.log.2`, etc.
- Dated patterns: `.log-YYYYMMDD`, `.log.YYYY-MM-DD`
- Old/archive patterns: `.log.old`, `.log.bak`
- Compressed patterns: `.log.1.gz`, `.log.gz`

Implementation approach: Glob for `{log_file}*` and check which files have matching fingerprints.

### Handle Multiple Rotations Between Observations
Current implementation assumes only one rotation occurred between observations. If logs rotate multiple times (e.g., `.log` → `.log.1` → `.log.2`), the offset may apply to `.log.2` or beyond.

Implementation approach: Walk through `.log.1`, `.log.2`, `.log.3`, etc. to find which file has our stored fingerprint, then continue reading from there.

## Future Features

### Additional Observer Types
- HTTP endpoint observer (check status codes, response times)
- Database query observer (check row counts, query results)
- File existence/modification time observer

### Additional Notifier Types
- Email notifier
- Slack notifier
- Discord notifier
- Custom webhook with templating

### Configuration Enhancements
- Environment variable substitution in config
- Config validation on startup
- Hot-reload of configuration without restart
