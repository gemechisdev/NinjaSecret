"""
WhispierBot Utility Functions
Handles whisper message processing, target resolution, and formatting
"""

import re
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pyrogram import enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from strings import get_string

# Monkey-themed emojis and styling
MONKEY_EMOJIS = {
    "monkey": "🐒",
    "banana": "🍌",
    "tree": "🌳",
    "thought": "💭",
    "whisper": "🤫",
    "fire": "🔥",
    "timer": "⏰",
    "crown": "👑",
    "heart": "💕",
    "circus": "🎪",
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
    Format: @whispierbot [message] [targets] [modifiers]

    Returns: (message_content, targets_string, modifiers)
    """
    if not text.strip():
        return None, None, {}

    # Remove bot username if present
    text = re.sub(r'^@\w+\s+', '', text.strip())

    # Extract modifiers (!delete, !timer:3600, !vip, !cute)
    modifiers = {}

    # Find timer modifier
    timer_match = re.search(r'!timer:(\d+)', text)
    if timer_match:
        modifiers['timer'] = int(timer_match.group(1))
        text = re.sub(r'!timer:\d+', '', text).strip()

    # Find other modifiers
    if '!delete' in text:
        modifiers['burn_after_reading'] = True
        text = text.replace('!delete', '').strip()

    if '!vip' in text:
        modifiers['style'] = 'vip'
        text = text.replace('!vip', '').strip()

    if '!cute' in text:
        modifiers['style'] = 'cute'
        text = text.replace('!cute', '').strip()

    # Extract targets (last @mention, series of @mentions, or user IDs)
    # Updated pattern to handle: @username, user_id, @all, @everyone, etc.
    target_pattern = r'((?:@(?:[\w]+|all|everyone)|[\d]{6,15})(?:\s*,\s*(?:@(?:[\w]+|all|everyone)|[\d]{6,15}))*)\s*$'
    target_match = re.search(target_pattern, text)

    if target_match:
        targets_string = target_match.group(1).strip()
        message_content = text[:target_match.start()].strip()
    else:
        # Try alternative pattern for single target at the end
        alt_pattern = r'(@(?:[\w]+|all|everyone)|[\d]{6,15})\s*$'
        alt_match = re.search(alt_pattern, text)
        if alt_match:
            targets_string = alt_match.group(1).strip()
            message_content = text[:alt_match.start()].strip()
        else:
            # No targets found
            return text.strip() if text.strip() else None, None, modifiers

    return message_content if message_content else None, targets_string, modifiers

def format_targets_display(targets: List[Dict], max_display: int = 3) -> str:
    """Format targets for display in messages"""
    if not targets:
        return "No targets"

    # Check for @all
    for target in targets:
        if target.get("type") == "all":
            return "Everyone"

    # Format individual targets
    target_names = []
    for target in targets[:max_display]:
        display_name = target.get("display_name", target.get("value", "unknown"))

        if target.get("resolved_id"):
            # Target found - use appropriate formatting
            if target.get("type") == "username":
                # For usernames, ensure @ prefix
                if not display_name.startswith("@"):
                    display_name = f"@{display_name}"
            # For user IDs or first names, use as-is (no @ prefix)
            target_names.append(display_name)
        else:
            # Target not found - always show without @ prefix regardless of type
            if not display_name.startswith("@"):
                display_name = f"{display_name}"
            target_names.append(f"{display_name} (not found)")

    if len(targets) > max_display:
        remaining = len(targets) - max_display
        target_names.append(f"and {remaining} more")

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
        return "Expired"

    if remaining.days > 0:
        return f"{remaining.days}d {remaining.seconds // 3600}h"
    elif remaining.seconds >= 3600:
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    elif remaining.seconds >= 60:
        minutes = remaining.seconds // 60
        seconds = remaining.seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        return f"{remaining.seconds}s"

def create_whisper_inline_result(whisper_id: str, content: str, targets: List[Dict], modifiers: Dict, lang: str = "en") -> Dict:
    """Create inline query result for whisper"""
    language = get_string(lang)

    # Format display
    target_display = format_targets_display(targets)
    target_count = len([t for t in targets if t.get("type") != "all"]) if not any(t.get("type") == "all" for t in targets) else "∞"

    # Style based on modifiers
    style_emoji = "🤫💭"
    if modifiers.get('style') == 'vip':
        style_emoji = "👑🍌"
    elif modifiers.get('style') == 'cute':
        style_emoji = "🐒💕"
    elif modifiers.get('burn_after_reading'):
        style_emoji = "💀🔥"
    elif modifiers.get('timer'):
        style_emoji = "⏰🐒"

    # Create description using language strings
    description_parts = []
    if target_count == "∞":
        description_parts.append(language["whisper_inline_desc_everyone"])
    else:
        description_parts.append(language["whisper_inline_desc_for"].format(f"{target_display} ({target_count} monkeys)"))

    if modifiers.get('burn_after_reading'):
        description_parts.append(language["whisper_inline_desc_burns"])

    if modifiers.get('timer'):
        timer_text = format_timer_display(modifiers['timer'])
        description_parts.append(language["whisper_inline_desc_expires"].format(timer_text))

    description_parts.append(language["whisper_inline_desc_style"].format(modifiers.get('style', 'Classic').title()))

    return {
        "type": "article",
        "id": whisper_id,
        "title": language["whisper_inline_title"].format(style_emoji),
        "description": "\n".join(description_parts),
        "thumb_url": "https://i.imgur.com/monkey-whisper.gif",
        "input_message_content": {
            "message_text": create_whisper_posted_message(content, targets, modifiers, lang),
            "parse_mode": enums.ParseMode.MARKDOWN
        },
        "reply_markup": create_whisper_keyboard(whisper_id)
    }

def format_timer_display(seconds: int) -> str:
    """Format timer seconds to human readable"""
    if seconds >= 86400:  # days
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''}"
    elif seconds >= 3600:  # hours
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif seconds >= 60:  # minutes
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return f"{seconds} second{'s' if seconds != 1 else ''}"

def create_whisper_posted_message(content: str, targets: List[Dict], modifiers: Dict, lang: str = "en") -> str:
    """Create the message that gets posted in chat"""
    target_display = format_targets_display(targets)
    language = get_string(lang)

    # Choose style header using language strings
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

    # Target info using language strings
    if any(t.get("type") == "all" for t in targets):
        message_parts.append(language["whisper_for_everyone"])
    else:
        message_parts.append(language["whisper_for_target"].format(target_display))

    # Timer info using language strings
    if modifiers.get('timer'):
        timer_text = format_timer_display(modifiers['timer'])
        message_parts.append(language["whisper_expires"].format(timer_text))

    # Burn info using language strings
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
                f"{MONKEY_EMOJIS['banana']} {MONKEY_EMOJIS['thought']} Peek Secret",
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
                f"{MONKEY_EMOJIS['thought']} {MONKEY_EMOJIS['banana']} Send Secret",
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
                f"{MONKEY_EMOJIS['banana']} Secret Stats",
                callback_data="whisper_stats"
            )
        ],
        [
            InlineKeyboardButton(
                f"{MONKEY_EMOJIS['circus']} Fun Modes",
                callback_data="whisper_styles"
            ),
            InlineKeyboardButton(
                f"{MONKEY_EMOJIS['tree']} Help Tree",
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
        title=language["whisper_empty_title"].format(MONKEY_EMOJIS['monkey']),
        description=language["whisper_empty_desc"].format(MONKEY_EMOJIS['monkey']),
        thumb_url="https://i.imgur.com/monkey-whisper.gif",
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
                f"{MONKEY_EMOJIS['lightning']} {MONKEY_EMOJIS['thought']} Try Now",
                switch_inline_query_current_chat="@whispierbot secret message @username"
            ),
            InlineKeyboardButton(
                f"{MONKEY_EMOJIS['monkey']} Tutorial",
                callback_data="whisper_tutorial"
            )
        ]
    ]

    return InlineKeyboardMarkup(buttons)

def create_secret_revealed_text(content: str, sender_username: str, whisper_data: Dict) -> str:
    """Create text shown when secret is revealed - DEPRECATED: Use language system instead"""
    burn_info = ""
    timer_info = ""

    if whisper_data.get("settings", {}).get("burn_after_reading"):
        targets = whisper_data.get("targets", [])
        unread_targets = [t for t in targets if not t.get("read_at")]
        if len(unread_targets) > 1:
            burn_info = f"\n💀 Burns when {len(unread_targets)-1} more read!"
        elif len(unread_targets) == 1:
            burn_info = "\n💀 Burns when 1 more reads!"
        else:
            burn_info = "\n💀 This was the last read - message burned!"

    if whisper_data.get("settings", {}).get("expires_at"):
        time_remaining = get_time_remaining_text(whisper_data["settings"]["expires_at"])
        if time_remaining != "Expired":
            timer_info = f"\n⏰ {time_remaining} left {MONKEY_EMOJIS['timer']}"

    # Updated to match new whisper_3 format - just show content and footer
    return f'"{content}"{burn_info}{timer_info}\n\n🐒 Keep it between us monkeys!'

def create_unauthorized_access_text(lang: str = "en") -> str:
    """Create text for unauthorized access attempt"""
    language = get_string(lang)
    return language["whisper_4"]

def create_unauthorized_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for unauthorized access"""
    buttons = [
        [
            InlineKeyboardButton(
                f"{MONKEY_EMOJIS['banana']} Create Secret",
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
            "secret_swinger": f"🥇 Secret Swinger (50+ secrets)",
            "burn_master": f"💀 Burn Master (10+ vanishing messages)",
            "time_keeper": f"⏰ Time Keeper (5+ timed drops)",
            "social_butterfly": f"{MONKEY_EMOJIS['circus']} Social Butterfly (20+ group secrets)",
            "whisper_rookie": f"{MONKEY_EMOJIS['banana']} Whisper Rookie (First secret!)",
            "banana_collector": f"{MONKEY_EMOJIS['banana']} Banana Collector (25+ received)"
        }

        user_achievements = [achievement_names.get(ach, ach) for ach in stats["achievements"]]
        achievements_text = f"\n🏆 **Monkey Achievements:**\n" + "\n".join(user_achievements)

    # Top targets
    favorite_targets = stats.get("favorite_targets", {})
    top_targets_text = ""
    if favorite_targets:
        sorted_targets = sorted(favorite_targets.items(), key=lambda x: x[1], reverse=True)[:3]
        top_targets_text = f"\n🎯 **Favorite Monkey Friends:**\n"
        for i, (target_id, count) in enumerate(sorted_targets, 1):
            top_targets_text += f"{i}. @user{target_id} ({count} banana exchanges)\n"

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
                f"{MONKEY_EMOJIS['monkey']} Full Stats",
                callback_data=f"whisper_full_stats_{user_id}"
            ),
            InlineKeyboardButton(
                f"🗑 {MONKEY_EMOJIS['tree']} Clean Jungle",
                callback_data="whisper_clean_history"
            )
        ],
        [
            InlineKeyboardButton(
                f"🏠 {MONKEY_EMOJIS['banana']} Home Tree",
                callback_data="whisper_dashboard"
            )
        ]
    ]

    return InlineKeyboardMarkup(buttons)
