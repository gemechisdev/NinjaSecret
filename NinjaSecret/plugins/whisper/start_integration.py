"""
Ninja Secret🥷 Start Command Integration
Adds ninja-themed welcome experience to the start command
"""

from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from NinjaSecret import app
from NinjaSecret.mongo.whisperdb import get_user_whisper_stats
from NinjaSecret.utils.whisper_utils import (
    create_dashboard_keyboard,
    format_user_stats,
    NINJA_EMOJIS
)
from config import BANNED_USERS

# This will be called when user sends /start whisper
@app.on_message(filters.command(["whisper"]) & filters.private & ~BANNED_USERS)
async def whisper_start(client, message: Message):
    """Handle /whisper command for direct whisper dashboard access"""
    try:
        user_id = message.from_user.id
        username = message.from_user.first_name or "Ninja Friend"

        # Get user stats
        stats = await get_user_whisper_stats(user_id)

        # Create welcome message
        welcome_text = f"""{NINJA_EMOJIS['ninja']} *Ninja appears in the shadows*

🎉 **Hey there, {username}! I'm Ninja Secret!**

🤫 I'm your personal secret-delivery ninja!
Drop private messages in any chat without anyone knowing.

✨ **What I do:**
🎯 Send secrets to specific people only
💀 Messages that vanish after reading
⏰ Timed secrets that self-destruct
🌙 Stealth multi-target secrets made easy

Ready to go stealth? {NINJA_EMOJIS['scroll']}"""

        # Show stats if user has used the bot before
        if stats.get('secrets_sent', 0) > 0 or stats.get('secrets_received', 0) > 0:
            welcome_text += f"\n\n{format_user_stats(stats, 'en')}"

        # Create keyboard
        keyboard = create_dashboard_keyboard()

        # Send sticker first
        await message.reply_sticker("CAACAgUAAxkBAAEQI1BlTLmx7PtOO3aPNshEU2gCy7iAFgACNQUAApqMuVeA6eJ50VbvmDME")

        # Send main message
        await message.reply_text(
            welcome_text,
            reply_markup=keyboard
        )

    except Exception as e:
        print(f"Whisper start error: {e}")
        await message.reply_text(
            f"{NINJA_EMOJIS['see_no_evil']} Something went wrong! Please try again later."
        )

def create_whisper_start_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for whisper start integration"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['shuriken']} {NINJA_EMOJIS['thought']} Send Secret",
                switch_inline_query_current_chat=""
            ),
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['ninja']} Quick Learn",
                callback_data="whisper_tutorial"
            )
        ],
        [
            InlineKeyboardButton(
                f"⚙️ {NINJA_EMOJIS['scroll']} My Dojo",
                callback_data="whisper_settings"
            ),
            InlineKeyboardButton(
                f"📊 {NINJA_EMOJIS['shuriken']} Secret Stats",
                callback_data="whisper_stats"
            )
        ],
        [
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['stealth']} {NINJA_EMOJIS['sparkles']} Stealth Modes",
                callback_data="whisper_styles"
            ),
            InlineKeyboardButton(
                f"💬 {NINJA_EMOJIS['scroll']} Help Scroll",
                callback_data="whisper_help"
            )
        ]
    ])

# Add whisper button to existing start command
def get_whisper_integration_button() -> InlineKeyboardButton:
    """Get button to add to existing start command"""
    return InlineKeyboardButton(
        f"{NINJA_EMOJIS['ninja']} {NINJA_EMOJIS['whisper']} Ninja Mode",
        callback_data="whisper_dashboard"
    )
