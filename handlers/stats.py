"""Stats related handlers."""
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.strings import Strings
from utils.keyboards import Keyboards

def register_stats_handlers(app: Client):
    @app.on_message(filters.private & filters.command("stats"))
    async def stats_handler(client: Client, message: Message):
        await message.reply_text(
            Strings.STATS.format(sent_count=0, received_count=0, active_count=0, level_info="🐒 Beginner Monkey"),
            reply_markup=Keyboards.back_to_home(),
            parse_mode="markdown"
        )
