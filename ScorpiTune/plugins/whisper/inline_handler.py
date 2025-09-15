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

from ScorpiTune import app, userbot
from ScorpiTune.mongo.whisperdb import (
    store_whisper,
    resolve_target,
    update_user_stats,
    check_and_award_achievements,
    attach_inline_message_id,
    upsert_user,
    store_recent_target,
    get_recent_targets
)
from ScorpiTune.utils.whisper_utils import (
    create_whisper_inline_result,
    create_empty_query_response,
    generate_whisper_id,
    create_whisper_keyboard,
    parse_whisper_command,
    MONKEY_EMOJIS
)

def extract_message_and_target_with_modifiers(text: str):
    """Enhanced extraction that supports special features while maintaining compatibility"""
    # First try the advanced parser for special features
    message_content, targets_string, modifiers = parse_whisper_command(text)

    # If advanced parser found everything, return it
    if message_content and targets_string:
        return message_content, targets_string, modifiers

    # Fallback to simple parsing (existing logic) for compatibility
    message_content, targets_string = extract_message_and_target(text)
    return message_content, targets_string, {}

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

    # Single @username, @all, or @everyone
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

    # @username, @all, or @everyone
    if part.startswith("@") and len(part) > 1:
        return True

    # Pure digit user_id - Telegram user IDs are typically 8-10 digits
    if part.isdigit() and 4 <= len(part) <= 15:
        return True

    return False

def create_enhanced_whisper_inline_result(whisper_id: str, content: str, targets: list, modifiers: dict, target_display: str, target_mentions: str = None, lang: str = "en") -> Dict:
    """Create enhanced inline query result that supports special features"""
    if modifiers:
        # Use advanced result with special features
        # Create proper target dictionaries for the advanced formatter
        targets_dict = []
        if targets:
            for target_id, target_username, original_token in targets:
                if original_token.lower() in ["@all", "@everyone"]:
                    targets_dict.append({"display_name": "Everyone", "type": "all"})
                else:
                    # Use mention format if we have target_id, otherwise use display
                    if target_id and target_mentions:
                        # Extract the mention for this specific target from combined mentions
                        display_name = target_mentions
                    else:
                        display_name = target_display
                    targets_dict.append({"display_name": display_name, "type": "user"})

        return create_whisper_inline_result(whisper_id, content, targets_dict, modifiers, lang)
    else:
        # Use simple result for compatibility
        return create_simple_whisper_inline_result(whisper_id, content, target_display, target_mentions, lang)

def create_simple_whisper_inline_result(whisper_id: str, content: str, target_display: str, target_mentions: str = None, lang: str = "en") -> Dict:
    """Create simplified inline query result for whisper"""
    language = get_string(lang)

    # Use mentions if provided, otherwise fall back to display
    target_for_message = target_mentions if target_mentions else target_display

    return {
        "id": whisper_id,
        "title": language["whisper_simple_title"].format(target_display),
        "description": language["whisper_simple_desc"],
        "thumb_url": "https://i.imgur.com/monkey-whisper.gif",
        "input_message_content": {
            "message_text": language["whisper_simple_message"].format(target_for_message),
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

        # Extract message, target, and modifiers (with fallback to simple parsing)
        message_content, target_token, modifiers = extract_message_and_target_with_modifiers(query_text)

        # If no target specified but we have message content, show recent target suggestions
        if message_content and not target_token:
            recent_targets = await get_recent_targets(query.from_user.id, 10)
            if recent_targets:
                # Create suggestions for recent targets
                results = []
                for target in recent_targets:
                    suggestion = create_recent_target_suggestion(target, message_content, "en")
                    results.append(suggestion)

                # Also add the help response as the last option
                results.append(create_invalid_format_response())

                await query.answer(results, cache_time=1, is_personal=True)
                return
            else:
                # No recent targets, show normal invalid format response
                results = [create_invalid_format_response()]
                await query.answer(results, cache_time=1, is_personal=True)
                return

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
        target_mentions = []  # For creating mentions in the message

        for token in target_tokens:
            # Handle special @all/@everyone cases
            if token.lower() in ["@all", "@everyone"]:
                resolved_targets.append((None, None, token))
                display_names.append("Everyone")
                target_mentions.append("Everyone")
            else:
                target_id, target_username, display_name = await resolve_target(token, app, userbot)
                resolved_targets.append((target_id, target_username, token))
                # Use the display name returned by resolve_target (it handles all cases properly)
                display_names.append(display_name or token)

                # Create mention for the message (using Markdown format)
                print(f"DEBUG: Creating mention - target_id: {target_id}, display_name: {display_name}")
                if target_id:
                    mention = f"[{display_name or token}](tg://user?id={target_id})"
                    target_mentions.append(mention)
                    print(f"DEBUG: Added mention: {mention}")
                else:
                    target_mentions.append(display_name or token)
                    print(f"DEBUG: No mention, added display: {display_name or token}")

        # Create combined display name
        if len(display_names) == 1:
            combined_display = display_names[0]
        elif len(display_names) == 2:
            combined_display = f"{display_names[0]} & {display_names[1]}"
        else:
            combined_display = f"{', '.join(display_names[:-1])} & {display_names[-1]}"

        # Create combined mention string for the message
        if len(target_mentions) == 1:
            combined_mentions = target_mentions[0]
        elif len(target_mentions) == 2:
            combined_mentions = f"{target_mentions[0]} & {target_mentions[1]}"
        else:
            combined_mentions = f"{', '.join(target_mentions[:-1])} & {target_mentions[-1]}"

        print(f"DEBUG: Final combined_mentions: {combined_mentions}")
        print(f"DEBUG: Final combined_display: {combined_display}")

        # Generate whisper ID
        whisper_id = generate_whisper_id()

        # For simplified storage, use the first target (maintaining compatibility)
        primary_target = resolved_targets[0] if resolved_targets else (None, None, target_token)

        # Pre-store whisper (so callbacks work immediately)
        store_data = {
            "whisper_id": whisper_id,
            "content": message_content,
            "sender_id": query.from_user.id,
            "target_username": primary_target[1],
            "target_id": primary_target[0],
            "original_target_token": target_token,  # Store the full target string for multiple targets
            "all_targets": resolved_targets,  # Store all targets for future use
            "target_mentions": combined_mentions  # Store formatted mentions for the message
        }

        # Add modifiers if present (special features)
        if modifiers:
            store_data["modifiers"] = modifiers

        await store_whisper(store_data)

        # Store recent targets for the sender (excluding @all/@everyone)
        for target_id, target_username, original_token in resolved_targets:
            if target_id and original_token.lower() not in ["@all", "@everyone"]:
                # Get display name from resolved target
                display_name = None
                for i, (tid, tusername, ttoken) in enumerate(resolved_targets):
                    if tid == target_id:
                        display_name = display_names[i]
                        break

                await store_recent_target(
                    sender_id=query.from_user.id,
                    target_id=target_id,
                    target_username=target_username,
                    target_display=display_name
                )

        # Create inline result (enhanced with special features support)
        result = create_enhanced_whisper_inline_result(whisper_id, message_content, resolved_targets, modifiers, combined_display, combined_mentions, "en")

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
• `@whispierbot confidential info @boss !delete`
• `@whispierbot party at 8pm @friends !timer:3600`
• `@whispierbot announcement @all !vip`

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

def create_recent_target_suggestion(target: Dict, message_content: str = "", lang: str = "en") -> InlineQueryResultArticle:
    """Create inline query result for recent target suggestion"""
    target_id = target.get("target_id")
    target_username = target.get("target_username")
    target_display = target.get("target_display", f"User {target_id}")

    # Create the suggestion text that will be inserted when selected
    if target_username:
        suggestion_text = f"@{target_username}"
    else:
        suggestion_text = str(target_id)

    # If there's existing message content, append the target
    if message_content.strip():
        full_text = f"{message_content.strip()} {suggestion_text}"
    else:
        full_text = f"your secret message {suggestion_text}"

    # Determine emoji based on target type
    emoji = "🎯"
    if target_username:
        emoji = f"{MONKEY_EMOJIS['monkey']}"

    return InlineQueryResultArticle(
        id=f"recent_target_{target_id}",
        title=f"{emoji} {target_display}",
        description=f"Recent target • Click to add {suggestion_text}",
        thumb_url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExYzZnaHloOWJ5N25scGo1OHFhY3h0bnEyb2Rkc2xkYWR2dW1qdm42ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/cwksT0tmuElnj09vuK/giphy.gif",
        input_message_content=InputTextMessageContent(
            message_text=f"@whispierbot {full_text}",
            parse_mode=enums.ParseMode.MARKDOWN
        )
    )

def create_recent_targets_help_response(recent_targets: List[Dict], lang: str = "en") -> InlineQueryResultArticle:
    """Create help response showing recent targets"""
    language = get_string(lang)

    targets_list = []
    for i, target in enumerate(recent_targets[:5], 1):
        target_display = target.get("target_display", f"User {target.get('target_id')}")
        if target.get("target_username"):
            targets_list.append(f"{i}. {target_display} (@{target['target_username']})")
        else:
            targets_list.append(f"{i}. {target_display} (ID: {target.get('target_id')})")

    targets_text = "\n".join(targets_list) if targets_list else "No recent targets yet"

    return InlineQueryResultArticle(
        id="recent_targets_help",
        title=f"{MONKEY_EMOJIS['monkey']} Recent Targets Available!",
        description=f"You have {len(recent_targets)} recent targets. Type your message to see suggestions!",
        thumb_url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExYzZnaHloOWJ5N25scGo1OHFhY3h0bnEyb2Rkc2xkYWR2dW1qdm42ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/cwksT0tmuElnj09vuK/giphy.gif",
        input_message_content=InputTextMessageContent(
            message_text=f"""{MONKEY_EMOJIS['banana']} **Your Recent Whisper Targets**

{MONKEY_EMOJIS['monkey']} **Recent monkeys you've whispered to:**

{targets_text}

💡 **How to use:**
• Type your message: `@whispierbot your secret message`
• Recent targets will appear as suggestions
• Click any suggestion to auto-complete

{MONKEY_EMOJIS['lightning']} **Or type full command:**
`@whispierbot your message @username`

{MONKEY_EMOJIS['tree']} Ready to swing into action!""",
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} Start Typing",
                switch_inline_query_current_chat=""
            )]
        ])
    )
