# NinjaSecret Command Flow Diagrams

This document provides visual representations of how commands flow through the NinjaSecret bot architecture.

## Table of Contents
1. [Overall Bot Architecture](#overall-bot-architecture)
2. [Command Processing Flow](#command-processing-flow)
3. [Plugin Loading Sequence](#plugin-loading-sequence)
4. [Database Interaction Flow](#database-interaction-flow)
5. [Specific Command Flows](#specific-command-flows)

---

## Overall Bot Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ FastAPI Server (Health Checks)                             │ │
│  │ - GET  /           → {"message": "Bot is running"}         │ │
│  │ - GET  /health     → {"status": "healthy", "uptime": ...}  │ │
│  │ - GET  /ping       → {"pong": "ok"}                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ▲                                   │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Bot Thread (daemon=True)                                   │ │
│  │   python -m NinjaSecret                                    │ │
│  └──────────────────────┬─────────────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   NinjaSecret Package                            │
│                                                                  │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │   core/    │  │ plugins/ │  │  utils/  │  │    mongo/    │ │
│  │            │  │          │  │          │  │              │ │
│  │  • bot.py  │  │  • bot/  │  │• database│  │ • whisperdb  │ │
│  │  • mongo   │  │  • sudo/ │  │• decorat │  │              │ │
│  │  • call    │  │  • tools/│  │• inline  │  │              │ │
│  └────────────┘  └──────────┘  └──────────┘  └──────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Pyrogram Client (app)                        │  │
│  │  • Receives Telegram updates                             │  │
│  │  • Routes to appropriate handlers                        │  │
│  │  • Manages connection to Telegram API                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          ▲
                          │
                          ▼
                    ┌───────────┐
                    │ Telegram  │
                    │  Servers  │
                    └───────────┘
```

---

## Command Processing Flow

### Complete Flow from User Input to Response

```
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 1: User Action                                                  │
│ User sends: "/start" in Telegram                                     │
└────────────┬─────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 2: Telegram Platform                                            │
│ • Telegram servers receive message                                   │
│ • Create Update object                                               │
│ • Send to bot via Bot API                                            │
└────────────┬─────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 3: Pyrogram Client Receives Update                             │
│ File: NinjaSecret/core/bot.py                                        │
│                                                                       │
│ class Hotty(Client):                                                 │
│     # Bot instance receives message                                  │
└────────────┬─────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 4: Filter Chain                                                 │
│                                                                       │
│ Check 1: filters.command("start")                                    │
│          ✓ Message text starts with "/start"                         │
│                                                                       │
│ Check 2: filters.private                                             │
│          ✓ Message is from private chat                              │
│                                                                       │
│ Check 3: ~BANNED_USERS                                               │
│          ✓ User is not banned                                        │
│                                                                       │
│ Result: All filters pass → Handler will execute                      │
└────────────┬─────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 5: Decorator Chain (Middleware)                                 │
│ File: NinjaSecret/utils/decorators/language.py                       │
│                                                                       │
│ @LanguageStart Decorator:                                            │
│   1. Check maintenance mode                                          │
│      • Query: await is_maintenance()                                 │
│      • If True and not sudo: Return "Under maintenance"              │
│                                                                       │
│   2. Get user's language preference                                  │
│      • Query: await get_lang(message.chat.id)                        │
│      • Load language strings: get_string(language)                   │
│      • Result: _ = {"start_2": "Welcome...", ...}                    │
│                                                                       │
│   3. Pass control to handler with language strings                   │
└────────────┬─────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 6: Command Handler Execution                                    │
│ File: NinjaSecret/plugins/bot/start.py                               │
│                                                                       │
│ async def start_pm(client, message: Message, _):                     │
│                                                                       │
│   A. Database Operations:                                            │
│      • await add_served_user(message.from_user.id)                   │
│      • await upsert_user({user_id, username, ...})                   │
│                                                                       │
│   B. Send welcome animation:                                         │
│      • await message.react("❤")                                      │
│      • Send loading messages                                         │
│                                                                       │
│   C. Build response:                                                 │
│      • Get user's photo or use default                               │
│      • Create inline keyboard: InlineKeyboardMarkup(out)             │
│      • Send photo with caption: _["start_2"]                         │
└────────────┬─────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 7: Optional Logging                                             │
│                                                                       │
│ if await is_on_off(config.LOG):                                      │
│     await app.send_message(                                          │
│         config.LOG_GROUP_ID,                                         │
│         "User X started the bot..."                                  │
│     )                                                                 │
└────────────┬─────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 8: Response Delivery                                            │
│ • Pyrogram sends response to Telegram                                │
│ • Telegram delivers to user                                          │
│ • User sees welcome message with photo and buttons                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Plugin Loading Sequence

### How Plugins are Auto-Discovered and Loaded

```
┌──────────────────────────────────────────────────────────────────┐
│ Bot Startup (__main__.py)                                        │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Import Plugin Index                                      │
│ from NinjaSecret.plugins import ALL_MODULES                      │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Plugin Discovery (plugins/__init__.py)                   │
│                                                                   │
│ def __list_all_modules():                                        │
│     work_dir = dirname(__file__)                                 │
│     # work_dir = "NinjaSecret/plugins"                           │
│                                                                   │
│     mod_paths = glob.glob(work_dir + "/*/*.py")                  │
│     # Finds:                                                     │
│     #   NinjaSecret/plugins/bot/start.py                         │
│     #   NinjaSecret/plugins/sudo/sudoers.py                      │
│     #   NinjaSecret/plugins/tools/id.py                          │
│     #   ... and more                                             │
│                                                                   │
│     # Convert paths to module names:                             │
│     all_modules = [                                              │
│         ".bot.start",                                            │
│         ".sudo.sudoers",                                         │
│         ".tools.id",                                             │
│         ...                                                      │
│     ]                                                            │
│                                                                   │
│ ALL_MODULES = sorted(__list_all_modules())                       │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: Dynamic Import Loop                                      │
│                                                                   │
│ for all_module in ALL_MODULES:                                   │
│     # all_module = ".bot.start"                                  │
│     importlib.import_module("NinjaSecret.plugins" + all_module)  │
│     # Imports: NinjaSecret.plugins.bot.start                     │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 4: Plugin Module Execution                                  │
│ File: NinjaSecret/plugins/bot/start.py                           │
│                                                                   │
│ When imported, decorators are evaluated:                         │
│                                                                   │
│ @app.on_message(filters.command("start") & ...)                  │
│ async def start_pm(client, message, _):                          │
│     ...                                                          │
│                                                                   │
│ This registers the handler with Pyrogram's dispatcher            │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 5: Handler Registration                                     │
│                                                                   │
│ Pyrogram internal:                                               │
│   handlers = {                                                   │
│     "message": [                                                 │
│       {                                                          │
│         "filters": filters.command("start") & ...,               │
│         "callback": start_pm,                                    │
│         "group": 0                                               │
│       },                                                         │
│       ...                                                        │
│     ]                                                            │
│   }                                                              │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Result: All Commands Ready                                       │
│                                                                   │
│ Bot now responds to:                                             │
│   • /start    → NinjaSecret/plugins/bot/start.py                 │
│   • /id       → NinjaSecret/plugins/tools/id.py                  │
│   • /sudolist → NinjaSecret/plugins/sudo/sudoers.py              │
│   • /logger   → NinjaSecret/plugins/sudo/logger.py               │
│   • ... and all other registered commands                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Database Interaction Flow

### Example: `/sudolist` Command with Database

```
┌──────────────────────────────────────────────────────────────────┐
│ User sends: /sudolist                                            │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Command Handler Triggered                                        │
│ File: NinjaSecret/plugins/sudo/sudoers.py                        │
│                                                                   │
│ @app.on_message(filters.command(["sudolist", ...]))              │
│ @language                                                        │
│ async def sudoers_list(client, message, _):                      │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Check User Permission                                            │
│                                                                   │
│ if message.from_user.id not in SUDOERS:                          │
│     # Non-sudo user                                              │
│     return "Show owner only"                                     │
│                                                                   │
│ # User is sudo, continue...                                      │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Query 1: Get Owner Info from Telegram                            │
│                                                                   │
│ user = await app.get_users(OWNER_ID)                             │
│ # Telegram API call                                              │
│                                                                   │
│ Result:                                                          │
│   user.id = 6153949909                                           │
│   user.first_name = "Owner Name"                                 │
│   user.mention = "@ownername"                                    │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Build Response: Owner Section                                    │
│                                                                   │
│ text = "💔 Sudo Users List:\n"                                   │
│ text += f"1➤ {user.mention}\n"                                   │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Loop Through SUDOERS (In-Memory)                                 │
│                                                                   │
│ SUDOERS = {6153949909, 1234567890, 9876543210}                   │
│ # Loaded from MongoDB at startup                                 │
│                                                                   │
│ for user_id in SUDOERS:                                          │
│     if user_id != OWNER_ID:  # Skip owner                        │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Query 2-N: Get Each Sudo User from Telegram                      │
│                                                                   │
│ For user_id = 1234567890:                                        │
│   user = await app.get_users(1234567890)                         │
│   # Telegram API call                                            │
│                                                                   │
│ For user_id = 9876543210:                                        │
│   user = await app.get_users(9876543210)                         │
│   # Telegram API call                                            │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Build Response: Sudo Users Section                               │
│                                                                   │
│ text += "\n✨ Other Sudo Users:\n"                               │
│ text += "1➤ @user1\n"                                            │
│ text += "2➤ @user2\n"                                            │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Send Response                                                     │
│                                                                   │
│ await message.reply_text(text, reply_markup=close_markup(_))     │
│                                                                   │
│ User sees:                                                       │
│   💔 Sudo Users List:                                            │
│   1➤ @owner                                                      │
│                                                                   │
│   ✨ Other Sudo Users:                                           │
│   1➤ @user1                                                      │
│   2➤ @user2                                                      │
│                                                                   │
│   [✯ ᴄʟᴏsᴇ ✯]                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### How SUDOERS is Loaded at Startup

```
┌──────────────────────────────────────────────────────────────────┐
│ Bot Startup: NinjaSecret/__main__.py                             │
│                                                                   │
│ async def init():                                                │
│     await sudo()  # Load sudo users                              │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Function: sudo() in NinjaSecret/misc.py                          │
│                                                                   │
│ async def sudo():                                                │
│     global SUDOERS                                               │
│                                                                   │
│     # Add owner                                                  │
│     SUDOERS.add(config.OWNER_ID)                                 │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ MongoDB Query                                                     │
│                                                                   │
│ sudoersdb = mongodb.sudoers                                      │
│ sudoers = await sudoersdb.find_one({"sudo": "sudo"})             │
│                                                                   │
│ MongoDB Document Structure:                                      │
│ {                                                                │
│   "_id": ObjectId("..."),                                        │
│   "sudo": "sudo",                                                │
│   "sudoers": [6153949909, 1234567890, 9876543210]                │
│ }                                                                │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Load into Memory                                                 │
│                                                                   │
│ sudoers = sudoers["sudoers"]  # [6153949909, 1234567890, ...]    │
│                                                                   │
│ for user_id in sudoers:                                          │
│     SUDOERS.add(user_id)                                         │
│                                                                   │
│ Result:                                                          │
│   SUDOERS = filters.user([6153949909, 1234567890, 9876543210])   │
│   # Can be used directly in filters                              │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Ready for Use                                                     │
│                                                                   │
│ Commands can now use:                                            │
│   @app.on_message(filters.command("restart") & SUDOERS)          │
│   # Only sudo users can execute                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Specific Command Flows

### Flow 1: `/id` Command (Simple, No Database)

```
User: "/id"
   │
   ▼
Pyrogram: Match filters.command("id")
   │
   ▼
Handler: ids(_, message)
   │
   ├─► Check if reply_to_message exists
   │   │
   │   ├─► YES: Get replied user's ID
   │   │   └─► Send: "User X ID is: 123456"
   │   │
   │   └─► NO: Get current chat ID
   │       └─► Send: "This group's ID is: -100123456"
   │
   └─► Add close button
       └─► Done
```

### Flow 2: `/logger` Command (Database Write)

```
User: "/logger enable"
   │
   ▼
Pyrogram: Match filters.command("logger") & SUDOERS
   │
   ▼
@language Decorator
   │
   ├─► Check maintenance mode
   │
   └─► Load language strings
       │
       ▼
Handler: logger(client, message, _)
   │
   ├─► Parse command: ["logger", "enable"]
   │
   ├─► state = "enable"
   │
   ▼
MongoDB Write: add_on(2)
   │
   ├─► Delete document: {"on_off": 2}
   │   (Absence means enabled)
   │
   └─► Success
       │
       ▼
Send Response: "Logging enabled ✅"
   │
   └─► Done
```

### Flow 3: `/start` Command (Complex, Multiple Operations)

```
User: "/start" in private chat
   │
   ▼
Pyrogram: Match filters.command("start") & filters.private & ~BANNED_USERS
   │
   ▼
@LanguageStart Decorator
   │
   └─► Load language strings: _
       │
       ▼
Handler: start_pm(client, message, _)
   │
   ├─► MongoDB Write 1: add_served_user(user_id)
   │   └─► Collection: usersdb
   │
   ├─► MongoDB Write 2: upsert_user({user_id, username, ...})
   │   └─► Collection: whisperdb (users)
   │
   ├─► Send Animation
   │   ├─► React with ❤
   │   ├─► Send loading messages (6 edits)
   │   └─► Delete loading message
   │
   ├─► Get User Photo
   │   ├─► Try: download_media(user.photo)
   │   └─► Fallback: "assets/nodp.png"
   │
   ├─► Build Inline Keyboard
   │   └─► private_panel(_)
   │
   ├─► Send Welcome Message
   │   ├─► Photo: user photo or default
   │   ├─► Caption: _["start_2"]
   │   └─► Buttons: Help, Stats, Settings, etc.
   │
   └─► Optional Logging
       │
       ├─► Check: await is_on_off(config.LOG)
       │
       └─► If enabled:
           └─► Send to LOG_GROUP_ID:
               "User X started the bot\nID: 123456"
```

### Flow 4: Whisper Inline Query (Advanced)

```
User: Types "@botname secret message @target" in any chat
   │
   ▼
Telegram: Sends InlineQuery to bot
   │
   ▼
Pyrogram: @app.on_inline_query()
   │
   ▼
Handler: inline_query_handler(client, query)
   │
   ├─► Parse Query
   │   ├─► Message: "secret message"
   │   ├─► Target: "@target"
   │   └─► Modifiers: None
   │
   ├─► Generate Whisper ID
   │   └─► whisper_id = uuid.uuid4()
   │
   ├─► Store in Pending Cache
   │   └─► pending_whispers[whisper_id] = {data}
   │       (Not in DB yet)
   │
   ├─► Create Inline Result
   │   ├─► Title: "🥷 Send secret to @target"
   │   ├─► Description: "Tap to send"
   │   ├─► Message: "🥷 Secret Message"
   │   └─► Button: "👁 Reveal Secret"
   │
   └─► Send Results
       └─► await query.answer([result])
           │
           ▼
User sees inline result and taps to send
   │
   ▼
Telegram: Sends ChosenInlineResult
   │
   ▼
Pyrogram: @app.on_chosen_inline_result()
   │
   ▼
Handler: chosen_handler(client, result)
   │
   ├─► Get from pending cache
   │   └─► data = pending_whispers[whisper_id]
   │
   ├─► MongoDB Write: store_whisper(data)
   │   └─► Collection: whisperdb
   │
   ├─► Attach inline_message_id
   │   └─► For future edits/deletes
   │
   └─► Update Stats
       ├─► Increment sender's whisper count
       └─► Check achievements
           │
           └─► Done!

Later: Target clicks "👁 Reveal Secret" button
   │
   ▼
Telegram: Sends CallbackQuery
   │
   ▼
Pyrogram: @app.on_callback_query(filters.regex("^reveal_"))
   │
   ▼
Handler: reveal_callback(client, callback)
   │
   ├─► Parse: whisper_id from callback.data
   │
   ├─► MongoDB Read: get_whisper(whisper_id)
   │
   ├─► Check Permission
   │   ├─► Is user the target? ✓
   │   └─► Is user the sender? ✓
   │
   ├─► Show Secret
   │   └─► callback.answer("secret message", show_alert=True)
   │
   └─► Optional: Mark as read / Burn after reading
       └─► MongoDB Update: mark_whisper_read()
```

---

## Summary

These diagrams show:

1. **Overall Architecture**: How main.py, bot, plugins, and database fit together
2. **Command Processing**: The complete journey from user input to response
3. **Plugin Loading**: How the auto-discovery system works
4. **Database Flow**: How commands interact with MongoDB
5. **Specific Commands**: Detailed flows for /id, /logger, /start, and whisper

The modular architecture allows:
- Easy addition of new commands (just drop a file in plugins/)
- Clear separation of concerns (core, plugins, utils, database)
- Reusable decorators for common functionality
- Scalable database operations
- Comprehensive logging and monitoring

---

*Companion document to ARCHITECTURE.md*
