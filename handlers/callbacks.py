"""Callback query handlers for Whispier Bot."""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from utils.strings import Strings
from utils.keyboards import Keyboards


def register_callback_handlers(app: Client):
    """Register callback query handlers."""
    
    @app.on_callback_query(filters.regex("^home$"))
    async def home_callback(client: Client, callback: CallbackQuery):
        """Handle home button."""
        await callback.edit_message_text(
            Strings.WELCOME,
            reply_markup=Keyboards.main_menu(),
            parse_mode="markdown"
        )
        await callback.answer()
    
    @app.on_callback_query(filters.regex("^tutorial$"))
    async def tutorial_callback(client: Client, callback: CallbackQuery):
        """Handle tutorial button."""
        await callback.edit_message_text(
            Strings.TUTORIAL,
            reply_markup=Keyboards.back_to_home(),
            parse_mode="markdown"
        )
        await callback.answer("🐒 Time to become a secret ninja!")
    
    @app.on_callback_query(filters.regex("^help$"))
    async def help_callback(client: Client, callback: CallbackQuery):
        """Handle help button."""
        await callback.edit_message_text(
            Strings.HELP,
            reply_markup=Keyboards.back_to_home(),
            parse_mode="markdown"
        )
        await callback.answer()
    
    @app.on_callback_query(filters.regex("^stats$"))
    async def stats_callback(client: Client, callback: CallbackQuery):
        """Handle stats button."""
        await callback.edit_message_text(
            Strings.STATS.format(
                sent_count=0,
                received_count=0,
                active_count=0,
                level_info="🐒 Beginner Monkey"
            ),
            reply_markup=Keyboards.back_to_home(),
            parse_mode="markdown"
        )
        await callback.answer("📊 Your monkey statistics!")
    
    @app.on_callback_query()
    async def whisper_callback(client: Client, callback: CallbackQuery):
        """Handle whisper reveal callbacks."""
        whisper_id = callback.data
        user_id = callback.from_user.id
        
        # Get whisper from database
        whisper = await client.db.get_whisper(whisper_id)
        
        if not whisper:
            await callback.answer(Strings.MESSAGE_NOT_FOUND, show_alert=True)
            return
        
        # Check authorization
        sender_id = whisper["sender_id"]
        target_username = whisper["target_username"]
        target_id = whisper.get("target_id")
        
        # User is authorized if they are sender or target
        is_sender = user_id == sender_id
        is_target = (target_id and user_id == target_id) or (
            callback.from_user.username and 
            callback.from_user.username.lower() == target_username.lower()
        )
        
        if not (is_sender or is_target):
            await callback.answer(Strings.NOT_FOR_YOU, show_alert=True)
            return
        
        # If target clicked and we didn't have their ID, link it now
        if is_target and not target_id:
            await client.db.link_username_to_user(target_username, user_id)
        
        # Show secret content
        try:
            sender = await client.get_users(sender_id)
            sender_name = f"@{sender.username}" if sender.username else sender.first_name
        except:
            sender_name = "Someone"
        
        await callback.answer(
            Strings.SECRET_REVEALED.format(
                sender=sender_name,
                content=whisper["content"]
            ),
            show_alert=True
        )
        
        # Mark as read if not already read
        if not whisper.get("read_at"):
            await client.db.mark_whisper_read(whisper_id, user_id)