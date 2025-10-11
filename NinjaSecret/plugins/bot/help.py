from typing import Union
import logging

from pyrogram import filters, types, enums
from pyrogram.types import InlineKeyboardMarkup, Message, InlineKeyboardButton
from pyrogram.errors import MessageNotModified

from NinjaSecret import app
from NinjaSecret.utils import help_pannel
from NinjaSecret.utils.database import get_lang
from NinjaSecret.utils.decorators.language import LanguageStart, languageCB
from NinjaSecret.utils.inline.help import help_back_markup, private_help_panel
from config import BANNED_USERS, START_IMG_URL, SUPPORT_CHAT
from strings import get_string, helpers
from NinjaSecret.utils.stuffs.buttons import BUTTONS
from NinjaSecret.utils.stuffs.helper import Helper

# Set up logging
logger = logging.getLogger(__name__)


@app.on_message(filters.command(["help"]) & filters.private & ~BANNED_USERS)
@app.on_callback_query(filters.regex("settings_back_helper") & ~BANNED_USERS)
async def helper_private(
    client: app, update: Union[types.Message, types.CallbackQuery]
):
    is_callback = isinstance(update, types.CallbackQuery)
    if is_callback:
        try:
            await update.answer()
        except:
            pass
        chat_id = update.message.chat.id
        language = await get_lang(chat_id)
        _ = get_string(language)
        keyboard = help_pannel(_, True)
        try:
            await update.edit_message_text(
                _["help_1"].format(SUPPORT_CHAT), reply_markup=keyboard
            )
        except MessageNotModified:
            # Message content is the same, no need to edit
            logger.debug("Help message content unchanged, skipping edit")
        except Exception as e:
            logger.error(f"Error editing help message: {str(e)}")
    else:
        try:
            await update.delete()
        except:
            pass
        language = await get_lang(update.chat.id)
        _ = get_string(language)
        keyboard = help_pannel(_)

        await update.reply_video(
            video="https://graph.org/file/84d30d4fd04570c0e0256.mp4",
            caption=_["help_1"].format(SUPPORT_CHAT), reply_markup=keyboard)


@app.on_message(filters.command(["help"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def help_com_group(client, message: Message, _):
    keyboard = private_help_panel(_)
    await message.reply_video(
        video="https://te.legra.ph/file/51293513e6af319726fe7.mp4",
        caption=_["help_2"], reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_callback_query(filters.regex("help_callback") & ~BANNED_USERS)
@languageCB
async def helper_cb(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    cb = callback_data.split(None, 1)[1]
    keyboard = help_back_markup(_)

    # Handle all help sections with proper error handling
    help_sections = {
        "hb1": helpers.HELP_1,
        "hb2": helpers.HELP_2,
        "hb3": helpers.HELP_3,
        "hb4": helpers.HELP_4,
        "hb5": helpers.HELP_5,
        "hb6": helpers.HELP_6,
        "hb7": helpers.HELP_7,
        "hb8": helpers.HELP_8,
        "hb9": helpers.HELP_9,
        "hb10": helpers.HELP_10,
        "hb11": helpers.HELP_11,
        "hb12": helpers.HELP_12,
        "hb13": helpers.HELP_13,
        "hb14": helpers.HELP_14,
        "hb15": helpers.HELP_15,
    }

    if cb in help_sections:
        try:
            await CallbackQuery.edit_message_text(help_sections[cb], reply_markup=keyboard)
        except MessageNotModified:
            # Message content is the same, no need to edit
            logger.debug(f"Help section {cb} content unchanged, skipping edit")
        except Exception as e:
            # Log the error for debugging
            logger.error(f"Error displaying help section {cb}: {str(e)}")
            # Fallback to error message if help section is too long
            error_msg = f"Help section {cb} is currently unavailable. Please try again later."
            try:
                await CallbackQuery.edit_message_text(error_msg, reply_markup=keyboard)
            except MessageNotModified:
                logger.debug("Error message content unchanged, skipping edit")
    else:
        # Handle unknown help sections
        logger.warning(f"Unknown help section requested: {cb}")
        try:
            await CallbackQuery.edit_message_text(
                "Help section not found.", reply_markup=keyboard
            )
        except MessageNotModified:
            logger.debug("Help section not found message unchanged, skipping edit")


@app.on_callback_query(filters.regex("mbot_cb") & ~BANNED_USERS)
async def helper_cb(client, CallbackQuery):
    try:
        await CallbackQuery.edit_message_text(Helper.HELP_M, reply_markup=InlineKeyboardMarkup(BUTTONS.MBUTTON))
    except MessageNotModified:
        # Message content is the same, no need to edit
        logger.debug("Main help message content unchanged, skipping edit")
    except Exception as e:
        logger.error(f"Error displaying main help: {str(e)}")


@app.on_callback_query(filters.regex('managebot123'))
async def on_back_button(client, CallbackQuery):
    try:
        callback_data = CallbackQuery.data.strip()
        cb = callback_data.split(None, 1)[1]

        if cb == "settings_back_helper":
            # Get language context for the user
            chat_id = CallbackQuery.message.chat.id
            language = await get_lang(chat_id)
            _ = get_string(language)

            keyboard = help_pannel(_, True)
            try:
                await CallbackQuery.edit_message_text(
                    _["help_1"].format(SUPPORT_CHAT), reply_markup=keyboard
                )
            except MessageNotModified:
                logger.debug("Back to help message content unchanged, skipping edit")
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Error in managebot123 callback: {str(e)}")
        # Handle any errors gracefully
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ʙᴀᴄᴋ", callback_data=f"mbot_cb")]])
        error_msg = "Error occurred while processing request. Please try again."
        try:
            await CallbackQuery.edit_message_text(error_msg, reply_markup=keyboard)
        except MessageNotModified:
            logger.debug("Error message content unchanged, skipping edit")

@app.on_callback_query(filters.regex('mplus'))
async def mb_plugin_button(client, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    cb = callback_data.split(None, 1)[1]
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ʙᴀᴄᴋ", callback_data=f"mbot_cb")]])

    if cb == "Okieeeeee":
        try:
            await CallbackQuery.edit_message_text(f"`something errors`",reply_markup=keyboard,parse_mode=enums.ParseMode.MARKDOWN)
        except MessageNotModified:
            logger.debug("Error message content unchanged, skipping edit")
    else:
        try:
            # Get the help text from Helper class
            help_text = getattr(Helper, cb, None)
            if help_text:
                try:
                    await CallbackQuery.edit_message_text(help_text, reply_markup=keyboard)
                except MessageNotModified:
                    logger.debug(f"Help section '{cb}' content unchanged, skipping edit")
            else:
                # Log the missing help section
                logger.warning(f"Help section '{cb}' not found in Helper class")
                # Handle case where help section doesn't exist
                error_msg = f"Help section '{cb}' not found. Please try again later."
                try:
                    await CallbackQuery.edit_message_text(error_msg, reply_markup=keyboard)
                except MessageNotModified:
                    logger.debug("Error message content unchanged, skipping edit")
        except AttributeError as e:
            # Log the specific attribute error
            logger.error(f"AttributeError in help section '{cb}': {str(e)}")
            # Handle missing attributes gracefully
            error_msg = f"Help section '{cb}' is not available. Please try another section."
            try:
                await CallbackQuery.edit_message_text(error_msg, reply_markup=keyboard)
            except MessageNotModified:
                logger.debug("Error message content unchanged, skipping edit")
        except Exception as e:
            # Log the error for debugging
            logger.error(f"Error loading help section '{cb}': {str(e)}")
            # Handle any errors gracefully
            error_msg = f"Error loading help section '{cb}'. Please try again later."
            try:
                await CallbackQuery.edit_message_text(error_msg, reply_markup=keyboard)
            except MessageNotModified:
                logger.debug("Error message content unchanged, skipping edit")
