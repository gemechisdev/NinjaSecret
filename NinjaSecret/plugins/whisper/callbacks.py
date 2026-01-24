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
    get_user_whisper_stats,
    update_user_stats,
    upsert_user,
    get_recent_targets,
    clear_recent_targets
)
from NinjaSecret.utils.decorators.language import languageCB
from NinjaSecret.utils.whisper_utils import (
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
                # all_targets format: [(target_id, target_username, original_token), ...]
                if len(target_tuple) == 3:
                    t_id, t_username, t_token = target_tuple
                    
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
        # This ensures we always have the most up-to-date user information
        from NinjaSecret.core.mongo import mongodb
        
        # Update the clicking user's information in our database
        await upsert_user({
            "user_id": user_id,
            "username": callback_query.from_user.username.lower() if callback_query.from_user.username else None,
            "first_name": callback_query.from_user.first_name,
            "last_name": callback_query.from_user.last_name
        })
        
        # If target clicked and wasn't resolved before, link them now
        if is_target and not target_id:
            # Update the whisper with the resolved target_id and fresh display name
            display_name = callback_query.from_user.first_name
            if callback_query.from_user.last_name:
                display_name += f" {callback_query.from_user.last_name}"
            
            # Update target mention with actual name now
            target_mention = f"[{display_name}](tg://user?id={user_id})"
            
            await mongodb.whispers.update_one(
                {"whisper_id": whisper_id},
                {"$set": {
                    "target_id": user_id,
                    "target_username": callback_query.from_user.username.lower() if callback_query.from_user.username else None,
                    "target_mentions": target_mention
                }}
            )
            
            # Don't edit the message for default whispers to preserve original delivery header
            # Only edit for special modifiers where we want to show the resolved name
            # This prevents changing "🤫 sᴇᴄʀᴇᴛ sʜᴜʀɪᴋᴇɴ ᴅᴇʟɪᴠᴇʀʏ 🥷" to "🤫 sᴇᴄʀᴇᴛ sʜᴜʀɪᴋᴇɴ 🥷"
            # The original header is preserved and looks better for default whispers
            
        elif is_target and target_id:
            # Target was already resolved, but update their display name if it changed
            display_name = callback_query.from_user.first_name
            if callback_query.from_user.last_name:
                display_name += f" {callback_query.from_user.last_name}"
            
            # Update target mention with fresh name
            target_mention = f"[{display_name}](tg://user?id={user_id})"
            
            await mongodb.whispers.update_one(
                {"whisper_id": whisper_id},
                {"$set": {
                    "target_username": callback_query.from_user.username.lower() if callback_query.from_user.username else None,
                    "target_mentions": target_mention
                }}
            )
            
            # Try to update the inline message to show the updated name
            try:
                from NinjaSecret.utils.whisper_utils import create_whisper_keyboard
                from strings import get_string
                language = get_string("en")
                
                # Create the updated message text
                message_text = language['whisper_simple_message'].format(target_mention)
                
                # Use callback_query.edit_message_text() which is a bound method that
                # automatically uses inline_message_id from the callback query for inline messages.
                await callback_query.edit_message_text(
                    text=message_text,
                    parse_mode=enums.ParseMode.MARKDOWN,
                    reply_markup=create_whisper_keyboard(whisper_id)
                )
            except Exception as e:
                # If we can't edit the message, that's okay - the DB is updated
                print(f"Could not update inline message with updated name: {e}")

        # Mark as read only if target is viewing (sender viewing doesn't count as "read")
        # Exception: if sender IS the target (self-whisper), then it counts as read
        should_mark_read = False
        if not whisper.get("read_at"):
            if is_target and not is_sender:
                # Target (not sender) is viewing - mark as read
                should_mark_read = True
            elif is_sender and is_target:
                # Sender is also the target (self-whisper) - mark as read
                should_mark_read = True

        if should_mark_read:
            await mark_whisper_read(whisper_id, user_id)

            # Handle burn after reading
            if settings.get("burn_after_reading"):
                should_burn = False
                original_token = whisper.get("original_target_token", "")

                # Check if this is a single target or @all/@everyone (burn immediately)
                if original_token.lower() in ["@all", "@everyone"] or "," not in original_token:
                    should_burn = True
                else:
                    # Multiple targets - would need complex tracking, for now burn immediately
                    # TODO: Implement proper multi-target burn tracking
                    should_burn = True

                if should_burn:
                    # Burn the whisper
                    from NinjaSecret.core.mongo import mongodb
                    await mongodb.whispers.update_one(
                        {"whisper_id": whisper_id},
                        {"$set": {"status": "burned"}}
                    )

                    # Edit the message to show it was read and remove button
                    try:
                        # Get target's display name
                        target_display_name = callback_query.from_user.first_name
                        if callback_query.from_user.username:
                            target_display_name = f"@{callback_query.from_user.username}"

                        # Get original target display for the message (with mentions if available)
                        target_for_display = whisper.get("target_mentions")
                        if not target_for_display:
                            # Fallback to original token
                            original_target = whisper.get("original_target_token", "Target")
                            if original_target.lower() in ["@all", "@everyone"]:
                                target_for_display = "Everyone"
                            else:
                                target_for_display = original_target

                        # Check if we should reveal who read it when burning
                        # Three distinct behaviors:
                        # !burn (!b) = reveal_on_read=True + burn_after_reading=True -> shows who read and burns
                        # !delete (!d, !del) = burn_after_reading=True only -> silent delete (no reader shown)
                        # !reveal (!r) = reveal_on_read=True only -> handled in elif below (shows reader, no burn)
                        if settings.get("reveal_on_read"):
                            # Show who read it (burn with reveal)
                            burned_message = _['whisper_burn_message'].format(target_for_display, target_display_name)
                        else:
                            # Silent delete (burn without revealing)
                            burned_message = _['whisper_delete_message'].format(target_for_display)

                        # Use callback_query.edit_message_text() which is a bound method that
                        # automatically uses inline_message_id from the callback query for inline messages.
                        # No need to manually pass inline_message_id - Pyrogram handles it internally.
                        await callback_query.edit_message_text(
                            text=burned_message,
                            parse_mode=enums.ParseMode.MARKDOWN,
                            reply_markup=None  # Remove the button
                        )
                    except Exception as e:
                        print(f"Failed to edit burned message: {e}")

            # Handle reveal-on-read (!r modifier) when NOT burning
            # This edits the message to show who read it (like @psstrobot)
            # Note: When burn_after_reading is also set, it's handled above (to prevent double-edit)
            # Note: For multi-target whispers, only the first reader is revealed (message can only be edited once)
            elif settings.get("reveal_on_read"):
                try:
                    # Build clickable read status with user's full name
                    reader = callback_query.from_user
                    reader_name = reader.first_name
                    if reader.last_name:
                        reader_name += " " + reader.last_name
                    # Escape HTML special characters using standard library
                    reader_name = html.escape(reader_name)
                    
                    # Create tappable name linking to profile
                    revealed_text = _['whisper_reveal_message'].format(reader_name, reader.id)
                    
                    # Use callback_query.edit_message_text() which is a bound method that
                    # automatically uses inline_message_id from the callback query for inline messages.
                    # No need to manually pass inline_message_id - Pyrogram handles it internally.
                    await callback_query.edit_message_text(
                        text=revealed_text,
                        parse_mode=enums.ParseMode.HTML,
                        reply_markup=None  # Remove the button to prevent re-click
                    )
                except Exception as e:
                    print(f"Failed to edit revealed message: {e}")

        # Get sender name for display
        try:
            sender = await app.get_users(sender_id)
            sender_name = f"@{sender.username}" if sender.username else sender.first_name
        except Exception:
            sender_name = "Someone"

        # Get the whisper content (no truncation - user should have been warned during creation)
        content = whisper['content']
        
        # Handle dual message content with new logic
        from NinjaSecret.utils.whisper_utils import get_content_for_user
        
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

        # Add special features info if present
        settings = whisper.get("settings", {})

        # Add timer info if present
        if settings.get("expires_at"):
            time_left = get_time_remaining_text(settings["expires_at"])
            if time_left != "Expired":
                display_content += f"\n⏰ {time_left} left"

        # Add emoji prefix based on modifier type to show in popup
        modifier_type = get_modifier_type(settings)
        if modifier_type == 'burn':
            display_content = f"💀🔥 {display_content}"
        elif modifier_type == 'delete':
            display_content = f"🗑️💥 {display_content}"
        elif modifier_type == 'reveal':
            display_content = f"👀 {display_content}"
        elif modifier_type == 'vip':
            display_content = f"👑 {display_content}"
        elif modifier_type == 'cute':
            display_content = f"💕 {display_content}"

        # Show as alert (popup) with enhanced content
        await callback_query.answer(display_content, show_alert=True)

    except Exception as e:
        print(f"Whisper view error: {e}")
        import traceback
        traceback.print_exc()
        await callback_query.answer(
            f"{NINJA_EMOJIS['see_no_evil']} {_['whisper_error_viewing']}",
            show_alert=True
        )

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

        # Format targets info
        targets = whisper.get('targets', [])
        target_display = format_targets_display(targets, max_display=10)

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

        if settings.get('expires_at'):
            time_left = get_time_remaining_text(settings['expires_at'])
            if time_left != "Expired":
                info_text += f"{_['whisper_expires_in'].format(time_left)}\n"

        info_text += f"\n{_['whisper_monkey_secured']}"

        await callback_query.answer(info_text, show_alert=True)

    except Exception as e:
        print(f"Whisper targets error: {e}")
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
        print(f"Dashboard error: {e}")
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
        print(f"Stats error: {e}")
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
        print(f"Tutorial error: {e}")
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
        print(f"Styles error: {e}")
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
        print(f"Help error: {e}")
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
        print(f"Settings error: {e}")
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
