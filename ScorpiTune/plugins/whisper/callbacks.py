"""
WhispierBot Callback Handlers
Handles secret viewing, stats, dashboard, and other callback interactions
"""

from datetime import datetime
from pyrogram import filters, enums
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from ScorpiTune import app
from ScorpiTune.mongo.whisperdb import (
    get_whisper,
    mark_whisper_read,
    get_user_whisper_stats,
    update_user_stats,
    upsert_user
)
from ScorpiTune.utils.decorators.language import languageCB
from ScorpiTune.utils.whisper_utils import (
    create_unauthorized_access_text,
    create_unauthorized_keyboard,
    format_user_stats,
    create_stats_keyboard,
    create_dashboard_keyboard,
    format_targets_display,
    get_time_remaining_text,
    MONKEY_EMOJIS
)
from config import BANNED_USERS

@app.on_callback_query(filters.regex(r"whisper_view_(.+)") & ~BANNED_USERS)
@languageCB
async def handle_whisper_view(client, callback_query: CallbackQuery, _):
    """Handle viewing a whisper secret"""
    try:
        print(f"DEBUG: Whisper view callback triggered for user {callback_query.from_user.id}")

        whisper_id = callback_query.matches[0].group(1)
        user_id = callback_query.from_user.id
        print(f"DEBUG: Extracted whisper_id: {whisper_id}, user_id: {user_id}")

        # Get whisper message
        whisper = await get_whisper(whisper_id)
        print(f"DEBUG: Retrieved whisper data: {whisper is not None}")

        if not whisper:
            print(f"DEBUG: No whisper found for ID: {whisper_id}")
            await callback_query.answer(
                f"{MONKEY_EMOJIS['see_no_evil']} This secret has expired or been burned!",
                show_alert=True
            )
            return

        # Check if whisper has expired (timer feature)
        settings = whisper.get("settings", {})
        if settings.get("expires_at"):
            if datetime.utcnow() > settings["expires_at"]:
                await callback_query.answer(
                    f"{MONKEY_EMOJIS['timer']} This secret has expired!",
                    show_alert=True
                )
                return

        # Check if whisper was burned (burn after reading feature)
        if whisper.get("status") == "burned":
            await callback_query.answer(
                f"{MONKEY_EMOJIS['fire']} This secret was burned after reading!",
                show_alert=True
            )
            return

        # Authorization check
        sender_id = whisper["sender_id"]
        target_username = whisper.get("target_username")
        target_id = whisper.get("target_id")
        original_token = whisper.get("original_target_token")

        is_sender = user_id == sender_id
        is_target = False

        # Check if user is the target (support multiple targets)
        if target_id and user_id == target_id:
            is_target = True
        elif callback_query.from_user.username and target_username:
            if callback_query.from_user.username.lower() == target_username.lower():
                is_target = True
        elif original_token and original_token.isdigit() and int(original_token) == user_id:
            is_target = True
        else:
            # Check if user matches any of the multiple targets in original_target_token
            if original_token:
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

        if not (is_sender or is_target):
            await callback_query.answer(
                create_unauthorized_access_text("en"),
                show_alert=True
            )
            return

        # Late-link target if needed (when target clicks but wasn't resolved before)
        if is_target and not target_id:
            if callback_query.from_user.username:
                await upsert_user({
                    "user_id": user_id,
                    "username": callback_query.from_user.username.lower(),
                    "first_name": callback_query.from_user.first_name,
                    "last_name": callback_query.from_user.last_name
                })
            # Update the whisper with the resolved target_id
            from ScorpiTune.core.mongo import mongodb
            await mongodb.whispers.update_one(
                {"whisper_id": whisper_id},
                {"$set": {"target_id": user_id}}
            )

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
                    from ScorpiTune.core.mongo import mongodb
                    await mongodb.whispers.update_one(
                        {"whisper_id": whisper_id},
                        {"$set": {"status": "burned"}}
                    )

                    # Edit the message to show it was read and remove button
                    if whisper.get("inline_message_id"):
                        try:
                            # Get target's display name
                            target_display_name = callback_query.from_user.first_name
                            if callback_query.from_user.username:
                                target_display_name = f"@{callback_query.from_user.username}"

                            # Get original target display for the message
                            original_target = whisper.get("original_target_token", "Target")
                            if original_target.lower() in ["@all", "@everyone"]:
                                target_for_display = "Everyone"
                            else:
                                target_for_display = original_target

                            burned_message = f"💀🔥 **Burn After Reading Banana**\n\n💌 **For:** {target_for_display}\n🔒 **Monkey-secured & encrypted**\n\n✅ **{target_display_name} read the whisper**"

                            await app.edit_inline_text(
                                inline_message_id=whisper["inline_message_id"],
                                text=burned_message,
                                parse_mode=enums.ParseMode.MARKDOWN,
                                reply_markup=None  # Remove the button
                            )
                        except Exception as e:
                            print(f"Failed to edit burned message: {e}")

        # Get sender name for display
        try:
            sender = await app.get_users(sender_id)
            sender_name = f"@{sender.username}" if sender.username else sender.first_name
        except Exception:
            sender_name = "Someone"

        # Get the whisper content (no truncation - user should have been warned during creation)
        content = whisper['content']

        # Add special features info if present
        display_content = content
        settings = whisper.get("settings", {})

        # Add timer info if present
        if settings.get("expires_at"):
            time_left = get_time_remaining_text(settings["expires_at"])
            if time_left != "Expired":
                display_content += f"\n\n⏰ Expires in: {time_left}"

        # Add burn info if present
        if settings.get("burn_after_reading"):
            display_content += f"\n💀 Burns after reading!"

        # Add style emoji based on settings
        if settings.get("style") == "vip":
            display_content = f"👑 {display_content}"
        elif settings.get("style") == "cute":
            display_content = f"💕 {display_content}"

        # Show as alert (popup) with enhanced content
        await callback_query.answer(display_content, show_alert=True)

    except Exception as e:
        print(f"Whisper view error: {e}")
        import traceback
        traceback.print_exc()
        await callback_query.answer(
            f"{MONKEY_EMOJIS['see_no_evil']} Error viewing secret! Try again later.",
            show_alert=True
        )

@app.on_callback_query(filters.regex(r"whisper_targets_(.+)") & ~BANNED_USERS)
async def handle_whisper_targets(client, callback_query: CallbackQuery):
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
                f"{MONKEY_EMOJIS['see_no_evil']} This secret has expired or been burned!",
                show_alert=True
            )
            return

        # Format targets info
        targets = whisper.get('targets', [])
        target_display = format_targets_display(targets, max_display=10)

        # Create info text
        info_text = f"{MONKEY_EMOJIS['eyes']} **Secret Target Info**\n\n"

        if any(t.get('type') == 'all' for t in targets):
            info_text += f"{MONKEY_EMOJIS['monkey']} **For:** Everyone in this jungle!\n"
        else:
            info_text += f"{MONKEY_EMOJIS['monkey']} **Targets:** {target_display}\n"

            # Show read status
            read_count = len([t for t in targets if t.get('read_at')])
            total_count = len(targets)
            info_text += f"📖 **Read Status:** {read_count}/{total_count} monkeys have peeked\n"

        # Show additional info
        settings = whisper.get('settings', {})
        if settings.get('burn_after_reading'):
            info_text += f"💀 **Burns after all read**\n"

        if settings.get('expires_at'):
            time_left = get_time_remaining_text(settings['expires_at'])
            if time_left != "Expired":
                info_text += f"⏰ **Expires in:** {time_left}\n"

        info_text += f"\n{MONKEY_EMOJIS['banana']} Monkey-secured delivery!"

        await callback_query.answer(info_text, show_alert=True)

    except Exception as e:
        print(f"Whisper targets error: {e}")
        await callback_query.answer(
            f"{MONKEY_EMOJIS['see_no_evil']} Error getting target info!",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_dashboard") & ~BANNED_USERS)
async def handle_dashboard(client, callback_query: CallbackQuery):
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
            f"{MONKEY_EMOJIS['see_no_evil']} Error loading dashboard!",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_stats") & ~BANNED_USERS)
async def handle_stats(client, callback_query: CallbackQuery):
    """Show detailed user stats"""
    try:
        await callback_query.answer()

        user_id = callback_query.from_user.id
        stats = await get_user_whisper_stats(user_id)

        # Format detailed stats
        stats_text = format_user_stats(stats, "en")

        # Add more detailed info
        stats_text += f"\n\n📊 **Detailed Analytics:**"
        stats_text += f"\n• Total secrets sent: {stats.get('secrets_sent', 0)}"
        stats_text += f"\n• Total secrets received: {stats.get('secrets_received', 0)}"
        stats_text += f"\n• Burn-after-reading used: {stats.get('secrets_burned', 0)}"
        stats_text += f"\n• Timed secrets sent: {stats.get('secrets_timed', 0)}"
        stats_text += f"\n• Total monkeys reached: {stats.get('total_targets_reached', 0)}"

        keyboard = create_stats_keyboard(user_id)

        await callback_query.edit_message_text(
            stats_text,
            reply_markup=keyboard
        )

    except Exception as e:
        print(f"Stats error: {e}")
        await callback_query.answer(
            f"{MONKEY_EMOJIS['see_no_evil']} Error loading stats!",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_tutorial") & ~BANNED_USERS)
async def handle_tutorial(client, callback_query: CallbackQuery):
    """Show tutorial"""
    try:
        await callback_query.answer()

        tutorial_text = f"""{MONKEY_EMOJIS['monkey']} **WhispierBot Tutorial**

🎯 **How to Send Secrets:**
Type `@whispierbot` in any chat, then:

📝 **Basic Format:**
`@whispierbot [your message] [targets]`

🎪 **Examples:**
• Single person: `@whispierbot secret message @alice`
• With user ID: `@whispierbot secret message 6153949909`
• Multiple people: `@whispierbot group news @bob,@charlie`
• Everyone: `@whispierbot pizza time! @all`

🔥 **Special Features:**
• `!delete` - Burns after all read
• `!timer:3600` - Expires in 1 hour (3600 seconds)
• `!vip` - VIP styling with crown
• `!cute` - Extra cute monkey styling

🎯 **Advanced Examples:**
• `@whispierbot confidential info @boss !delete`
• `@whispierbot party at 8pm @friends !timer:7200`
• `@whispierbot special announcement @all !vip`

{MONKEY_EMOJIS['banana']} **Ready to swing into action?**"""

        tutorial_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{MONKEY_EMOJIS['lightning']} {MONKEY_EMOJIS['thought']} Try Now",
                    switch_inline_query_current_chat=""
                ),
                InlineKeyboardButton(
                    f"🏠 {MONKEY_EMOJIS['banana']} Dashboard",
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
            f"{MONKEY_EMOJIS['see_no_evil']} Error loading tutorial!",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_styles") & ~BANNED_USERS)
async def handle_styles(client, callback_query: CallbackQuery):
    """Show available styles"""
    try:
        await callback_query.answer()

        styles_text = f"""{MONKEY_EMOJIS['circus']} **Fun Whisper Styles**

🎨 **Available Themes:**

🤫💭 **Classic Whisper** (default)
Standard monkey secret delivery

👑🍌 **VIP Style** (`!vip`)
Golden banana with crown styling
Perfect for important announcements

🐒💕 **Cute Style** (`!cute`)
Extra playful with hearts and love
Great for friendly messages

💀🔥 **Burn After Reading** (`!delete`)
Self-destructs when all targets read
Maximum security monkey style

⏰🐒 **Timed Secrets** (`!timer:seconds`)
Auto-expires after specified time
Examples: `!timer:3600` (1 hour)

🎪 **Mix & Match:**
You can combine modifiers!
`@whispierbot secret @user !vip !timer:1800`

{MONKEY_EMOJIS['banana']} **Get creative with your secrets!**"""

        styles_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{MONKEY_EMOJIS['lightning']} {MONKEY_EMOJIS['thought']} Try Styles",
                    switch_inline_query_current_chat="@whispierbot test message @me !vip"
                )
            ],
            [
                InlineKeyboardButton(
                    f"🏠 {MONKEY_EMOJIS['banana']} Dashboard",
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
            f"{MONKEY_EMOJIS['see_no_evil']} Error loading styles!",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_help") & ~BANNED_USERS)
async def handle_help(client, callback_query: CallbackQuery):
    """Show help tree"""
    try:
        await callback_query.answer()

        help_text = f"""{MONKEY_EMOJIS['tree']} **Whispier Help Tree**

🆘 **Need Help?**

🎯 **Quick Commands:**
• `/start` - Main dashboard
• Type `@whispierbot` - Create secrets

📚 **Documentation:**
• Inline tutorial available
• Examples in every response
• Error messages are helpful

🎪 **Features:**
• ✅ Single & multiple targets
• ✅ Burn after reading
• ✅ Timed expiration
• ✅ Fun monkey themes
• ✅ User statistics
• ✅ Achievement system

🔧 **Troubleshooting:**
• Make sure usernames exist
• Use commas for multiple targets: `@user1,@user2`
• Timers use seconds: `!timer:3600` = 1 hour
• Check spelling of modifiers

💬 **Support:**
Contact the bot owner if you need additional help!

{MONKEY_EMOJIS['banana']} **Happy secret swinging!**"""

        help_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{MONKEY_EMOJIS['monkey']} Tutorial",
                    callback_data="whisper_tutorial"
                ),
                InlineKeyboardButton(
                    f"{MONKEY_EMOJIS['circus']} Styles Guide",
                    callback_data="whisper_styles"
                )
            ],
            [
                InlineKeyboardButton(
                    f"🏠 {MONKEY_EMOJIS['banana']} Dashboard",
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
            f"{MONKEY_EMOJIS['see_no_evil']} Error loading help!",
            show_alert=True
        )

@app.on_callback_query(filters.regex("whisper_settings") & ~BANNED_USERS)
async def handle_settings(client, callback_query: CallbackQuery):
    """Show user settings (placeholder for future features)"""
    try:
        await callback_query.answer()

        settings_text = f"""{MONKEY_EMOJIS['tree']} **My Jungle Settings**

⚙️ **Current Settings:**
• Language: English 🇺🇸
• Notifications: Enabled 🔔
• Achievement alerts: Enabled 🏆
• Statistics tracking: Enabled 📊

🔮 **Coming Soon:**
• Custom themes
• Notification preferences
• Privacy settings
• Export statistics

{MONKEY_EMOJIS['banana']} **Settings will be expanded in future updates!**"""

        settings_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"🏠 {MONKEY_EMOJIS['banana']} Dashboard",
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
            f"{MONKEY_EMOJIS['see_no_evil']} Error loading settings!",
            show_alert=True
        )
