"""Start command handler."""
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.strings import Strings
from utils.keyboards import Keyboards


def register_start_command(app: Client):
    @app.on_message(filters.private & filters.command("start"))
    async def start_handler(client: Client, message: Message):
        user = message.from_user
        await client.db.upsert_user({
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": (user.username or "").lower() if user.username else None
        })
        await message.reply_text(
            Strings.WELCOME,
            reply_markup=Keyboards.main_menu(),
            parse_mode="markdown"
        )
