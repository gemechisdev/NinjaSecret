"""
Ninja Secret🥷 Cleanup Task
Handles periodic cleanup of expired whispers and maintenance tasks
"""

import asyncio
from datetime import datetime, timedelta
from NinjaSecret.mongo.whisperdb import (
    cleanup_expired_whispers,
    get_whispers_pending_expiry_edit,
    claim_expiry_edit,
    release_expiry_edit,
)
from NinjaSecret.logging import LOGGER

# Cache cleanup configuration
PENDING_WHISPER_MAX_AGE_SECONDS = 300  # 5 minutes - whispers not sent after this time are removed

# Expiry watcher configuration
# Timed cards show their countdown with <tg-time format="r">, which Telegram
# clients tick themselves, so no periodic countdown edits are needed any more.
# The watcher only has to swap the card for the "expired" card once time is up.
EXPIRY_CHECK_INTERVAL_SECONDS = 15
EXPIRY_EDIT_BATCH = 50
# Small delay between edits to stay far below Telegram's rate limits
EXPIRY_EDIT_DELAY_SECONDS = 0.1


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
    """Background task: replace expired timed cards with the "expired" card.

    Name kept for compatibility with __main__.py. Every pass it
      1. finds rich whispers whose timer ran out and whose card still shows the secret,
      2. atomically claims each one (so two passes never edit the same card twice),
      3. edits the card via the Rich Message API.

    A transient failure (network, flood wait, 5xx) releases the claim so the
    edit is retried on the next pass. Permanent failures (message deleted, ...)
    keep the claim so they are not retried forever.
    """
    from NinjaSecret.utils.rich_api import edit_rich_message, RichApiError, MessageNotModified
    from NinjaSecret.utils.whisper_card import expired_card

    logger = LOGGER(__name__)

    while True:
        try:
            pending = await get_whispers_pending_expiry_edit(EXPIRY_EDIT_BATCH)

            for whisper in pending:
                whisper_id = whisper.get("whisper_id")
                inline_message_id = whisper.get("inline_message_id")
                if not whisper_id or not inline_message_id:
                    continue

                # Another pass (or process) may have claimed it already
                if not await claim_expiry_edit(whisper_id):
                    continue

                try:
                    await edit_rich_message(expired_card(), inline_message_id=inline_message_id)
                except MessageNotModified:
                    pass
                except RichApiError as e:
                    if e.transient:
                        await release_expiry_edit(whisper_id)
                        logger.warning(f"Expiry edit for {whisper_id} will be retried: {e}")
                    else:
                        logger.info(f"Expiry edit for {whisper_id} skipped: {e}")
                except Exception as e:
                    await release_expiry_edit(whisper_id)
                    logger.error(f"Expiry edit for {whisper_id} failed unexpectedly: {e}")

                await asyncio.sleep(EXPIRY_EDIT_DELAY_SECONDS)

            await asyncio.sleep(EXPIRY_CHECK_INTERVAL_SECONDS)

        except Exception as e:
            logger.error(f"Expiry watcher error: {e}")
            await asyncio.sleep(EXPIRY_CHECK_INTERVAL_SECONDS)


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
    LOGGER(__name__).info("Whisper expiry watcher started")