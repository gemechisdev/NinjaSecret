from pyrogram import filters
from pyrogram.types import Message, ChatPrivileges

from NinjaSecret import app
from NinjaSecret.misc import SUDOERS
from NinjaSecret.utils.decorators.language import language
from NinjaSecret.logging import LOGGER
from NinjaSecret.utils.database import is_on_off
import config


@app.on_message(filters.command(["autopromote", "apromote"]) & filters.group)
@language
async def auto_promote_sudo_users(client, message: Message, _):
    """Manually promote all sudo users in the current group"""
    if message.from_user.id not in SUDOERS:
        return await message.reply_text("❌ Only sudo users can use this command.")

    if not config.AUTO_PROMOTE_SUDO_USERS:
        return await message.reply_text("❌ Auto-promotion is disabled in configuration.")

    try:
        # Check if bot has promote permissions
        bot_member = await app.get_chat_member(message.chat.id, app.id)
        bot_priv = getattr(bot_member, "privileges", None)

        if not bot_priv or not getattr(bot_priv, "can_promote_members", False):
            return await message.reply_text("❌ Bot doesn't have permission to promote members.")

        promoted_count = 0
        failed_count = 0

        # Get all chat members
        async for member in app.get_chat_members(message.chat.id):
            if member.user.id in SUDOERS:
                try:
                    # Check if user is already admin
                    if member.status not in ["administrator", "creator", "owner"]:
                        # Promote with all permissions that the bot has
                        priv = ChatPrivileges(
                            can_manage_chat=bool(getattr(bot_priv, "can_manage_chat", False)),
                            can_delete_messages=bool(getattr(bot_priv, "can_delete_messages", False)),
                            can_manage_video_chats=bool(getattr(bot_priv, "can_manage_video_chats", False)),
                            can_restrict_members=bool(getattr(bot_priv, "can_restrict_members", False)),
                            can_promote_members=bool(getattr(bot_priv, "can_promote_members", False)),
                            can_change_info=bool(getattr(bot_priv, "can_change_info", False)),
                            can_invite_users=bool(getattr(bot_priv, "can_invite_users", False)),
                            can_pin_messages=bool(getattr(bot_priv, "can_pin_messages", False)),
                            can_post_stories=bool(getattr(bot_priv, "can_post_stories", False)),
                            can_edit_stories=bool(getattr(bot_priv, "can_edit_stories", False)),
                            can_delete_stories=bool(getattr(bot_priv, "can_delete_stories", False)),
                            is_anonymous=False,
                        )
                        await message.chat.promote_member(member.user.id, privileges=priv)

                        # Set custom title after promotion
                        try:
                            await app.set_administrator_title(message.chat.id, member.user.id, "ᴍʏ❦")
                        except Exception as title_error:
                            LOGGER(__name__).error(
                                f"Title setting error for user {member.user.id}: {title_error}"
                            )
                            pass  # Title setting might fail, but promotion should still work
                        promoted_count += 1
                except Exception as e:
                    LOGGER(__name__).error(
                        f"Manual promotion error for user {member.user.id}: {e}"
                    )
                    failed_count += 1

        if promoted_count > 0:
            # Build permission list for notification
            permissions = []
            if getattr(bot_priv, "can_promote_members", False):
                permissions.append("Promote")
            if getattr(bot_priv, "can_restrict_members", False):
                permissions.append("Restrict/Ban")
            if getattr(bot_priv, "can_delete_messages", False):
                permissions.append("Delete")
            if getattr(bot_priv, "can_pin_messages", False):
                permissions.append("Pin")
            if getattr(bot_priv, "can_manage_chat", False):
                permissions.append("Manage Chat")
            if getattr(bot_priv, "can_change_info", False):
                permissions.append("Change Info")
            if getattr(bot_priv, "can_invite_users", False):
                permissions.append("Invite")
            if getattr(bot_priv, "can_manage_video_chats", False):
                permissions.append("Manage VC")
            if getattr(bot_priv, "can_post_stories", False):
                permissions.append("Post Stories")
            if getattr(bot_priv, "can_edit_stories", False):
                permissions.append("Edit Stories")
            if getattr(bot_priv, "can_delete_stories", False):
                permissions.append("Delete Stories")

            perm_text = ", ".join(permissions) if permissions else "Basic Admin"

            # Send notification to command user privately
            try:
                await app.send_message(
                    message.from_user.id,
                    f"✅ **Auto-Promotion Complete**\n\n"
                    f"🏷️ **Group:** {message.chat.title}\n"
                    f"🆔 **Group ID:** `{message.chat.id}`\n"
                    f"🛡️ **Promoted:** {promoted_count} sudo users\n"
                    f"👑 **Title:** ᴍʏ❦\n"
                    f"❌ **Failed:** {failed_count} users\n"
                    f"🔐 **Permissions:** {perm_text}\n"
                    f"⚡ **Status:** All sudo users are now administrators"
                )
            except:
                pass  # User might have blocked the bot

            # Log to logs channel if enabled
            if await is_on_off(config.LOG):
                try:
                    await app.send_message(
                        config.LOG_GROUP_ID,
                        f"✅ **Manual Auto-Promotion Log**\n\n"
                        f"👤 **Command User:** {message.from_user.mention} (`{message.from_user.id}`)\n"
                        f"🏷️ **Group:** {message.chat.title}\n"
                        f"🆔 **Group ID:** `{message.chat.id}`\n"
                        f"🛡️ **Promoted:** {promoted_count} sudo users\n"
                        f"👑 **Title:** ᴍʏ❦\n"
                        f"❌ **Failed:** {failed_count} users\n"
                        f"🔐 **Permissions:** {perm_text}\n"
                        f"⚡ **Action:** Manual auto-promotion command"
                    )
                except:
                    pass
        else:
            # Send notification to command user privately
            try:
                await app.send_message(
                    message.from_user.id,
                    f"ℹ️ **No Promotions Needed**\n\n"
                    f"🏷️ **Group:** {message.chat.title}\n"
                    f"🆔 **Group ID:** `{message.chat.id}`\n"
                    f"⚡ **Status:** All sudo users are already administrators or promotion failed"
                )
            except:
                pass  # User might have blocked the bot

    except Exception as e:
        await message.reply_text(f"❌ Error during auto-promotion: {str(e)}")


__MODULE__ = "Auto Promote"
__HELP__ = """
**Auto-Promotion Commands:**

• `/autopromote` or `/apromote` - Manually promote all sudo users in the current group

**Auto-Promotion Features:**
• Automatically promotes sudo users when they join groups
• Grants ALL permissions that the bot has (dynamic)
• Sets custom admin title "ᴍʏ❦" for promoted users
• Works only if bot has promote permissions
• Silent failure if promotion fails
• Notifications sent privately to sudo users and logged to logs channel
"""
