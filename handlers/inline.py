"""Inline query handlers for Whispier Bot."""

import uuid
import re
from pyrogram import Client
from pyrogram.types import (
    InlineQuery, 
    InlineQueryResultArticle, 
    InputTextMessageContent,
    ChosenInlineResult
)

from utils.strings import Strings
from utils.keyboards import Keyboards


def register_inline_handlers(app: Client):
    """Register inline query handlers."""
    
    @app.on_inline_query()
    async def inline_query_handler(client: Client, query: InlineQuery):
        """Handle inline queries."""
        text = query.query.strip()
        
        if not text:
            await query.answer([
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="🎯 Ready to Drop a Secret? 🐒",
                    description="Type your message + target @username",
                    input_message_content=InputTextMessageContent(Strings.INLINE_EMPTY),
                    reply_markup=Keyboards.inline_help()
                )
            ], cache_time=1)
            return
        
        # Parse message and target
        parts = text.split()
        if len(parts) < 2 or not any(part.startswith('@') for part in parts):
            await query.answer([
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="🎯 Almost There, Monkey! 🐒",
                    description=f"Add target: {text} @username",
                    input_message_content=InputTextMessageContent(
                        Strings.INLINE_NO_TARGET.format(message=text)
                    ),
                    reply_markup=Keyboards.inline_help()
                )
            ], cache_time=1)
            return
        
        # Find target username
        target_username = None
        for part in reversed(parts):
            if part.startswith('@'):
                target_username = part[1:]  # Remove @
                break
        
        if not target_username:
            return
        
        # Extract message content (everything except target)
        message_words = []
        for part in parts:
            if part == f"@{target_username}":
                break
            message_words.append(part)
        
        message_content = " ".join(message_words)
        
        if not message_content:
            return
        
        # Try to resolve username to user
        target_id = await client.db.resolve_username(target_username)
        display_name = f"@{target_username}"
        
        if target_id:
            try:
                target_user = await client.get_users(target_id)
                display_name = target_user.first_name
                if target_user.last_name:
                    display_name += f" {target_user.last_name}"
            except:
                pass
        
        # Create inline result
        whisper_id = str(uuid.uuid4())
        await query.answer([
            InlineQueryResultArticle(
                id=whisper_id,
                title=f"🤫 Secret for {display_name} 🐒",
                description="🍌 Only you and they can peek",
                input_message_content=InputTextMessageContent(
                    Strings.WHISPER_CREATED.format(target=display_name)
                ),
                reply_markup=Keyboards.whisper_buttons(whisper_id)
            )
        ], cache_time=1)
    
    @app.on_chosen_inline_result()
    async def chosen_result_handler(client: Client, result: ChosenInlineResult):
        """Handle chosen inline results."""
        query = result.query.strip()
        parts = query.split()
        
        # Find target username
        target_username = None
        for part in reversed(parts):
            if part.startswith('@'):
                target_username = part[1:]
                break
        
        if not target_username:
            return
        
        # Extract message content
        message_words = []
        for part in parts:
            if part == f"@{target_username}":
                break
            message_words.append(part)
        
        message_content = " ".join(message_words)
        
        # Try to resolve target user
        target_id = await client.db.resolve_username(target_username)
        
        # Store whisper in database
        await client.db.store_whisper({
            "inline_message_id": result.inline_message_id,
            "content": message_content,
            "sender_id": result.from_user.id,
            "target_username": target_username,
            "target_id": target_id
        })