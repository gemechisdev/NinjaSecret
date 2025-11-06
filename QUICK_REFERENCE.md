# NinjaSecret Quick Reference Guide

**Quick reference for developers wanting to understand or build similar Telegram bots**

📚 **Full Documentation**: See [ARCHITECTURE.md](ARCHITECTURE.md) and [COMMAND_FLOW_DIAGRAMS.md](COMMAND_FLOW_DIAGRAMS.md)

---

## 🎯 Key Concepts at a Glance

### Bot Entry Point
```
main.py (wrapper)
  └─> NinjaSecret/__main__.py (bot initialization)
      └─> Loads all plugins from NinjaSecret/plugins/
```

### Command Registration (Any Plugin)
```python
from NinjaSecret import app
from pyrogram import filters

@app.on_message(filters.command("mycommand") & ~BANNED_USERS)
async def my_handler(client, message):
    await message.reply_text("Response")
```

### Plugin Auto-Discovery
Drop any `.py` file in `NinjaSecret/plugins/*/` and it's automatically loaded at startup!

---

## 📂 Directory Structure

```
NinjaSecret/
├── main.py                    # Wrapper (FastAPI + bot thread)
├── NinjaSecret/
│   ├── __main__.py           # Bot entry point
│   ├── core/
│   │   └── bot.py            # Pyrogram client
│   ├── plugins/              # ⭐ Add commands here
│   │   ├── __init__.py       # Auto-discovery magic
│   │   ├── bot/             # /start, /help
│   │   ├── sudo/            # /sudolist, /logger
│   │   ├── tools/           # /id, /ping
│   │   └── [your_plugin]/   # Add your own!
│   ├── utils/
│   │   ├── database.py      # DB operations
│   │   └── decorators/      # Middleware
│   └── mongo/
│       └── whisperdb.py     # Database models
```

---

## 🚀 Quick Start: Add Your First Command

### Step 1: Create Plugin File
```bash
touch NinjaSecret/plugins/tools/mycommand.py
```

### Step 2: Write Handler
```python
# NinjaSecret/plugins/tools/mycommand.py
from NinjaSecret import app
from pyrogram import filters
from pyrogram.types import Message

@app.on_message(filters.command("mycommand"))
async def my_command(client, message: Message):
    await message.reply_text(f"Hello {message.from_user.first_name}!")
```

### Step 3: Restart Bot
```bash
python -m NinjaSecret
```

✅ Done! Bot now responds to `/mycommand`

---

## 🎨 Common Patterns

### 1. Command with Filters
```python
@app.on_message(
    filters.command("admin") & 
    filters.group & 
    ~BANNED_USERS
)
async def admin_command(client, message):
    # Only works in groups, not for banned users
    pass
```

### 2. With Language Support
```python
from NinjaSecret.utils.decorators.language import language

@app.on_message(filters.command("hello"))
@language
async def hello(client, message, _):
    # _ contains language strings
    await message.reply_text(_["hello_message"])
```

### 3. With Admin Check
```python
from NinjaSecret.utils.decorators import AdminActual

@app.on_message(filters.command("kick"))
@AdminActual
async def kick_user(client, message, _):
    # Only admins can execute
    pass
```

### 4. With Database
```python
from NinjaSecret.utils.database import add_served_user

@app.on_message(filters.command("register"))
async def register(client, message):
    await add_served_user(message.from_user.id)
    await message.reply_text("Registered!")
```

### 5. With Inline Keyboard
```python
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

@app.on_message(filters.command("menu"))
async def menu(client, message):
    buttons = [
        [InlineKeyboardButton("Option 1", callback_data="opt1")],
        [InlineKeyboardButton("Option 2", callback_data="opt2")]
    ]
    await message.reply_text(
        "Choose an option:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
```

---

## 📊 Database Operations

### Read
```python
from NinjaSecret.core.mongo import mongodb

usersdb = mongodb.users
user = await usersdb.find_one({"user_id": 123456})
```

### Write
```python
await usersdb.update_one(
    {"user_id": 123456},
    {"$set": {"username": "john"}},
    upsert=True
)
```

### Delete
```python
await usersdb.delete_one({"user_id": 123456})
```

---

## 🔍 Command Examples from Codebase

### `/id` - Simple Command
**File**: `NinjaSecret/plugins/tools/id.py`
```python
@app.on_message(filters.command("id"))
def ids(_, message):
    if message.reply_to_message:
        # Show replied user's ID
        user_id = message.reply_to_message.from_user.id
        message.reply_text(f"User ID: {user_id}")
    else:
        # Show chat ID
        message.reply_text(f"Chat ID: {message.chat.id}")
```

### `/sudolist` - Database Read
**File**: `NinjaSecret/plugins/sudo/sudoers.py`
```python
@app.on_message(filters.command("sudolist") & ~BANNED_USERS)
@language
async def sudoers_list(client, message, _):
    # Check permission
    if message.from_user.id not in SUDOERS:
        return await message.reply_text("Owner only")
    
    # Build list
    text = "Sudo Users:\n"
    for user_id in SUDOERS:
        user = await app.get_users(user_id)
        text += f"• {user.mention}\n"
    
    await message.reply_text(text)
```

### `/logger` - Database Write
**File**: `NinjaSecret/plugins/sudo/logger.py`
```python
@app.on_message(filters.command("logger") & SUDOERS)
@language
async def logger(client, message, _):
    state = message.text.split()[1]  # "enable" or "disable"
    
    if state == "enable":
        await add_on(2)  # Enable logging
        await message.reply_text("Logging enabled")
    elif state == "disable":
        await add_off(2)  # Disable logging
        await message.reply_text("Logging disabled")
```

---

## 🎭 Decorators Explained

### `@language`
- Checks maintenance mode
- Loads user's language preferences
- May delete command message if cleaning enabled
- Passes `_` (language strings) to handler

### `@AdminActual`
- Checks if user is admin or sudo
- Blocks non-admins
- Used for admin-only commands

### `@LanguageStart`
- Like `@language` but without maintenance check
- Used for /start command

---

## 🗄️ MongoDB Collections Used

| Collection | Purpose |
|------------|---------|
| `sudoers` | Sudo user IDs |
| `users` | Served user data |
| `chats` | Served chat data |
| `gban` | Global bans |
| `onoffper` | Feature toggles |
| `whispers` | Secret messages |
| `whisper_stats` | User statistics |
| `language` | User language prefs |

---

## 📝 Logging

### Console Logging
```python
from NinjaSecret.logging import LOGGER

logger = LOGGER(__name__)
logger.info("Something happened")
logger.error(f"Error: {e}")
```

### Telegram Logging
```python
from NinjaSecret.utils.database import is_on_off
import config

if await is_on_off(config.LOG):
    await app.send_message(
        config.LOG_GROUP_ID,
        f"User {user.mention} did something"
    )
```

---

## 🔧 Common Filters

```python
filters.command("start")           # /start command
filters.private                    # Private chats only
filters.group                      # Groups only
filters.channel                    # Channels only
~BANNED_USERS                      # Exclude banned users
SUDOERS                            # Only sudo users
filters.reply                      # Only if replying to message
filters.text                       # Only text messages
filters.photo                      # Only photos
```

### Combine Filters
```python
filters.command("ban") & filters.group & ~BANNED_USERS
# Command "ban" in groups, not for banned users
```

---

## 🎯 Best Practices

1. **One command per file** - Keeps things organized
2. **Use decorators** - Don't repeat auth/language code
3. **Handle errors** - Use try-except blocks
4. **Check permissions** - Verify user can execute command
5. **Async/await** - Always use async for I/O operations
6. **Close buttons** - Add close button to responses
7. **Language support** - Use `@language` decorator
8. **Log important actions** - Help with debugging

---

## 🚦 Flow Summary

```
User Input
    ↓
Telegram API
    ↓
Pyrogram Client
    ↓
Filter Chain (command, chat type, banned users)
    ↓
Decorator Chain (language, admin check, etc.)
    ↓
Command Handler
    ↓
Database Operations (if needed)
    ↓
Response to User
    ↓
Optional Logging
```

---

## 📚 Learn More

- **Full Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Visual Diagrams**: [COMMAND_FLOW_DIAGRAMS.md](COMMAND_FLOW_DIAGRAMS.md)
- **Pyrogram Docs**: https://docs.pyrogram.org/
- **MongoDB Docs**: https://motor.readthedocs.io/

---

## 💡 Tips for Building Your Bot

1. **Start small** - One command at a time
2. **Copy patterns** - Look at existing plugins
3. **Test frequently** - Run after each change
4. **Use logging** - Debug with console logs
5. **Read errors** - Python errors are helpful
6. **Ask questions** - Check Pyrogram docs
7. **Keep it modular** - One feature per file
8. **Document code** - Future you will thank you

---

## 🎉 You're Ready!

You now understand:
- ✅ How commands are registered
- ✅ How plugins are auto-discovered
- ✅ How to add your own commands
- ✅ How to use decorators
- ✅ How to interact with database
- ✅ How to use filters
- ✅ Best practices for bot development

**Start coding!** 🚀

---

*For detailed explanations, see [ARCHITECTURE.md](ARCHITECTURE.md)*
