from pyrogram.enums import MessageEntityType
from pyrogram.types import Message, User

from ScorpiTune import app


async def extract_user(m: Message) -> User:
    if m.reply_to_message:
        return m.reply_to_message.from_user
    # Try to resolve from a text mention entity first if present
    if m.entities:
        # If command, the mention entity is often at index 1; otherwise at 0
        idx = 1 if (m.text and m.text.startswith("/")) else 0
        if len(m.entities) > idx and m.entities[idx].type == MessageEntityType.TEXT_MENTION:
            return await app.get_users(m.entities[idx].user.id)
    # Fallback to parse the second token argument
    if not m.command or len(m.command) < 2:
        raise ValueError("No user specified")
    argument = m.command[1]
    try:
        # numeric id
        if argument.isdecimal():
            return await app.get_users(int(argument))
        # username or phone or other identifier
        return await app.get_users(argument)
    except Exception:
        # As a last resort, attempt to treat raw text as username without @
        clean = argument.lstrip("@")
        return await app.get_users(clean)
