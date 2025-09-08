"""Keep-alive service to prevent Render.com from sleeping."""

import asyncio
import aiohttp
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class KeepAlive:
    """Service to keep web app alive by self-pinging."""

    def __init__(self, url: str, interval: int = 840):  # 14 minutes
        self.url = url
        self.interval = interval

    async def ping(self):
        """Ping the service to keep it alive."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/ping") as response:
                    if response.status == 200:
                        logger.info(f"🏓 Keep-alive ping successful: {datetime.utcnow()}")
                    else:
                        logger.warning(f"Keep-alive ping failed with status: {response.status}")
        except Exception as e:
            logger.error(f"Keep-alive ping error: {e}")

    async def start(self):
        """Start the keep-alive service."""
        logger.info(f"🚀 Keep-alive service started for {self.url}")
        while True:
            await asyncio.sleep(self.interval)
            await self.ping()
