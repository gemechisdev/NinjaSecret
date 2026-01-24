# NinjaSecret Code Review Report

**Date:** January 24, 2026  
**Scope:** Complete review of files changed in the last commit  
**Focus:** Bug detection, functionality issues, best practices, and improvements

---

## Executive Summary

After a comprehensive review of the NinjaSecret codebase, I've identified **several critical issues**, **moderate concerns**, and **improvement opportunities**. The codebase implements a Telegram bot for sending secret/whisper messages with various features like burn-after-reading, timers, and reveal functionality.

### Issue Categories:
- 🔴 **Critical Issues** (4): Bugs that cause incorrect behavior or failures
- 🟡 **Moderate Issues** (8): Code quality, potential problems, improvements needed
- 🟢 **Minor/Style** (5): Code style, documentation, and minor improvements

---

## 🔴 Critical Issues

### 1. Security: Exposed Credentials in `config.py`

**File:** `config.py` (Lines 14-23)

**Issue:** Hardcoded sensitive credentials that should NEVER be in source code:

```python
API_ID = int(getenv("API_ID", "24408788"))
API_HASH = getenv("API_HASH", "1c77b4a5cdbedf00286208adece69e1a")
BOT_TOKEN = getenv("BOT_TOKEN", "8206335201:AAFAVQc_sEz42sdl12tqT9VmdDFCoc8n4hw")
MONGO_DB_URI = getenv("MONGO_DB_URI", "mongodb+srv://ninjasecretbot:ninjasecretbot@cluster0.yn5yeik.mongodb.net/?appName=Cluster0")
```

**Risk:** These credentials are exposed publicly. Anyone with access to this repository can:
- Control the bot
- Access the MongoDB database
- Perform unauthorized actions

**Fix Required:**
```python
API_ID = int(getenv("API_ID"))
API_HASH = getenv("API_HASH")
BOT_TOKEN = getenv("BOT_TOKEN")
MONGO_DB_URI = getenv("MONGO_DB_URI")

# Add validation
if not all([API_ID, API_HASH, BOT_TOKEN, MONGO_DB_URI]):
    raise SystemExit("[ERROR] - Missing required environment variables: API_ID, API_HASH, BOT_TOKEN, MONGO_DB_URI")
```

**Immediate Action Required:**
1. Revoke the exposed bot token via @BotFather
2. Change MongoDB password
3. Generate new API credentials from my.telegram.org
4. Remove default values from config.py

---

### 2. Duplicate Class Definition in `core/call.py` and `core/bot.py`

**Files:** `NinjaSecret/core/bot.py` and `NinjaSecret/core/call.py`

**Issue:** Both files define a class named `Hotty`, which causes confusion and potential import conflicts:

**bot.py (Line 9):**
```python
class Hotty(Client):
    def __init__(self):
        LOGGER(__name__).info(f"Starting Bot...")
        super().__init__(...)
```

**call.py (Line 12):**
```python
class Hotty:
    """Minimal Hotty class for compatibility"""
    def __init__(self):
        self.app = app
```

**Problem:** The `call.py` version is a stub that doesn't extend `Client` and has a circular import issue (`from NinjaSecret import app` imports from `__init__.py` which imports `Hotty` from `bot.py`).

**Fix:**
- Rename the class in `call.py` to something like `CallHandler` or `HottyStub`
- Or remove the duplicate class if it's not needed

---

### 3. Potential Infinite Loop / Memory Leak in `cleanup_expired_whispers`

**File:** `NinjaSecret/mongo/whisperdb.py` (Lines 263-278)

**Issue:** The cleanup function calls `mark_whisper_expired(whisper["inline_message_id"])` but doesn't handle cases where `inline_message_id` might be `None`:

```python
async def cleanup_expired_whispers():
    """Clean up expired whispers (run periodically)"""
    current_time = datetime.utcnow()

    expired_whispers = whisperdb.find({
        "settings.expires_at": {"$lt": current_time},
        "status": "active"
    })

    count = 0
    async for whisper in expired_whispers:
        await mark_whisper_expired(whisper["inline_message_id"])  # ❌ Can be None!
        count += 1

    return count
```

**Fix:**
```python
async for whisper in expired_whispers:
    inline_message_id = whisper.get("inline_message_id")
    if inline_message_id:
        await mark_whisper_expired(inline_message_id)
    else:
        # Mark expired using whisper_id directly
        await whisperdb.update_one(
            {"whisper_id": whisper.get("whisper_id")},
            {"$set": {"status": "expired"}}
        )
    count += 1
```

---

### 4. `is_heroku` Function Called Incorrectly

**File:** `NinjaSecret/misc.py` (Line 66)

**Issue:** `is_heroku` is a function but is being used without calling it:

```python
def heroku():
    global HAPP
    if is_heroku:  # ❌ Should be: if is_heroku():
        if config.HEROKU_API_KEY and config.HEROKU_APP_NAME:
```

**Problem:** `if is_heroku:` always evaluates to `True` because `is_heroku` is a function object (truthy), not the result of the function call.

**Fix:**
```python
if is_heroku():  # ✅ Call the function
```

---

## 🟡 Moderate Issues

### 5. Bare `except` Clauses Throughout the Codebase

**Files:** Multiple files including `__main__.py`, `bot.py`, `database.py`

**Issue:** Many bare `except:` clauses that catch all exceptions, including `KeyboardInterrupt` and `SystemExit`:

**Examples:**
```python
# __main__.py line 28-29
except:
    return {'rss': 0, 'vms': 0, 'percent': 0}

# bot.py line 80-85
except:
    continue

# database.py multiple locations
except:
    pass
```

**Problem:** This silently swallows all errors, making debugging extremely difficult.

**Fix:** Use specific exception types:
```python
except Exception as e:
    LOGGER(__name__).error(f"Error: {e}")
    return {'rss': 0, 'vms': 0, 'percent': 0}
```

---

### 6. Missing Error Handling in Async Context

**File:** `NinjaSecret/__main__.py` (Lines 186-197)

**Issue:** The `init()` function has a bare `except: pass` that silently ignores errors when loading banned users:

```python
try:
    users = await get_gbanned()
    for user_id in users:
        BANNED_USERS.add(user_id)
    users = await get_banned_users()
    for user_id in users:
        BANNED_USERS.add(user_id)
except:
    pass  # ❌ Silently ignores ALL errors
```

**Fix:**
```python
except Exception as e:
    LOGGER(__name__).warning(f"Could not load banned users: {e}")
```

---

### 7. Inconsistent Import Statement in `whisperdb.py`

**File:** `NinjaSecret/mongo/whisperdb.py` (Lines 311, 624, 696)

**Issue:** The function `get_user_whisper_stats` imports `datetime` at line 311, but `datetime` is already imported at the top of the file:

```python
async def get_user_whisper_stats(user_id: int) -> Dict:
    """Get user's whisper statistics..."""
    from datetime import datetime, timedelta  # ❌ Redundant import
```

**Fix:** Remove the redundant import since `datetime` is already imported at line 6.

---

### 8. Potential Race Condition in Pending Whispers Cache

**File:** `NinjaSecret/plugins/whisper/inline_handler.py` (Lines 50-54)

**Issue:** The pending whispers dictionary could have race conditions in high-traffic scenarios:

```python
# In-memory cache for pending whispers (before they are sent)
# Key: whisper_id, Value: whisper data dict
pending_whispers = {}
```

While the comment acknowledges this is safe in asyncio single-threaded event loop, there's no protection against dictionary modification during iteration in cleanup:

```python
# cleanup_task.py line 96-105
for whisper_id, data in pending_whispers.items():  # ❌ Can fail if dict modified
    ...
for whisper_id in to_remove:
    del pending_whispers[whisper_id]
```

**Fix:**
```python
# Use list() to create a snapshot
for whisper_id, data in list(pending_whispers.items()):
    ...
```

---

### 9. Hardcoded Log Group ID in `config.py`

**File:** `config.py` (Lines 31, 35)

**Issue:** Default log group IDs are hardcoded:

```python
LOGGER_ID = int(getenv("LOGGER_ID", "-1003029976514"))
LOG_GROUP_ID = int(getenv("LOG_GROUP_ID", "-1003029976514"))
```

**Problem:** These chat IDs will fail for new deployments where the bot isn't in these groups.

**Fix:** Make these required or handle gracefully:
```python
LOGGER_ID = int(getenv("LOGGER_ID")) if getenv("LOGGER_ID") else None
LOG_GROUP_ID = int(getenv("LOG_GROUP_ID")) if getenv("LOG_GROUP_ID") else None
```

---

### 10. Missing `ParseMode` Import in Timer Countdown

**File:** `NinjaSecret/plugins/whisper/cleanup_task.py` (Line 203)

**Issue:** The code uses `enums.ParseMode.MARKDOWN` but imports `enums` from `pyrogram`:

```python
from pyrogram import enums  # ✅ Correct import

await app.edit_inline_text(
    inline_message_id=inline_message_id,
    text=updated_message,
    parse_mode=enums.ParseMode.MARKDOWN,  # ✅ Correctly used
    reply_markup=create_whisper_keyboard(whisper_id)
)
```

**Status:** This is actually correctly implemented. No issue here.

---

### 11. Callback Error Handling Uses `print()` Instead of Logger

**Files:** `callbacks.py`, `inline_handler.py`, multiple plugins

**Issue:** Error handling uses `print()` statements instead of the proper logger:

```python
# callbacks.py line 222, 297, 325, 375, etc.
print(f"Could not update inline message with updated name: {e}")
print(f"Failed to edit burned message: {e}")
print(f"Whisper view error: {e}")
```

**Problem:** Print statements don't include timestamps, log levels, or module context.

**Fix:**
```python
logger.error(f"Could not update inline message: {e}")
```

---

### 12. Undefined Variable in `start.py`

**File:** `NinjaSecret/plugins/bot/start.py` (Line 103)

**Issue:** `START_IMG_URL` is used but not imported:

```python
chat_photo = userss_photo if userss_photo else START_IMG_URL  # ❌ Not imported
```

The import at line 13 is `from config import BANNED_USERS, OWNER_ID` but `START_IMG_URL` comes from config as `config.START_IMG_URL`.

**Fix:** Either import it directly or use `config.START_IMG_URL`:
```python
from config import BANNED_USERS, OWNER_ID, START_IMG_URL
# or
chat_photo = userss_photo if userss_photo else config.START_IMG_URL
```

---

## 🟢 Minor Issues / Improvements

### 13. Unnecessary String Formatting in Logs

**File:** `NinjaSecret/core/bot.py` (Line 11)

**Issue:** Using f-string without variables:

```python
LOGGER(__name__).info(f"Starting Bot...")  # ❌ No variables
```

**Fix:**
```python
LOGGER(__name__).info("Starting Bot...")
```

---

### 14. Music Bot Reference in Non-Music Bot

**File:** `NinjaSecret/core/bot.py` (Line 49)

**Issue:** Log message says "Music Bot" but this is a Whisper/Secret bot:

```python
LOGGER(__name__).info(f"Music Bot Started as {self.name}")
```

**Fix:**
```python
LOGGER(__name__).info(f"NinjaSecret Bot Started as {self.name}")
```

Similarly in `web_server.py` line 103:
```python
"description": "Telegram music bot with health monitoring endpoints"
```
Should be:
```python
"description": "NinjaSecret Telegram bot with health monitoring endpoints"
```

---

### 15. Deprecated `asyncio.get_event_loop()` Usage

**File:** `NinjaSecret/__main__.py` (Line 239)

**Issue:** Using deprecated `asyncio.get_event_loop()`:

```python
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
```

**Fix:** Use the modern approach:
```python
if __name__ == "__main__":
    asyncio.run(init())
```

---

### 16. Missing Type Hints in Several Functions

**Files:** Multiple files

**Issue:** Many functions lack proper type hints, making the code harder to understand:

```python
# whisperdb.py
async def store_whisper(data: Dict) -> str:  # ✅ Good
async def cleanup_expired_whispers():  # ❌ Missing return type
```

---

### 17. Documentation Inconsistencies

**Files:** Multiple documentation files

**Issue:** Several documentation files reference outdated features or have inconsistent information. For example, the bot is described as both a "Music Bot" and a "Whisper/Secret Bot" in different places.

---

## Architecture Observations

### Positive Aspects:
1. ✅ Good modular structure with separate plugins, utils, and core directories
2. ✅ Comprehensive whisper functionality with modifiers (burn, timer, reveal)
3. ✅ Good use of async/await patterns
4. ✅ Proper use of MongoDB with motor async driver
5. ✅ Language localization support via strings module
6. ✅ Health check endpoints for deployment platforms

### Areas for Improvement:
1. ⚠️ Circular imports between modules (call.py imports from __init__.py)
2. ⚠️ Mixed responsibility in some files (config.py has filters and dicts)
3. ⚠️ Inconsistent error handling patterns
4. ⚠️ Some code appears to be remnants from a music bot fork

---

## Recommendations

### Immediate Actions (Priority 1):
1. **CRITICAL:** Rotate all exposed credentials immediately
2. Fix `is_heroku` function call
3. Fix potential `None` handling in `cleanup_expired_whispers`
4. Rename duplicate `Hotty` class

### Short-term (Priority 2):
1. Replace bare `except` clauses with specific exception handling
2. Replace `print()` statements with proper logging
3. Fix undefined variable `START_IMG_URL` in start.py
4. Add proper error messages for missing environment variables

### Long-term (Priority 3):
1. Add comprehensive type hints
2. Refactor music bot references to whisper bot
3. Consider using asyncio.run() instead of deprecated get_event_loop()
4. Add unit tests for critical paths
5. Document the dual-message feature more thoroughly

---

## Conclusion

The NinjaSecret codebase has a solid foundation with good async patterns and modular design. However, the **exposed credentials** and several **bug fixes** need immediate attention before the next deployment. The code quality can be significantly improved by addressing the error handling and logging inconsistencies.

**Estimated effort to fix critical issues:** 2-4 hours  
**Estimated effort to fix all issues:** 1-2 days

---

*Report generated by Code Review Agent*
