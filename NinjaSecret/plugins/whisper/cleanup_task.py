"""
Ninja Secret🥷 Cleanup Task
Handles periodic cleanup of expired whispers and maintenance tasks
"""

import asyncio
from datetime import datetime, timedelta
from pyrogram import enums
from NinjaSecret.mongo.whisperdb import cleanup_expired_whispers, get_active_timed_whispers
from NinjaSecret.logging import LOGGER

# Cache cleanup configuration
PENDING_WHISPER_MAX_AGE_SECONDS = 300  # 5 minutes - whispers not sent after this time are removed

# Timer countdown update configuration
# Base interval for checking whispers (5 seconds)
TIMER_CHECK_INTERVAL_SECONDS = 5

# Track when each whisper was last updated to implement smart update intervals
# Key: whisper_id, Value: datetime of last update
_last_update_times = {}


def _should_update_whisper(whisper_id: str, time_remaining_seconds: float) -> bool:
    """Determine if a whisper should be updated based on time remaining.
    
    Smart update intervals:
    - Less than 5 minutes remaining: update every 5 seconds (every cycle)
    - 5-30 minutes remaining: update every 1 minute
    - 30 minutes - 1 hour remaining: update every 3 minutes
    - More than 1 hour remaining: update every 5 minutes
    
    Args:
        whisper_id: The whisper's unique ID
        time_remaining_seconds: Seconds until the whisper expires
        
    Returns:
        True if the whisper should be updated this cycle
    """
    now = datetime.utcnow()
    last_update = _last_update_times.get(whisper_id)
    
    # Always update if never updated before
    if last_update is None:
        return True
    
    seconds_since_update = (now - last_update).total_seconds()
    
    # Determine update interval based on time remaining
    if time_remaining_seconds <= 300:  # Less than 5 minutes
        # Update every 5 seconds (every cycle)
        return seconds_since_update >= 5
    elif time_remaining_seconds <= 1800:  # 5-30 minutes
        # Update every 1 minute
        return seconds_since_update >= 60
    elif time_remaining_seconds <= 3600:  # 30 minutes - 1 hour
        # Update every 3 minutes
        return seconds_since_update >= 180
    else:  # More than 1 hour
        # Update every 5 minutes
        return seconds_since_update >= 300


def _record_update(whisper_id: str):
    """Record that a whisper was updated."""
    _last_update_times[whisper_id] = datetime.utcnow()


def _cleanup_update_times(active_whisper_ids: set):
    """Remove update times for whispers that are no longer active."""
    # Use set operations for efficient cleanup
    expired_ids = set(_last_update_times.keys()) - active_whisper_ids
    for wid in expired_ids:
        del _last_update_times[wid]


async def cleanup_pending_whispers_cache():
    """
    Clean up old pending whispers from in-memory cache.
    Import and call this from the inline_handler module.
    Pending whispers older than PENDING_WHISPER_MAX_AGE_SECONDS are removed (they were never sent).
    """
    # Import inside function to avoid circular dependency at module load time
    # The inline_handler module imports this module for the cleanup task
    from NinjaSecret.plugins.whisper.inline_handler import pending_whispers
    
    if not pending_whispers:
        return 0
    
    # Get current time
    now = datetime.utcnow()
    
    # Find whispers older than configured max age
    # We store creation timestamp in the cache entries
    to_remove = []
    for whisper_id, data in pending_whispers.items():
        # Check if whisper has been in cache for too long
        # If no created_at field (old format), consider it stale
        created_at = data.get("created_at")
        if created_at is None or (now - created_at).total_seconds() > PENDING_WHISPER_MAX_AGE_SECONDS:
            to_remove.append(whisper_id)
    
    # Remove stale whispers
    for whisper_id in to_remove:
        del pending_whispers[whisper_id]
    
    return len(to_remove)

async def whisper_cleanup_task():
    """Periodic cleanup task for whisper messages"""
    while True:
        try:
            # Clean up expired whispers in database
            cleaned_count = await cleanup_expired_whispers()
            
            if cleaned_count > 0:
                LOGGER(__name__).info(f"Cleaned up {cleaned_count} expired whisper messages")
            
            # Clean up stale pending whispers in cache
            cache_cleaned = await cleanup_pending_whispers_cache()
            if cache_cleaned > 0:
                LOGGER(__name__).info(f"Cleaned up {cache_cleaned} stale pending whispers from cache")
            
            # Wait 10 minutes before next cleanup
            await asyncio.sleep(600)
            
        except Exception as e:
            LOGGER(__name__).error(f"Whisper cleanup error: {e}")
            # Wait 5 minutes before retrying on error
            await asyncio.sleep(300)


async def timer_countdown_update_task():
    """Background task to update timed whisper messages with current countdown.
    
    This task checks every 5 seconds but uses smart update intervals:
    - Less than 5 minutes remaining: update every 5 seconds
    - 5-30 minutes remaining: update every 1 minute  
    - 30 minutes - 1 hour remaining: update every 3 minutes
    - More than 1 hour remaining: update every 5 minutes
    
    This reduces API calls and avoids rate limiting while still providing
    timely updates for whispers that are about to expire.
    """
    # Import here to avoid circular imports
    from NinjaSecret import app
    from NinjaSecret.utils.whisper_utils import create_timer_countdown_message, create_whisper_keyboard
    
    logger = LOGGER(__name__)
    
    # Small delay between individual message updates to avoid hitting rate limits
    # Telegram allows ~30 messages per second for bots
    UPDATE_DELAY_SECONDS = 0.1
    
    while True:
        try:
            # Get all active timed whispers with inline_message_id
            timed_whispers = await get_active_timed_whispers()
            
            if timed_whispers:
                updated_count = 0
                skipped_count = 0
                error_count = 0
                
                # Build set of active whisper IDs for cleanup
                active_whisper_ids = set()
                
                for whisper in timed_whispers:
                    try:
                        inline_message_id = whisper.get("inline_message_id")
                        whisper_id = whisper.get("whisper_id")
                        settings = whisper.get("settings", {})
                        expires_at = settings.get("expires_at")
                        
                        if not inline_message_id or not whisper_id:
                            continue
                        
                        # Calculate time remaining in seconds first to check if expired
                        if not expires_at:
                            continue
                            
                        time_remaining_seconds = (expires_at - datetime.utcnow()).total_seconds()
                        
                        # Skip if expired (let cleanup task handle it) - check early to avoid unnecessary processing
                        if time_remaining_seconds <= 0:
                            continue
                        
                        # Add to active set only for non-expired whispers
                        active_whisper_ids.add(whisper_id)
                        
                        # Check if we should update this whisper based on smart intervals
                        if not _should_update_whisper(whisper_id, time_remaining_seconds):
                            skipped_count += 1
                            continue
                        
                        # Create the updated message with current time remaining
                        updated_message = create_timer_countdown_message(whisper)
                        
                        if updated_message:
                            # Edit the inline message to show updated countdown
                            # Using app.edit_inline_text similar to how !reveal uses
                            # callback_query.edit_message_text()
                            await app.edit_inline_text(
                                inline_message_id=inline_message_id,
                                text=updated_message,
                                parse_mode=enums.ParseMode.MARKDOWN,
                                reply_markup=create_whisper_keyboard(whisper_id)
                            )
                            
                            # Record that we updated this whisper
                            _record_update(whisper_id)
                            updated_count += 1
                            
                            # Small delay between updates to avoid rate limiting
                            await asyncio.sleep(UPDATE_DELAY_SECONDS)
                            
                    except Exception as e:
                        # Silently handle individual whisper update errors
                        # Common errors: message not modified, message deleted, etc.
                        error_count += 1
                        # Only log if it's not a common "message not modified" error
                        error_str = str(e).lower()
                        if "not modified" not in error_str:
                            logger.debug(f"Timer update failed for whisper {whisper.get('whisper_id', 'unknown')}: {e}")
                
                # Clean up tracking for expired whispers
                _cleanup_update_times(active_whisper_ids)
                
                if updated_count > 0:
                    logger.debug(f"Updated {updated_count} timed whisper messages (skipped {skipped_count} not due yet)")
            
            # Wait before next check cycle
            await asyncio.sleep(TIMER_CHECK_INTERVAL_SECONDS)
            
        except Exception as e:
            logger.error(f"Timer countdown update task error: {e}")
            # Wait before retrying on error
            await asyncio.sleep(TIMER_CHECK_INTERVAL_SECONDS)


def start_cleanup_task():
    """Start the whisper cleanup background task.
    
    Note: This should be called after the bot has started and the event loop is running.
    Called from __main__.py after bot initialization.
    """
    asyncio.create_task(whisper_cleanup_task())
    LOGGER(__name__).info("Whisper cleanup task started")


def start_timer_countdown_task():
    """Start the timer countdown update background task.
    
    Note: This should be called after the bot has started and the event loop is running.
    Called from __main__.py after bot initialization.
    """
    asyncio.create_task(timer_countdown_update_task())
    LOGGER(__name__).info("Timer countdown update task started (smart intervals based on time remaining)")