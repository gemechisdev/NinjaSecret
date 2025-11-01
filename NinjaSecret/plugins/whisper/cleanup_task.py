"""
Ninja Secret🥷 Cleanup Task
Handles periodic cleanup of expired whispers and maintenance tasks
"""

import asyncio
from datetime import datetime, timedelta
from NinjaSecret.mongo.whisperdb import cleanup_expired_whispers
from NinjaSecret.logging import LOGGER

async def cleanup_pending_whispers_cache():
    """
    Clean up old pending whispers from in-memory cache.
    Import and call this from the inline_handler module.
    Pending whispers older than 5 minutes are removed (they were never sent).
    """
    # Import inside function to avoid circular dependency at module load time
    # The inline_handler module imports this module for the cleanup task
    from NinjaSecret.plugins.whisper.inline_handler import pending_whispers
    
    if not pending_whispers:
        return 0
    
    # Get current time
    now = datetime.utcnow()
    
    # Find whispers older than 5 minutes (300 seconds)
    # We store creation timestamp in the cache entries
    to_remove = []
    for whisper_id, data in pending_whispers.items():
        # Check if whisper has been in cache for too long
        # If no created_at field (old format), consider it stale
        created_at = data.get("created_at")
        if created_at is None or (now - created_at).total_seconds() > 300:
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

# Start the cleanup task when this module is imported
def start_cleanup_task():
    """Start the whisper cleanup background task"""
    asyncio.create_task(whisper_cleanup_task())
    LOGGER(__name__).info("Whisper cleanup task started")

# Auto-start the cleanup task
start_cleanup_task()