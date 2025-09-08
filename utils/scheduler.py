"""Background task scheduler for Whispier Bot."""

import asyncio
import aiohttp
from datetime import datetime
from config import Config

async def keep_alive_task():
    """Background task to keep service alive."""
    if Config.DEV_MODE:
        return

    service_url = "https://whispierbot.onrender.com"

    while True:
        try:
            await asyncio.sleep(840)  # 14 minutes
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{service_url}/ping") as response:
                    print(f"🏓 Keep-alive: {response.status} at {datetime.utcnow()}")
        except Exception as e:
            print(f"Keep-alive error: {e}")

async def cleanup_expired_whispers():
    """Background task to clean up expired whispers."""
    while True:
        try:
            await asyncio.sleep(3600)  # 1 hour
            print(f"🧹 Cleanup task executed at {datetime.utcnow()}")
        except Exception as e:
            print(f"Cleanup error: {e}")
