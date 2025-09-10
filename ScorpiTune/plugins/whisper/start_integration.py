"""
WhispierBot Start Command Integration
Adds whisper-themed welcome experience to the start command
"""

from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from ScorpiTune import app
from ScorpiTune.mongo.whisperdb import get_user_whisper_stats
from ScorpiTune.utils.whisper_utils import (
    create_dashboard_keyboard,
    format_user_stats,
    MONKEY_EMOJIS
)
from config import BANNED_USERS

# This will be called when user sends /start whisper
@app.on_message(filters.command(["whisper"]) & filters.private & ~BANNED_USERS)
async def whisper_start(client, message: Message):
    """Handle /whisper command for direct whisper dashboard access"""
    try:
        user_id = message.from_user.id
        username = message.from_user.first_name or "Monkey Friend"
        
        # Get user stats
        stats = await get_user_whisper_stats(user_id)
        
        # Create welcome message
        welcome_text = f"""{MONKEY_EMOJIS['monkey']} *Monkey swings into chat*

🎉 **Hey there, {username}! I'm Whispier!** 

🤫 I'm your personal secret-delivery monkey!
Drop private messages in any chat without the drama.

✨ **What I do:**
🎯 Send secrets to specific people only
💀 Messages that vanish after reading  
⏰ Timed secrets that self-destruct
🎪 Multi-target whispers made easy

Ready to swing into action? {MONKEY_EMOJIS['tree']}"""

        # Show stats if user has used the bot before
        if stats.get('secrets_sent', 0) > 0 or stats.get('secrets_received', 0) > 0:
            welcome_text += f"\n\n{format_user_stats(stats)}"
        
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
            f"{MONKEY_EMOJIS['see_no_evil']} Something went wrong! Please try again later."
        )

def create_whisper_start_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for whisper start integration"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{MONKEY_EMOJIS['banana']} {MONKEY_EMOJIS['thought']} Send Secret",
                switch_inline_query_current_chat=""
            ),
            InlineKeyboardButton(
                f"{MONKEY_EMOJIS['monkey']} Quick Learn",
                callback_data="whisper_tutorial"
            )
        ],
        [
            InlineKeyboardButton(
                f"⚙️ {MONKEY_EMOJIS['tree']} My Jungle",
                callback_data="whisper_settings"
            ),
            InlineKeyboardButton(
                f"📊 {MONKEY_EMOJIS['banana']} Secret Stats",
                callback_data="whisper_stats"
            )
        ],
        [
            InlineKeyboardButton(
                f"{MONKEY_EMOJIS['circus']} {MONKEY_EMOJIS['sparkles']} Fun Modes",
                callback_data="whisper_styles"
            ),
            InlineKeyboardButton(
                f"💬 {MONKEY_EMOJIS['tree']} Help Tree",
                callback_data="whisper_help"
            )
        ]
    ])

# Add whisper button to existing start command
def get_whisper_integration_button() -> InlineKeyboardButton:
    """Get button to add to existing start command"""
    return InlineKeyboardButton(
        f"{MONKEY_EMOJIS['monkey']} {MONKEY_EMOJIS['whisper']} Whisper Mode",
        callback_data="whisper_dashboard"
    )