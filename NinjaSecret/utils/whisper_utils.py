"""
Ninja Secret🥷 Utility Functions
Handles secret message processing, target resolution, and formatting
"""

import re
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pyrogram import enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from strings import get_string

# Ninja-themed emojis and styling
NINJA_EMOJIS = {
    "ninja": "🥷",
    "shuriken": "⭐",
    "scroll": "📜",
    "thought": "💭",
    "whisper": "🤫",
    "fire": "🔥",
    "timer": "⏰",
    "crown": "👑",
    "heart": "💕",
    "stealth": "🌙",
    "see_no_evil": "🙈",
    "hear_no_evil": "🙉",
    "speak_no_evil": "🙊",
    "lightning": "⚡",
    "eyes": "👀",
    "sparkles": "✨"
}

def generate_whisper_id() -> str:
    """Generate unique whisper message ID"""
    return str(uuid.uuid4())

def parse_whisper_command(text: str) -> Tuple[Optional[str], Optional[str], Dict[str, any]]:
    """
    Parse whisper command from inline query
    Format: @ninjasecretbot [message] [targets] [modifiers]

    Returns: (message_content, targets_string, modifiers)
    """
    if not text.strip():
        return None, None, {}

    text = re.sub(r'^@\w+\s+', '', text.strip())

    modifiers = {}

    timer_match = re.search(r'!timer:(\d+)', text)
    if timer_match:
        modifiers['timer'] = int(timer_match.group(1))
        text = re.sub(r'!timer:\d+', '', text).strip()

    if '!delete' in text:
        modifiers['burn_after_reading'] = True
        text = text.replace('!delete', '').strip()

    if '!vip' in text:
        modifiers['style'] = 'vip'
        text = text.replace('!vip', '').strip()

    if '!cute' in text:
        modifiers['style'] = 'cute'
        text = text.replace('!cute', '').strip()

    target_pattern = r'((?:@(?:[\w]+|all|everyone)|[\d]{6,15})(?:\s*,\s*(?:@(?:[\w]+|all|everyone)|[\d]{6,15}))*)\s*$'
    target_match = re.search(target_pattern, text)

    if target_match:
        targets_string = target_match.group(1).strip()
        message_content = text[:target_match.start()].strip()
    else:
        alt_pattern = r'(@(?:[\w]+|all|everyone)|[\d]{6,15})\s*$'
        alt_match = re.search(alt_pattern, text)
        if alt_match:
            targets_string = alt_match.group(1).strip()
            message_content = text[:alt_match.start()].strip()
        else:
            return text.strip() if text.strip() else None, None, modifiers

    return message_content if message_content else None, targets_string, modifiers

def format_targets_display(targets: List[Dict], max_display: int = 3) -> str:
    """Format targets for display in messages"""
    if not targets:
        return "ɴᴏ ᴛᴀʀɢᴇᴛs"

    for target in targets:
        if target.get("type") == "all":
            return "ᴇᴠᴇʀʏᴏɴᴇ"

    target_names = []
    for target in targets[:max_display]:
        display_name = target.get("display_name", target.get("value", "ᴜɴᴋɴᴏᴡɴ"))

        if target.get("resolved_id"):
            if target.get("type") == "username":
                if not display_name.startswith("@"):
                    display_name = f"@{display_name}"
            target_names.append(display_name)
        else:
            if not display_name.startswith("@"):
                display_name = f"{display_name}"
            target_names.append(display_name)

    if len(targets) > max_display:
        remaining = len(targets) - max_display
        target_names.append(f"ᴀɴᴅ {remaining} ᴍᴏʀᴇ")

    return " & ".join(target_names) if len(target_names) <= 2 else ", ".join(target_names[:-1]) + f" & {target_names[-1]}"

def format_whisper_preview(content: str, max_length: int = 50) -> str:
    """Format whisper content for preview"""
    if len(content) <= max_length:
        return content
    return content[:max_length-3] + "..."

def get_time_remaining_text(expires_at: datetime) -> str:
    """Get human-readable time remaining"""
    if not expires_at:
        return ""

    remaining = expires_at - datetime.utcnow()

    if remaining.total_seconds() <= 0:
        return "ᴇxᴘɪʀᴇᴅ"

    if remaining.days > 0:
        return f"{remaining.days}ᴅ {remaining.seconds // 3600}ʜ"
    elif remaining.seconds >= 3600:
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        return f"{hours}ʜ {minutes}ᴍ"
    elif remaining.seconds >= 60:
        minutes = remaining.seconds // 60
        seconds = remaining.seconds % 60
        return f"{minutes}ᴍ {seconds}s"
    else:
        return f"{remaining.seconds}s"

def create_whisper_inline_result(whisper_id: str, content: str, targets: List[Dict], modifiers: Dict, lang: str = "en") -> Dict:
    """Create inline query result for whisper"""
    language = get_string(lang)

    target_display = format_targets_display(targets)
    target_count = len([t for t in targets if t.get("type") != "all"]) if not any(t.get("type") == "all" for t in targets) else "∞"

    style_emoji = f"{NINJA_EMOJIS['whisper']}{NINJA_EMOJIS['thought']}"
    if modifiers.get('style') == 'vip':
        style_emoji = f"{NINJA_EMOJIS['crown']}{NINJA_EMOJIS['shuriken']}"
    elif modifiers.get('style') == 'cute':
        style_emoji = f"{NINJA_EMOJIS['ninja']}{NINJA_EMOJIS['heart']}"
    elif modifiers.get('burn_after_reading'):
        style_emoji = f"💀{NINJA_EMOJIS['fire']}"
    elif modifiers.get('timer'):
        style_emoji = f"{NINJA_EMOJIS['timer']}{NINJA_EMOJIS['ninja']}"

    description_parts = []
    if target_count == "∞":
        description_parts.append(language["whisper_inline_desc_everyone"])
    else:
        description_parts.append(language["whisper_inline_desc_for"].format(f"{target_display} ({target_count} ᴍᴏɴᴋᴇʏs)"))

    if modifiers.get('burn_after_reading'):
        description_parts.append(language["whisper_inline_desc_burns"])

    if modifiers.get('timer'):
        timer_text = format_timer_display(modifiers['timer'])
        description_parts.append(language["whisper_inline_desc_expires"].format(timer_text))

    description_parts.append(language["whisper_inline_desc_style"].format(modifiers.get('style', 'ᴄʟᴀssɪᴄ').title()))

    return {
        "type": "article",
        "id": whisper_id,
        "title": language["whisper_inline_title"].format(style_emoji),
        "description": "\n".join(description_parts),
        "thumb_url": "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExYzZnaHloOWJ5N25scGo1OHFhY3h0bnEyb2Rkc2xkYWR2dW1qdm42ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/cwksT0tmuElnj09vuK/giphy.gif",
        "input_message_content": {
            "message_text": create_whisper_posted_message(content, targets, modifiers, lang),
            "parse_mode": enums.ParseMode.MARKDOWN
        },
        "reply_markup": create_whisper_keyboard(whisper_id)
    }

def format_timer_display(seconds: int) -> str:
    """Format timer seconds to human readable"""
    if seconds >= 86400:
        days = seconds // 86400
        return f"{days} ᴅᴀʏ{'s' if days != 1 else ''}"
    elif seconds >= 3600:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}ʜ {minutes}ᴍ"
        return f"{hours} ʜᴏᴜʀ{'s' if hours != 1 else ''}"
    elif seconds >= 60:
        minutes = seconds // 60
        return f"{minutes} ᴍɪɴᴜᴛᴇ{'s' if minutes != 1 else ''}"
    else:
        return f"{seconds} sᴇᴄᴏɴᴅ{'s' if seconds != 1 else ''}"

def create_whisper_posted_message(content: str, targets: List[Dict], modifiers: Dict, lang: str = "en") -> str:
    """Create the message that gets posted in chat"""
    target_display = format_targets_display(targets)
    language = get_string(lang)

    if modifiers.get('style') == 'vip':
        header = language["whisper_delivery_vip"]
    elif modifiers.get('style') == 'cute':
        header = language["whisper_delivery_cute"]
    elif modifiers.get('burn_after_reading'):
        header = language["whisper_delivery_burn"]
    elif modifiers.get('timer'):
        header = language["whisper_delivery_timer"]
    else:
        header = language["whisper_delivery_base"]

    message_parts = [header, ""]

    if any(t.get("type") == "all" for t in targets):
        message_parts.append(language["whisper_for_everyone"])
    else:
        message_parts.append(language["whisper_for_target"].format(target_display))

    if modifiers.get('timer'):
        timer_text = format_timer_display(modifiers['timer'])
        message_parts.append(language["whisper_expires"].format(timer_text))

    if modifiers.get('burn_after_reading'):
        if any(t.get("type") == "all" for t in targets):
            message_parts.append(language["whisper_burns_all"])
        else:
            target_count = len(targets)
            message_parts.append(language["whisper_burns_count"].format(target_count))

    message_parts.extend([
        language["whisper_encrypted"],
        ""
    ])

    return "\n".join(message_parts)

def create_whisper_keyboard(whisper_id: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for whisper message"""
    buttons = [
        [
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['shuriken']} ʀᴇᴀᴅ sᴇᴄʀᴇᴛ {NINJA_EMOJIS['thought']}",
                callback_data=f"whisper_view_{whisper_id}"
            )
        ]
    ]

    return InlineKeyboardMarkup(buttons)

def create_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for user dashboard"""
    buttons = [
        [
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['thought']} sᴇɴᴅ sᴇᴄʀᴇᴛ {NINJA_EMOJIS['shuriken']}",
                switch_inline_query_current_chat=""
            ),
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['ninja']} ǫᴜɪᴄᴋ ʟᴇᴀʀɴ",
                callback_data="whisper_tutorial"
            )
        ],
        [
            InlineKeyboardButton(
                f"🎯 ʀᴇᴄᴇɴᴛ ᴛᴀʀɢᴇᴛs",
                callback_data="whisper_recent_targets"
            ),
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['shuriken']} sᴇᴄʀᴇᴛ sᴛᴀᴛs",
                callback_data="whisper_stats"
            )
        ],
        [
            InlineKeyboardButton(
                f"⚙️ ᴍʏ ᴊᴜɴɢʟᴇ {NINJA_EMOJIS['scroll']}",
                callback_data="whisper_settings"
            ),
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['stealth']} ғᴜɴ ᴍᴏᴅᴇs",
                callback_data="whisper_styles"
            )
        ],
        [
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['scroll']} ʜᴇʟᴘ ᴛʀᴇᴇ",
                callback_data="whisper_help"
            )
        ]
    ]

    return InlineKeyboardMarkup(buttons)

def create_empty_query_response(lang: str = "en") -> InlineQueryResultArticle:
    """Create response for empty inline query"""
    language = get_string(lang)
    return InlineQueryResultArticle(
        id="empty_query",
        title=language["whisper_empty_title"].format(NINJA_EMOJIS['ninja']),
        description=language["whisper_empty_desc"].format(NINJA_EMOJIS['ninja']),
        thumb_url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExYzZnaHloOWJ5N25scGo1OHFhY3h0bnEyb2Rkc2xkYWR2dW1qdm42ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/cwksT0tmuElnj09vuK/giphy.gif",
        input_message_content=InputTextMessageContent(
            message_text=create_empty_query_help_text(lang),
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=create_empty_query_keyboard()
    )

def create_empty_query_help_text(lang: str = "en") -> str:
    """Create help text for empty query"""
    language = get_string(lang)
    return language["whisper_7"]

def create_empty_query_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for empty query response"""
    buttons = [
        [
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['lightning']} ᴛʀʏ ɴᴏᴡ {NINJA_EMOJIS['thought']}",
                switch_inline_query_current_chat="secret message @username"
            ),
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['ninja']} ᴛᴜᴛᴏʀɪᴀʟ",
                callback_data="whisper_tutorial"
            )
        ]
    ]

    return InlineKeyboardMarkup(buttons)

def create_secret_revealed_text(content: str, sender_username: str, whisper_data: Dict) -> str:
    """Create text shown when secret is revealed"""
    burn_info = ""
    timer_info = ""

    if whisper_data.get("settings", {}).get("burn_after_reading"):
        targets = whisper_data.get("targets", [])
        unread_targets = [t for t in targets if not t.get("read_at")]
        if len(unread_targets) > 1:
            burn_info = f"\n💀 ʙᴜʀɴs ᴡʜᴇɴ {len(unread_targets)-1} ᴍᴏʀᴇ ʀᴇᴀᴅ!"
        elif len(unread_targets) == 1:
            burn_info = "\n💀 ʙᴜʀɴs ᴡʜᴇɴ 1 ᴍᴏʀᴇ ʀᴇᴀᴅs!"
        else:
            burn_info = "\n💀 ᴛʜɪs ᴡᴀs ᴛʜᴇ ʟᴀsᴛ ʀᴇᴀᴅ - ᴍᴇssᴀɢᴇ ʙᴜʀɴᴇᴅ!"

    if whisper_data.get("settings", {}).get("expires_at"):
        time_remaining = get_time_remaining_text(whisper_data["settings"]["expires_at"])
        if time_remaining != "ᴇxᴘɪʀᴇᴅ":
            timer_info = f"\n{NINJA_EMOJIS['timer']} {time_remaining} ʟᴇғᴛ"

    return f'"{content}"{burn_info}{timer_info}\n\n{NINJA_EMOJIS["monkey"]} ᴋᴇᴇᴘ ɪᴛ ʙᴇᴛᴡᴇᴇɴ ᴜs ᴍᴏɴᴋᴇʏs!'

def create_unauthorized_access_text(lang: str = "en") -> str:
    """Create text for unauthorized access attempt"""
    language = get_string(lang)
    return language["whisper_4"]

def create_unauthorized_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for unauthorized access"""
    buttons = [
        [
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['shuriken']} ᴄʀᴇᴀᴛᴇ sᴇᴄʀᴇᴛ",
                switch_inline_query_current_chat=""
            )
        ]
    ]

    return InlineKeyboardMarkup(buttons)

def format_user_stats(stats: Dict, lang: str = "en") -> str:
    """Format user statistics for display"""
    achievements_text = ""
    if stats.get("achievements"):
        achievement_names = {
            "secret_swinger": f"🥇 sᴇᴄʀᴇᴛ sᴡɪɴɢᴇʀ (50+ sᴇᴄʀᴇᴛs)",
            "burn_master": f"💀 ʙᴜʀɴ ᴍᴀsᴛᴇʀ (10+ ᴠᴀɴɪsʜɪɴɢ ᴍᴇssᴀɢᴇs)",
            "time_keeper": f"{NINJA_EMOJIS['timer']} ᴛɪᴍᴇ ᴋᴇᴇᴘᴇʀ (5+ ᴛɪᴍᴇᴅ ᴅʀᴏᴘs)",
            "social_butterfly": f"{NINJA_EMOJIS['stealth']} sᴏᴄɪᴀʟ ʙᴜᴛᴛᴇʀғʟʏ (20+ ɢʀᴏᴜᴘ sᴇᴄʀᴇᴛs)",
            "whisper_rookie": f"{NINJA_EMOJIS['shuriken']} ᴡʜɪsᴘᴇʀ ʀᴏᴏᴋɪᴇ (ғɪʀsᴛ sᴇᴄʀᴇᴛ!)",
            "banana_collector": f"{NINJA_EMOJIS['shuriken']} ʙᴀɴᴀɴᴀ ᴄᴏʟʟᴇᴄᴛᴏʀ (25+ ʀᴇᴄᴇɪᴠᴇᴅ)"
        }

        user_achievements = [achievement_names.get(ach, ach) for ach in stats["achievements"]]
        achievements_text = f"\n🏆 **ᴍᴏɴᴋᴇʏ ᴀᴄʜɪᴇᴠᴇᴍᴇɴᴛs:**\n" + "\n".join(user_achievements)

    favorite_targets = stats.get("favorite_targets", {})
    top_targets_text = ""
    if favorite_targets:
        sorted_targets = sorted(favorite_targets.items(), key=lambda x: x[1], reverse=True)[:3]
        top_targets_text = f"\n🎯 **ғᴀᴠᴏʀɪᴛᴇ ᴍᴏɴᴋᴇʏ ғʀɪᴇɴᴅs:**\n"
        for i, (target_id, count) in enumerate(sorted_targets, 1):
            top_targets_text += f"{i}. @user{target_id} ({count} ʙᴀɴᴀɴᴀ ᴇxᴄʜᴀɴɢᴇs)\n"

    weekly_stats = stats.get("weekly_stats", {})

    language = get_string(lang)
    return language["whisper_5"].format(
        weekly_stats.get('secrets_sent', 0),
        weekly_stats.get('secrets_received', 0),
        stats.get('secrets_burned', 0),
        stats.get('secrets_timed', 0)
    ) + achievements_text + top_targets_text

def create_stats_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Create keyboard for stats display"""
    buttons = [
        [
            InlineKeyboardButton(
                f"{NINJA_EMOJIS['ninja']} ғᴜʟʟ sᴛᴀᴛs",
                callback_data=f"whisper_full_stats_{user_id}"
            ),
            InlineKeyboardButton(
                f"🗑 ᴄʟᴇᴀɴ ᴊᴜɴɢʟᴇ {NINJA_EMOJIS['scroll']}",
                callback_data="whisper_clean_history"
            )
        ],
        [
            InlineKeyboardButton(
                f"🏠 ʜᴏᴍᴇ ᴛʀᴇᴇ {NINJA_EMOJIS['shuriken']}",
                callback_data="whisper_dashboard"
            )
        ]
    ]

    return InlineKeyboardMarkup(buttons)
