"""
WhispierBot Inline Query Handler
Handles inline whisper message creation with monkey-themed responses
"""

import asyncio
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import (
    InlineQuery, 
    InlineQueryResultArticle, 
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from ScorpiTune import app
from ScorpiTune.mongo.whisperdb import (
    create_whisper_message, 
    resolve_targets,
    update_user_stats,
    check_and_award_achievements
)
from ScorpiTune.utils.whisper_utils import (
    parse_whisper_command,
    create_whisper_inline_result,
    create_empty_query_response,
    generate_whisper_id,
    MONKEY_EMOJIS
)
from config import BANNED_USERS

@app.on_inline_query(~BANNED_USERS)
async def handle_inline_query(client, query: InlineQuery):
    """Handle inline queries for whisper messages"""
    try:
        query_text = query.query.strip()
        
        # Empty query - show help
        if not query_text:
            results = [create_empty_query_response()]
            await query.answer(results, cache_time=1, is_personal=True)
            return
        
        # Parse the whisper command
        message_content, targets_string, modifiers = parse_whisper_command(query_text)
        
        # Invalid format - show help with example
        if not message_content or not targets_string:
            results = [create_invalid_format_response()]
            await query.answer(results, cache_time=1, is_personal=True)
            return
        
        # Resolve targets
        targets = await resolve_targets(targets_string, app)
        
        if not targets:
            results = [create_no_targets_response()]
            await query.answer(results, cache_time=1, is_personal=True)
            return
        
        # Generate whisper ID
        whisper_id = generate_whisper_id()
        
        # Calculate expiry time if timer is set
        expires_at = None
        if modifiers.get('timer'):
            expires_at = datetime.utcnow() + timedelta(seconds=modifiers['timer'])
        
        # Create the whisper in database (will be created when message is sent)
        # For now, we'll create the inline result
        
        # Create inline result
        result = create_whisper_inline_result(whisper_id, message_content, targets, modifiers)
        
        # Convert to Pyrogram format
        pyrogram_result = InlineQueryResultArticle(
            id=result["id"],
            title=result["title"],
            description=result["description"],
            thumb_url=result.get("thumb_url"),
            input_message_content=InputTextMessageContent(
                message_text=result["input_message_content"]["message_text"],
                parse_mode=result["input_message_content"].get("parse_mode", "Markdown")
            ),
            reply_markup=result.get("reply_markup")
        )
        
        # Store whisper data temporarily for when the message is actually sent
        # We'll use the chosen inline result handler for this
        
        await query.answer([pyrogram_result], cache_time=1, is_personal=True)
        
        # Store the whisper data for the chosen inline result handler
        app.whisper_temp_data = getattr(app, 'whisper_temp_data', {})
        app.whisper_temp_data[whisper_id] = {
            'content': message_content,
            'targets': targets,
            'modifiers': modifiers,
            'sender_id': query.from_user.id,
            'sender_username': query.from_user.username or f"user{query.from_user.id}",
            'expires_at': expires_at
        }
        
    except Exception as e:
        # Log error and return error response
        print(f"Inline query error: {e}")
        results = [create_error_response()]
        await query.answer(results, cache_time=1, is_personal=True)

@app.on_chosen_inline_result()
async def handle_chosen_inline_result(client, chosen_result):
    """Handle when user sends an inline result"""
    try:
        result_id = chosen_result.result_id
        
        # Skip if it's not a whisper
        if result_id in ['empty_query', 'invalid_format', 'no_targets', 'error']:
            return
        
        # Get stored whisper data
        whisper_temp_data = getattr(app, 'whisper_temp_data', {})
        whisper_data = whisper_temp_data.get(result_id)
        
        if not whisper_data:
            return
        
        # Create the whisper message in database
        await create_whisper_message(
            inline_message_id=chosen_result.inline_message_id,
            content=whisper_data['content'],
            sender_id=whisper_data['sender_id'],
            sender_username=whisper_data['sender_username'],
            targets=whisper_data['targets'],
            burn_after_reading=whisper_data['modifiers'].get('burn_after_reading', False),
            expires_at=whisper_data.get('expires_at'),
            style_theme=whisper_data['modifiers'].get('style', 'classic')
        )
        
        # Update user stats
        target_ids = [t.get('resolved_id') for t in whisper_data['targets'] if t.get('resolved_id')]
        await update_user_stats(
            whisper_data['sender_id'], 
            'secrets_sent', 
            1,
            targets=target_ids
        )
        
        # Update specific stats based on modifiers
        if whisper_data['modifiers'].get('burn_after_reading'):
            await update_user_stats(whisper_data['sender_id'], 'secrets_burned', 1)
        
        if whisper_data['modifiers'].get('timer'):
            await update_user_stats(whisper_data['sender_id'], 'secrets_timed', 1)
        
        # Check for achievements
        new_achievements = await check_and_award_achievements(whisper_data['sender_id'])
        
        # Send achievement notification if any new achievements
        if new_achievements:
            try:
                achievement_text = f"{MONKEY_EMOJIS['banana']} **New Achievement{'s' if len(new_achievements) > 1 else ''}!**\n\n"
                for achievement in new_achievements:
                    achievement_names = {
                        "secret_swinger": "🥇 Secret Swinger - 50+ secrets sent!",
                        "burn_master": "💀 Burn Master - 10+ burn-after-reading messages!",
                        "time_keeper": "⏰ Time Keeper - 5+ timed secrets!",
                        "social_butterfly": f"{MONKEY_EMOJIS['circus']} Social Butterfly - 20+ different targets!",
                        "whisper_rookie": f"{MONKEY_EMOJIS['banana']} Whisper Rookie - First secret sent!",
                        "banana_collector": f"{MONKEY_EMOJIS['banana']} Banana Collector - 25+ secrets received!"
                    }
                    achievement_text += f"{achievement_names.get(achievement, achievement)}\n"
                
                achievement_text += f"\n{MONKEY_EMOJIS['monkey']} Keep swinging those secrets!"
                
                await app.send_message(whisper_data['sender_id'], achievement_text)
            except:
                pass  # User might have blocked the bot
        
        # Clean up temporary data
        if result_id in whisper_temp_data:
            del whisper_temp_data[result_id]
        
    except Exception as e:
        print(f"Chosen inline result error: {e}")

def create_invalid_format_response() -> dict:
    """Create response for invalid format"""
    return {
        "type": "article",
        "id": "invalid_format",
        "title": f"{MONKEY_EMOJIS['see_no_evil']} Oops! Format Error",
        "description": f"Need both message and targets!\nExample: secret message @username",
        "thumb_url": "https://i.imgur.com/monkey-error.gif",
        "input_message_content": {
            "message_text": f"""{MONKEY_EMOJIS['see_no_evil']} **Monkey Format Error!**

{MONKEY_EMOJIS['monkey']} You need both a message AND targets!

✅ **Correct format:**
`@whispierbot your secret message @username`

📝 **Examples:**
• `@whispierbot pizza party tonight @alice`
• `@whispierbot meeting at 3pm @bob,@charlie`
• `@whispierbot surprise! @everyone`

{MONKEY_EMOJIS['banana']} Try again, monkey friend!""",
            "parse_mode": "Markdown"
        },
        "reply_markup": InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} Try Again",
                switch_inline_query_current_chat=""
            )]
        ])
    }

def create_no_targets_response() -> dict:
    """Create response when no valid targets found"""
    return {
        "type": "article",
        "id": "no_targets",
        "title": f"{MONKEY_EMOJIS['see_no_evil']} No Valid Targets",
        "description": f"Couldn't find any valid targets!\nCheck usernames and try again.",
        "thumb_url": "https://i.imgur.com/monkey-error.gif",
        "input_message_content": {
            "message_text": f"""{MONKEY_EMOJIS['see_no_evil']} **No Valid Targets Found!**

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
            "parse_mode": "Markdown"
        },
        "reply_markup": InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} Try Again",
                switch_inline_query_current_chat=""
            )]
        ])
    }

def create_error_response() -> dict:
    """Create response for general errors"""
    return {
        "type": "article",
        "id": "error",
        "title": f"{MONKEY_EMOJIS['see_no_evil']} Something Went Wrong",
        "description": "An error occurred. Please try again!",
        "thumb_url": "https://i.imgur.com/monkey-error.gif",
        "input_message_content": {
            "message_text": f"""{MONKEY_EMOJIS['see_no_evil']} **Monkey Error!**

{MONKEY_EMOJIS['monkey']} Something went wrong while processing your secret.

🔄 **Please try again!**

If the problem persists, contact support.

{MONKEY_EMOJIS['banana']} Thanks for your patience!""",
            "parse_mode": "Markdown"
        },
        "reply_markup": InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{MONKEY_EMOJIS['lightning']} Try Again",
                switch_inline_query_current_chat=""
            )]
        ])
    }