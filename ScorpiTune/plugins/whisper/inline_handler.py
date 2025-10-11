"""
Ninja Secret🥷 Inline Query Handler
Handles inline secret message creation with ninja-themed responses
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
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
    NINJA_EMOJIS
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
    if len(parts) < 1:
        return None, None

    # Only check the LAST part as target (targets must be at the end)
    last_token = parts[-1]

    # Check if the last token looks like a target token
    if is_target_token(last_token):
        msg = " ".join(parts[:-1]).strip()
        if not msg:
            return None, None
        return msg, last_token

    # If no target found, return the full text as message and None as target
    return text.strip(), None

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
        language = get_string(lang)
        if targets:
            for target_id, target_username, original_token in targets:
                if original_token.lower() in ["@all", "@everyone"]:
                    targets_dict.append({"display_name": language['whisper_everyone'], "type": "all"})
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
                    # Refresh target information to get updated name
                    target_id = target.get("target_id")
                    target_username = target.get("target_username")

                    # Try to resolve current user information using userbot first
                    if target_id:
                        try:
                            resolved_target_id, resolved_username, resolved_display = await resolve_target(str(target_id), app, userbot)
                            if resolved_display and resolved_display != f"User {target_id}":
                                # Update target with fresh information
                                target["target_display"] = resolved_display
                                target["target_username"] = resolved_username
                        except Exception as e:
                            pass  # Use cached information if resolution fails

                    # Create a whisper ID for this suggestion
                    whisper_id = generate_whisper_id()

                    # Pre-store whisper data for this suggestion
                    # Create proper target token
                    if target.get("target_username"):
                        target_token = f"@{target['target_username']}"
                    else:
                        target_token = str(target.get("target_id"))

                    # Create proper mention for the message
                    target_display = target.get("target_display")
                    if not target_display:
                        language = get_string("en")
                        target_display = language['whisper_user_fallback'].format(target_id)

                    # Create mention with tg://user?id= format
                    if target_id:
                        target_mention = f"[{target_display}](tg://user?id={target_id})"
                    else:
                        target_mention = target_display

                    store_data = {
                        "whisper_id": whisper_id,
                        "content": message_content,
                        "sender_id": query.from_user.id,
                        "target_username": target.get("target_username"),
                        "target_id": target.get("target_id"),
                        "original_target_token": target_token,
                        "target_mentions": target_mention
                    }
                    await store_whisper(store_data)

                    # Create the suggestion with proper whisper format
                    suggestion = create_recent_target_suggestion_with_id(target, message_content, whisper_id, "en")
                    results.append(suggestion)

                # Also add the help response as the last option
                results.append(create_invalid_format_response("en"))

                await query.answer(results, cache_time=1, is_personal=True)
                return
            else:
                # No recent targets, show normal invalid format response
                results = [create_invalid_format_response("en")]
                await query.answer(results, cache_time=1, is_personal=True)
                return

        # Invalid format - show help with example
        if not message_content or not target_token:
            results = [create_invalid_format_response("en")]
            await query.answer(results, cache_time=1, is_personal=True)
            return

        # Check message length (Telegram callback answer limit is ~200 chars)
        max_content_length = 180  # Leave buffer for safety
        if len(message_content) > max_content_length:
            results = [create_message_too_long_response(len(message_content), max_content_length, "en")]
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
                language = get_string("en")  # Default language for now
                everyone_text = language['whisper_everyone']
                display_names.append(everyone_text)
                target_mentions.append(everyone_text)
            else:
                target_id, target_username, display_name = await resolve_target(token, app, userbot)
                resolved_targets.append((target_id, target_username, token))
                # Use the display name returned by resolve_target (it handles all cases properly)
                display_names.append(display_name or token)

                # Create mention for the message (using Markdown format)
                if target_id:
                    mention = f"[{display_name or token}](tg://user?id={target_id})"
                    target_mentions.append(mention)
                else:
                    target_mentions.append(display_name or token)

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
        results = [create_error_response("en")]
        await query.answer(results, cache_time=1, is_personal=True)

@app.on_chosen_inline_result()
async def handle_chosen_inline_result(client, chosen_result):
    """Handle when user sends an inline result"""
    try:
        whisper_id = chosen_result.result_id

        # Skip if it's not a whisper
        if whisper_id in ['empty_query', 'invalid_format', 'no_targets', 'error', 'recent_targets_help']:
            return

        # Attach the inline_message_id to the existing whisper
        if chosen_result.inline_message_id:
            await attach_inline_message_id(whisper_id, chosen_result.inline_message_id)

            # If this was a recent target suggestion, update the recent targets with fresh info
            from ScorpiTune.mongo.whisperdb import get_whisper
            whisper = await get_whisper(whisper_id)
            if whisper and whisper.get("target_id"):
                # Try to get fresh user information using userbot first
                target_display = whisper.get("target_mentions", get_string("en")['whisper_user_fallback'].format(whisper['target_id']))
                target_username = whisper.get("target_username")

                # Attempt to refresh user info
                try:
                    resolved_target_id, resolved_username, resolved_display = await resolve_target(str(whisper["target_id"]), app, userbot)
                    if resolved_display and resolved_display != f"User {whisper['target_id']}":
                        target_display = resolved_display
                        target_username = resolved_username
                except Exception as e:
                    pass

                await store_recent_target(
                    sender_id=whisper["sender_id"],
                    target_id=whisper["target_id"],
                    target_username=target_username,
                    target_display=target_display
                )

    except Exception as e:
        print(f"Chosen inline result error: {e}")

def create_invalid_format_response(lang: str = "en") -> InlineQueryResultArticle:
    """Create response for invalid format"""
    language = get_string(lang)
    return InlineQueryResultArticle(
        id="invalid_format",
        title=f"{NINJA_EMOJIS['see_no_evil']} {language['whisper_invalid_format_title']}",
        description=language['whisper_invalid_format_desc'],
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=language['whisper_invalid_format_message'],
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{NINJA_EMOJIS['lightning']} {language['whisper_try_again']}",
                switch_inline_query_current_chat=""
            )]
        ])
    )

def create_no_targets_response(lang: str = "en") -> InlineQueryResultArticle:
    """Create response when no valid targets found"""
    language = get_string(lang)
    return InlineQueryResultArticle(
        id="no_targets",
        title=f"{NINJA_EMOJIS['see_no_evil']} {language['whisper_no_targets_title']}",
        description=language['whisper_no_targets_desc'],
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=language['whisper_no_targets_message'],
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{NINJA_EMOJIS['lightning']} {language['whisper_try_again']}",
                switch_inline_query_current_chat=""
            )]
        ])
    )

def create_message_too_long_response(current_length: int, max_length: int, lang: str = "en") -> InlineQueryResultArticle:
    """Create response for message that's too long"""
    language = get_string(lang)
    return InlineQueryResultArticle(
        id="message_too_long",
        title=f"{NINJA_EMOJIS['see_no_evil']} {language['whisper_message_too_long_title']}",
        description=language['whisper_message_too_long_desc'].format(current_length, max_length),
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=language['whisper_message_too_long_message'].format(current_length, max_length, current_length - max_length),
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{NINJA_EMOJIS['lightning']} {language['whisper_try_shorter']}",
                switch_inline_query_current_chat=""
            )]
        ])
    )

def create_error_response(lang: str = "en") -> InlineQueryResultArticle:
    """Create response for general errors"""
    language = get_string(lang)
    return InlineQueryResultArticle(
        id="error",
        title=f"{NINJA_EMOJIS['see_no_evil']} {language['whisper_something_wrong_title']}",
        description=language['whisper_something_wrong_desc'],
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=language['whisper_something_wrong_message'],
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{NINJA_EMOJIS['lightning']} {language['whisper_try_again']}",
                switch_inline_query_current_chat=""
            )]
        ])
    )

def create_recent_target_whisper_message(target_display: str, target_id: int, lang: str = "en") -> str:
    """Create whisper message with proper user mention"""
    language = get_string(lang)
    if target_id:
        # Create proper Telegram mention
        mention = f"[{target_display}](tg://user?id={target_id})"
        return language['whisper_recent_secret_message'].format(mention)
    else:
        return language['whisper_recent_secret_message'].format(target_display)

def create_recent_target_suggestion_with_id(target: Dict, message_content: str, whisper_id: str, lang: str = "en") -> InlineQueryResultArticle:
    """Create inline query result for recent target suggestion - creates actual whisper"""
    target_id = target.get("target_id")
    target_username = target.get("target_username")
    target_display = target.get("target_display")
    if not target_display:
        language = get_string(lang)
        target_display = language['whisper_user_fallback'].format(target_id)

    language = get_string(lang)

    return InlineQueryResultArticle(
        id=whisper_id,
        title=language['whisper_recent_secret_for'].format(target_display),
        description=language['whisper_recent_click_desc'],
        thumb_url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExYzZnaHloOWJ5N25scGo1OHFhY3h0bnEyb2Kkc2xkYWR2dW1qdm42ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/cwksT0tmuElnj09vuK/giphy.gif",
        input_message_content=InputTextMessageContent(
            message_text=create_recent_target_whisper_message(target_display, target_id, lang),
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=create_whisper_keyboard(whisper_id)
    )

def create_recent_targets_help_response(recent_targets: List[Dict], lang: str = "en") -> InlineQueryResultArticle:
    """Create help response showing recent targets"""
    language = get_string(lang)

    targets_list = []
    for i, target in enumerate(recent_targets[:5], 1):
        target_display = target.get("target_display")
        if not target_display:
            target_display = language['whisper_user_fallback'].format(target.get('target_id'))

        if target.get("target_username"):
            targets_list.append(f"{i}. {target_display} (@{target['target_username']})")
        else:
            targets_list.append(f"{i}. {target_display} (ID: {target.get('target_id')})")

    targets_text = "\n".join(targets_list) if targets_list else language['whisper_no_recent_targets']

    return InlineQueryResultArticle(
        id="recent_targets_help",
        title=f"{NINJA_EMOJIS['ninja']} {language['whisper_recent_targets_title']}",
        description=language['whisper_recent_targets_desc'].format(len(recent_targets)),
        thumb_url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExYzZnaHloOWJ5N25scGo1OHFhY3h0bnEyb2Rkc2xkYWR2dW1qdm42ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/cwksT0tmuElnj09vuK/giphy.gif",
        input_message_content=InputTextMessageContent(
            message_text=language['whisper_recent_targets_message'].format(targets_text),
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{NINJA_EMOJIS['lightning']} {language['whisper_start_typing']}",
                switch_inline_query_current_chat=""
            )]
        ])
    )
