# Fix Summary: Health Server and User Caching Issues

## Problem Statement

The bot had three main issues:
1. **Port Conflict Error**: Health server failing with "address already in use" error on port 10000
2. **User ID Display Issue**: When using numeric user IDs (e.g., `285969911`), the bot showed "User 285969911" instead of the actual name
3. **Premature Caching**: The bot was storing user targets in "recent targets" during inline query autocomplete, not just when the secret was actually sent

## Solutions Implemented

### 1. Fixed Port Conflict (NinjaSecret/web_server.py)

**Issue**: Both `main.py` FastAPI wrapper and `NinjaSecret/__main__.py` health server were trying to bind to the same PORT, causing conflicts.

**Solution**:
- Modified `start_health_server()` to use `HEALTH_PORT` environment variable if set
- Falls back to `PORT + 1` if `HEALTH_PORT` is not set (avoids conflict with main.py wrapper)
- Added graceful error handling for "address already in use" (errno 98)
- Added `reuse_address=True` to TCPSite for better port reuse
- When port is already in use, logs a warning and continues gracefully instead of failing

**Code Changes**:
```python
# Use HEALTH_PORT if available, otherwise fallback to PORT + 1
if port is None:
    main_port = int(os.getenv('PORT', 8000))
    port = int(os.getenv('HEALTH_PORT', main_port + 1))

# Graceful handling of port conflicts
except OSError as e:
    if e.errno == 98:  # Address already in use
        LOGGER(__name__).warning(f"Port {self.port} already in use...")
```

### 2. Fixed User ID Resolution (NinjaSecret/mongo/whisperdb.py)

**Issue**: When resolving numeric user IDs, the bot was falling back to "User {id}" display instead of fetching actual names.

**Solution**:
- Fixed potential None concatenation errors when `first_name` is None/empty
- Added null-safety: `(user.first_name or "")` to prevent crashes
- Added error logging to help debug user resolution failures
- Applied fixes to all three user resolution code paths:
  - Chat members lookup
  - Bot API (`app.get_users()`)
  - Userbot API (`userbot.get_users()`)

**Code Changes**:
```python
# Before:
display = user.first_name + (f" {user.last_name}" if user.last_name else "")

# After (null-safe):
display = (user.first_name or "") + (f" {user.last_name}" if user.last_name else "")

# Added error logging:
except Exception as e:
    print(f"Bot get_users failed for {ref}: {e}")
```

### 3. Fixed Premature Recent Targets Caching (NinjaSecret/plugins/whisper/inline_handler.py)

**Issue**: The bot was storing "recent targets" during inline query autocomplete (when user is still typing), not just when the secret was actually sent.

**Scenario**:
- User types: `@ninjasecretbot Hi @venop` → bot caches @venop as recent target
- User continues: `@ninjasecretbot Hi @venopyx` → bot caches @venopyx as recent target
- But user never sent the message to @venop!

**Solution**:
- Removed `store_recent_target()` calls from inline query handler (where inline results are created)
- Recent targets are now ONLY stored in `handle_chosen_inline_result()` (when message is actually sent)
- Updated `handle_chosen_inline_result()` to store ALL targets from whisper, not just the primary target
- Added support for `all_targets` field in whisper data to properly handle multiple recipients
- Excluded @all/@everyone from recent targets as intended

**Code Changes**:
```python
# Removed from inline query handler (lines 320-335):
# await store_recent_target(...) # REMOVED - was premature

# Enhanced in handle_chosen_inline_result():
all_targets = whisper.get("all_targets", [])
for target_id, target_username, original_token in all_targets:
    if target_id and original_token.lower() not in ["@all", "@everyone"]:
        await store_recent_target(...)  # Only when message is SENT
```

## Files Modified

1. `NinjaSecret/web_server.py` - Health server port configuration and error handling
2. `NinjaSecret/mongo/whisperdb.py` - User resolution null-safety and error logging
3. `NinjaSecret/plugins/whisper/inline_handler.py` - Recent targets caching timing

## Testing Recommendations

### 1. Port Conflict Test
```bash
# Set PORT to 10000 and run the bot
export PORT=10000
python3 main.py
# Should see: Warning about port in use, bot continues running
```

### 2. User ID Resolution Test
- Send inline query: `@ninjasecretbot Hello 285969911`
- Verify it shows actual name (e.g., "John Doe") instead of "User 285969911"
- Check logs for any "get_users failed" messages

### 3. Recent Targets Test
- Type inline query: `@ninjasecretbot Hi @user1` but DON'T send
- Type another: `@ninjasecretbot Hi @user2` and SEND this one
- Check recent targets - should only have @user2, not @user1

### 4. Multiple Targets Test
- Send: `@ninjasecretbot Secret message @user1,@user2`
- Check recent targets - should have both @user1 and @user2

## Environment Variables

New optional environment variable:
- `HEALTH_PORT` - Port for internal health server (default: PORT + 1)

Example:
```bash
export PORT=10000          # Main wrapper port
export HEALTH_PORT=10001   # Internal health server port
```

## Benefits

1. **No More Port Conflicts**: Bot starts reliably without "address already in use" errors
2. **Better User Experience**: Shows actual user names instead of "User {id}"
3. **Accurate Recent Targets**: Only stores targets when messages are actually sent
4. **Better Debugging**: Error logging helps identify API issues
5. **Null Safety**: Prevents crashes when users have no first_name

## Backward Compatibility

All changes are backward compatible:
- No changes to existing environment variables required
- Existing configurations work as-is
- Optional `HEALTH_PORT` variable for advanced configurations
- Fallback behavior maintains previous functionality

## Notes

- User resolution via `app.get_users()` is limited by Telegram API
- Bot can only fetch users who have started the bot or are in common groups
- Error logs will help identify when API limitations are hit
- The user info cache (for first_name, last_name) remains for performance
- Only the "recent targets" list respects the send-only policy
