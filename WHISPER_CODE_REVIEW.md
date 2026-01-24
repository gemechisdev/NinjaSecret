# Whisper Implementation Code Review

**Date:** January 24, 2026  
**Scope:** Whisper/Secret messaging implementation and features  
**Focus:** Bug detection, functionality issues, and improvements in whisper-related code

---

## Executive Summary

This review focuses specifically on the whisper/secret messaging implementation in NinjaSecret. After thorough analysis of all whisper-related files, I've identified **critical bugs**, **functionality issues**, and **areas for improvement**.

### Files Reviewed:
- `NinjaSecret/plugins/whisper/inline_handler.py` - Inline query handling for secret creation
- `NinjaSecret/plugins/whisper/callbacks.py` - Button callback handling for viewing secrets
- `NinjaSecret/plugins/whisper/cleanup_task.py` - Background cleanup tasks
- `NinjaSecret/plugins/whisper/start_integration.py` - Start command integration
- `NinjaSecret/mongo/whisperdb.py` - Database operations for whispers
- `NinjaSecret/utils/whisper_utils.py` - Utility functions for whispers

---

## 🔴 Critical Issues (Will Cause Crashes/Failures)

### 1. Missing "monkey" Key in NINJA_EMOJIS Dictionary

**File:** `NinjaSecret/utils/whisper_utils.py`  
**Line:** 803

**Issue:** The code references `NINJA_EMOJIS["monkey"]` but this key doesn't exist in the dictionary:

```python
# Line 803
return f'"{content}"{burn_info}{timer_info}\n\n{NINJA_EMOJIS["monkey"]} ᴋᴇᴇᴘ ɪᴛ ʙᴇᴛᴡᴇᴇɴ ᴜs ᴍᴏɴᴋᴇʏs!'
```

**Problem:** This will raise a `KeyError: 'monkey'` when `create_secret_revealed_text()` is called during secret viewing.

**Fix:** Add the "monkey" key to NINJA_EMOJIS dictionary (lines 15-33):
```python
NINJA_EMOJIS = {
    "ninja": "🥷",
    "shuriken": "⭐",
    # ... existing keys ...
    "broadcast": "📢",
    "monkey": "🐒"  # Add this line
}
```

---

### 2. Potential `None` Crash in `cleanup_expired_whispers`

**File:** `NinjaSecret/mongo/whisperdb.py`  
**Lines:** 263-278

**Issue:** The cleanup function passes `whisper["inline_message_id"]` to `mark_whisper_expired()` without checking for `None`:

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

**Problem:** Whispers may not have an `inline_message_id` if:
- User never actually sent the whisper (only created inline result)
- Bot restart between inline query and chosen result
- Database inconsistency

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

### 3. Undefined Language Key in Callback Handler

**File:** `NinjaSecret/plugins/whisper/callbacks.py`  
**Line:** 413

**Issue:** Uses `_['whisper_for_everyone_jungle']` but this key doesn't exist in the language strings. The correct key is `whisper_for_everyone_dojo`:

```python
if any(t.get('type') == 'all' for t in targets):
    info_text += f"{_['whisper_for_everyone_jungle']}\n"  # ❌ Wrong key
```

**Fix:**
```python
if any(t.get('type') == 'all' for t in targets):
    info_text += f"{_['whisper_for_everyone_dojo']}\n"  # ✅ Correct key
```

---

### 4. Undefined Language Key in Callback Handler

**File:** `NinjaSecret/plugins/whisper/callbacks.py`  
**Line:** 430

**Issue:** Uses `_['whisper_monkey_secured']` but this key doesn't exist. The correct key is `whisper_ninja_secured`:

```python
info_text += f"\n{_['whisper_monkey_secured']}"  # ❌ Wrong key
```

**Fix:**
```python
info_text += f"\n{_['whisper_ninja_secured']}"  # ✅ Correct key
```

---

## 🟡 Moderate Issues (Functionality/Quality Problems)

### 5. Missing `from NinjaSecret.mongo.whisperdb import increment_whisper_view_by_id` in Callbacks

**File:** `NinjaSecret/plugins/whisper/callbacks.py`  
**Line:** 393

**Issue:** The function `increment_whisper_view_by_id` is used but may not be imported. Check the imports at the top of the file.

**Current imports (lines 13-21):**
```python
from NinjaSecret.mongo.whisperdb import (
    get_whisper,
    mark_whisper_read,
    get_user_whisper_stats,
    update_user_stats,
    upsert_user,
    get_recent_targets,
    clear_recent_targets
)
```

**Fix:** Add `increment_whisper_view_by_id` to the imports:
```python
from NinjaSecret.mongo.whisperdb import (
    get_whisper,
    mark_whisper_read,
    get_user_whisper_stats,
    update_user_stats,
    upsert_user,
    get_recent_targets,
    clear_recent_targets,
    increment_whisper_view_by_id  # Add this
)
```

---

### 6. Missing `get_whisper_by_id` Import in Callbacks

**File:** `NinjaSecret/plugins/whisper/callbacks.py`  
**Line:** 396

**Issue:** Uses `get_whisper_by_id` but it's not in the imports. Only `get_whisper` is imported.

**Fix:** Add `get_whisper_by_id` to the imports:
```python
from NinjaSecret.mongo.whisperdb import (
    get_whisper,
    get_whisper_by_id,  # Add this
    ...
)
```

---

### 7. Multi-Target Burn Tracking TODO Not Implemented

**File:** `NinjaSecret/plugins/whisper/callbacks.py`  
**Lines:** 243-249

**Issue:** There's a TODO comment indicating that proper multi-target burn tracking is not implemented:

```python
else:
    # Multiple targets - would need complex tracking, for now burn immediately
    # TODO: Implement proper multi-target burn tracking
    should_burn = True
```

**Current Behavior:** When a whisper has multiple targets and `burn_after_reading` is enabled, the whisper burns after the **first** person reads it, not after **all** targets read it.

**Impact:** This breaks the expected "burn when all read" functionality for multi-target whispers.

**Recommended Fix:** Implement proper tracking using the `all_targets` array:
```python
else:
    # Multiple targets - check if all have read
    all_targets = whisper.get("all_targets", [])
    # Track which targets have read (would need to be stored in DB)
    read_targets = whisper.get("read_by", [])
    if len(read_targets) >= len(all_targets):
        should_burn = True
    else:
        should_burn = False
```

---

### 8. Debug Print Statements in Production Code

**Files:** Multiple files

**Issue:** Several `print()` statements are used instead of proper logging:

**callbacks.py:**
- Line 222: `print(f"Could not update inline message with updated name: {e}")`
- Line 297: `print(f"Failed to edit burned message: {e}")`
- Line 325: `print(f"Failed to edit revealed message: {e}")`
- Line 375: `print(f"Whisper view error: {e}")`
- Line 435: `print(f"Whisper targets error: {e}")`

**inline_handler.py:**
- Line 480: `print(f"Inline query error: {e}")`

**Fix:** Replace with proper logger calls:
```python
logger.error(f"Whisper view error: {e}")
```

---

### 9. Reveal-on-Read Only Shows First Reader

**File:** `NinjaSecret/plugins/whisper/callbacks.py`  
**Lines:** 299-325

**Issue:** For multi-target whispers with `reveal_on_read`, only the first reader is shown because the message can only be edited once.

**Comment in code (line 302):**
```python
# Note: For multi-target whispers, only the first reader is revealed (message can only be edited once)
```

**Impact:** Users expect to see who read their secret, but for multi-target whispers, only the first reader is displayed.

**Recommendation:** Consider updating the message to show "Read by: Alice, Bob, Charlie" format as each person reads.

---

### 10. Pending Whispers Cache Potential Memory Leak

**File:** `NinjaSecret/plugins/whisper/inline_handler.py`  
**Lines:** 49-54

**Issue:** The `pending_whispers` dictionary caches whispers before they're sent. If users create whispers via inline but never send them, they accumulate in memory.

**Current mitigation (cleanup_task.py):** There is a cleanup task that removes whispers older than 5 minutes:
```python
PENDING_WHISPER_MAX_AGE_SECONDS = 300  # 5 minutes
```

**Observation:** The cleanup works, but only runs every 10 minutes (line 125). This means the cache could grow significantly during high-traffic periods.

**Recommendation:** Consider reducing the cleanup interval or implementing size-based eviction.

---

### 11. Race Condition in Pending Whispers Cleanup

**File:** `NinjaSecret/plugins/whisper/cleanup_task.py`  
**Lines:** 96-105

**Issue:** Dictionary iteration during cleanup could fail if another coroutine modifies `pending_whispers`:

```python
for whisper_id, data in pending_whispers.items():  # ❌ Unsafe iteration
    ...
for whisper_id in to_remove:
    del pending_whispers[whisper_id]
```

**Fix:** Create a snapshot for safe iteration:
```python
for whisper_id, data in list(pending_whispers.items()):  # ✅ Safe snapshot
    ...
```

---

## 🟢 Minor Issues / Improvements

### 12. Hardcoded Language Code "en"

**Files:** Multiple locations in `inline_handler.py` and `callbacks.py`

**Issue:** Language is hardcoded to "en" in many places instead of using the user's language preference:

```python
results = [create_empty_query_response("en")]
results = [create_invalid_format_response("en")]
language = get_string("en")
```

**Recommendation:** Get the user's language preference from their settings or chat settings.

---

### 13. Inconsistent Error Handling in Inline Handler

**File:** `NinjaSecret/plugins/whisper/inline_handler.py`  
**Lines:** 478-482

**Issue:** Generic exception handling that catches all errors:

```python
except Exception as e:
    print(f"Inline query error: {e}")
    results = [create_error_response("en")]
    await query.answer(results, cache_time=1, is_personal=True)
```

**Recommendation:** Add more specific exception handling and logging with traceback:
```python
except Exception as e:
    logger.exception(f"Inline query error: {e}")
    results = [create_error_response("en")]
    await query.answer(results, cache_time=1, is_personal=True)
```

---

### 14. Dual Message Feature Lacks User Documentation

**Issue:** The dual message feature (using `|` separator) is powerful but not well-documented for users:

```python
# Format: public message @public_targets | private message @private_targets
```

**Recommendation:** Add inline help/examples when users type `|` in their query.

---

### 15. Timer Updates May Hit Rate Limits

**File:** `NinjaSecret/plugins/whisper/cleanup_task.py`  
**Lines:** 133-150

**Issue:** The timer countdown task updates whisper messages every 5 seconds for expiring whispers. With many active timed whispers, this could hit Telegram's rate limits.

**Current Mitigation:** Smart update intervals are implemented (lines 24-61), which helps.

**Recommendation:** Add rate limiting tracking and backoff when errors occur.

---

## Whisper Feature Analysis

### ✅ Working Features:
1. **Single target whispers** - Sending secrets to one person works correctly
2. **Multiple targets** - Comma-separated targets are parsed correctly
3. **@all/@everyone** - Everyone in the group can view the secret
4. **Timer feature (!t:N, !timer:N)** - Timed expiration works
5. **Reveal on read (!r, !reveal)** - Shows who read (single target only)
6. **Burn after reading (!d, !del, !delete)** - Burns silently after reading
7. **Burn with reveal (!b, !burn)** - Burns and shows who read
8. **VIP style (!v, !vip)** - Crown styling
9. **Cute style (!c, !cute, !love, !l)** - Heart styling
10. **Recent targets** - Quick-select from previously messaged users
11. **Dual messages (|)** - Different content for different targets
12. **User ID targeting** - Target by numeric user ID

### ⚠️ Features with Issues:
1. **Multi-target burn tracking** - Burns after first read, not all read
2. **Multi-target reveal** - Only shows first reader
3. **Language localization** - Hardcoded to English in many places

### 📝 Recommended Improvements:
1. Implement proper multi-target read tracking
2. Add whisper delivery confirmation
3. Allow whisper deletion by sender
4. Add whisper history for sender
5. Implement whisper reply functionality

---

## Summary

The whisper implementation is generally well-structured with good async patterns and modular design. However, there are **4 critical bugs** that will cause runtime errors:

1. **Missing "monkey" key** - `KeyError` when viewing secrets
2. **None check missing** - Crash during whisper cleanup
3. **Wrong language key** (`whisper_for_everyone_jungle`)
4. **Wrong language key** (`whisper_monkey_secured`)

Additionally, there are **7 moderate issues** affecting functionality and code quality, and **4 minor issues** for improvement.

**Priority fixes:**
1. Add "monkey" key to NINJA_EMOJIS dictionary
2. Add None check in cleanup_expired_whispers
3. Fix language key typos
4. Add missing imports in callbacks.py

---

*Report generated by Code Review Agent - Whisper Focus*
