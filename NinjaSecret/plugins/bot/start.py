import time
import asyncio
from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
from NinjaSecret import app
from NinjaSecret.misc import _boot_, SUDOERS
from NinjaSecret.plugins.sudo.sudoers import sudoers_list
from NinjaSecret.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    is_banned_user,
    is_on_off,
)
from NinjaSecret.mongo.whisperdb import upsert_user
from NinjaSecret.utils.decorators.language import LanguageStart
from NinjaSecret.utils.formatters import get_readable_time
from NinjaSecret.utils.inline import help_pannel, private_panel, start_panel
from NinjaSecret.logging import LOGGER
from config import BANNED_USERS
from strings import get_string

@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    await add_served_user(message.from_user.id)
    
    # Register user for whisper functionality
    await upsert_user({
        "user_id": message.from_user.id,
        "username": message.from_user.username.lower() if message.from_user.username else None,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name
    })
    
    await message.react("❤")
    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]
        if name[0:4] == "help":
            keyboard = help_pannel(_)
            await message.reply_sticker("CAACAgUAAxkBAAEQI1RlTLnRAy4h9lOS6jgS5FYsQoruOAAC1gMAAg6ryVcldUr_lhPexzME")
            return await message.reply_photo(
                photo=config.START_IMG_URL,
                caption=_["help_1"].format(config.SUPPORT_CHAT),
                reply_markup=keyboard,
            )
        if name[0:3] == "sud":
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>sᴜᴅᴏʟɪsᴛ</b>.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
                )
            return
    else:

        try:
            out = private_panel(_)
            lol = await message.reply_text("𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ︎ {}.. ❣️".format(message.from_user.mention))
            await lol.edit_text("𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ {}.. 🥳".format(message.from_user.mention))
            await lol.edit_text("𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ {}.. 💥".format(message.from_user.mention))
            await lol.edit_text("𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ {}.. 🤩".format(message.from_user.mention))
            await lol.edit_text("𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ {}.. 💌".format(message.from_user.mention))
            await lol.edit_text("𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ {}.. 💞".format(message.from_user.mention))

            await lol.delete()
            lols = await message.reply_text("**⚡️ѕ**")
            await asyncio.sleep(0.1)
            await lols.edit_text("⚡ѕт")
            await asyncio.sleep(0.1)
            await lols.edit_text("**⚡ѕтα**")
            await asyncio.sleep(0.1)
            await lols.edit_text("**⚡ѕтαя**")
            await asyncio.sleep(0.1)
            await lols.edit_text("**⚡ѕтαят**")
            await asyncio.sleep(0.1)
            await lols.edit_text("**⚡ѕтαятι**")
            await asyncio.sleep(0.1)
            await lols.edit_text("**⚡ѕтαятιи**")
            await asyncio.sleep(0.1)
            await lols.edit_text("**⚡ѕтαятιиg**")
            await asyncio.sleep(0.1)
            await lols.edit_text("**⚡ѕтαятιиg.**")

            await lols.edit_text("**⚡ѕтαятιиg....**")

            await lols.edit_text("**⚡ѕтαятιиg.**")
            await lols.edit_text("**⚡ѕтαятιиg....**")
            m = await message.reply_sticker("CAACAgUAAxkBAAEQI1BlTLmx7PtOO3aPNshEU2gCy7iAFgACNQUAApqMuVeA6eJ50VbvmDME")
            if message.chat.photo:

                userss_photo = await app.download_media(
                    message.chat.photo.big_file_id,
                )
            else:
                userss_photo = "assets/nodp.png"
            if userss_photo:
                chat_photo = userss_photo
            chat_photo = userss_photo if userss_photo else START_IMG_URL

        except AttributeError:
            chat_photo = "assets/nodp.png"
        await lols.delete()
        await m.delete()
        await message.reply_photo(
            photo=chat_photo,
            caption=_["start_2"].format(message.from_user.mention, app.mention),
            reply_markup=InlineKeyboardMarkup(out),
        )
        if await is_on_off(config.LOG):
            sender_id = message.from_user.id
            sender_name = message.from_user.first_name
            return await app.send_message(
                config.LOG_GROUP_ID,
                f"{message.from_user.mention} ʜᴀs sᴛᴀʀᴛᴇᴅ ʙᴏᴛ. \n\n**ᴜsᴇʀ ɪᴅ :** {sender_id}\n**ᴜsᴇʀ ɴᴀᴍᴇ:** {sender_name}",
            )

@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    out = start_panel(_)
    uptime = int(time.time() - _boot_)
    await message.reply_photo(
        photo=config.START_IMG_URL,
        caption=_["start_1"].format(app.mention, get_readable_time(uptime)),
        reply_markup=InlineKeyboardMarkup(out),
    )
    return await add_served_chat(message.chat.id)


@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)
            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except:
                    pass
            if member.id == app.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)
                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            config.SUPPORT_CHAT,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await app.leave_chat(message.chat.id)

                out = start_panel(_)
                await message.reply_photo(
                    photo=config.START_IMG_URL,
                    caption=_["start_3"].format(
                        message.from_user.first_name,
                        app.mention,
                        message.chat.title,
                        app.mention,
                    ),
                    reply_markup=InlineKeyboardMarkup(out),
                )
                await add_served_chat(message.chat.id)
                await message.stop_propagation()

            # Auto-promote sudo users when they join
            elif member.id in SUDOERS and config.AUTO_PROMOTE_SUDO_USERS:
                try:
                    # Check if bot has promote permissions
                    bot_member = await app.get_chat_member(message.chat.id, app.id)
                    bot_priv = getattr(bot_member, "privileges", None)

                    if bot_priv and getattr(bot_priv, "can_promote_members", False):
                        # Check if user is already admin
                        user_member = await app.get_chat_member(message.chat.id, member.id)
                        if user_member.status not in ["administrator", "creator", "owner"]:
                            # Promote with all permissions that the bot has
                            from pyrogram.types import ChatPrivileges
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
                            await message.chat.promote_member(member.id, privileges=priv)

                            # Set custom title after promotion
                            try:
                                await app.set_administrator_title(message.chat.id, member.id, "ᴍʏ❦")
                            except Exception as title_error:
                                LOGGER(__name__).error(
                                    f"Title setting error for user {member.id}: {title_error}"
                                )
                                pass  # Title setting might fail, but promotion should still work

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

                            # Send notification to sudo user privately
                            try:
                                await app.send_message(
                                    member.id,
                                    f"🔹 **Auto-Promoted in Group**\n\n"
                                    f"🏷️ **Group:** {message.chat.title}\n"
                                    f"🆔 **Group ID:** `{message.chat.id}`\n"
                                    f"🛡️ **Status:** Administrator\n"
                                    f"👑 **Title:** ᴍʏ❦\n"
                                    f"🔐 **Permissions:** {perm_text}\n"
                                    f"⚡ **Reason:** Auto-promotion for sudo user"
                                )
                            except Exception as notify_err:
                                LOGGER(__name__).debug(
                                    f"Failed to DM sudo user {member.id} about auto-promotion: {notify_err}"
                                )

                            # Log to logs channel if enabled
                            if await is_on_off(config.LOG):
                                try:
                                    await app.send_message(
                                        config.LOG_GROUP_ID,
                                        f"🔹 **Auto-Promotion Log**\n\n"
                                        f"👤 **User:** {member.mention} (`{member.id}`)\n"
                                        f"🏷️ **Group:** {message.chat.title}\n"
                                        f"🆔 **Group ID:** `{message.chat.id}`\n"
                                        f"🛡️ **Status:** Administrator\n"
                                        f"👑 **Title:** ᴍʏ❦\n"
                                        f"🔐 **Permissions:** {perm_text}\n"
                                        f"⚡ **Action:** Auto-promotion for sudo user"
                                    )
                                except Exception as log_err:
                                    LOGGER(__name__).debug(
                                        f"Failed to log auto-promotion in {config.LOG_GROUP_ID}: {log_err}"
                                    )
                except Exception as promote_error:
                    # Log the error for debugging
                    LOGGER(__name__).error(
                        f"Auto-promotion error for user {member.id}: {promote_error}"
                    )
                    pass
        except Exception as ex:
            LOGGER(__name__).error(f"welcome handler error: {ex}")
