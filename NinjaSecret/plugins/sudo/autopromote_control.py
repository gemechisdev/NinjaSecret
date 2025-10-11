from pyrogram import filters
from pyrogram.types import Message

from NinjaSecret import app
from NinjaSecret.misc import SUDOERS
from NinjaSecret.utils.decorators.language import language
import config


@app.on_message(filters.command(["toggleautopromote", "tap"]) & filters.group)
@language
async def toggle_auto_promote(client, message: Message, _):
    """Toggle auto-promotion feature on/off"""
    if message.from_user.id not in SUDOERS:
        return await message.reply_text("❌ Only sudo users can use this command.")

    # Toggle the setting
    config.AUTO_PROMOTE_SUDO_USERS = not config.AUTO_PROMOTE_SUDO_USERS

    status = "enabled" if config.AUTO_PROMOTE_SUDO_USERS else "disabled"
    emoji = "✅" if config.AUTO_PROMOTE_SUDO_USERS else "❌"

    # Send notification to command user privately
    try:
        await app.send_message(
            message.from_user.id,
            f"{emoji} **Auto-Promotion {status.title()}**\n\n"
            f"🛡️ **Status:** {status}\n"
            f"⚡ **Effect:** Sudo users will {'be automatically promoted with ALL bot permissions' if config.AUTO_PROMOTE_SUDO_USERS else 'not be automatically promoted'} when joining groups"
        )
    except:
        pass  # User might have blocked the bot


@app.on_message(filters.command(["autopromotestatus", "aps"]) & filters.group)
@language
async def auto_promote_status(client, message: Message, _):
    """Check auto-promotion status"""
    if message.from_user.id not in SUDOERS:
        return await message.reply_text("❌ Only sudo users can use this command.")

    status = "enabled" if config.AUTO_PROMOTE_SUDO_USERS else "disabled"
    emoji = "✅" if config.AUTO_PROMOTE_SUDO_USERS else "❌"

    # Send notification to command user privately
    try:
        await app.send_message(
            message.from_user.id,
            f"{emoji} **Auto-Promotion Status**\n\n"
            f"🛡️ **Current Status:** {status}\n"
            f"⚡ **Behavior:** Sudo users {'will be' if config.AUTO_PROMOTE_SUDO_USERS else 'will not be'} automatically promoted with ALL bot permissions when joining groups\n"
            f"🔧 **Configuration:** Set AUTO_PROMOTE_SUDO_USERS environment variable to True/False"
        )
    except:
        pass  # User might have blocked the bot


__MODULE__ = "Auto Promote Control"
__HELP__ = """
**Auto-Promotion Control Commands:**

• `/toggleautopromote` or `/tap` - Toggle auto-promotion on/off
• `/autopromotestatus` or `/aps` - Check current auto-promotion status

**Configuration:**
• Set `AUTO_PROMOTE_SUDO_USERS=True` in environment variables to enable by default
• Set `AUTO_PROMOTE_SUDO_USERS=False` in environment variables to disable by default
• Notifications sent privately to command users
"""
