import os
import json
import ast
from typing import Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, status
from telegram import Bot, Update, InlineQueryResultArticle, InputTextMessageContent
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import TelegramError, BadRequest, Forbidden
import logging
import re

from ..db import supabase
from ..models import TelegramUpdate

logger = logging.getLogger(__name__)

# Changed router prefix to match webhook URL
router = APIRouter(prefix="/api", tags=["telegram"])

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logger.warning("No TELEGRAM_BOT_TOKEN provided!")

ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))

@router.post("/webhook")
async def webhook(request: Request):
    """Handle incoming updates from Telegram."""
    if not TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bot token not configured"
        )

    try:
        # Get update data
        data = await request.json()
        logger.info(f"Received update: {data.get('update_id', 'No update_id')}")

        # Create bot instance
        bot = Bot(token=TOKEN)

        # Process update directly
        update = Update.de_json(data, bot)

        # Handle different update types
        if update.message:
            await handle_message(bot, update)
        elif update.inline_query:
            await handle_inline_query(bot, update)
        elif update.callback_query:
            await handle_callback_query(bot, update)
        elif update.chosen_inline_result:
            await handle_chosen_inline_result(bot, update)

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return {
            "status": "error", 
            "message": str(e)
        }


async def handle_message(bot: Bot, update: Update):
    """Handle regular messages."""
    message = update.message
    user = message.from_user

    # Store user in database
    await store_user(user.id, None)

    if message.text:
        text = message.text.strip()
        if text.startswith('/start'):
            await send_start_message(bot, message)
        elif text.startswith('/help'):
            await send_help_message(bot, message)
        elif text.startswith('/stats') and user.id == ADMIN_USER_ID:
            await send_stats_message(bot, message)


async def handle_inline_query(bot: Bot, update: Update):
    """Handle inline queries for whisper creation."""
    query = update.inline_query
    query_text = query.query.strip()
    sender_id = query.from_user.id

    # Store user
    await store_user(sender_id, None)

    results = []

    if not query_text:
        # Empty query - show main result
        results = [get_main_result()]
    else:
        # Parse query to extract message and target
        parts = query_text.split()
        if len(parts) >= 2:
            target = parts[-1]
            message = " ".join(parts[:-1])

            # Validate and clean target
            target_user = await get_target_user(bot, target, sender_id)
            
            if target_user:
                # Create whisper result with proper target name
                data_list = [sender_id, target_user["id"]]
                name = target_user["name"]
                mention = target_user["mention"]

                results = [InlineQueryResultArticle(
                    id="whisper",
                    title=f"🔒 Whisper to {name}",
                    description="Only they can open this message",
                    input_message_content=InputTextMessageContent(
                        f"🔒 A whisper message to {mention} 🔒\nOnly they can open it.",
                        parse_mode="HTML"
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔐 Show Message 🔐", callback_data=str(data_list))
                    ]])
                )]
                
                logger.info(f"Created whisper result for {name} (ID: {target_user['id']})")
            else:
                # Fall back to previous targets or main result
                results = await get_previous_target_results(sender_id) or [get_main_result()]
        else:
            # Single word - show previous target or main
            results = await get_previous_target_results(sender_id) or [get_main_result()]

    try:
        await query.answer(results, cache_time=1)
    except Exception as e:
        logger.error(f"Error answering inline query: {e}")


async def get_target_user(bot: Bot, target: str, sender_id: int) -> Dict[str, Any]:
    """Get target user information and store it."""
    try:
        target_user = None
        
        # Clean the target string
        target = target.strip()
        
        if target.startswith('@'):
            # Username lookup
            username = target[1:]  # Remove @
            logger.info(f"Looking up username: {username}")
            
            try:
                # For usernames, we need to use get_chat
                chat = await bot.get_chat(f"@{username}")
                if chat.type == "private":
                    target_user = chat
                else:
                    logger.warning(f"Target {username} is not a private chat: {chat.type}")
                    return None
            except Exception as e:
                logger.error(f"Error getting chat for username @{username}: {e}")
                return None
                
        elif target.isdigit():
            # User ID lookup
            try:
                user_id = int(target)
                logger.info(f"Looking up user ID: {user_id}")
                target_user = await bot.get_chat(user_id)
            except Exception as e:
                logger.error(f"Error getting user by ID {target}: {e}")
                return None
        else:
            logger.warning(f"Invalid target format: {target}")
            return None

        if target_user:
            # Extract user information
            user_data = {
                "id": target_user.id,
                "first_name": getattr(target_user, 'first_name', ''),
                "last_name": getattr(target_user, 'last_name', ''),
                "username": getattr(target_user, 'username', ''),
                "title": getattr(target_user, 'title', ''),
                "type": getattr(target_user, 'type', 'private')
            }
            
            # Format name properly
            if user_data["first_name"]:
                name = user_data["first_name"]
                if user_data["last_name"]:
                    name += f" {user_data['last_name']}"
            elif user_data["title"]:
                name = user_data["title"]
            elif user_data["username"]:
                name = f"@{user_data['username']}"
            else:
                name = str(user_data["id"])

            # Create mention
            if user_data["username"]:
                mention = f"@{user_data['username']}"
            else:
                mention = f'<a href="tg://user?id={user_data["id"]}">{name}</a>'

            # Store target user info for sender
            await store_user(sender_id, user_data)

            return {
                "id": user_data["id"],
                "name": name,
                "mention": mention,
                "raw_data": user_data
            }

    except Exception as e:
        logger.error(f"Error in get_target_user for {target}: {e}")
    
    return None


async def handle_callback_query(bot: Bot, update: Update):
    """Handle callback queries for whisper viewing."""
    callback_query = update.callback_query
    user_id = callback_query.from_user.id

    try:
        # Handle navigation callbacks
        if callback_query.data in ["home", "help", "about"]:
            await handle_navigation_callback(bot, callback_query)
            return

        # Parse callback data for whisper access
        data_list = ast.literal_eval(callback_query.data)

        if user_id in data_list:
            # User is authorized to see whisper
            inline_message_id = callback_query.inline_message_id

            if supabase and inline_message_id:
                try:
                    result = supabase.table("whispers").select("message").eq(
                        "inline_message_id", inline_message_id
                    ).execute()

                    if result.data and len(result.data) > 0:
                        message = result.data[0]["message"]
                        await callback_query.answer(f"🔒 Whisper: {message}", show_alert=True)
                    else:
                        await callback_query.answer("❌ Message not found or expired", show_alert=True)
                except Exception as e:
                    logger.error(f"Error fetching whisper: {e}")
                    await callback_query.answer("❌ Error retrieving message", show_alert=True)
            else:
                await callback_query.answer("❌ Database not available", show_alert=True)
        else:
            await callback_query.answer(
                "🚫 Sorry, this whisper is not meant for you!",
                show_alert=True
            )
    except (ValueError, SyntaxError):
        await callback_query.answer("❌ Invalid request", show_alert=True)
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        await callback_query.answer("❌ Error processing request", show_alert=True)


async def handle_navigation_callback(bot: Bot, callback_query):
    """Handle navigation callback queries."""
    user = callback_query.from_user
    
    if callback_query.data == "home":
        text = f"""
🔒 <b>Welcome to WhispierBot</b> 🔒

Hello {user.mention_html()}!

I help you send secret messages (whispers) that only specific people can read, even in public groups!

<b>How to use me:</b>
1. Type <code>@whispierbot</code> in any chat
2. Write your message followed by the recipient's @username
3. Send it - only they can open the whisper!

<b>Example:</b> <code>@whispierbot Hello there! @username</code>

Built with ❤️ using PyVueBot by @venopyx
        """
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔒 Try Whisper", switch_inline_query="")],
            [InlineKeyboardButton("📖 Help", callback_data="help")],
            [InlineKeyboardButton("ℹ️ About", callback_data="about")]
        ])
    elif callback_query.data == "help":
        text = """
📖 <b>How to Use WhispierBot</b>

<b>Step 1:</b> Type <code>@whispierbot</code> in any chat
<b>Step 2:</b> Write your secret message
<b>Step 3:</b> Add the recipient's @username or ID at the end
<b>Step 4:</b> Send it!

<b>Example:</b>
<code>@whispierbot This is a secret message @john</code>

<b>Features:</b>
✅ Works in any chat or group
✅ Only the recipient can read the message
✅ Messages are secure and private
✅ No one else can see the content

<b>Note:</b> The recipient must have started the bot at least once.
        """
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔒 Try Now", switch_inline_query="")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ])
    elif callback_query.data == "about":
        text = """
ℹ️ <b>About WhispierBot</b>

<b>What is this bot?</b>
WhispierBot allows you to send secret messages that only specific people can read, even in public chats!

<b>How it works:</b>
- Your message is securely stored
- Only you and the recipient can access it
- Works in any Telegram chat or group
- Messages expire after 7 days for security

<b>Technology:</b>
🚀 Built with FastAPI and PyVueBot
💾 Powered by Supabase database
⚡ Deployed on Vercel for reliability

<b>Developer:</b> @venopyx
<b>Source:</b> Open source and secure
        """
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔒 Send Whisper", switch_inline_query="")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ])
    
    try:
        await callback_query.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except BadRequest:
        # Message content is the same, just answer the callback
        await callback_query.answer()


async def handle_chosen_inline_result(bot: Bot, update: Update):
    """Handle chosen inline results to store whispers."""
    result = update.chosen_inline_result

    if not result.query.strip():
        return

    try:
        parts = result.query.split()
        if len(parts) >= 2:
            target = parts[-1]
            message = " ".join(parts[:-1])

            # Get target user info
            target_user = await get_target_user(bot, target, result.from_user.id)
            
            if target_user:
                recipient_ids = [result.from_user.id, target_user["id"]]
            else:
                recipient_ids = [result.from_user.id]
        else:
            message = result.query
            recipient_ids = [result.from_user.id]

        # Store whisper in database
        if supabase and result.inline_message_id:
            try:
                supabase.table("whispers").insert({
                    "inline_message_id": result.inline_message_id,
                    "message": message,
                    "sender_id": result.from_user.id,
                    "recipient_ids": recipient_ids
                }).execute()
                logger.info(f"Stored whisper: {result.inline_message_id}")
            except Exception as e:
                logger.error(f"Error storing whisper: {e}")
    except Exception as e:
        logger.error(f"Error processing chosen result: {e}")


async def get_previous_target_results(sender_id: int):
    """Get previous target results for the user."""
    if not supabase:
        return None

    try:
        result = supabase.table("users").select("target_user").eq("id", sender_id).execute()
        
        if result.data and len(result.data) > 0:
            target_user_data = result.data[0].get("target_user")
            if target_user_data and isinstance(target_user_data, dict):
                receiver_id = target_user_data.get("id")
                if not receiver_id:
                    return None
                    
                data_list = [sender_id, receiver_id]
                
                # Build name from available data
                first_name = target_user_data.get("first_name", "")
                last_name = target_user_data.get("last_name", "")
                title = target_user_data.get("title", "")
                username = target_user_data.get("username", "")
                
                if first_name:
                    name = first_name
                    if last_name:
                        name += f" {last_name}"
                elif title:
                    name = title
                elif username:
                    name = f"@{username}"
                else:
                    name = str(receiver_id)
                
                # Create mention
                if username:
                    mention = f"@{username}"
                else:
                    mention = f'<a href="tg://user?id={receiver_id}">{name}</a>'
                
                text1 = f"🔒 A whisper message to {name}"
                text2 = "Only they can open it."
                
                return [
                    InlineQueryResultArticle(
                        id="previous_target",
                        title=text1,
                        input_message_content=InputTextMessageContent(
                            f"🔒 A whisper message to {mention} 🔒\n{text2}",
                            parse_mode="HTML"
                        ),
                        description=text2,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                "🔐 Show Message 🔐",
                                callback_data=str(data_list)
                            )
                        ]])
                    ),
                    get_main_result()
                ]
    except Exception as e:
        logger.error(f"Error getting previous target: {e}")
    
    return None


def get_main_result():
    """Get the main inline query result."""
    return InlineQueryResultArticle(
        id="main",
        title="🔒 WhispierBot",
        description="Send secret messages that only specific users can read",
        input_message_content=InputTextMessageContent(
            "🔒 Write your message followed by the recipient's @username or ID\n\n"
            "<b>Example:</b> <code>Hello there! @username</code>\n\n"
            "Start typing to create your whisper message!",
            parse_mode="HTML"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 Learn More", url="https://t.me/whispierbot?start=help")],
            [InlineKeyboardButton("🔒 Try Whisper", switch_inline_query="")]
        ])
    )


async def store_user(user_id: int, target_user_data: Dict[str, Any] = None):
    """Store or update user in database."""
    if not supabase:
        return

    try:
        # Check if user exists
        result = supabase.table("users").select("id").eq("id", user_id).execute()
        
        if result.data and len(result.data) > 0:
            # User exists, update if target_user_data provided
            if target_user_data:
                supabase.table("users").update({
                    "target_user": target_user_data
                }).eq("id", user_id).execute()
                logger.info(f"Updated target user for {user_id}: {target_user_data.get('username', target_user_data.get('id'))}")
        else:
            # New user - insert with upsert to handle conflicts
            supabase.table("users").upsert({
                "id": user_id,
                "target_user": target_user_data
            }).execute()
            logger.info(f"Stored new user: {user_id}")
    except Exception as e:
        logger.error(f"Error storing user {user_id}: {e}")


async def send_start_message(bot: Bot, message):
    """Send start message."""
    user = message.from_user
    text = f"""
🔒 <b>Welcome to WhispierBot</b> 🔒

Hello {user.mention_html()}!

I help you send secret messages (whispers) that only specific people can read, even in public groups!

<b>How to use me:</b>
1. Type <code>@whispierbot</code> in any chat
2. Write your message followed by the recipient's @username
3. Send it - only they can open the whisper!

<b>Example:</b> <code>@whispierbot Hello there! @username</code>

Built with ❤️ using PyVueBot by @venopyx
    """

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Try Whisper", switch_inline_query="")],
        [InlineKeyboardButton("📖 Help", callback_data="help")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ])

    try:
        await bot.send_message(
            chat_id=message.chat.id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error sending start message: {e}")


async def send_help_message(bot: Bot, message):
    """Send help message."""
    text = """
📖 <b>How to Use WhispierBot</b>

<b>Step 1:</b> Type <code>@whispierbot</code> in any chat
<b>Step 2:</b> Write your secret message
<b>Step 3:</b> Add the recipient's @username or ID at the end
<b>Step 4:</b> Send it!

<b>Example:</b>
<code>@whispierbot This is a secret message @john</code>

<b>Features:</b>
✅ Works in any chat or group
✅ Only the recipient can read the message
✅ Messages are secure and private
✅ No one else can see the content

<b>Note:</b> The recipient must have started the bot at least once.
    """

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Try Now", switch_inline_query="")],
        [InlineKeyboardButton("🏠 Back to Start", callback_data="home")]
    ])

    try:
        await bot.send_message(
            chat_id=message.chat.id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error sending help message: {e}")


async def send_stats_message(bot: Bot, message):
    """Send stats message (admin only)."""
    if not supabase:
        await bot.send_message(message.chat.id, "❌ Database not available")
        return

    try:
        users_result = supabase.table("users").select("id", count="exact").execute()
        whispers_result = supabase.table("whispers").select("inline_message_id", count="exact").execute()

        users_count = users_result.count or 0
        whispers_count = whispers_result.count or 0

        text = f"""
📊 <b>WhispierBot Statistics</b>

👥 <b>Total Users:</b> {users_count:,}
💬 <b>Total Whispers:</b> {whispers_count:,}
🚀 <b>Status:</b> Active
⚡ <b>Platform:</b> Vercel + Supabase
🛠️ <b>Developer:</b> @venopyx

<b>System Status:</b> ✅ All systems operational
        """

        await bot.send_message(
            chat_id=message.chat.id,
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await bot.send_message(message.chat.id, f"❌ Error getting stats: {e}")


@router.get("/telegram/setup-webhook")
async def setup_webhook(webhook_url: str = None):
    """Setup webhook for the bot."""
    if not TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bot token not configured"
        )

    if not webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="webhook_url parameter is required"
        )

    try:
        bot = Bot(token=TOKEN)
        # First, delete any existing webhook
        await bot.delete_webhook(drop_pending_updates=True)

        # Set new webhook
        success = await bot.set_webhook(url=webhook_url)
        if success:
            webhook_info = await bot.get_webhook_info()
            logger.info(f"Webhook set to: {webhook_info.url}")
            return {
                "status": "success",
                "message": f"Webhook set to {webhook_url}",
                "webhook_info": {
                    "url": webhook_info.url,
                    "has_custom_certificate": webhook_info.has_custom_certificate,
                    "pending_update_count": webhook_info.pending_update_count,
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set webhook"
            )
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
