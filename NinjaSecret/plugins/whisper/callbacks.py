"""
Ninja Secret🥷 Callback Handlers
Handles secret viewing, stats, dashboard, and other callback interactions
"""

import html
from datetime import datetime
from pyrogram import filters, enums
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from NinjaSecret import app
from NinjaSecret.logging import LOGGER
from NinjaSecret.mongo.whisperdb import (
    get_whisper,
    mark_whisper_read,
    add_whisper_reader,
    claim_burn,
    link_target_id,
    attach_inline_message_id,
    get_user_whisper_stats,
    update_user_stats,
    upsert_user,
    get_recent_targets,
    clear_recent_targets
)
from NinjaSecret.utils.decorators.language import languageCB
from NinjaSecret.utils.rich_api import edit_rich_message, RichApiError, MessageNotModified
from NinjaSecret.utils.whisper_card import (
    card_from_whisper,
    card_targets,
    burned_card_from_whisper,
    deleted_card,
    is_everyone as card_is_everyone,
)
from NinjaSecret.utils.whisper_utils import (
    get_content_for_user,
    create_unauthorized_access_text,
    create_unauthorized_keyboard,
    format_user_stats,
    create_stats_keyboard,
    create_dashboard_keyboard,
    format_targets_display,
    get_time_remaining_text,
    get_modifier_type,
    NINJA_EMOJIS
)
from config import BANNED_USERS, OWNER_ID
from NinjaSecret.misc import SUDOERS

# Get logger for this module
logger = LOGGER(__name__)

def _reader_display_name(user) -> str:
    """Full name of a Telegram user, falling back to @username / id."""
    name = (user.first_name or "").strip()
    if user.last_name:
        name = f"{name} {user.last_name}".strip()
    if name:
        return name
    return f"@{user.username}" if user.username else str(user.id)


async def _edit_card(callback_query: CallbackQuery, whisper: dict, card: dict) -> None:
    """Replace the whisper card with `card` through the raw Rich Message API.

    Never raises: a failed edit must not stop the secret from opening.
    An identical card (MessageNotModified) is expected and ignored.
    """
    try:
        inline_id = callback_query.inline_message_id or whisper.get("inline_message_id")
        if inline_id:
            await edit_rich_message(card, inline_message_id=inline_id)
        elif callback_query.message:
            await edit_rich_message(
                card,
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.id,
            )
        else:
            logger.warning(f"No message reference to edit for whisper {whisper.get('whisper_id')}")
    except MessageNotModified:
        pass
    except RichApiError as e:
        logger.error(f"Rich edit failed for whisper {whisper.get('whisper_id')}: {e}")
    except Exception:
        logger.exception("Unexpected error while editing whisper card")


async def _record_read(callback_query: CallbackQuery, whisper: dict) -> None:
    """Register a valid read, then update the card (progress, reveal, burn, delete).

    Called only after the secret popup was shown. Rules:
      * a repeat read by the same person changes nothing (no edit, no error);
      * burn/delete wait until every target read (@all: first read);
      * burned/deleted/expired cards are final and never rebuilt.
    """
    whisper_id = whisper["whisper_id"]
    user = callback_query.from_user
    is_new, _readers = await add_whisper_reader(whisper_id, user.id, _reader_display_name(user))
    await mark_whisper_read(whisper_id, user.id)
    if not is_new:
        return

    targets = card_targets(whisper)
    await link_target_id(
        whisper_id,
        user.id,
        user.username,
        primary=targets is not None and len(targets) == 1,
    )

    fresh = await get_whisper(whisper_id) or whisper
    if not fresh.get("rich"):
        return  # sent before the rich format existed: its message cannot be rebuilt
    if fresh.get("status") in ("burned", "expired"):
        return  # terminal state wins over a late progress edit

    settings = fresh.get("settings") or {}
    readers = fresh.get("readers") or []
    targets = card_targets(fresh)

    if settings.get("burn_after_reading"):
        all_read = targets is None or len(readers) >= len(targets)
        if all_read:
            if await claim_burn(whisper_id):  # only one concurrent reader wins
                if settings.get("reveal_on_read"):
                    await _edit_card(callback_query, fresh, burned_card_from_whisper(fresh))
                else:
                    await _edit_card(callback_query, fresh, deleted_card())
            return

    await _edit_card(callback_query, fresh, card_from_whisper(fresh))


@app.on_callback_query(filters.regex(r"whisper_view_(.+)") & ~BANNED_USERS)
@languageCB
async def handle_whisper_view(client, callback_query: CallbackQuery, _):
    """Handle viewing a whisper secret"""
    try:
        whisper_id = callback_query.matches[0].group(1)
        user_id = callback_query.from_user.id

        # Get whisper message
        whisper = await get_whisper(whisper_id)

        if not whisper:
            await callback_query.answer(
                f"{NINJA_EMOJIS['see_no_evil']} {_['whisper_expired_burned']}",
                show_alert=True
            )
            return

        # Check if whisper has expired (timer feature)
        settings = whisper.get("settings", {})
        if settings.get("expires_at"):
            if datetime.utcnow() > settings["expires_at"]:
                await callback_query.answer(
                    f"{NINJA_EMOJIS['timer']} {_['whisper_timer_expired']}",
                    show_alert=True
                )
                return

        # Check if whisper was burned (burn after reading feature)
        if whisper.get("status") == "burned":
            await callback_query.answer(
                f"{NINJA_EMOJIS['fire']} {_['whisper_burned_after_read']}",
                show_alert=True
            )
            return

        # Authorization check
        sender_id = whisper["sender_id"]
        target_username = whisper.get("target_username")
        target_id = whisper.get("target_id")
        original_token = whisper.get("original_target_token")
        all_targets = whisper.get("all_targets", [])

        is_sender = user_id == sender_id
        is_target = False
        is_owner = user_id == OWNER_ID
        is_sudo = user_id in SUDOERS

        # Check if user is the target (support multiple targets)
        # First check the primary target fields for backward compatibility
        if target_id and user_id == target_id:
            is_target = True
        elif callback_query.from_user.username and target_username:
            if callback_query.from_user.username.lower() == target_username.lower():
                is_target = True
        elif original_token and original_token.isdigit() and int(original_token) == user_id:
            is_target = True
        
        # Check all_targets array if not already authorized
        if not is_target and all_targets:
            for target_tuple in all_targets:
                # all_targets format: [(target_id, target_username, original_token, target_display_name), ...]
                if len(target_tuple) >= 3:
                    t_id, t_username, t_token = target_tuple[:3]
                    
                    # Check for @all/@everyone
                    if t_token and t_token.lower() in ["@all", "@everyone"]:
                        is_target = True
                        break
                    
                    # Check if user_id matches (use 'is not None' to handle user_id=0)
                    if t_id is not None and t_id == user_id:
                        is_target = True
                        break
                    
                    # Check if username matches
                    if t_username and callback_query.from_user.username:
                        if t_username.lower() == callback_query.from_user.username.lower():
                            is_target = True
                            break
        
        # Fallback: Check original_target_token string for comma-separated targets
        # (for backward compatibility with older whispers without all_targets)
        if not is_target and original_token:
            # Handle @all/@everyone - everyone can access
            if original_token.lower() in ["@all", "@everyone"]:
                is_target = True
            elif "," in original_token:
                target_tokens = [token.strip() for token in original_token.split(",")]
                for token in target_tokens:
                    # Check for @all/@everyone in multiple targets
                    if token.lower() in ["@all", "@everyone"]:
                        is_target = True
                        break
                    elif token.startswith("@") and callback_query.from_user.username:
                        if token[1:].lower() == callback_query.from_user.username.lower():
                            is_target = True
                            break
                    elif token.isdigit() and 4 <= len(token) <= 15:
                        if int(token) == user_id:
                            is_target = True
                            break

        # Allow owner and sudo users to read any whisper for moderation purposes
        if not (is_sender or is_target or is_owner or is_sudo):
            await callback_query.answer(
                create_unauthorized_access_text("en"),
                show_alert=True
            )
            return

        # Always update user info when they interact (names can change over time)
        await upsert_user({
            "user_id": user_id,
            "username": callback_query.from_user.username.lower() if callback_query.from_user.username else None,
            "first_name": callback_query.from_user.first_name,
            "last_name": callback_query.from_user.last_name
        })

        # With rich buttons chosen_inline_result may arrive without inline_message_id,
        # so remember it from this callback (needed for edits and timer expiry).
        if callback_query.inline_message_id and not whisper.get("inline_message_id"):
            await attach_inline_message_id(whisper_id, callback_query.inline_message_id)
            whisper["inline_message_id"] = callback_query.inline_message_id

        # Only a real target's read counts. Opens by the sender, the owner or sudo
        # users never change the card. For @all whispers everyone but those is a reader.
        if card_is_everyone(whisper):
            counts_as_read = is_target and not (is_sender or is_owner or is_sudo)
        else:
            counts_as_read = is_target

        # Get the whisper content (no truncation - user should have been warned during creation)
        content = whisper['content']

        # Handle dual message content with new logic
        display_content = get_content_for_user(
            content=content,
            user_id=user_id,
            username=callback_query.from_user.username,
            is_sender=is_sender,
            is_owner=is_owner,
            is_sudo=is_sudo
        )

        # If None returned, user has no access to either message
        if display_content is None:
            await callback_query.answer(
                create_unauthorized_access_text("en"),
                show_alert=True
            )
            return

        # Add emoji prefix based on modifier type to show in popup
        # Only !cute and !vip display emoji prefix in callback alert
        modifier_type = get_modifier_type(settings)
        if modifier_type == 'vip':
            display_content = f"👑 {display_content}"
        elif modifier_type == 'cute':
            display_content = f"💕 {display_content}"

        # Show the secret first. If this fails the reader did not see it,
        # so nothing is marked as read (the generic handler below reports it).
        await callback_query.answer(display_content, show_alert=True)

    except Exception as e:
        logger.error(f"Whisper view error: {e}")
        import traceback
        traceback.print_exc()
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} {_['whisper_error_viewing']}",
            show_alert=True
        )
        return

    # Read tracking and card edits happen after the popup and can never break it.
    if counts_as_read:
        try:
            await _record_read(callback_query, whisper)
        except Exception:
            logger.exception("Failed to record whisper read")

@app.on_callback_query(filters.regex(r"whisper_targets_(.+)") & ~BANNED_USERS)
@languageCB
async def handle_whisper_targets(client, callback_query: CallbackQuery, _):
    """Show who the whisper is for"""
    try:
        await callback_query.answer()

        whisper_id = callback_query.matches[0].group(1)

        # Increment view analytics
        await increment_whisper_view_by_id(whisper_id)

        # Get whisper message
        whisper = await get_whisper_by_id(whisper_id)

        if not whisper:
            await callback_query.answer(
                f"{NINJA_EMOJIS['see_no_evil']} This secret has expired or been burned!",
                show_alert=True
            )
            return

        # Format targets info - all_targets is stored as tuples (target_id, target_username, original_token, target_display_name)
        # Convert to dict format expected by format_targets_display
        raw_targets = whisper.get('targets') or whisper.get('all_targets', [])
        targets = []
        if raw_targets:
            for t in raw_targets:
                if isinstance(t, dict):
                    targets.append(t)
                elif isinstance(t, (list, tuple)) and len(t) >= 4:
                    target_id, target_username, original_token, target_display_name = t
                    if original_token.lower() in ["@all", "@everyone"]:
                        targets.append({
                            "display_name": target_display_name,
                            "type": "all",
                            "resolved_id": None,
                        })
                    else:
                        targets.append({
                            "display_name": target_display_name,
                            "type": "user",
                            "resolved_id": target_id,
                            "target_id": target_id,
                            "username": target_username,
                        })

        # Create info text
        info_text = f"{_['whisper_target_info']}\n\n"

        if any(t.get('type') == 'all' for t in targets):
            info_text += f"{_['whisper_for_everyone_jungle']}\n"
        else:
            info_text += f"{_['whisper_targets_label'].format(target_display)}\n"

            # Show read status
            read_count = len([t for t in targets if t.get('read_at')])
            total_count = len(targets)
            info_text += f"{_['whisper_read_status'].format(read_count, total_count)}\n"

        # Show additional info
        settings = whisper.get('settings', {})
        if settings.get('burn_after_reading'):
            info_text += f"{_['whisper_burns_all_read']}\n"

        # Timer info is now displayed on the inline message itself (updated every 5 seconds)
        # so we don't need to show it in the callback alert anymore

        info_text += f"\n{_['whisper_monkey_secured']}"

        await callback_query.answer(info_text, show_alert=True)

    except Exception as e:
        logger.error(f"Whisper targets error: {e}")
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} {_['whisper_error_targets']}",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_dashboard") & ~BANNED_USERS)
@languageCB
async def handle_dashboard(client, callback_query: CallbackQuery, _):
    """Show user dashboard"""
    try:
        await callback_query.answer()

        # Get user stats
        stats = await get_user_whisper_stats(callback_query.from_user.id)

        # Format stats text
        stats_text = format_user_stats(stats, "en")

        # Create dashboard keyboard
        keyboard = create_dashboard_keyboard()

        await callback_query.edit_message_text(
            stats_text,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} {_['whisper_error_dashboard']}",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_stats") & ~BANNED_USERS)
@languageCB
async def handle_stats(client, callback_query: CallbackQuery, _):
    """Show detailed user stats"""
    try:
        await callback_query.answer()

        user_id = callback_query.from_user.id
        stats = await get_user_whisper_stats(user_id)

        # Format detailed stats
        stats_text = format_user_stats(stats, "en")

        # Add more detailed info
        stats_text += f"\n\n{_['whisper_detailed_analytics']}"
        stats_text += f"\n{_['whisper_total_sent'].format(stats.get('secrets_sent', 0))}"
        stats_text += f"\n{_['whisper_total_received'].format(stats.get('secrets_received', 0))}"
        stats_text += f"\n{_['whisper_burn_used'].format(stats.get('secrets_burned', 0))}"
        stats_text += f"\n{_['whisper_timed_sent'].format(stats.get('secrets_timed', 0))}"
        stats_text += f"\n{_['whisper_monkeys_reached'].format(stats.get('total_targets_reached', 0))}"

        keyboard = create_stats_keyboard(user_id)

        await callback_query.edit_message_text(
            stats_text,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Stats error: {e}")
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} {_['whisper_error_stats']}",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_tutorial") & ~BANNED_USERS)
@languageCB
async def handle_tutorial(client, callback_query: CallbackQuery, _):
    """Show tutorial"""
    try:
        await callback_query.answer()

        tutorial_text = f"""{_['whisper_tutorial_title']}

{_['whisper_tutorial_how']}

{_['whisper_tutorial_format']}

{_['whisper_tutorial_examples']}

{_['whisper_tutorial_features']}

{_['whisper_tutorial_dual']}

{_['whisper_tutorial_advanced']}

{_['whisper_tutorial_ready']}"""

        tutorial_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{NINJA_EMOJIS['lightning']} {NINJA_EMOJIS['thought']} Try Now",
                    switch_inline_query_current_chat=""
                ),
                InlineKeyboardButton(
                    f"🏠 {NINJA_EMOJIS['shuriken']} Dashboard",
                    callback_data="whisper_dashboard"
                )
            ]
        ])

        await callback_query.edit_message_text(
            tutorial_text,
            reply_markup=tutorial_keyboard
        )

    except Exception as e:
        logger.error(f"Tutorial error: {e}")
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} {_['whisper_error_tutorial']}",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_styles") & ~BANNED_USERS)
@languageCB
async def handle_styles(client, callback_query: CallbackQuery, _):
    """Show available styles"""
    try:
        await callback_query.answer()

        styles_text = f"""{_['whisper_styles_title']}

{_['whisper_styles_themes']}

{_['whisper_styles_classic']}

{_['whisper_styles_vip']}

{_['whisper_styles_cute']}

{_['whisper_styles_reveal']}

{_['whisper_styles_delete']}

{_['whisper_styles_burn']}

{_['whisper_styles_timed']}

{_['whisper_styles_mix']}

{_['whisper_styles_creative']}"""

        styles_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{NINJA_EMOJIS['lightning']} {NINJA_EMOJIS['thought']} Try Styles",
                    switch_inline_query_current_chat="@ninjasecretbot test message @me !vip"
                )
            ],
            [
                InlineKeyboardButton(
                    f"🏠 {NINJA_EMOJIS['shuriken']} Dashboard",
                    callback_data="whisper_dashboard"
                )
            ]
        ])

        await callback_query.edit_message_text(
            styles_text,
            reply_markup=styles_keyboard
        )

    except Exception as e:
        logger.error(f"Styles error: {e}")
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} {_['whisper_error_styles']}",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_help") & ~BANNED_USERS)
@languageCB
async def handle_help(client, callback_query: CallbackQuery, _):
    """Show help tree"""
    try:
        await callback_query.answer()

        help_text = f"""{_['whisper_help_title']}

{_['whisper_help_need']}

{_['whisper_help_commands']}

{_['whisper_help_docs']}

{_['whisper_help_features']}

{_['whisper_help_troubleshoot']}

{_['whisper_help_support']}

{_['whisper_help_happy']}"""

        help_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{NINJA_EMOJIS['ninja']} Tutorial",
                    callback_data="whisper_tutorial"
                ),
                InlineKeyboardButton(
                    f"{NINJA_EMOJIS['stealth']} Styles Guide",
                    callback_data="whisper_styles"
                )
            ],
            [
                InlineKeyboardButton(
                    f"🏠 {NINJA_EMOJIS['shuriken']} Dashboard",
                    callback_data="whisper_dashboard"
                )
            ]
        ])

        await callback_query.edit_message_text(
            help_text,
            reply_markup=help_keyboard
        )

    except Exception as e:
        logger.error(f"Help error: {e}")
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} {_['whisper_error_help']}",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_settings") & ~BANNED_USERS)
@languageCB
async def handle_settings(client, callback_query: CallbackQuery, _):
    """Show user settings (placeholder for future features)"""
    try:
        await callback_query.answer()

        settings_text = f"""{_['whisper_settings_title']}

{_['whisper_settings_current']}

{_['whisper_settings_coming']}

{_['whisper_settings_expanded']}"""

        settings_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"🏠 {NINJA_EMOJIS['shuriken']} Dashboard",
                    callback_data="whisper_dashboard"
                )
            ]
        ])

        await callback_query.edit_message_text(
            settings_text,
            reply_markup=settings_keyboard
        )

    except Exception as e:
        logger.error(f"Settings error: {e}")
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} {_['whisper_error_settings']}",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_recent_targets") & ~BANNED_USERS)
async def handle_recent_targets(client, callback_query: CallbackQuery):
    """Show recent targets list"""
    try:
        await callback_query.answer()
        
        user_id = callback_query.from_user.id
        recent_targets = await get_recent_targets(user_id)
        
        if not recent_targets:
            recent_text = f"""{NINJA_EMOJIS['see_no_evil']} **No Recent Targets**

You haven't sent any secrets yet! 

Use inline mode to send your first secret message:
`@ninjasecretbot [message] [target]`

Example: `@ninjasecretbot Hey there! @username`"""
        else:
            recent_text = f"""{NINJA_EMOJIS['scroll']} **Recent Targets**

Here are your last {len(recent_targets)} secret recipients (most recent first):

"""
            for i, target in enumerate(recent_targets, 1):
                display_name = target.get("display_name", "Unknown")
                username = target.get("username")
                user_id_str = target.get("user_id")
                
                # Format target info
                if username:
                    target_info = f"@{username}"
                elif user_id_str:
                    target_info = str(user_id_str)
                else:
                    target_info = target.get("original_token", "Unknown")
                
                recent_text += f"{i}. {display_name} ({target_info})\n"
            
            recent_text += f"""
{NINJA_EMOJIS['shuriken']} **Quick Send:**
Click any button below to send a secret to that target!"""
        
        # Create buttons for recent targets
        buttons = []
        for i, target in enumerate(recent_targets[:5], 1):  # Show top 5 as quick buttons
            display_name = target.get("display_name", "Unknown")
            username = target.get("username")
            user_id_str = target.get("user_id")
            
            # Determine what to use as the target reference
            if username:
                target_ref = f"@{username}"
            elif user_id_str:
                target_ref = str(user_id_str)
            else:
                target_ref = target.get("original_token", "@unknown")
            
            # Truncate long display names
            button_text = display_name[:20] + "..." if len(display_name) > 20 else display_name
            
            buttons.append([
                InlineKeyboardButton(
                    f"{i}. {button_text}",
                    switch_inline_query_current_chat=f"Your message here {target_ref}"
                )
            ])
        
        # Add control buttons
        if recent_targets:
            buttons.append([
                InlineKeyboardButton(
                    f"🗑️ Clear History",
                    callback_data="whisper_clear_recent_targets"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                f"🏠 {NINJA_EMOJIS['shuriken']} Dashboard",
                callback_data="whisper_dashboard"
            )
        ])
        
        recent_keyboard = InlineKeyboardMarkup(buttons)
        
        await callback_query.edit_message_text(
            recent_text,
            reply_markup=recent_keyboard
        )
    
    except Exception:
        logger.exception("Error in handle_recent_targets")
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} Error loading recent targets!",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_clear_recent_targets") & ~BANNED_USERS)
async def handle_clear_recent_targets(client, callback_query: CallbackQuery):
    """Clear recent targets"""
    try:
        user_id = callback_query.from_user.id
        await clear_recent_targets(user_id)
        
        await callback_query.answer(
            f"{NINJA_EMOJIS['sparkles']} Recent targets cleared!",
            show_alert=True
        )
        
        # Refresh the view
        recent_text = f"""{NINJA_EMOJIS['see_no_evil']} **No Recent Targets**

Your recent targets history has been cleared!

Use inline mode to send secrets:
`@ninjasecretbot [message] [target]`"""
        
        clear_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"🏠 {NINJA_EMOJIS['shuriken']} Dashboard",
                    callback_data="whisper_dashboard"
                )
            ]
        ])
        
        await callback_query.edit_message_text(
            recent_text,
            reply_markup=clear_keyboard
        )
    
    except Exception:
        logger.exception("Error in handle_clear_recent_targets")
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} Error clearing targets!",
            show_alert=True
        )


@app.on_callback_query(filters.regex(r"whisper_full_stats_(\d+)") & ~BANNED_USERS)
@languageCB
async def handle_full_stats(client, callback_query: CallbackQuery, _):
    """Show full stats for a user"""
    try:
        await callback_query.answer()

        user_id = callback_query.from_user.id
        stats = await get_user_whisper_stats(user_id)

        stats_text = format_user_stats(stats, "en")

        stats_text += f"\n\n{_['whisper_detailed_analytics']}"
        stats_text += f"\n{_['whisper_total_sent'].format(stats.get('secrets_sent', 0))}"
        stats_text += f"\n{_['whisper_total_received'].format(stats.get('secrets_received', 0))}"
        stats_text += f"\n{_['whisper_burn_used'].format(stats.get('secrets_burned', 0))}"
        stats_text += f"\n{_['whisper_timed_sent'].format(stats.get('secrets_timed', 0))}"
        stats_text += f"\n{_['whisper_monkeys_reached'].format(stats.get('total_targets_reached', 0))}"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"🏠 ʜᴏᴍᴇ ᴛʀᴇᴇ {NINJA_EMOJIS['shuriken']}",
                    callback_data="whisper_dashboard"
                )
            ]
        ])

        await callback_query.edit_message_text(
            stats_text,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.exception("Error in handle_full_stats")
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} Error loading full stats!",
            show_alert=True
        )


@app.on_callback_query(filters.regex("whisper_clean_history") & ~BANNED_USERS)
async def handle_clean_history(client, callback_query: CallbackQuery):
    """Clean user's whisper history"""
    try:
        from NinjaSecret.mongo.whisperdb import whisperdb as whisper_collection

        user_id = callback_query.from_user.id

        # Delete whispers sent by the user that have been read or expired
        result = await whisper_collection.delete_many({
            "sender_id": user_id,
            "$or": [
                {"status": "read"},
                {"status": "burned"},
                {"status": "expired"}
            ]
        })

        deleted_count = result.deleted_count

        await callback_query.answer(
            f"{NINJA_EMOJIS['sparkles']} Cleaned {deleted_count} old secrets!",
            show_alert=True
        )

        # Refresh stats view
        stats = await get_user_whisper_stats(user_id)
        keyboard = create_stats_keyboard(user_id)
        stats_text = format_user_stats(stats, "en")

        await callback_query.edit_message_text(
            stats_text,
            reply_markup=keyboard
        )

    except Exception:
        logger.exception("Error in handle_clean_history")
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} Error cleaning history!",
            show_alert=True
        )
