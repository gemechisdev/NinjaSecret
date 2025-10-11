# Main Wrapper Service Documentation

## Overview

The `main.py` file provides a production-ready wrapper service for the NinjaSecret bot, ensuring 24/7 availability with automatic restart capabilities.

## Features

### 1. **Automatic Restart on Failure**
- The bot runs as a subprocess and is automatically restarted if it crashes
- Configurable restart delay (5 seconds by default)
- Graceful cleanup of crashed processes

### 2. **Health Monitoring Endpoints**
The wrapper exposes three HTTP endpoints for monitoring:

- **`GET /`** - Root endpoint returning bot status
  ```json
  {"message": "NinjaSecret Bot is running"}
  ```

- **`GET /health`** - Health check endpoint with uptime information
  ```json
  {
    "status": "healthy",
    "uptime_seconds": 3600
  }
  ```
  Returns 503 status code if bot is not running.

- **`GET /ping` and `HEAD /ping`** - Simple ping endpoints
  ```json
  {"pong": "ok"}
  ```

### 3. **Detailed Logging**
- All logs include timestamps in `HH:MM:SS` format
- Process lifecycle events are logged
- Uptime is logged every 60 seconds
- Health check status changes are logged (not every check, only on status change)

### 4. **Process Management**
- Bot runs in a separate thread to avoid blocking the web server
- Proper process cleanup on errors (graceful terminate, then force kill if needed)
- Subprocess output is piped to stdout/stderr for visibility

## Configuration

### Environment Variables

- **`PORT`** - Port for the uvicorn web server (default: 8000)
  ```bash
  export PORT=8000
  ```

## Running the Service

### Development
```bash
python3 main.py
```

### Production (Docker)
The Dockerfile is configured to run the wrapper automatically:
```dockerfile
CMD python3 main.py
```

### Docker Build & Run
```bash
# Build the image
docker build -t ninjasecret-bot .

# Run the container
docker run -p 8000:8000 --env-file .env ninjasecret-bot
```

## Architecture

```
main.py (FastAPI/uvicorn)
    │
    ├── Web Server Thread (main thread)
    │   ├── GET /
    │   ├── GET /health
    │   └── GET /ping
    │
    └── Bot Manager Thread (daemon)
        └── NinjaSecret Bot (subprocess)
            └── Auto-restarts on exit
```

## Monitoring

### Health Checks
Most deployment platforms (Render, Railway, Heroku, etc.) support health checks:

- **Health Check Path**: `/health`
- **Expected Response**: HTTP 200 with `{"status": "healthy", ...}`
- **Unhealthy Response**: HTTP 503

### Uptime Tracking
The `/health` endpoint reports bot uptime in seconds, which can be used for monitoring and alerting.

## Error Handling

### Bot Crashes
When the bot crashes:
1. The exit code and uptime are logged
2. Process cleanup is attempted (terminate → kill if needed)
3. A 5-second delay occurs before restart
4. The bot is automatically restarted

### Thread Safety
- The `run_bot()` function catches all exceptions to prevent thread crashes
- Health check endpoint uses thread-safe status tracking

## Differences from Direct Bot Execution

| Aspect | Direct (`python3 -m NinjaSecret`) | Wrapper (`python3 main.py`) |
|--------|----------------------------------|----------------------------|
| Auto-restart | ❌ No | ✅ Yes |
| Health endpoints | ⚠️ Internal only (port 8000) | ✅ External (configurable port) |
| Uptime tracking | ❌ No | ✅ Yes |
| Process monitoring | ❌ No | ✅ Yes |
| Crash recovery | ❌ Manual restart needed | ✅ Automatic |

## Best Practices

1. **Monitor the `/health` endpoint** - Set up monitoring to alert on 503 responses
2. **Check logs regularly** - The wrapper provides detailed logging of bot lifecycle
3. **Set appropriate PORT** - Ensure the PORT environment variable matches your deployment platform's requirements
4. **Use in production** - This wrapper is designed for production deployments where 24/7 availability is critical

## Troubleshooting

### Bot keeps restarting
- Check NinjaSecret logs for the actual error
- Ensure all environment variables are set correctly (API_ID, BOT_TOKEN, MONGO_DB_URI, etc.)
- Verify database connectivity

### Health endpoint returns 503
- Check if the bot subprocess is running
- Look for error messages in the logs
- Verify the bot can start successfully

### Port already in use
- Change the PORT environment variable
- Ensure no other service is using the port
- Check for zombie processes: `ps aux | grep python`

## Migration from Old Setup

If you were previously running the bot directly:

**Old:**
```dockerfile
CMD python3 -m NinjaSecret
```

**New:**
```dockerfile
CMD python3 main.py
```

No other changes are needed - the wrapper is backward compatible and requires no changes to the bot code.
