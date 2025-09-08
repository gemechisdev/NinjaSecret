"""Callback query handlers for Whispier Bot."""
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from utils.strings import Strings
from utils.keyboards import Keyboards


def register_callback_handlers(app: Client):
    @app.on_callback_query(filters.regex("^home$"))
    async def home_callback(client: Client, callback: CallbackQuery):
        await callback.edit_message_text(
            Strings.WELCOME,
            reply_markup=Keyboards.main_menu(),
            parse_mode="markdown"
        )
        await callback.answer()

    @app.on_callback_query(filters.regex("^tutorial$"))
    async def tutorial_callback(client: Client, callback: CallbackQuery):
        await callback.edit_message_text(
            Strings.TUTORIAL,
            reply_markup=Keyboards.back_to_home(),
            parse_mode="markdown"
        )
        await callback.answer("🐒 Time to become a secret ninja!")

    @app.on_callback_query(filters.regex("^help$"))
    async def help_callback(client: Client, callback: CallbackQuery):
        await callback.edit_message_text(
            Strings.HELP,
            reply_markup=Keyboards.back_to_home(),
            parse_mode="markdown"
        )
        await callback.answer()

    @app.on_callback_query(filters.regex("^stats$"))
    async def stats_callback(client: Client, callback: CallbackQuery):
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
        whisper_id = callback.data
        user_id = callback.from_user.id

        whisper = await client.db.get_whisper(whisper_id)
        if not whisper:
            await callback.answer(Strings.MESSAGE_NOT_FOUND, show_alert=True)
            return

        sender_id = whisper["sender_id"]
        target_username = whisper.get("target_username")
        target_id = whisper.get("target_id")
        original_token = whisper.get("original_target_token")

        is_sender = user_id == sender_id
        is_target = False

        if target_id and user_id == target_id:
            is_target = True
        elif callback.from_user.username and target_username:
            if callback.from_user.username.lower() == target_username.lower():
                is_target = True
        elif original_token and original_token.isdigit() and int(original_token) == user_id:
            is_target = True

        if not (is_sender or is_target):
            await callback.answer(Strings.NOT_FOR_YOU, show_alert=True)
            return

        if is_target and not target_id:
            # Link late
            if callback.from_user.username:
                await client.db.link_username_to_user(callback.from_user.username, user_id)
            await client.db.whispers.update_one(
                {"whisper_id": whisper_id},
                {"$set": {"target_id": user_id}}
            )

        try:
            sender = await client.get_users(sender_id)
            sender_name = f"@{sender.username}" if sender.username else sender.first_name
        except Exception:
            sender_name = "Someone"

        await callback.answer(
            Strings.SECRET_REVEALED.format(
                sender=sender_name,
                content=whisper["content"]
            ),
            show_alert=True
        )

        if not whisper.get("read_at"):
            await client.db.mark_whisper_read(whisper_id, user_id)
