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
    InlineKeyboardButton,
    ChosenInlineResult
)
from strings import get_string

from NinjaSecret import app
from NinjaSecret.logging import LOGGER
from NinjaSecret.mongo.whisperdb import (
    store_whisper,
    resolve_target,
    update_user_stats,
    check_and_award_achievements,
    attach_inline_message_id,
    upsert_user,
    add_recent_target,
    get_whisper,
    get_recent_targets
)
from NinjaSecret.utils.whisper_utils import (
    create_whisper_inline_result,
    create_empty_query_response,
    generate_whisper_id,
    create_whisper_keyboard,
    parse_whisper_command,
    NINJA_EMOJIS
)

# Get logger for this module
logger = LOGGER(__name__)

# Log when module is loaded
logger.info("Whisper inline_handler module loaded - on_chosen_inline_result handler registered")
logger.info("NOTE: ChosenInlineResult handler requires 'inline feedback' enabled in @BotFather")
logger.info("To enable: Message @BotFather -> /mybots -> Select bot -> Bot Settings -> Inline Feedback -> Turn on")

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

        # If message but no target, show recent targets as quick-select options
        if message_content and not target_token:
            user_id = query.from_user.id
            recent_targets = await get_recent_targets(user_id)
            
            if recent_targets:
                # Create inline results for each recent target
                results = []
                language = get_string("en")
                
                for i, target in enumerate(recent_targets[:5], 1):  # Show top 5
                    target_username = target.get("username")
                    target_user_id = target.get("user_id")
                    original_token = target.get("original_token", "")
                    
                    # Try to fetch fresh user info to get updated names
                    display_name = None
                    fresh_first_name = None
                    fresh_last_name = None
                    
                    if target_user_id:
                        try:
                            user = await client.get_users(target_user_id)
                            # Build display name from first_name + last_name
                            fresh_first_name = user.first_name
                            fresh_last_name = user.last_name
                            display_name = user.first_name
                            if user.last_name:
                                display_name += f" {user.last_name}"
                            # Update username if it changed
                            if user.username:
                                target_username = user.username.lower()
                            
                            # Update the stored recent target with fresh info
                            target["display_name"] = display_name
                            target["username"] = target_username
                            target["first_name"] = fresh_first_name
                            target["last_name"] = fresh_last_name
                            await add_recent_target(user_id, target)
                            
                            logger.info(f"Fetched and updated recent target: {display_name} (@{target_username})")
                        except Exception as e:
                            logger.warning(f"Could not fetch fresh user info for {target_user_id}: {e}")
                            # Fall back to stored display_name
                            display_name = target.get("display_name")
                    
                    # If we still don't have a display name, build it from stored data or fallback
                    if not display_name:
                        stored_first = target.get("first_name")
                        stored_last = target.get("last_name")
                        
                        if stored_first:
                            # Use stored first + last name
                            display_name = stored_first
                            if stored_last:
                                display_name += f" {stored_last}"
                        elif target_username:
                            # Fallback to username
                            display_name = f"@{target_username}"
                        elif target_user_id:
                            # Fallback to user ID
                            display_name = str(target_user_id)
                        else:
                            # Last resort: use original token
                            display_name = original_token or "Unknown"
                    
                    # Determine the target reference for mentions
                    if target_username:
                        target_ref = f"@{target_username}"
                    elif target_user_id:
                        target_ref = str(target_user_id)
                    else:
                        target_ref = original_token
                    
                    # Generate whisper for this target
                    whisper_id = generate_whisper_id()
                    
                    # Create proper mention with display name (not username/ID)
                    if target_user_id:
                        target_mention = f"[{display_name}](tg://user?id={target_user_id})"
                    else:
                        target_mention = display_name
                    
                    # Store whisper with this target
                    store_data = {
                        "whisper_id": whisper_id,
                        "content": message_content,
                        "sender_id": query.from_user.id,
                        "target_username": target_username,
                        "target_id": target_user_id,
                        "original_target_token": target_ref,
                        "all_targets": [(target_user_id, target_username, target_ref)],
                        "target_mentions": target_mention
                    }
                    
                    if modifiers:
                        store_data["modifiers"] = modifiers
                    
                    await store_whisper(store_data)
                    
                    # Create inline result
                    result_data = create_simple_whisper_inline_result(
                        whisper_id, 
                        message_content, 
                        display_name,
                        target_mention,
                        "en"
                    )
                    
                    # Convert to Pyrogram format with display name in title
                    pyrogram_result = InlineQueryResultArticle(
                        id=result_data["id"],
                        title=f"{NINJA_EMOJIS['lightning']} {display_name} (Recent)",
                        description=result_data["description"],
                        thumb_url=result_data.get("thumb_url"),
                        input_message_content=InputTextMessageContent(
                            message_text=result_data["input_message_content"]["message_text"],
                            parse_mode=enums.ParseMode.MARKDOWN
                        ),
                        reply_markup=result_data.get("reply_markup")
                    )
                    results.append(pyrogram_result)
                
                await query.answer(results, cache_time=1, is_personal=True)
                return
            else:
                # No recent targets, show error with guidance
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
                target_id, target_username, display_name = await resolve_target(token, app)
                resolved_targets.append((target_id, target_username, token))
                
                # When display_name is None but we have target_id, use user ID as placeholder
                if display_name:
                    display_names.append(display_name)
                elif target_id:
                    # Use user ID as placeholder for display
                    display_names.append(str(target_id))
                else:
                    display_names.append(token)

                # Create mention for the message (using Markdown format)
                if target_id:
                    # Use user ID as placeholder if no display name - more informative than zero-width space
                    placeholder = display_name if display_name else str(target_id)
                    mention = f"[{placeholder}](tg://user?id={target_id})"
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
async def handle_chosen_inline_result(client, chosen_result: ChosenInlineResult):
    """Handle when user sends an inline result
    
    Note: This handler requires 'inline feedback' to be enabled in @BotFather
    for the bot to receive ChosenInlineResult updates.
    """
    try:
        whisper_id = chosen_result.result_id
        from_user = chosen_result.from_user
        
        logger.info(f"=== ChosenInlineResult received ===")
        logger.info(f"  result_id (whisper_id): {whisper_id}")
        logger.info(f"  from_user: {from_user.id if from_user else 'None'} (@{from_user.username if from_user and from_user.username else 'no username'})")
        logger.info(f"  inline_message_id: {chosen_result.inline_message_id if chosen_result.inline_message_id else 'None'}")
        logger.info(f"  query: {chosen_result.query if hasattr(chosen_result, 'query') else 'N/A'}")

        # Skip if it's not a whisper
        if whisper_id in ['empty_query', 'invalid_format', 'no_targets', 'error', 'message_too_long']:
            logger.info(f"Skipping non-whisper result: {whisper_id}")
            return

        # Attach the inline_message_id to the existing whisper (only if available)
        if chosen_result.inline_message_id:
            await attach_inline_message_id(whisper_id, chosen_result.inline_message_id)
            logger.info(f"Attached inline_message_id for whisper {whisper_id}")
        
        # Get the whisper to extract target information
        whisper = await get_whisper(whisper_id)
        if not whisper:
            logger.error(f"Whisper not found: {whisper_id}")
            return
            
        logger.info(f"Retrieved whisper {whisper_id} for sender {whisper.get('sender_id')}")
        
        sender_id = whisper.get("sender_id")
        all_targets = whisper.get("all_targets", [])
        
        logger.info(f"Processing {len(all_targets)} targets for recent targets list")
        
        # Add each target to the sender's recent targets list
        for target_id, target_username, original_token in all_targets:
            # Skip @all and @everyone
            if original_token.lower() in ["@all", "@everyone"]:
                logger.info(f"Skipping @all/@everyone target")
                continue
            
            logger.info(f"Processing target: id={target_id}, username={target_username}, token={original_token}")
            
            # Get display name for the target
            display_name = None
            first_name = None
            last_name = None
            
            if target_id:
                try:
                    user = await client.get_users(target_id)
                    first_name = user.first_name
                    last_name = user.last_name
                    display_name = user.first_name
                    if user.last_name:
                        display_name += f" {user.last_name}"
                    # Update username if it changed
                    if user.username:
                        target_username = user.username.lower()
                    logger.info(f"Fetched user info: display_name={display_name}, username={target_username}")
                except Exception as e:
                    logger.warning(f"Could not fetch user info for {target_id}: {e}")
            
            # If we still don't have a display name, use username or ID
            if not display_name:
                if target_username:
                    display_name = f"@{target_username}"
                elif target_id:
                    display_name = str(target_id)
                else:
                    display_name = original_token
            
            # Create target data dict with first_name and last_name
            target_data = {
                "user_id": target_id,
                "username": target_username,
                "first_name": first_name,
                "last_name": last_name,
                "display_name": display_name,
                "original_token": original_token,
                "added_at": datetime.utcnow()
            }
            
            logger.info(f"Adding to recent targets: {target_data}")
            
            # Add to recent targets
            try:
                await add_recent_target(sender_id, target_data)
                logger.info(f"Successfully added target to recent targets for sender {sender_id}")
            except Exception as e:
                logger.exception(f"Failed to add recent target: {e}")

    except Exception:
        logger.exception("Error in handle_chosen_inline_result")

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
