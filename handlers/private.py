"""Private message handlers for Whispier Bot."""

from pyrogram import Client, filters
from pyrogram.types import Message

from utils.strings import Strings
from utils.keyboards import Keyboards


def register_private_handlers(app: Client):
    """Register private message handlers."""
    
    @app.on_message(filters.private & filters.command("start"))
    async def start_handler(client: Client, message: Message):
        """Handle /start command."""
        user = message.from_user
        
        await client.db.upsert_user({
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username
        })
        
        await message.reply_text(
            Strings.WELCOME,
            reply_markup=Keyboards.main_menu(),
            parse_mode="markdown"
        )
    
    @app.on_message(filters.private & filters.command("help"))
    async def help_handler(client: Client, message: Message):
        """Handle /help command."""
        await message.reply_text(
            Strings.HELP,
            reply_markup=Keyboards.back_to_home(),
            parse_mode="markdown"
        )
    
    @app.on_message(filters.private & filters.command("stats"))
    async def stats_handler(client: Client, message: Message):
        """Handle /stats command."""
        # TODO: Implement user statistics
        await message.reply_text(
            Strings.STATS.format(
                sent_count=0,
                received_count=0, 
                active_count=0,
                level_info="🐒 Beginner Monkey"
            ),
            reply_markup=Keyboards.back_to_home(),
            parse_mode="markdown"
        )