#!/usr/bin/env python3
"""Whispier Bot main application with FastAPI health server and userbot."""
import asyncio
import logging
import threading
from datetime import datetime

from pyrogram import Client, idle
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

from config import Config
from core.database import Database
from handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

web_app = FastAPI(title="Whispier Bot", version="1.0.0")

@web_app.get("/")
@web_app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "service": "whispier-bot", "ts": datetime.utcnow().isoformat()})

@web_app.get("/ping")
async def ping():
    return {"pong": True, "ts": datetime.utcnow().isoformat()}


class WhispierRuntime:
    def __init__(self):
        self.bot = Client(
            "whispier_bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
        self.user_client: Client | None = None
        if Config.USER_SESSION_STRING:
            self.user_client = Client(
                name="whispier_userbot",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                session_string=Config.USER_SESSION_STRING,
                no_updates=True
            )
        self.db: Database | None = None

    async def start(self):
        self.db = await Database.create(Config.MONGODB_URL)
        await self.db.initialize()
        self.bot.db = self.db
        if self.user_client:
            await self.user_client.start()
            logger.info("Userbot started for global user resolution.")
            self.bot.user_client = self.user_client
        register_handlers(self.bot)
        await self.bot.start()
        me = await self.bot.get_me()
        logger.info(f"🐒 {me.first_name} (@{me.username}) started successfully!")
        await idle()

    async def stop(self):
        if self.bot.is_connected:
            await self.bot.stop()
        if self.user_client and self.user_client.is_connected:
            await self.user_client.stop()
        if self.db:
            await self.db.close()


def run_web():
    uvicorn.run(web_app, host="0.0.0.0", port=Config.PORT, log_level="info")


async def main():
    runtime = WhispierRuntime()
    thread = threading.Thread(target=run_web, daemon=True)
    thread.start()
    try:
        await runtime.start()
    finally:
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
