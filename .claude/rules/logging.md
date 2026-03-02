# Logging System

> **Template**: Customize this file for your project's logging setup.
> Delete this notice and the example content, then fill in your own.

## Log File Locations

| Log Type | Path | Purpose |
|----------|------|---------|
| Application | `logs/app.log` | Main application logs |
| Error | `logs/error.log` | Error-level logs only |
| Access | `logs/access.log` | HTTP request logs |

## Log Format

Structured JSON format:
- `timestamp`: ISO 8601
- `level`: DEBUG / INFO / WARNING / ERROR
- `logger`: Source module
- `message`: Log message
- `request_id`: Request trace ID (if applicable)
- `exception`: Stack trace (on errors)

## Viewing Logs

```bash
# Tail application logs (pretty print with jq)
tail -f logs/app.log | jq

# Filter errors only
tail -f logs/app.log | jq 'select(.level == "ERROR")'

# Search by request ID
grep "REQUEST_ID" logs/app.log | jq

# Filter by module
tail -f logs/app.log | jq 'select(.logger | contains("module_name"))'
```

## Debugging with Logs

1. **Trace a request**: Use `request_id` from API response headers
2. **Pipeline issues**: Filter by logger name for the specific module
3. **Startup failures**: Check first 50 lines of log after restart

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Minimum log level |
| `LOG_FILE` | logs/app.log | Log file path |
| `LOG_FORMAT` | json | Log format (json or text) |
