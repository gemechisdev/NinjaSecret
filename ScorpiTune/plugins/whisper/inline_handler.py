
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
from pyrogram import filters, enums
from pyrogram.types import (
    InlineQuery,
    update_user_stats,
    check_and_award_achievements,
    attach_inline_message_id,
    upsert_user,
    store_recent_target,
    get_recent_targets
)
from ScorpiTune.utils.whisper_utils import (
    create_whisper_inline_result,
def extract_message_and_target(text: str):
    """Extract message and target from query text - targets must be at the END only"""
    parts = text.split()
    if len(parts) < 1:
        return None, None

    # Only check the LAST part as target (targets must be at the end)
            return None, None
        return msg, last_token

    # If no target found, return the full text as message and None as target
    return text.strip(), None

def is_target_token(token: str) -> bool:
    """Check if a token looks like a target (username, user_id, or mixed targets)"""
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
        # Extract message, target, and modifiers (with fallback to simple parsing)
        message_content, target_token, modifiers = extract_message_and_target_with_modifiers(query_text)

        # If no target specified but we have message content, show recent target suggestions
        if message_content and not target_token:
            recent_targets = await get_recent_targets(query.from_user.id, 10)
            if recent_targets:
                # Create suggestions for recent targets
                results = []
                for target in recent_targets:
                    # Create a whisper ID for this suggestion
                    whisper_id = generate_whisper_id()

                    # Pre-store whisper data for this suggestion
                    # Create proper target token
                    if target.get("target_username"):
                        target_token = f"@{target['target_username']}"
                    else:
                        target_token = str(target.get("target_id"))

                    store_data = {
                        "whisper_id": whisper_id,
                        "content": message_content,
                        "sender_id": query.from_user.id,
                        "target_username": target.get("target_username"),
                        "target_id": target.get("target_id"),
                        "original_target_token": target_token,
                        "target_mentions": target.get("target_display")
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
                display_names.append(display_name or token)

                # Create mention for the message (using Markdown format)
                if target_id:
                    mention = f"[{display_name or token}](tg://user?id={target_id})"
                    target_mentions.append(mention)
                else:
                    target_mentions.append(display_name or token)

        # Create combined display name
        if len(display_names) == 1:
        else:
            combined_mentions = f"{', '.join(target_mentions[:-1])} & {target_mentions[-1]}"


        # Generate whisper ID
        whisper_id = generate_whisper_id()

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

    except Exception as e:
        # Log error and return error response
        print(f"Inline query error: {e}")
        results = [create_error_response("en")]
        await query.answer(results, cache_time=1, is_personal=True)

@app.on_chosen_inline_result()
        whisper_id = chosen_result.result_id

        # Skip if it's not a whisper
        if whisper_id in ['empty_query', 'invalid_format', 'no_targets', 'error', 'recent_targets_help']:
            return

        # Attach the inline_message_id to the existing whisper
        if chosen_result.inline_message_id:
            await attach_inline_message_id(whisper_id, chosen_result.inline_message_id)

            # If this was a recent target suggestion, update the recent targets
            from ScorpiTune.mongo.whisperdb import get_whisper
            whisper = await get_whisper(whisper_id)
            if whisper and whisper.get("target_id"):
                await store_recent_target(
                    sender_id=whisper["sender_id"],
                    target_id=whisper["target_id"],
                    target_username=whisper.get("target_username"),
                    target_display=whisper.get("target_mentions", get_string("en")['whisper_user_fallback'].format(whisper['target_id']))
                )

    except Exception as e:
        print(f"Chosen inline result error: {e}")

def create_invalid_format_response(lang: str = "en") -> InlineQueryResultArticle:
    """Create response for invalid format"""
    language = get_string(lang)
    return InlineQueryResultArticle(
        id="invalid_format",
        title=f"{MONKEY_EMOJIS['see_no_evil']} {language['whisper_invalid_format_title']}",
        description=language['whisper_invalid_format_desc'],
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=language['whisper_invalid_format_message'],
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} {language['whisper_try_again']}",
                switch_inline_query_current_chat=""
            )]
        ])
    )

def create_no_targets_response(lang: str = "en") -> InlineQueryResultArticle:
    """Create response when no valid targets found"""
    language = get_string(lang)
    return InlineQueryResultArticle(
        id="no_targets",
        title=f"{MONKEY_EMOJIS['see_no_evil']} {language['whisper_no_targets_title']}",
        description=language['whisper_no_targets_desc'],
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=language['whisper_no_targets_message'],
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} {language['whisper_try_again']}",
                switch_inline_query_current_chat=""
            )]
        ])
    )

def create_message_too_long_response(current_length: int, max_length: int, lang: str = "en") -> InlineQueryResultArticle:
    """Create response for message that's too long"""
    language = get_string(lang)
    return InlineQueryResultArticle(
        id="message_too_long",
        title=f"{MONKEY_EMOJIS['see_no_evil']} {language['whisper_message_too_long_title']}",
        description=language['whisper_message_too_long_desc'].format(current_length, max_length),
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=language['whisper_message_too_long_message'].format(current_length, max_length, current_length - max_length),
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} {language['whisper_try_shorter']}",
                switch_inline_query_current_chat=""
            )]
        ])
    )

def create_error_response(lang: str = "en") -> InlineQueryResultArticle:
    """Create response for general errors"""
    language = get_string(lang)
    return InlineQueryResultArticle(
        id="error",
        title=f"{MONKEY_EMOJIS['see_no_evil']} {language['whisper_something_wrong_title']}",
        description=language['whisper_something_wrong_desc'],
        thumb_url="https://i.imgur.com/monkey-error.gif",
        input_message_content=InputTextMessageContent(
            message_text=language['whisper_something_wrong_message'],
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} {language['whisper_try_again']}",
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
        title=f"{MONKEY_EMOJIS['monkey']} {language['whisper_recent_targets_title']}",
        description=language['whisper_recent_targets_desc'].format(len(recent_targets)),
        thumb_url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExYzZnaHloOWJ5N25scGo1OHFhY3h0bnEyb2Rkc2xkYWR2dW1qdm42ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/cwksT0tmuElnj09vuK/giphy.gif",
        input_message_content=InputTextMessageContent(
            message_text=language['whisper_recent_targets_message'].format(targets_text),
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} {language['whisper_start_typing']}",
                switch_inline_query_current_chat=""
            )]
        ])
