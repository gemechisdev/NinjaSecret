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

from NinjaSecret import app
from NinjaSecret.logging import LOGGER
from NinjaSecret.mongo.whisperdb import (
    store_whisper,
    resolve_target,
    update_user_stats,
    check_and_award_achievements,
    upsert_user,
    store_recent_target,
    get_recent_targets,
    MAX_RECENT_TARGETS
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

# Temporary cache for whisper data before they are actually sent
# Key: whisper_id, Value: {"data": whisper_data, "timestamp": datetime}
# This prevents storing whispers in DB during inline query generation
pending_whispers_cache: Dict[str, Dict] = {}

# Cache timeout in seconds (5 minutes)
CACHE_TIMEOUT_SECONDS = 300

# Cleanup counter - cleanup every N queries to reduce overhead
cleanup_counter = 0
CLEANUP_INTERVAL = 50  # Cleanup every 50 queries

async def cleanup_stale_cache_entries():
    """Remove cache entries older than CACHE_TIMEOUT_SECONDS"""
    global cleanup_counter
    cleanup_counter += 1
    
    # Only cleanup every CLEANUP_INTERVAL queries
    if cleanup_counter < CLEANUP_INTERVAL:
        return
    
    cleanup_counter = 0
    current_time = datetime.utcnow()
    stale_keys = []
    
    for whisper_id, cache_entry in pending_whispers_cache.items():
        timestamp = cache_entry.get("timestamp")
        if timestamp and (current_time - timestamp).total_seconds() > CACHE_TIMEOUT_SECONDS:
            stale_keys.append(whisper_id)
    
    for key in stale_keys:
        del pending_whispers_cache[key]
        logger.debug(f"Removed stale cache entry: {key}")
    
    if stale_keys:
        logger.info(f"Cleaned up {len(stale_keys)} stale cache entries")

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
            logger.info(f"No target specified for user {query.from_user.id}, checking recent targets...")
            recent_targets = await get_recent_targets(query.from_user.id, MAX_RECENT_TARGETS)
            logger.info(f"Found {len(recent_targets)} recent targets for user {query.from_user.id}")
            if recent_targets:
                # Create suggestions for recent targets
                results = []
                for target in recent_targets:
                    # Get target information
                    target_id = target.get("target_id")
                    target_username = target.get("target_username")
                    original_token = target.get("original_token")
                    target_display = target.get("target_display")
                    
                    # Try to get fresh display name if we have target_id
                    if target_id:
                        try:
                            resolved_target_id, resolved_username, resolved_display = await resolve_target(str(target_id), app)
                            if resolved_display:
                                target_display = resolved_display
                                target_username = resolved_username
                        except Exception:
                            pass  # Use cached information if resolution fails
                    
                    # Generate whisper ID for this suggestion
                    whisper_id = generate_whisper_id()
                    
                    # Determine target token for whisper storage
                    if original_token:
                        use_target_token = original_token
                    elif target_username:
                        use_target_token = f"@{target_username}"
                    elif target_id:
                        use_target_token = str(target_id)
                    else:
                        continue  # Skip if we can't identify the target
                    
                    # Create display name if not available
                    if not target_display:
                        if target_username:
                            target_display = f"@{target_username}"
                        elif target_id:
                            target_display = str(target_id)
                        else:
                            target_display = original_token or "Unknown"
                    
                    # Create mention for message
                    if target_id:
                        target_mention = f"[{target_display}](tg://user?id={target_id})"
                    else:
                        target_mention = target_display
                    
                    # Cache whisper data (don't store in DB yet - only when user sends)
                    store_data = {
                        "whisper_id": whisper_id,
                        "content": message_content,
                        "sender_id": query.from_user.id,
                        "target_username": target_username,
                        "target_id": target_id,
                        "original_target_token": use_target_token,
                        "all_targets": [(target_id, target_username, use_target_token)],
                        "target_mentions": target_mention
                    }
                    # Store in temporary cache with timestamp
                    pending_whispers_cache[whisper_id] = {
                        "data": store_data,
                        "timestamp": datetime.utcnow()
                    }
                    
                    # Create inline result
                    logger.debug(f"Creating recent target suggestion for {target_display} (ID: {target_id})")
                    suggestion = create_recent_target_suggestion(target_display, target_id, whisper_id, "en")
                    results.append(suggestion)
                
                logger.info(f"Showing {len(results)} recent target suggestions (plus help) to user {query.from_user.id}")
                # Add help response as last option
                results.append(create_invalid_format_response("en"))
                
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

        # Cache whisper data (don't store in DB yet - only when user actually sends)
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

        # Store in temporary cache with timestamp
        pending_whispers_cache[whisper_id] = {
            "data": store_data,
            "timestamp": datetime.utcnow()
        }
        
        # Periodically cleanup stale cache entries
        await cleanup_stale_cache_entries()

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

        # Answer the inline query with the result
        # Whisper will only be stored in DB when user actually sends it (chosen_inline_result)
        await query.answer([pyrogram_result], cache_time=1, is_personal=True)

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
        logger.info(f"Chosen inline result: whisper_id={whisper_id}, user={chosen_result.from_user.id}")

        # Skip if it's not a whisper
        if whisper_id in ['empty_query', 'invalid_format', 'no_targets', 'error', 'message_too_long']:
            logger.debug(f"Skipping non-whisper result: {whisper_id}")
            return

        # Retrieve whisper data from cache
        cache_entry = pending_whispers_cache.get(whisper_id)
        if not cache_entry:
            logger.warning(f"Whisper data not found in cache for ID {whisper_id}")
            return
        
        whisper_data = cache_entry.get("data")
        if not whisper_data:
            logger.warning(f"Whisper data structure invalid for ID {whisper_id}")
            return
        
        logger.info(f"Retrieved whisper from cache: {whisper_id}")
        
        # Add inline_message_id if available
        if chosen_result.inline_message_id:
            whisper_data["inline_message_id"] = chosen_result.inline_message_id
        
        # NOW store the whisper in the database (only when user actually sends it)
        await store_whisper(whisper_data)
        logger.info(f"Stored whisper {whisper_id} in database after user sent it")
        
        # Remove from cache to free memory
        del pending_whispers_cache[whisper_id]
        
        # Get all targets from the whisper
        all_targets = whisper_data.get("all_targets", [])
        
        # Fallback to single target if all_targets not available
        if not all_targets and whisper_data.get("target_id"):
            all_targets = [(whisper_data["target_id"], whisper_data.get("target_username"), whisper_data.get("original_target_token"))]
        
        if not all_targets:
            logger.warning(f"No targets found in whisper {whisper_id}")
            return
        
        logger.info(f"Found {len(all_targets)} target(s) in whisper {whisper_id}")
        
        # Store recent target for each target (excluding @all/@everyone)
        for target_id, target_username, original_token in all_targets:
            # Skip special targets
            if original_token and original_token.lower() in ["@all", "@everyone"]:
                logger.debug(f"Skipping special target: {original_token}")
                continue
            
            # Ensure target_id is integer if provided
            if target_id:
                try:
                    target_id = int(target_id)
                except (ValueError, TypeError):
                    target_id = None
            
            logger.info(f"Processing target: id={target_id}, username={target_username}, token={original_token}")
            
            # Try to get fresh user information
            target_display = None
            if target_id:
                try:
                    resolved_target_id, resolved_username, resolved_display = await resolve_target(str(target_id), app)
                    if resolved_display:
                        target_display = resolved_display
                        target_username = resolved_username
                    logger.debug(f"Resolved target {target_id}: display={resolved_display}, username={resolved_username}")
                except Exception as e:
                    logger.warning(f"Failed to resolve target {target_id}: {e}")
            
            # Store the recent target
            try:
                logger.info(f"Storing recent target for user {whisper_data['sender_id']}: target_id={target_id}, username={target_username}, display={target_display}, token={original_token}")
                await store_recent_target(
                    sender_id=whisper_data["sender_id"],
                    target_id=target_id,
                    target_username=target_username,
                    target_display=target_display,
                    original_token=original_token
                )
                logger.info(f"Successfully stored recent target for user {whisper_data['sender_id']}")
            except Exception:
                logger.exception(f"Failed to store recent target for user {whisper_data['sender_id']}")

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

def create_recent_target_suggestion(target_display: str, target_id: int, whisper_id: str, lang: str = "en") -> InlineQueryResultArticle:
    """Create inline query result for recent target suggestion"""
    language = get_string(lang)
    
    # Create mention for message
    if target_id:
        mention = f"[{target_display}](tg://user?id={target_id})"
    else:
        mention = target_display
    
    return InlineQueryResultArticle(
        id=whisper_id,
        title=language['whisper_recent_secret_for'].format(target_display),
        description=language['whisper_recent_click_desc'],
        thumb_url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExYzZnaHloOWJ5N25scGo1OHFhY3h0bnEyb2Rkc2xkYWR2dW1qdm42ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/cwksT0tmuElnj09vuK/giphy.gif",
        input_message_content=InputTextMessageContent(
            message_text=language['whisper_recent_secret_message'].format(mention),
            parse_mode=enums.ParseMode.MARKDOWN
        ),
        reply_markup=create_whisper_keyboard(whisper_id)
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
