"""Inline query handlers for Whispier Bot."""
import asyncio
import uuid
from pyrogram import Client
from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ChosenInlineResult
)
from utils.strings import Strings
from utils.keyboards import Keyboards
from core.resolver import TargetResolver


def extract_message_and_target(text: str):
    parts = text.split()
    if len(parts) < 2:
        return None, None
    # target is last token if it's @username or numeric id
    last = parts[-1]
    if last.startswith("@") or (last.isdigit() and 5 <= len(last) <= 15):
        message_content = " ".join(parts[:-1]).strip()
        if not message_content:
            return None, None
        return message_content, last
    # otherwise scan for any @username earlier (fallback old style)
    for i in range(len(parts)-1, -1, -1):
        token = parts[i]
        if token.startswith("@"):
            message_content = " ".join(parts[:i]).strip()
            if not message_content:
                return None, None
            return message_content, token
    return None, None


def register_inline_handlers(app: Client):
    resolver = TargetResolver(app, getattr(app, "user_client", None), app.db)

    @app.on_inline_query()
    async def inline_query_handler(client: Client, query: InlineQuery):
        try:
            q = query.query.strip()

            if not q:
                await query.answer([
                    InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title="🎯 Drop a Secret",
                        description="Type your message + target (@username or user id)",
                        input_message_content=InputTextMessageContent(Strings.INLINE_EMPTY),
                        reply_markup=Keyboards.inline_help()
                    )
                ], cache_time=30)
                return
        except Exception as e:
            print(f"Error in empty query handling: {e}")
            return

        try:
            message_content, target_token = extract_message_and_target(q)

            if not target_token or not message_content:
                await query.answer([
                    InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title="🎯 Specify Target",
                        description="Add @username or numeric user id at end",
                        input_message_content=InputTextMessageContent(
                            Strings.INLINE_NO_TARGET.format(message=q)
                        ),
                        reply_markup=Keyboards.inline_help()
                    )
                ], cache_time=30)
                return

            # Add timeout for resolver to prevent hanging
            try:
                target_id, normalized_username, display = await asyncio.wait_for(
                    resolver.resolve(target_token), timeout=5.0
                )
            except asyncio.TimeoutError:
                print(f"Resolver timeout for token: {target_token}")
                # Use fallback display
                target_id, normalized_username, display = None, None, target_token

            whisper_id = str(uuid.uuid4())

            title_display = display if display else target_token
            await query.answer([
                InlineQueryResultArticle(
                    id=whisper_id,
                    title=f"🤫 Secret for {title_display}",
                    description="🍌 Only you and target can peek",
                    input_message_content=InputTextMessageContent(
                        Strings.WHISPER_CREATED.format(
                            target=title_display
                        )
                    ),
                    reply_markup=Keyboards.whisper_buttons(whisper_id)
                )
            ], cache_time=1)

            # Pre-store the whisper so callback works even before chosen inline result returns inline_message_id
            await client.db.store_whisper({
                "whisper_id": whisper_id,
                "content": message_content,
                "sender_id": query.from_user.id,
                "target_username": normalized_username,
                "target_id": target_id,
                "original_target_token": target_token
            })
            
        except Exception as e:
            print(f"Error in inline query processing: {e}")
            # Send a fallback response
            try:
                await query.answer([
                    InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title="⚠️ Error Processing Query",
                        description="Please try again in a moment",
                        input_message_content=InputTextMessageContent(
                            "⚠️ There was an error processing your whisper. Please try again."
                        )
                    )
                ], cache_time=30)
            except:
                pass  # If we can't even send error response, just fail silently

    @app.on_chosen_inline_result()
    async def chosen_result_handler(client: Client, result: ChosenInlineResult):
        try:
            whisper_id = result.result_id
            if result.inline_message_id:
                await client.db.attach_inline_message_id(whisper_id, result.inline_message_id)

            # Attempt late resolution if still missing target_id but token numeric or username available
            whisper = await client.db.get_whisper(whisper_id)
            if whisper and not whisper.get("target_id"):
                token = whisper.get("original_target_token")
                if token:
                    try:
                        target_id, norm_username, _ = await asyncio.wait_for(
                            resolver.resolve(token if token.startswith("@") else token),
                            timeout=5.0
                        )
                        if target_id or norm_username:
                            update = {}
                            if target_id:
                                update["target_id"] = target_id
                            if norm_username:
                                update["target_username"] = norm_username
                            if update:
                                await client.db.whispers.update_one(
                                    {"whisper_id": whisper_id},
                                    {"$set": update}
                                )
                    except (asyncio.TimeoutError, Exception) as e:
                        print(f"Error in late resolution for {token}: {e}")
        except Exception as e:
            print(f"Error in chosen result handler: {e}")
