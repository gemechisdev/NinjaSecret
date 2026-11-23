import re
import time
from datetime import datetime, timedelta
from typing import Union

from pyrogram import filters
from pyrogram.errors import FloodWait, UserAdminInvalid, ChatAdminRequired
from pyrogram.types import Message, ChatPermissions

from NinjaSecret import app
from NinjaSecret.logging import LOGGER
from NinjaSecret.utils.admin_check import admin_check
from NinjaSecret.utils.decorators.language import language
from NinjaSecret.utils.extraction import extract_user
from NinjaSecret.utils.database import (
    add_banned_user,
    remove_banned_user,
    is_banned_user,
    forwarddb,
    linksdb,
    slowmodedb,
)
from config import BANNED_USERS, OWNER_ID

logger = LOGGER(__name__)

# In-memory storage for performance
forward_settings = {}
links_settings = {}
slowmode_settings = {}

# URL regex pattern for detecting links (case-insensitive and more comprehensive)
URL_PATTERN = re.compile(
    r'https?://[^\s<>"{}|\\^`\[\]]+',
    re.IGNORECASE
)

def contains_links(text: str) -> bool:
    """Check if text contains any form of links (case-insensitive)"""
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Check for explicit URL patterns
    if URL_PATTERN.search(text):
        return True
    
    # Check for common link indicators (but be more careful about standalone TLDs)
    link_indicators = [
        'http://', 'https://', 'ftp://', 'sftp://', 'www.',
    ]
    
    for indicator in link_indicators:
        if indicator in text_lower:
            return True
    
    # Check for TLDs but only if they're part of a proper domain
    tld_indicators = [
        '.com', '.org', '.net', '.edu', '.gov', '.mil',
        '.io', '.co', '.me', '.tv', '.app', '.dev', '.tech',
        '.online', '.site', '.web', '.blog', '.shop', '.store',
        '.info', '.biz', '.mobi', '.pro', '.name', '.aero'
    ]
    
    # Only check TLDs if they appear to be part of a domain, not standalone
    for tld in tld_indicators:
        if tld in text_lower:
            # Check if this TLD is part of a proper domain pattern
            # Look for patterns like "something.tld" or "something-something.tld"
            tld_pattern = r'\b[a-zA-Z0-9][a-zA-Z0-9\-]*' + re.escape(tld) + r'\b'
            if re.search(tld_pattern, text_lower):
                return True
    
    # Check for potential embedded links with spaces or special characters
    # This catches cases like "check out example . com" or "visit example-dot-com"
    potential_links = re.findall(r'\b[a-zA-Z0-9][a-zA-Z0-9\-]*\s*\.\s*[a-zA-Z]{2,}\b', text_lower)
    if potential_links:
        return True
    
    # Check for URLs with different protocols or variations
    # This catches cases like "Https://example.com", "HTTP://example.com", etc.
    protocol_patterns = [
        r'\bhttps?://[^\s<>"{}|\\^`\[\]]+',
        r'\bftp://[^\s<>"{}|\\^`\[\]]+',
        r'\bsftp://[^\s<>"{}|\\^`\[\]]+',
        r'\bwww\.[^\s<>"{}|\\^`\[\]]+'
    ]
    
    for pattern in protocol_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    # Check for domain-like patterns that might be links
    # This catches cases like "example.com", "sub.example.org", etc.
    # But excludes invalid patterns like "example..com" or ".com"
    domain_pattern = r'\b[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.([a-zA-Z]{2,})\b'
    if re.search(domain_pattern, text):
        # Additional validation: make sure there are no consecutive dots
        if '..' not in text:
            return True
    
    # Additional checks for common link patterns
    # Check for IP addresses (IPv4)
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    if re.search(ip_pattern, text):
        return True
    
    # Check for shortened URLs (common in social media)
    short_url_patterns = [
        r'\b(?:bit\.ly|t\.co|goo\.gl|tinyurl\.com|is\.gd|cli\.gs|ow\.ly|su\.pr|twurl\.nl|snipurl\.com|short\.to|BudURL\.com|ping\.fm|tr\.im|loopt\.us|Is\.gd|po\.st|bc\.vc|twitthis\.com|u\.to|j\.mp|buzurl\.com|cutt\.us|u\.bb|yourls\.org|x\.co|prettylinkpro\.com|viralurl\.com|vurl\.com|tr\.im|link\.zip\.net)\b'
    ]
    
    for pattern in short_url_patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False

async def check_bot_permissions(chat_id: int, permission: str) -> bool:
    """Check if bot has specific permission in the chat"""
    try:
        bot_member = await app.get_chat_member(chat_id, app.id)
        if permission == "delete":
            return bot_member.privileges.can_delete_messages
        elif permission == "restrict":
            return bot_member.privileges.can_restrict_members
        return False
    except Exception:
        return False

async def is_user_admin(chat_id: int, user_id: int) -> bool:
    """Check if a user is an admin/owner in the chat"""
    try:
        member = await app.get_chat_member(chat_id, user_id)
        status = getattr(member, "status", None)
        if isinstance(status, str):
            if status in ["administrator", "creator", "owner"]:
                return True
        if getattr(member, "privileges", None) is not None:
            return True
        return False
    except Exception:
        return False

# Forward Control Functions
async def get_forward_setting(chat_id: int) -> dict:
    """Get forward control setting for a chat"""
    if chat_id in forward_settings:
        return forward_settings[chat_id]

    setting = await forwarddb.find_one({"chat_id": chat_id})
    if setting:
        forward_settings[chat_id] = setting
        return setting
    return {"chat_id": chat_id, "non_admin_forward": True, "global_forward": True}

async def set_forward_setting(chat_id: int, non_admin_forward: bool, global_forward: bool):
    """Set forward control setting for a chat"""
    await forwarddb.update_one(
        {"chat_id": chat_id},
        {"$set": {"non_admin_forward": non_admin_forward, "global_forward": global_forward}},
        upsert=True
    )
    forward_settings[chat_id] = {"chat_id": chat_id, "non_admin_forward": non_admin_forward, "global_forward": global_forward}

# Links Control Functions
async def get_links_setting(chat_id: int) -> dict:
    """Get links control setting for a chat"""
    if chat_id in links_settings:
        return links_settings[chat_id]

    setting = await linksdb.find_one({"chat_id": chat_id})
    if setting:
        links_settings[chat_id] = setting
        return setting
    return {"chat_id": chat_id, "non_admin_links": True, "global_links": True}

async def set_links_setting(chat_id: int, non_admin_links: bool, global_links: bool):
    """Set links control setting for a chat"""
    await linksdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"non_admin_links": non_admin_links, "global_links": global_links}},
        upsert=True
    )
    links_settings[chat_id] = {"chat_id": chat_id, "non_admin_links": non_admin_links, "global_links": global_links}

# Slowmode Functions
async def get_slowmode_setting(chat_id: int) -> dict:
    """Get slowmode setting for a chat"""
    if chat_id in slowmode_settings:
        return slowmode_settings[chat_id]

    setting = await slowmodedb.find_one({"chat_id": chat_id})
    if setting:
        slowmode_settings[chat_id] = setting
        return setting
    return {"chat_id": chat_id, "enabled": False, "seconds": 0}

async def set_slowmode_setting(chat_id: int, enabled: bool, seconds: int = 0):
    """Set slowmode setting for a chat"""
    await slowmodedb.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": enabled, "seconds": seconds}},
        upsert=True
    )
    slowmode_settings[chat_id] = {"chat_id": chat_id, "enabled": enabled, "seconds": seconds}

# User last message tracking for slowmode
user_last_message = {}

# Forward Control Commands
@app.on_message(filters.command(["forward"]) & filters.group)
@language
async def forward_control(client, message: Message, _):
    """Handle forward control commands"""
    if not await admin_check(message):
        return await message.reply_text(_["action_1"])

    if len(message.command) < 2:
        return await message.reply_text(_["chat_control_10"])

    action = message.command[1].lower()
    chat_id = message.chat.id

    if action in ["enable", "disable"]:
        # For non-admins only
        non_admin_forward = action == "enable"
        setting = await get_forward_setting(chat_id)
        await set_forward_setting(chat_id, non_admin_forward, setting.get("global_forward", True))

        status = "enabled" if non_admin_forward else "disabled"
        await message.reply_text(_["chat_control_1"].format(status))

    elif action in ["allow", "block"]:
        # For everyone (including admins)
        global_forward = action == "allow"
        setting = await get_forward_setting(chat_id)
        await set_forward_setting(chat_id, setting.get("non_admin_forward", True), global_forward)

        status = "allowed" if global_forward else "blocked"
        await message.reply_text(_["chat_control_2"].format(status))

    else:
        await message.reply_text(_["chat_control_7"])

# Links Control Commands
@app.on_message(filters.command(["links"]) & filters.group)
@language
async def links_control(client, message: Message, _):
    """Handle links control commands"""
    if not await admin_check(message):
        return await message.reply_text(_["action_1"])

    if len(message.command) < 2:
        return await message.reply_text(_["chat_control_11"])

    action = message.command[1].lower()
    chat_id = message.chat.id

    if action in ["enable", "disable"]:
        # For non-admins only
        non_admin_links = action == "enable"
        setting = await get_links_setting(chat_id)
        await set_links_setting(chat_id, non_admin_links, setting.get("global_links", True))

        status = "enabled" if non_admin_links else "disabled"
        await message.reply_text(_["chat_control_3"].format(status))

    elif action in ["allow", "block"]:
        # For everyone (including admins)
        global_links = action == "allow"
        setting = await get_links_setting(chat_id)
        await set_links_setting(chat_id, setting.get("non_admin_links", True), global_links)

        status = "allowed" if global_links else "blocked"
        await message.reply_text(_["chat_control_4"].format(status))

    else:
        await message.reply_text(_["chat_control_8"])

# Slowmode Command
@app.on_message(filters.command(["slowmode"]) & filters.group)
@language
async def slowmode_control(client, message: Message, _):
    """Handle slowmode control commands"""
    if not await admin_check(message):
        return await message.reply_text(_["action_1"])

    if len(message.command) < 2:
        return await message.reply_text(_["chat_control_12"])

    action = message.command[1].lower()
    chat_id = message.chat.id

    if action == "enable":
        if len(message.command) < 3:
            return await message.reply_text(_["chat_control_13"])

        try:
            seconds = int(message.command[2])
            if seconds < 0 or seconds > 86400:  # Max 24 hours
                return await message.reply_text(_["chat_control_14"])
        except ValueError:
            return await message.reply_text(_["chat_control_15"])

        await set_slowmode_setting(chat_id, True, seconds)
        await message.reply_text(_["chat_control_5"].format(seconds))

    elif action == "disable":
        await set_slowmode_setting(chat_id, False, 0)
        await message.reply_text(_["chat_control_6"])

    else:
        await message.reply_text(_["chat_control_9"])

# Message Handlers
@app.on_message(filters.forwarded & filters.group, group=2)
async def handle_forwarded_messages(client, message: Message):
    """Handle forwarded messages based on forward control settings"""
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Get forward settings
        setting = await get_forward_setting(chat_id)

        # Check if user is admin
        is_admin = await is_user_admin(chat_id, user_id)

        # Apply forward restrictions
        if not setting.get("global_forward", True):
            # Global forwarding is blocked for everyone
            await message.delete()
            return

        if not is_admin and not setting.get("non_admin_forward", True):
            # Non-admin forwarding is blocked
            await message.delete()
            return

    except Exception:
        pass

@app.on_message(filters.text & filters.group, group=3)
async def handle_text_messages(client, message: Message):
    """Handle text messages for links control and slowmode"""
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Check if user is admin
        is_admin = await is_user_admin(chat_id, user_id)

        # Links Control
        links_setting = await get_links_setting(chat_id)
        if message.text and contains_links(message.text):
            # Log link detection for debugging
            logger.debug(f"🔗 Link detected in message from user {user_id} in chat {chat_id}: {message.text[:100]}...")
            
            if not links_setting.get("global_links", True):
                # Global links are blocked
                logger.debug(f"❌ Global links blocked, deleting message from user {user_id}")
                await message.delete()
                return

            if not is_admin and not links_setting.get("non_admin_links", True):
                # Non-admin links are blocked
                logger.debug(f"❌ Non-admin links blocked, deleting message from user {user_id}")
                await message.delete()
                return

        # Slowmode Control
        slowmode_setting = await get_slowmode_setting(chat_id)
        if slowmode_setting.get("enabled", False) and not is_admin:
            seconds = slowmode_setting.get("seconds", 0)
            if seconds > 0:
                current_time = time.time()
                user_key = f"{chat_id}_{user_id}"

                if user_key in user_last_message:
                    last_time = user_last_message[user_key]
                    if current_time - last_time < seconds:
                        # User is sending too fast
                        await message.delete()
                        return

                user_last_message[user_key] = current_time

    except Exception:
        pass

@app.on_message(filters.group & ~filters.text, group=4)
async def handle_other_messages(client, message: Message):
    """Handle non-text messages (captions, etc.) for links control"""
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Check if user is admin
        is_admin = await is_user_admin(chat_id, user_id)

        # Links Control for captions
        links_setting = await get_links_setting(chat_id)
        if message.caption and contains_links(message.caption):
            # Log link detection in caption for debugging
            logger.debug(f"🔗 Link detected in caption from user {user_id} in chat {chat_id}: {message.caption[:100]}...")
            
            if not links_setting.get("global_links", True):
                # Global links are blocked
                logger.debug(f"❌ Global links blocked in caption, deleting message from user {user_id}")
                await message.delete()
                return

            if not is_admin and not links_setting.get("non_admin_links", True):
                # Non-admin links are blocked
                logger.debug(f"❌ Non-admin links blocked in caption, deleting message from user {user_id}")
                await message.delete()
                return

    except Exception:
        pass

# Clean up old slowmode data periodically
@app.on_message(filters.command("cleanup_slowmode") & filters.user(OWNER_ID))
async def cleanup_slowmode_data(client, message: Message):
    """Clean up old slowmode data (owner only)"""
    try:
        current_time = time.time()
        cutoff_time = current_time - 86400  # 24 hours ago

        # Remove old entries
        keys_to_remove = []
        for key, timestamp in user_last_message.items():
            if timestamp < cutoff_time:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del user_last_message[key]

        await message.reply_text(_["chat_control_19"].format(len(keys_to_remove)))

    except Exception as e:
        await message.reply_text(_["chat_control_20"].format(str(e)))

# Status Commands
@app.on_message(filters.command(["forwardstatus"]) & filters.group)
@language
async def forward_status(client, message: Message, _):
    """Show forward control status"""
    if not await admin_check(message):
        return await message.reply_text(_["action_1"])

    chat_id = message.chat.id
    setting = await get_forward_setting(chat_id)

    status_text = _["chat_control_16"].format(
        message.chat.title,
        '✅ Enabled' if setting.get('non_admin_forward', True) else '❌ Disabled',
        '✅ Allowed' if setting.get('global_forward', True) else '❌ Blocked'
    )

    await message.reply_text(status_text)

@app.on_message(filters.command(["linksstatus"]) & filters.group)
@language
async def links_status(client, message: Message, _):
    """Show links control status"""
    if not await admin_check(message):
        return await message.reply_text(_["action_1"])

    chat_id = message.chat.id
    setting = await get_links_setting(chat_id)

    status_text = _["chat_control_17"].format(
        message.chat.title,
        '✅ Allowed' if setting.get('non_admin_links', True) else '❌ Blocked',
        '✅ Allowed' if setting.get('global_links', True) else '❌ Blocked'
    )

    await message.reply_text(status_text)

@app.on_message(filters.command(["slowmodestatus"]) & filters.group)
@language
async def slowmode_status(client, message: Message, _):
    """Show slowmode status"""
    if not await admin_check(message):
        return await message.reply_text(_["action_1"])

    chat_id = message.chat.id
    setting = await get_slowmode_setting(chat_id)

    if setting.get("enabled", False):
        seconds = setting.get("seconds", 0)
        status_text = _["chat_control_18"].format(
            message.chat.title,
            '✅ Enabled',
            seconds
        )
    else:
        status_text = _["chat_control_18"].format(
            message.chat.title,
            '❌ Disabled',
            0
        )

    await message.reply_text(status_text)
