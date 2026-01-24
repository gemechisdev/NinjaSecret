# Ninja Secret🥷 - Secret Messaging Bot

Send private, ninja-style secret messages to anyone in Telegram groups and chats! 🤫

## What is Ninja Secret?

**Ninja Secret** is a Telegram bot that lets you send secret messages (whispers) to specific people in groups. Only the sender and intended recipient(s) can read the message - perfect for private conversations in public spaces!

## Core Features

🥷 **Secret Shuriken Delivery**
- Send secrets to one person or multiple people
- Use `@all` or `@everyone` to share with the whole group
- Sender and targets can read - everyone else gets blocked

🔥 **Special Abilities**
- 💀 **Reveal & Burn** (`!reveal`, `!r`, `!burn`, `!b`, `!d`, `!del`, `!delete`) - Shows who read and self-destructs
- ⏰ **Timed Secrets** (`!timer:seconds` or `!t:seconds`) - Auto-expires after specified time
- 👑 **VIP Style** (`!vip` or `!v`) - Golden shuriken with crown styling
- 💕 **Cute Style** (`!cute`, `!c`, `!love`, `!l`) - Playful hearts and love

📊 **Ninja Stats & Achievements**
- Track your secret-sending statistics
- Unlock achievements as you become a master ninja
- View recent targets for quick secret drops

## Quick Start Guide

### Basic Usage

**Format:** `@ninjasecretbot [your message] [targets]`

**Examples:**
```
@ninjasecretbot pizza party tonight! @alice
@ninjasecretbot meeting at 3pm @bob,@charlie
@ninjasecretbot announcement everyone! @all
```

### Advanced Features

**Dual Messages (NEW!):**
Send different messages to different users with flexible targeting:

**Simple Format** (public + private):
```
@ninjasecretbot Hi everyone! | Secret note @user1,@user2
@ninjasecretbot Public announcement | Private details @team !vip
```
- Public message (before `|`) shown to unauthorized users
- Private message (after `|`) shown only to specified targets

**Advanced Format** (different targets, different messages):
```
@ninjasecretbot Message for Alice @alice | Message for Bob @bob
@ninjasecretbot Hi user1! @user1 | Hi user2 and user3! @user2,12345678
@ninjasecretbot Public @all | Private @admin,@moderator
```
- First target group sees first message
- Second target group sees second message
- Users not in any target list cannot read

**Features:**
- Works with all modifiers (!cute, !timer, !reveal, etc.)
- Sender and bot owner can always see the private (second) message
- Flexible: use whichever format fits your needs

**Reveal & Burn:**
```
@ninjasecretbot confidential info @boss !reveal
```

**Timed Secrets:**
```
@ninjasecretbot party at 8pm @friends !t:3600
```
(Timer uses seconds: 3600 = 1 hour, 7200 = 2 hours)

**VIP Styling:**
```
@ninjasecretbot special announcement @all !v
```

**Mix & Match:**
```
@ninjasecretbot top secret @user1,@user2 !reveal !t:1800
@ninjasecretbot Public msg | Private msg @user !c !t:600
```

## Target Options

- **Single user**: `@alice` or `123456789` (user ID)
- **Multiple users**: `@bob,@charlie,@david`
- **Everyone**: `@all` or `@everyone`
- **Recent targets**: Just type your message and select from suggestions!

## Installation

### Requirements
- Python 3.8+
- MongoDB database
- Telegram Bot Token from @BotFather
- Telegram API credentials from my.telegram.org

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/gemechisdev/NinjaSecret
   cd NinjaSecret
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp sample.env .env
   # Edit .env with your configuration
   ```

4. **Essential environment variables**
   ```env
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   MONGO_DB_URI=mongodb_connection_string
   OWNER_ID=your_telegram_user_id
   LOGGER_ID=log_group_id
   ```

5. **Run the bot**
   ```bash
   python -m NinjaSecret
   ```

### Enable Inline Feedback (Required)

For the bot to track when messages are sent:
1. Message @BotFather on Telegram
2. Select your bot
3. Go to Bot Settings → Inline Feedback
4. Turn it ON

## Bot Commands

- `/start` - Start the bot and see the main dashboard
- `/help` - Get help and documentation
- `/ping` - Check bot status
- `/stats` - View your whisper statistics

**Admin commands** (for group admins):
- `/auth` - Authorize users
- `/reload` - Reload admin cache

## Project Structure

```
NinjaSecret/
├── core/              # Core bot functionality
├── plugins/
│   ├── whisper/       # Secret messaging features
│   ├── admins/        # Admin-only commands
│   ├── bot/           # Basic bot commands
│   ├── misc/          # Miscellaneous features
│   └── tools/         # Utility tools
├── utils/             # Helper utilities
│   └── whisper_utils.py  # Whisper formatting & logic
├── mongo/             # Database models
│   └── whisperdb.py   # Whisper data storage
└── strings/           # Localization strings
```

## Features in Detail

### Security & Privacy
- Messages are only viewable by sender and specified targets
- Optional burn-after-reading for maximum privacy
- Timed expiration for temporary secrets
- Owner can read all messages for moderation

### User Experience
- Recent targets suggestions for quick messaging
- Achievement system to encourage engagement
- Statistics tracking (weekly and lifetime)
- Multiple message styling options
- Inline mode works in any chat

### Database Storage
- MongoDB for scalable data storage
- User caching for fast target resolution
- Statistics and achievements tracking
- Recent targets history (last 10)

## Technologies Used

- **Pyrogram** - Modern Telegram Bot framework
- **MongoDB** - NoSQL database for data storage
- **Python 3.8+** - Core programming language
- **Motor** - Async MongoDB driver

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact the bot owner through the bot's support button

---

Made with 🥷 by the Ninja Secret team