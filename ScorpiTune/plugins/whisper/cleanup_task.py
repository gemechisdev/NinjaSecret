"""
Ninja Secret🥷 Cleanup Task
Handles periodic cleanup of expired whispers and maintenance tasks
"""

import asyncio
from datetime import datetime, timedelta
from ScorpiTune.mongo.whisperdb import cleanup_expired_whispers
from ScorpiTune.logging import LOGGER

async def whisper_cleanup_task():
    """Periodic cleanup task for whisper messages"""
    while True:
        try:
            # Clean up expired whispers
            cleaned_count = await cleanup_expired_whispers()
            
            if cleaned_count > 0:
                LOGGER(__name__).info(f"Cleaned up {cleaned_count} expired whisper messages")
            
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