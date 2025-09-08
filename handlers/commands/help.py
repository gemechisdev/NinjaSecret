"""Help command handler."""
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.strings import Strings
from utils.keyboards import Keyboards


def register_help_command(app: Client):
    @app.on_message(filters.private & filters.command("help"))
    async def help_handler(client: Client, message: Message):
        await message.reply_text(
            Strings.HELP,
            reply_markup=Keyboards.back_to_home(),
            parse_mode="markdown"
        )
