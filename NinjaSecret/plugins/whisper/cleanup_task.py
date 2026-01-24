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

# Timer countdown update interval (5 seconds as requested)
TIMER_UPDATE_INTERVAL_SECONDS = 5

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
    
    This task runs every 5 seconds and updates the inline message text
    for all active timed whispers to show the remaining time.
    This is similar to how !reveal edits the message when someone reads it.
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
                error_count = 0
                
                for whisper in timed_whispers:
                    try:
                        inline_message_id = whisper.get("inline_message_id")
                        whisper_id = whisper.get("whisper_id")
                        
                        if not inline_message_id:
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
                
                if updated_count > 0:
                    logger.debug(f"Updated {updated_count} timed whisper messages")
            
            # Wait 5 seconds before next update cycle
            await asyncio.sleep(TIMER_UPDATE_INTERVAL_SECONDS)
            
        except Exception as e:
            logger.error(f"Timer countdown update task error: {e}")
            # Wait 5 seconds before retrying on error
            await asyncio.sleep(TIMER_UPDATE_INTERVAL_SECONDS)


# Start the cleanup task when this module is imported
def start_cleanup_task():
    """Start the whisper cleanup background task"""
    asyncio.create_task(whisper_cleanup_task())
    LOGGER(__name__).info("Whisper cleanup task started")


def start_timer_countdown_task():
    """Start the timer countdown update background task"""
    asyncio.create_task(timer_countdown_update_task())
    LOGGER(__name__).info("Timer countdown update task started (updates every 5 seconds)")

# Auto-start the cleanup task
start_cleanup_task()

# Auto-start the timer countdown task
start_timer_countdown_task()