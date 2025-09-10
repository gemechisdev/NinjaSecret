"""
WhispierBot Inline Query Handler
Handles inline whisper message creation with monkey-themed responses
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict
from pyrogram import filters, enums
from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from strings import get_string

from ScorpiTune import app
from ScorpiTune.mongo.whisperdb import (
    store_whisper,
    resolve_target,
    update_user_stats,
    check_and_award_achievements,
    attach_inline_message_id,
    upsert_user
)
from ScorpiTune.utils.whisper_utils import (
    create_whisper_inline_result,
    create_empty_query_response,
    generate_whisper_id,
    create_whisper_keyboard,
    MONKEY_EMOJIS
)

def extract_message_and_target(text: str):
    """Extract message and target from query text - targets must be at the END only"""
    parts = text.split()
    if len(parts) < 2:
        return None, None

    # Only check the LAST part as target (targets must be at the end)
    last_token = parts[-1]

    # Check if the last token looks like a target token
    if is_target_token(last_token):
        msg = " ".join(parts[:-1]).strip()
        if not msg:
            return None, None
        return msg, last_token

    return None, None

def is_target_token(token: str) -> bool:
    """Check if a token looks like a target (username, user_id, or mixed targets)"""
    if not token:
        return False

    # Single @username
    if token.startswith("@") and len(token) > 1:
        return True

    # Single user_id (pure digits) - Telegram user IDs are typically 8-10 digits
    if token.isdigit() and 4 <= len(token) <= 15:
        return True

    # Mixed targets separated by commas (e.g., "2342,@bona", "@alice,123456789")
    if "," in token:
        parts = [part.strip() for part in token.split(",")]
        if len(parts) >= 2:
            # All parts must be valid individual targets
            return all(is_single_target_valid(part) for part in parts if part)

    return False

def is_single_target_valid(part: str) -> bool:
    """Check if a single target part is valid"""
    if not part:
        return False

    # @username
    if part.startswith("@") and len(part) > 1:
        return True

    # Pure digit user_id - Telegram user IDs are typically 8-10 digits
    if part.isdigit() and 4 <= len(part) <= 15:
        return True

    return False

def create_simple_whisper_inline_result(whisper_id: str, content: str, target_display: str, lang: str = "en") -> Dict:
    """Create simplified inline query result for whisper"""
    language = get_string(lang)
    return {
        "id": whisper_id,
        "title": language["whisper_simple_title"].format(target_display),
        "description": language["whisper_simple_desc"],
        "thumb_url": "https://i.imgur.com/monkey-whisper.gif",
        "input_message_content": {
            "message_text": language["whisper_simple_message"].format(target_display),
            "parse_mode": "MARKDOWN"
        },
        "reply_markup": create_whisper_keyboard(whisper_id)
    }

from config import BANNED_USERS

@app.on_inline_query(~BANNED_USERS)
async def handle_inline_query(client, query: InlineQuery):
    """Handle inline queries for whisper messages"""
    try:
        query_text = query.query.strip()

        # Empty query - show help
        if not query_text:
            results = [create_empty_query_response("en")]
            await query.answer(results, cache_time=1, is_personal=True)
            return

        # Extract message and target
        message_content, target_token = extract_message_and_target(query_text)

        # Invalid format - show help with example
        if not message_content or not target_token:
            results = [create_invalid_format_response()]
            await query.answer(results, cache_time=1, is_personal=True)
            return

        # Check message length (Telegram callback answer limit is ~200 chars)
        max_content_length = 180  # Leave buffer for safety
        if len(message_content) > max_content_length:
            results = [create_message_too_long_response(len(message_content), max_content_length)]
            await query.answer(results, cache_time=1, is_personal=True)
            return

        # Parse multiple targets
        target_tokens = [token.strip() for token in target_token.split(",")]
        resolved_targets = []
        display_names = []

        for token in target_tokens:
            target_id, target_username, display_name = await resolve_target(token, app)
            resolved_targets.append((target_id, target_username, token))

            # Better display name logic for resolved targets
            if display_name and display_name != token:
                # We got a resolved name (first name + last name)
                display_names.append(display_name)
            elif target_username:
                # We have a username
                display_names.append(f"@{target_username}")
            elif target_id:
                # We have an ID but no username, show as User ID
                display_names.append(f"User {target_id}")
            else:
                # Fallback to original token
                display_names.append(token)

        # Create combined display name
        if len(display_names) == 1:
            combined_display = display_names[0]
        elif len(display_names) == 2:
            combined_display = f"{display_names[0]} & {display_names[1]}"
        else:
            combined_display = f"{', '.join(display_names[:-1])} & {display_names[-1]}"

        # Generate whisper ID
        whisper_id = generate_whisper_id()

        # For simplified storage, use the first target (maintaining compatibility)
        primary_target = resolved_targets[0] if resolved_targets else (None, None, target_token)

        # Pre-store whisper (so callbacks work immediately)
        await store_whisper({
            "whisper_id": whisper_id,
            "content": message_content,
            "sender_id": query.from_user.id,
            "target_username": primary_target[1],
            "target_id": primary_target[0],
            "original_target_token": target_token,  # Store the full target string for multiple targets
            "all_targets": resolved_targets  # Store all targets for future use
        })

        # Create inline result (simplified - no complex modifiers for now)
        result = create_simple_whisper_inline_result(whisper_id, message_content, combined_display, "en")

        # Convert to Pyrogram format
        pyrogram_result = InlineQueryResultArticle(
            id=result["id"],
            title=result["title"],
            description=result["description"],
            thumb_url=result.get("thumb_url"),
            input_message_content=InputTextMessageContent(
                message_text=result["input_message_content"]["message_text"],
                parse_mode=enums.ParseMode.MARKDOWN
            ),
            reply_markup=result.get("reply_markup")
        )

        # Store whisper data temporarily for when the message is actually sent
        # We'll use the chosen inline result handler for this

        await query.answer([pyrogram_result], cache_time=1, is_personal=True)

        # No need to store temp data - whisper is already in database

    except Exception as e:
        # Log error and return error response
        print(f"Inline query error: {e}")
        results = [create_error_response()]
        await query.answer(results, cache_time=1, is_personal=True)

@app.on_chosen_inline_result()
async def handle_chosen_inline_result(client, chosen_result):
    """Handle when user sends an inline result"""
    try:
        whisper_id = chosen_result.result_id

        # Skip if it's not a whisper
        if whisper_id in ['empty_query', 'invalid_format', 'no_targets', 'error']:
            return

        # Attach the inline_message_id to the existing whisper
        if chosen_result.inline_message_id:
            await attach_inline_message_id(whisper_id, chosen_result.inline_message_id)

    except Exception as e:
        print(f"Chosen inline result error: {e}")

def create_invalid_format_response() -> InlineQueryResultArticle:
    """Create response for invalid format"""
    return InlineQueryResultArticle(
        id="invalid_format",
        title=f"{MONKEY_EMOJIS['see_no_evil']} Oops! Format Error",
        description=f"Need both message and targets!\nExample: secret message @username",
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=f"""{MONKEY_EMOJIS['see_no_evil']} **Monkey Format Error!**

{MONKEY_EMOJIS['monkey']} You need both a message AND targets!

✅ **Correct format:**
`@whispierbot your secret message @username`
`@whispierbot your secret message 123456789`

📝 **Examples:**
• `@whispierbot pizza party tonight @alice`
• `@whispierbot meeting at 3pm @bob,@charlie`
• `@whispierbot mixed targets 2342,@bona`
• `@whispierbot surprise! @everyone`
• `@whispierbot secret message 6153949909`

{MONKEY_EMOJIS['banana']} Try again, monkey friend!""",
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} Try Again",
                switch_inline_query_current_chat=""
            )]
        ])
    )

def create_no_targets_response() -> InlineQueryResultArticle:
    """Create response when no valid targets found"""
    return InlineQueryResultArticle(
        id="no_targets",
        title=f"{MONKEY_EMOJIS['see_no_evil']} No Valid Targets",
        description=f"Couldn't find any valid targets!\nCheck usernames and try again.",
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=f"""{MONKEY_EMOJIS['see_no_evil']} **No Valid Targets Found!**

{MONKEY_EMOJIS['monkey']} I couldn't find any valid users to send to!

💡 **Tips:**
• Make sure usernames exist: `@alice`
• Use commas for multiple: `@bob,@charlie`
• Use `@all` or `@everyone` for everyone
• Remove the @ symbol is optional

📝 **Examples:**
• `@whispierbot secret @validusername`
• `@whispierbot news @user1,@user2`
• `@whispierbot announcement @all`

{MONKEY_EMOJIS['banana']} Try with valid usernames!""",
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} Try Again",
                switch_inline_query_current_chat=""
            )]
        ])
    )

def create_message_too_long_response(current_length: int, max_length: int) -> InlineQueryResultArticle:
    """Create response for message that's too long"""
    return InlineQueryResultArticle(
        id="message_too_long",
        title=f"{MONKEY_EMOJIS['see_no_evil']} Message Too Long!",
        description=f"Your message is {current_length} characters, but max is {max_length}. Please shorten it!",
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=f"""{MONKEY_EMOJIS['see_no_evil']} **Message Too Long, Monkey!**

{MONKEY_EMOJIS['monkey']} Your secret message is **{current_length} characters** long, but the maximum allowed is **{max_length} characters**.

📏 **Please reduce your message by {current_length - max_length} characters.**

💡 **Tips for shorter secrets:**
• Use abbreviations where possible
• Remove unnecessary words
• Split into multiple whispers if needed

{MONKEY_EMOJIS['banana']} Try again with a shorter message!""",
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} Try Shorter Message",
                switch_inline_query_current_chat=""
            )]
        ])
    )

def create_error_response() -> InlineQueryResultArticle:
    """Create response for general errors"""
    return InlineQueryResultArticle(
        id="error",
        title=f"{MONKEY_EMOJIS['see_no_evil']} Something Went Wrong",
        description="An error occurred. Please try again!",
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=f"""{MONKEY_EMOJIS['see_no_evil']} **Monkey Error!**

{MONKEY_EMOJIS['monkey']} Something went wrong while processing your secret.

🔄 **Please try again!**

If the problem persists, contact support.

{MONKEY_EMOJIS['banana']} Thanks for your patience!""",
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} Try Again",
                switch_inline_query_current_chat=""
            )]
        ])
    )
