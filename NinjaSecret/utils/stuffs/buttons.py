from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram import Client, filters, enums

class BUTTONS(object):
    MBUTTON = [[InlineKeyboardButton("Iɴꜰᴏ", callback_data="mplus HELP_Info"),
    InlineKeyboardButton("Gʀᴏᴜᴘ Mɢᴍᴛ", callback_data="mplus HELP_GroupManagement")],
    [InlineKeyboardButton("◁", callback_data=f"settings_back_helper"),
     InlineKeyboardButton("↻ ʙᴀᴄᴋ ↻", callback_data=f"mbot_cb"),
    InlineKeyboardButton("▷", callback_data=f"managebot123 settings_back_helper"),
    ]]
