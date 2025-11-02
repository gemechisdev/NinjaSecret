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
    get_recent_targets,
    get_user_by_id
)
from NinjaSecret.utils.whisper_utils import (
    create_whisper_inline_result,
    create_empty_query_response,
    generate_whisper_id,
    create_whisper_keyboard,
    parse_whisper_command,
    NINJA_EMOJIS,
    get_style_emojis
)

# Get logger for this module
logger = LOGGER(__name__)

# In-memory cache for pending whispers (before they are sent)
# Key: whisper_id, Value: whisper data dict
# This prevents saving whispers to DB before user actually sends them
# Note: This is safe in asyncio single-threaded event loop environment
# If using multiple workers, consider using Redis or similar shared cache
pending_whispers = {}

# Log when module is loaded
logger.info("Whisper inline_handler module loaded - on_chosen_inline_result handler registered")
logger.info("NOTE: ChosenInlineResult handler requires 'inline feedback' enabled in @BotFather")
logger.info("To enable: Message @BotFather -> /mybots -> Select bot -> Bot Settings -> Inline Feedback -> Turn on")

def extract_message_and_target_with_modifiers(text: str):
    """Enhanced extraction that supports special features while maintaining compatibility"""
    # Use the advanced parser for special features - it always extracts modifiers correctly
    message_content, targets_string, modifiers = parse_whisper_command(text)
    
    # Return the parsed result - modifiers are preserved even when there's no target
    return message_content, targets_string, modifiers

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

def create_unified_whisper_inline_result(whisper_id: str, content: str, targets: list, modifiers: dict, target_display: str, target_mentions: str = None, lang: str = "en") -> Dict:
    """Create unified inline query result that handles all whisper types (with or without modifiers)
    
    This function replaces the old create_simple_whisper_inline_result and create_enhanced_whisper_inline_result
    to provide a single, consistent way to create inline results that properly handles all cases including
    tags (!cute, !delete, !timer) with recent targets.
    """
    language = get_string(lang)
    
    # Create proper target dictionaries for the formatter
    targets_dict = []
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
    
    # Always use create_whisper_inline_result - it handles both styled and plain whispers
    # When modifiers is empty dict, it will create a plain whisper with default styling
    return create_whisper_inline_result(whisper_id, content, targets_dict, modifiers, lang)

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
                    
                    # Build token for resolve_target (prefer username, fallback to user_id)
                    token_to_resolve = None
                    if target_username:
                        token_to_resolve = f"@{target_username}"
                    elif target_user_id:
                        token_to_resolve = str(target_user_id)
                    else:
                        token_to_resolve = original_token
                    
                    # Use existing resolve_target to get fresh info (checks DB first, then API)
                    resolved_id, resolved_username, display_name = await resolve_target(token_to_resolve, client)
                    
                    # Update with resolved values
                    if resolved_id:
                        target_user_id = resolved_id
                    if resolved_username:
                        target_username = resolved_username
                    
                    # Fallback to stored data if resolve_target didn't find display_name
                    if not display_name:
                        stored_first = target.get("first_name")
                        stored_last = target.get("last_name")
                        
                        if stored_first:
                            display_name = stored_first
                            if stored_last:
                                display_name += f" {stored_last}"
                        elif target_username:
                            display_name = f"@{target_username}"
                        elif target_user_id:
                            display_name = str(target_user_id)
                        else:
                            display_name = token_to_resolve or "Unknown"
                    
                    # Determine the target reference for storage
                    if target_username:
                        target_ref = f"@{target_username}"
                    elif target_user_id:
                        target_ref = str(target_user_id)
                    else:
                        target_ref = original_token
                    
                    # Generate whisper for this target
                    whisper_id = generate_whisper_id()
                    
                    # Create proper mention with display name
                    if target_user_id and display_name:
                        target_mention = f"[{display_name}](tg://user?id={target_user_id})"
                    elif display_name:
                        target_mention = display_name
                    else:
                        target_mention = target_ref
                    
                    # Cache whisper data temporarily (don't save to DB yet)
                    # Will be saved to DB only when user actually sends it (in chosen_inline_result handler)
                    store_data = {
                        "whisper_id": whisper_id,
                        "content": message_content,
                        "sender_id": query.from_user.id,
                        "target_username": target_username,
                        "target_id": target_user_id,
                        "original_target_token": target_ref,
                        "all_targets": [(target_user_id, target_username, target_ref)],
                        "target_mentions": target_mention,
                        "created_at": datetime.utcnow()  # Track when cached for cleanup
                    }
                    
                    if modifiers:
                        store_data["modifiers"] = modifiers
                    
                    # Store in memory cache instead of database
                    pending_whispers[whisper_id] = store_data
                    
                    # Create inline result using unified function that handles all cases
                    result_data = create_unified_whisper_inline_result(
                        whisper_id,
                        message_content,
                        [(target_user_id, target_username, target_ref)],
                        modifiers,
                        display_name,
                        target_mention,
                        "en"
                    )
                    
                    # Convert to Pyrogram format - preserve style from result_data
                    # For recent targets, we want to show the target name in the title
                    # while preserving any style indicators from the modifiers
                    title_text = result_data["title"]
                    
                    # Check if we have a styled title (contains style emoji)
                    has_style_emoji = any(emoji in title_text for emoji in get_style_emojis())
                    
                    if has_style_emoji:
                        # Keep the styled title, add target name as suffix
                        final_title = f"{title_text} → {display_name}"
                    else:
                        # Simple result, show target name with lightning emoji
                        final_title = f"{NINJA_EMOJIS['lightning']} {display_name} (Recent)"
                    
                    pyrogram_result = InlineQueryResultArticle(
                        id=result_data["id"],
                        title=final_title,
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

        # Cache whisper data temporarily (don't save to DB yet)
        # Will be saved to DB only when user actually sends it (in chosen_inline_result handler)
        store_data = {
            "whisper_id": whisper_id,
            "content": message_content,
            "sender_id": query.from_user.id,
            "target_username": primary_target[1],
            "target_id": primary_target[0],
            "original_target_token": target_token,  # Store the full target string for multiple targets
            "all_targets": resolved_targets,  # Store all targets for future use
            "target_mentions": combined_mentions,  # Store formatted mentions for the message
            "created_at": datetime.utcnow()  # Track when cached for cleanup
        }

        # Add modifiers if present (special features)
        if modifiers:
            store_data["modifiers"] = modifiers

        # Store in memory cache instead of database
        pending_whispers[whisper_id] = store_data

        # Create inline result using unified function that handles all cases
        result = create_unified_whisper_inline_result(whisper_id, message_content, resolved_targets, modifiers, combined_display, combined_mentions, "en")

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

        # Retrieve whisper data from pending cache
        whisper_data = pending_whispers.get(whisper_id)
        if not whisper_data:
            logger.error(f"Whisper data not found in cache: {whisper_id}")
            # Fallback: Try to get from database for backward compatibility
            # This handles edge cases like:
            # 1. Bot restart between inline query and chosen result (cache lost)
            # 2. Old whispers created before this change
            # 3. Whispers created by other instances in multi-instance setup
            whisper = await get_whisper(whisper_id)
            if not whisper:
                logger.error(f"Whisper not found in database either: {whisper_id}")
                return
            logger.info(f"Retrieved whisper from database (fallback): {whisper_id}")
        else:
            # Store the whisper to database now that it's actually sent
            logger.info(f"Storing whisper {whisper_id} to database (user sent it)")
            await store_whisper(whisper_data)
            
            # Remove from pending cache
            del pending_whispers[whisper_id]
            logger.info(f"Removed whisper {whisper_id} from pending cache")
            
            # Retrieve the stored whisper for further processing
            whisper = await get_whisper(whisper_id)
        
        # Attach the inline_message_id to the whisper (only if available)
        if chosen_result.inline_message_id:
            await attach_inline_message_id(whisper_id, chosen_result.inline_message_id)
            logger.info(f"Attached inline_message_id for whisper {whisper_id}")
        
        if not whisper:
            logger.error(f"Whisper not found after storage: {whisper_id}")
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
            
            # Use resolve_target to get/update user info (uses DB cache first, then API if needed)
            # This ensures we always have the latest info and updates the users collection
            resolved_id, resolved_username, display_name = await resolve_target(original_token, client)
            
            # Update with resolved values
            if resolved_id:
                target_id = resolved_id
            if resolved_username:
                target_username = resolved_username
            
            # Get additional user info from database after resolve_target has cached it
            first_name = None
            last_name = None
            if target_id:
                cached_user = await get_user_by_id(target_id)
                if cached_user:
                    first_name = cached_user.get("first_name")
                    last_name = cached_user.get("last_name")
            
            # Fallback display name logic if resolve_target didn't provide one
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
