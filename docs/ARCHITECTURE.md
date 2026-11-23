# NinjaSecret Bot Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [Command Handling Flow](#command-handling-flow)
3. [Plugin System Architecture](#plugin-system-architecture)
4. [Specific Command Implementations](#specific-command-implementations)
5. [Database Integration](#database-integration)
6. [Logging System](#logging-system)
7. [File Structure](#file-structure)
8. [How to Build Similar Bots](#how-to-build-similar-bots)

---

## Overview

NinjaSecret is a Telegram bot built using the **Pyrogram** framework with a modular, plugin-based architecture. The bot is designed to be scalable, maintainable, and easy to extend with new features.

### Core Technologies
- **Pyrogram**: Modern Telegram Bot framework (async)
- **MongoDB**: Database for storing user data, whispers, stats
- **FastAPI**: Health check endpoints for deployment platforms
- **Motor**: Async MongoDB driver

---

## Command Handling Flow

### 1. Entry Point: `main.py`
```
User → Telegram → Pyrogram Client → Plugin Handler → Command Execution
```

**File**: `/main.py`

The main wrapper starts the bot in a separate thread:
```python
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
```

### 2. Bot Initialization: `NinjaSecret/__main__.py`

The actual bot initialization happens here:

```python
async def init():
    # 1. Load sudo users from database
    await sudo()
    
    # 2. Load banned users
    users = await get_gbanned()
    for user_id in users:
        BANNED_USERS.add(user_id)
    
    # 3. Start the bot client
    await app.start()
    
    # 4. Dynamically import all plugin modules
    for all_module in ALL_MODULES:
        importlib.import_module("NinjaSecret.plugins" + all_module)
    
    # 5. Keep bot running
    await idle()
```

**Key Points:**
- Bot starts with retry mechanism for flood wait errors
- Loads all modules dynamically
- Initializes database connections
- Starts memory cleanup tasks

### 3. Plugin Discovery: `NinjaSecret/plugins/__init__.py`

This module automatically discovers all plugin files:

```python
def __list_all_modules():
    work_dir = dirname(__file__)
    mod_paths = glob.glob(work_dir + "/*/*.py")
    
    all_modules = [
        (((f.replace(work_dir, "")).replace("/", "."))[:-3])
        for f in mod_paths
        if isfile(f) and f.endswith(".py") and not f.endswith("__init__.py")
    ]
    
    return all_modules

ALL_MODULES = sorted(__list_all_modules())
```

**What this does:**
- Scans all subdirectories in `plugins/`
- Finds all `.py` files (except `__init__.py`)
- Converts paths to module names (e.g., `.bot.start` → `NinjaSecret.plugins.bot.start`)
- Returns a list of module paths for dynamic import

### 4. Command Registration

Each plugin file registers its own commands using Pyrogram decorators:

```python
@app.on_message(filters.command("start") & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    # Command logic here
    pass
```

**How it works:**
1. `@app.on_message()` - Pyrogram decorator that registers message handler
2. `filters.command("start")` - Only triggers for `/start` command
3. `filters.private` - Only in private chats
4. `~BANNED_USERS` - Exclude banned users
5. `@LanguageStart` - Custom decorator for language support

### 5. User Input Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User sends message: "/start"                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Telegram sends update to bot                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Pyrogram Client (app) receives message                   │
│    File: NinjaSecret/core/bot.py (Hotty class)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Pyrogram checks registered handlers                      │
│    - Matches filters (command, chat type, banned users)     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Decorators execute (middleware pattern)                  │
│    a. @LanguageStart - Gets user's language                 │
│    b. Checks maintenance mode                               │
│    c. May delete command message if enabled                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Command function executes                                │
│    - Database operations                                    │
│    - Business logic                                         │
│    - Send response to user                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Optional logging to LOG_GROUP_ID                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Plugin System Architecture

### Plugin Organization

```
NinjaSecret/plugins/
├── __init__.py          # Auto-discovers all plugins
├── admins/              # Admin management commands
│   ├── auth.py         # /auth, /unauth, /authlist
│   └── chat_control.py # Chat management
├── bot/                 # Core bot commands
│   ├── start.py        # /start command
│   └── help.py         # /help command
├── misc/                # Miscellaneous features
│   ├── broadcast.py    # Broadcasting
│   └── info.py         # User/chat info
├── sudo/                # Sudo/owner commands
│   ├── logger.py       # /logger command
│   ├── sudoers.py      # /sudolist, /addsudo, /delsudo
│   ├── gban.py         # Global ban
│   └── restart.py      # Bot restart
├── tools/               # Utility commands
│   ├── id.py           # /id command
│   ├── ping.py         # /ping command
│   └── stats.py        # /stats command
└── whisper/             # Secret message features
    ├── inline_handler.py    # Inline query handling
    ├── callbacks.py         # Button callbacks
    └── cleanup_task.py      # Background cleanup
```

### Plugin Structure Pattern

Each plugin follows this pattern:

```python
# 1. Import required modules
from pyrogram import filters
from pyrogram.types import Message
from NinjaSecret import app
from NinjaSecret.utils.decorators.language import language

# 2. Register command handler with decorators
@app.on_message(filters.command("commandname") & ~BANNED_USERS)
@language  # Optional: adds language support
async def command_handler(client, message: Message, _):
    """
    Handle /commandname
    
    Args:
        client: Bot client instance
        message: Incoming message object
        _: Language strings (from @language decorator)
    """
    # 3. Implement command logic
    await message.reply_text("Response")
```

### Key Plugin Components

#### 1. Filters
Pyrogram filters determine when a handler should trigger:

```python
# Command filter
filters.command("start")  # Matches /start

# Chat type filters
filters.private           # Only private chats
filters.group            # Only groups
filters.channel          # Only channels

# User filters
~BANNED_USERS            # Exclude banned users
SUDOERS                  # Only sudo users

# Combined filters
filters.command("ping") & filters.group & ~BANNED_USERS
```

#### 2. Decorators
Custom decorators add middleware functionality:

**`@language`** - Language support:
```python
def language(mystic):
    async def wrapper(_, message, **kwargs):
        # Check maintenance mode
        if await is_maintenance() is False:
            if message.from_user.id not in SUDOERS:
                return await message.reply_text("Under maintenance")
        
        # Delete command if cleaning enabled
        if await should_delete_command(message.chat.id):
            await message.delete()
        
        # Get user's language
        language = await get_lang(message.chat.id)
        language = get_string(language)
        
        # Call original function with language strings
        return await mystic(_, message, language)
    
    return wrapper
```

**`@AdminActual`** - Admin check:
```python
def AdminActual(mystic):
    async def wrapper(_, message):
        # Check if user is admin
        chat = message.chat
        user = message.from_user
        
        if user.id in SUDOERS:
            return await mystic(_, message)
        
        member = await chat.get_member(user.id)
        if member.status in ["creator", "administrator"]:
            return await mystic(_, message)
        
        await message.reply_text("You must be admin")
    
    return wrapper
```

---

## Specific Command Implementations

### 1. `/id` Command

**File**: `NinjaSecret/plugins/tools/id.py`

**Purpose**: Get user ID or chat ID

```python
@app.on_message(filters.command("id"))
def ids(_, message):
    reply = message.reply_to_message
    
    if reply:
        # User replied to someone - show that user's ID
        button = InlineKeyboardButton("✯ ᴄʟᴏsᴇ ✯", callback_data="close")
        markup = InlineKeyboardMarkup([[button]])
        message.reply_text(
            f"User {reply.from_user.first_name} ID is : {reply.from_user.id}",
            reply_markup=markup
        )
    else:
        # No reply - show chat/group ID
        button = InlineKeyboardButton("✯ ᴄʟᴏsᴇ ✯", callback_data="close")
        markup = InlineKeyboardMarkup([[button]])
        message.reply(
           f"ᴛʜɪs ɢʀᴏᴜᴩ's ɪᴅ ɪs: {message.chat.id}",
           reply_markup=markup
        )
```

**Flow**:
1. User sends `/id` or replies to a message with `/id`
2. Pyrogram matches `filters.command("id")`
3. No decorators - executes directly
4. Checks if message is a reply
   - If yes: Shows replied user's ID
   - If no: Shows current chat ID
5. Adds a close button using InlineKeyboardMarkup

**Database**: None (no database interaction)

**Logging**: None (no logging)

### 2. `/sudolist` Command

**File**: `NinjaSecret/plugins/sudo/sudoers.py`

**Purpose**: Show list of sudo users (bot administrators)

```python
@app.on_message(filters.command(["sudolist", "listsudo", "sudoers"]) & ~BANNED_USERS)
@language
async def sudoers_list(client, message: Message, _):
    # Non-sudo users see only owner
    if message.from_user.id not in SUDOERS:
        return await message.reply_text(
            "💔 <b>ᴏᴡɴᴇʀ:</b>\n1➤ <a href='https://t.me/venopyx'>Owner</a>",
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML
        )
    
    # Build sudo list
    text = _["sudo_5"]  # Header from language strings
    
    # Add owner first
    user = await app.get_users(OWNER_ID)
    user = user.first_name if not user.mention else user.mention
    text += f"1➤ {user}\n"
    
    # Add other sudo users
    count = 0
    smex = 0
    for user_id in SUDOERS:
        if user_id != OWNER_ID:
            try:
                user = await app.get_users(user_id)
                user = user.first_name if not user.mention else user.mention
                if smex == 0:
                    smex += 1
                    text += _["sudo_6"]  # "Other Sudo Users:"
                count += 1
                text += f"{count}➤ {user}\n"
            except:
                continue
    
    # Send response
    if not text:
        await message.reply_text(_["sudo_7"])  # "No sudo users"
    else:
        await message.reply_text(text, reply_markup=close_markup(_))
```

**Flow**:
1. User sends `/sudolist`, `/listsudo`, or `/sudoers`
2. Pyrogram matches command filter + banned users filter
3. `@language` decorator:
   - Checks maintenance mode
   - Deletes command if cleaning enabled
   - Loads language strings
4. Function checks if user is sudo:
   - Non-sudo: Show only owner
   - Sudo: Show full list
5. Fetches owner info from Telegram API
6. Iterates through SUDOERS set
7. Fetches each user's info from Telegram API
8. Builds formatted response
9. Sends with close button

**Database Interaction**:
- Reads from `SUDOERS` global set (loaded from MongoDB at startup)
- MongoDB collection: `mongodb.sudoers`
- Structure: `{"sudo": "sudo", "sudoers": [id1, id2, ...]}`

**Logging**: None for listing (only for add/remove operations)

### 3. `/logger` Command

**File**: `NinjaSecret/plugins/sudo/logger.py`

**Purpose**: Enable/disable activity logging to log group

```python
@app.on_message(filters.command(["logger"]) & SUDOERS)
@language
async def logger(client, message, _):
    usage = _["log_1"]  # Usage instructions
    
    # Check command syntax
    if len(message.command) != 2:
        return await message.reply_text(usage)
    
    # Get enable/disable state
    state = message.text.split(None, 1)[1].strip().lower()
    
    if state == "enable":
        # Enable logging
        await add_on(2)  # 2 is the logging feature ID
        await message.reply_text(_["log_2"])  # "Logging enabled"
    elif state == "disable":
        # Disable logging
        await add_off(2)
        await message.reply_text(_["log_3"])  # "Logging disabled"
    else:
        await message.reply_text(usage)
```

**Flow**:
1. User sends `/logger enable` or `/logger disable`
2. Pyrogram matches command filter + SUDOERS filter
3. `@language` decorator processes
4. Parses command arguments
5. Calls database function to enable/disable logging
6. Sends confirmation message

**Database Interaction**:

**File**: `NinjaSecret/utils/database.py`

```python
# Check if logging is enabled
async def is_on_off(on_off: int) -> bool:
    onoff = await onoffdb.find_one({"on_off": on_off})
    if not onoff:
        return True  # Default enabled
    return False

# Enable logging
async def add_on(on_off: int):
    await onoffdb.delete_one({"on_off": on_off})

# Disable logging
async def add_off(on_off: int):
    await onoffdb.insert_one({"on_off": on_off})
```

**MongoDB Collection**: `mongodb.onoffper`
**Structure**: `{"on_off": 2}` (presence = disabled, absence = enabled)

**Logging Usage Example** (from `/start` command):

```python
# After handling /start command
if await is_on_off(config.LOG):
    sender_id = message.from_user.id
    sender_name = message.from_user.first_name
    await app.send_message(
        config.LOG_GROUP_ID,
        f"{message.from_user.mention} started the bot.\n"
        f"User ID: {sender_id}\nUsername: {sender_name}"
    )
```

---

## Database Integration

### Database Architecture

**File**: `NinjaSecret/core/mongo.py`

```python
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import config

# Async client (for async operations)
mongodb = AsyncIOMotorClient(config.MONGO_DB_URI)
mongodb = mongodb.NinjaSecret

# Sync client (for sync operations)
pymongodb = MongoClient(config.MONGO_DB_URI)
pymongodb = pymongodb.NinjaSecret
```

### Database Collections

The bot uses multiple MongoDB collections:

**File**: `NinjaSecret/utils/database.py`

```python
# Collection references
authdb = mongodb.adminauth           # Authorized users
authuserdb = mongodb.authuser        # Auth user data
autoenddb = mongodb.autoend          # Auto-end settings
blacklist_chatdb = mongodb.blacklistChat  # Blacklisted chats
blockeddb = mongodb.blockedusers     # Blocked users
chatsdb = mongodb.chats              # Served chats
gbansdb = mongodb.gban               # Global bans
langdb = mongodb.language            # Language preferences
onoffdb = mongodb.onoffper           # Feature toggles
sudoersdb = mongodb.sudoers          # Sudo users
usersdb = mongodb.tgusersdb          # Telegram users
```

### Whisper Database

**File**: `NinjaSecret/mongo/whisperdb.py`

```python
from NinjaSecret.core.mongo import mongodb

# Whisper-specific collections
whisperdb = mongodb.whispers                # Secret messages
whisper_stats = mongodb.whisper_stats       # User statistics
whisper_achievements = mongodb.whisper_achievements  # Achievements
```

### Database Operations Pattern

#### 1. Reading Data

```python
# Get single document
async def get_sudo_users():
    sudoers = await sudoersdb.find_one({"sudo": "sudo"})
    return [] if not sudoers else sudoers["sudoers"]

# Get multiple documents
async def get_banned_users():
    users = []
    async for user in blockeddb.find({"user_id": {"$gt": 0}}):
        users.append(user["user_id"])
    return users
```

#### 2. Writing Data

```python
# Insert/Update (upsert)
async def add_sudo(user_id: int):
    sudoers = await sudoersdb.find_one({"sudo": "sudo"})
    sudoers = [] if not sudoers else sudoers["sudoers"]
    
    sudoers.append(user_id)
    
    await sudoersdb.update_one(
        {"sudo": "sudo"},
        {"$set": {"sudoers": sudoers}},
        upsert=True
    )
    return True
```

#### 3. Deleting Data

```python
# Delete specific document
async def remove_sudo(user_id: int):
    sudoers = await sudoersdb.find_one({"sudo": "sudo"})
    if not sudoers:
        return False
    
    sudoers = sudoers["sudoers"]
    if user_id in sudoers:
        sudoers.remove(user_id)
        await sudoersdb.update_one(
            {"sudo": "sudo"},
            {"$set": {"sudoers": sudoers}}
        )
        return True
    return False
```

### Whisper Storage Example

**File**: `NinjaSecret/mongo/whisperdb.py`

```python
async def store_whisper(data: Dict) -> str:
    """Store a secret message"""
    whisper_data = {
        "whisper_id": data["whisper_id"],
        "inline_message_id": data.get("inline_message_id"),
        "content": data["content"],
        "sender_id": data["sender_id"],
        "target_id": data.get("target_id"),
        "created_at": datetime.utcnow(),
        "read_at": None,
        "status": "active"
    }
    
    # Add special features
    if data.get("modifiers"):
        settings = {}
        modifiers = data["modifiers"]
        
        # Timer expiration
        if modifiers.get("timer"):
            expires_at = datetime.utcnow() + timedelta(seconds=modifiers["timer"])
            settings["expires_at"] = expires_at
        
        # Burn after reading
        if modifiers.get("burn_after_reading"):
            settings["burn_after_reading"] = True
        
        if settings:
            whisper_data["settings"] = settings
    
    await whisperdb.insert_one(whisper_data)
    return data["whisper_id"]
```

---

## Logging System

### Logging Architecture

The bot has two types of logging:

### 1. Application Logging (Console/File)

**File**: `NinjaSecret/logging.py`

```python
import logging

def LOGGER(name: str) -> logging.Logger:
    """Get logger instance for module"""
    return logging.getLogger(name)
```

**Usage in code**:

```python
from NinjaSecret.logging import LOGGER

logger = LOGGER(__name__)

logger.info("Bot started successfully")
logger.error(f"Error occurred: {error}")
logger.warning("Warning message")
logger.debug("Debug information")
```

### 2. Activity Logging (Telegram Group)

Activity logs are sent to a configured Telegram group/channel.

**Configuration**: `config.py`

```python
LOG = True  # Enable/disable logging
LOG_GROUP_ID = -1003029976514  # Group to send logs
LOGGER_ID = -1003029976514  # Same as LOG_GROUP_ID
```

**Usage Pattern**:

```python
from NinjaSecret.utils.database import is_on_off
from NinjaSecret import app
import config

# Check if logging is enabled
if await is_on_off(config.LOG):
    await app.send_message(
        config.LOG_GROUP_ID,
        f"User {user.mention} performed action XYZ\n"
        f"User ID: {user.id}\n"
        f"Time: {datetime.now()}"
    )
```

**Examples from codebase**:

1. **Start Command Logging**:
```python
# File: NinjaSecret/plugins/bot/start.py
if await is_on_off(config.LOG):
    return await app.send_message(
        config.LOG_GROUP_ID,
        f"{message.from_user.mention} started bot.\n"
        f"User ID: {sender_id}\n"
        f"User name: {sender_name}"
    )
```

2. **Auto-Promotion Logging**:
```python
# File: NinjaSecret/plugins/bot/start.py
if await is_on_off(config.LOG):
    await app.send_message(
        config.LOG_GROUP_ID,
        f"🔹 Auto-Promotion Log\n\n"
        f"User: {member.mention}\n"
        f"Group: {message.chat.title}\n"
        f"Status: Administrator"
    )
```

### Logging Best Practices

1. **Module-level loggers**:
```python
from NinjaSecret.logging import LOGGER
logger = LOGGER(__name__)
```

2. **Log levels**:
- `logger.info()` - Normal operations
- `logger.warning()` - Warnings
- `logger.error()` - Errors
- `logger.debug()` - Debug info

3. **Activity logging**:
- Check if enabled: `await is_on_off(config.LOG)`
- Send to LOG_GROUP_ID
- Include: user info, action, timestamp

---

## File Structure

```
NinjaSecret/
├── main.py                      # Main wrapper (FastAPI + bot thread)
├── config.py                    # Configuration
├── requirements.txt             # Dependencies
│
├── NinjaSecret/                 # Main bot package
│   ├── __init__.py             # Package initialization
│   ├── __main__.py             # Bot entry point
│   ├── logging.py              # Logging utility
│   ├── misc.py                 # Global variables (SUDOERS, etc.)
│   ├── web_server.py           # Health check server
│   │
│   ├── core/                   # Core functionality
│   │   ├── bot.py             # Bot client (Hotty class)
│   │   ├── mongo.py           # MongoDB connection
│   │   ├── dir.py             # Directory setup
│   │   └── call.py            # Call client
│   │
│   ├── plugins/                # Plugin modules
│   │   ├── __init__.py        # Auto-discovery
│   │   ├── admins/            # Admin commands
│   │   ├── bot/               # Core bot commands
│   │   ├── misc/              # Miscellaneous
│   │   ├── sudo/              # Sudo commands
│   │   ├── tools/             # Utility commands
│   │   └── whisper/           # Secret messages
│   │
│   ├── utils/                  # Utilities
│   │   ├── database.py        # Database operations
│   │   ├── decorators/        # Custom decorators
│   │   │   ├── language.py   # Language support
│   │   │   └── admins.py     # Admin checks
│   │   ├── inline.py          # Inline keyboards
│   │   ├── formatters.py      # Text formatting
│   │   └── whisper_utils.py   # Whisper utilities
│   │
│   ├── mongo/                  # Database models
│   │   └── whisperdb.py       # Whisper database
│   │
│   └── strings/                # Localization
│       └── langs/
│           └── en.yml         # English strings
│
└── strings/                    # Language strings
    └── langs/
        └── en.yml             # English translations
```

---

## How to Build Similar Bots

### Step 1: Setup Project Structure

```bash
mkdir MyBot
cd MyBot

# Create structure
mkdir -p MyBot/{core,plugins,utils,mongo}
touch MyBot/__init__.py MyBot/__main__.py
touch config.py main.py requirements.txt
```

### Step 2: Install Dependencies

```python
# requirements.txt
pyrogram
tgcrypto
motor
python-dotenv
```

```bash
pip install -r requirements.txt
```

### Step 3: Create Configuration

```python
# config.py
from os import getenv
from dotenv import load_dotenv
from pyrogram import filters

load_dotenv()

API_ID = int(getenv("API_ID"))
API_HASH = getenv("API_HASH")
BOT_TOKEN = getenv("BOT_TOKEN")
MONGO_DB_URI = getenv("MONGO_DB_URI")
OWNER_ID = int(getenv("OWNER_ID"))

BANNED_USERS = filters.user()
```

### Step 4: Create Bot Client

```python
# MyBot/core/bot.py
from pyrogram import Client
import config

class BotClient(Client):
    def __init__(self):
        super().__init__(
            name="MyBot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            in_memory=True
        )
    
    async def start(self):
        await super().start()
        print(f"Bot started: @{self.username}")
    
    async def stop(self):
        await super().stop()
        print("Bot stopped")
```

### Step 5: Initialize Bot

```python
# MyBot/__init__.py
from MyBot.core.bot import BotClient

app = BotClient()
```

### Step 6: Create Plugin Auto-Discovery

```python
# MyBot/plugins/__init__.py
import glob
from os.path import dirname, isfile

def __list_all_modules():
    work_dir = dirname(__file__)
    mod_paths = glob.glob(work_dir + "/*/*.py")
    
    all_modules = [
        (((f.replace(work_dir, "")).replace("/", "."))[:-3])
        for f in mod_paths
        if isfile(f) and f.endswith(".py") and not f.endswith("__init__.py")
    ]
    
    return all_modules

ALL_MODULES = sorted(__list_all_modules())
```

### Step 7: Create Your First Plugin

```python
# MyBot/plugins/basic/start.py
from pyrogram import filters
from pyrogram.types import Message
from MyBot import app
import config

@app.on_message(filters.command("start") & ~config.BANNED_USERS)
async def start_command(client, message: Message):
    await message.reply_text(
        f"Hello {message.from_user.mention}!\n"
        f"I'm {client.mention}"
    )
```

### Step 8: Create Main Entry Point

```python
# MyBot/__main__.py
import asyncio
import importlib
from pyrogram import idle
from MyBot import app
from MyBot.plugins import ALL_MODULES

async def main():
    # Start bot
    await app.start()
    
    # Import all plugins
    for module in ALL_MODULES:
        importlib.import_module("MyBot.plugins" + module)
    print(f"Loaded {len(ALL_MODULES)} modules")
    
    # Keep running
    await idle()
    
    # Stop bot
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 9: Run Your Bot

```bash
python -m MyBot
```

### Step 10: Add Database Support

```python
# MyBot/core/mongo.py
from motor.motor_asyncio import AsyncIOMotorClient
import config

mongodb = AsyncIOMotorClient(config.MONGO_DB_URI)
mongodb = mongodb.MyBot
```

```python
# MyBot/utils/database.py
from MyBot.core.mongo import mongodb

usersdb = mongodb.users

async def add_user(user_id: int, username: str):
    await usersdb.update_one(
        {"user_id": user_id},
        {"$set": {"username": username}},
        upsert=True
    )

async def get_user(user_id: int):
    return await usersdb.find_one({"user_id": user_id})
```

### Step 11: Add Custom Decorators

```python
# MyBot/utils/decorators.py
from functools import wraps
import config

def sudo_only(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        if message.from_user.id != config.OWNER_ID:
            return await message.reply_text("Owner only!")
        return await func(client, message, *args, **kwargs)
    return wrapper
```

```python
# Usage in plugin
from MyBot.utils.decorators import sudo_only

@app.on_message(filters.command("restart"))
@sudo_only
async def restart(client, message):
    await message.reply_text("Restarting...")
    # Restart logic
```

### Step 12: Add More Commands

```python
# MyBot/plugins/basic/id.py
from pyrogram import filters
from MyBot import app

@app.on_message(filters.command("id"))
async def id_command(client, message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        await message.reply_text(f"User ID: {user_id}")
    else:
        await message.reply_text(f"Chat ID: {message.chat.id}")
```

```python
# MyBot/plugins/basic/ping.py
from pyrogram import filters
from MyBot import app
from datetime import datetime

@app.on_message(filters.command("ping"))
async def ping_command(client, message):
    start = datetime.now()
    msg = await message.reply_text("Pinging...")
    end = datetime.now()
    ms = (end - start).microseconds / 1000
    await msg.edit_text(f"Pong! `{ms}ms`")
```

---

## Key Takeaways for Building Similar Bots

### 1. **Modular Architecture**
- Separate concerns (core, plugins, utils, database)
- Each plugin is independent
- Easy to add/remove features

### 2. **Plugin Auto-Discovery**
- No need to manually import modules
- Just drop a `.py` file in plugins folder
- Bot automatically loads it on startup

### 3. **Decorator Pattern**
- Use decorators for middleware (auth, language, logging)
- Keeps command handlers clean
- Reusable across multiple commands

### 4. **Filter Composition**
- Combine multiple filters with `&` (AND)
- Negate filters with `~` (NOT)
- Example: `filters.command("start") & filters.private & ~BANNED_USERS`

### 5. **Database Layer**
- Separate database operations from business logic
- Use async/await for non-blocking operations
- MongoDB provides flexibility for dynamic data

### 6. **Configuration Management**
- Store sensitive data in `.env` file
- Load with `python-dotenv`
- Never commit secrets to git

### 7. **Error Handling**
- Use try-except blocks
- Log errors for debugging
- Provide user-friendly error messages

### 8. **Scalability**
- Use async/await throughout
- Motor for async MongoDB
- Multiple workers possible

### 9. **Logging**
- Console logging for developers
- Activity logging to Telegram group
- Different log levels (info, warning, error)

### 10. **User Experience**
- Inline keyboards for interactions
- Reply markup for better UX
- Language support for internationalization

---

## Advanced Features (NinjaSecret Specific)

### 1. Inline Queries
**File**: `NinjaSecret/plugins/whisper/inline_handler.py`

```python
@app.on_inline_query()
async def inline_query_handler(client, query: InlineQuery):
    # Parse query
    text = query.query
    
    # Generate results
    results = []
    result = InlineQueryResultArticle(
        title="Secret Message",
        input_message_content=InputTextMessageContent("🥷"),
        reply_markup=keyboard
    )
    results.append(result)
    
    # Send results
    await query.answer(results, cache_time=0)
```

### 2. Callback Queries
**File**: `NinjaSecret/plugins/whisper/callbacks.py`

```python
@app.on_callback_query(filters.regex("^reveal_"))
async def reveal_callback(client, callback: CallbackQuery):
    # Parse callback data
    whisper_id = callback.data.split("_")[1]
    
    # Check permission
    whisper = await get_whisper(whisper_id)
    if callback.from_user.id != whisper["target_id"]:
        return await callback.answer("Not for you!", show_alert=True)
    
    # Show secret
    await callback.answer(whisper["content"], show_alert=True)
```

### 3. Background Tasks

```python
async def cleanup_task():
    """Background task to clean expired whispers"""
    while True:
        try:
            # Find expired whispers
            expired = await find_expired_whispers()
            
            # Delete them
            for whisper in expired:
                await delete_whisper(whisper["whisper_id"])
            
            # Wait 5 minutes
            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
```

### 4. Retry Mechanism

```python
async def start_bot_with_retry(max_retries=5):
    """Start bot with retry for flood wait errors"""
    for attempt in range(max_retries):
        try:
            await app.start()
            return True
        except Exception as e:
            if "FLOOD_WAIT" in str(e):
                wait_time = extract_wait_time(e)
                await asyncio.sleep(wait_time)
                continue
            raise e
    return False
```

---

## Conclusion

The NinjaSecret bot demonstrates a well-architected, scalable Telegram bot with:

1. **Modular plugin system** - Easy to extend
2. **Decorator pattern** - Clean middleware
3. **Async operations** - Non-blocking I/O
4. **Database integration** - Persistent storage
5. **Comprehensive logging** - Both console and Telegram
6. **Error handling** - Graceful failures
7. **Auto-discovery** - Minimal boilerplate

This architecture can be adapted for any Telegram bot project, from simple utility bots to complex multi-feature bots.

### Next Steps for Developers

1. Study the plugin structure
2. Understand the decorator pattern
3. Learn Pyrogram filters
4. Practice with MongoDB
5. Build your own plugins
6. Extend with custom features

### Resources

- [Pyrogram Documentation](https://docs.pyrogram.org/)
- [MongoDB Motor Documentation](https://motor.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Python Async/Await](https://docs.python.org/3/library/asyncio.html)

---

*This documentation was created to help developers understand and build similar plugin-based, scalable Telegram bots.*
