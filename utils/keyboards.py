"""Keyboard layouts for Whispier Bot."""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .strings import Strings


class Keyboards:
    """Keyboard layout definitions."""
    
    @staticmethod
    def main_menu():
        """Main menu keyboard."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(Strings.BTN_SEND_SECRET, switch_inline_query="")],
            [
                InlineKeyboardButton(Strings.BTN_TUTORIAL, callback_data="tutorial"),
                InlineKeyboardButton(Strings.BTN_STATS, callback_data="stats")
            ],
            [InlineKeyboardButton(Strings.BTN_HELP, callback_data="help")]
        ])
    
    @staticmethod
    def back_to_home():
        """Back to home button."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(Strings.BTN_HOME, callback_data="home")]
        ])
    
    @staticmethod
    def whisper_buttons(callback_data: str):
        """Whisper message buttons."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(Strings.WHISPER_BUTTON, callback_data=callback_data)]
        ])
    
    @staticmethod
    def inline_help():
        """Inline query help buttons."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎓 Learn More", url="https://t.me/whispierbot?start=tutorial")]
        ])