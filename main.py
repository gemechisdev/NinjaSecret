#!/usr/bin/env python3
"""
Whispier Bot - The Ultimate Secret Messenger
A modular, scalable Telegram whisper bot with MongoDB backend.
"""

import asyncio
import logging
from pyrogram import Client, idle

from config import Config
from core.database import Database
from handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WhispierBot:
    """Main application class for Whispier Bot."""

    def __init__(self):
        self.app = Client(
            "whispier_bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
        )
        self.db = None

    async def start(self):
        """Initialize bot and database connections."""
        try:
            self.db = await Database.create(Config.MONGODB_URL)
            await self.db.initialize()

            self.app.db = self.db
            register_handlers(self.app)

            await self.app.start()
            me = await self.app.get_me()
            logger.info(f"🐒 {me.first_name} (@{me.username}) started successfully!")

            await idle()

        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources."""
        if self.app.is_connected:
            await self.app.stop()
        if self.db:
            await self.db.close()


async def main():
    """Entry point."""
    bot = WhispierBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
