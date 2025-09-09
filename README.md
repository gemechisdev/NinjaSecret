# WhispierBot - Clean Bot Foundation

This is a cleaned version of the ScorpiTune music bot, optimized to serve as a foundation for the WhispierBot (whisper messaging functionality).

## What's Included

### Core Architecture
- ✅ **Bot Core**: Clean Pyrogram-based bot structure
- ✅ **Userbot Support**: Multi-session userbot management
- ✅ **Database Integration**: MongoDB with comprehensive examples
- ✅ **Plugin System**: Modular plugin architecture
- ✅ **Configuration Management**: Environment-based configuration
- ✅ **Logging System**: Comprehensive logging setup

### General Purpose Features Kept
- **Admin Tools**: User authorization, chat control (forward/links/slowmode)
- **Bot Commands**: Start, help, ping, stats, language settings
- **Utility Tools**: Google search, image tools, telegraph upload, paste functionality
- **Misc Features**: AFK system, broadcast, info commands, truth/dare game, MongoDB checker
- **User Management**: Couples game, user info with Sangmata integration

### Removed Music-Specific Features
- ❌ Music streaming and playback
- ❌ YouTube/Spotify/Apple Music integrations
- ❌ Audio/video downloading
- ❌ Queue management
- ❌ Platform-specific APIs (SafoneAPI, etc.)
- ❌ Music-related admin controls
- ❌ Playlist management

## Directory Structure

```
ScorpiTune/
├── core/           # Core bot functionality
├── plugins/        # Feature plugins
│   ├── admins/     # Admin-only commands
│   ├── bot/        # Basic bot commands
│   ├── misc/       # Miscellaneous features
│   ├── sudo/       # Super admin commands
│   └── tools/      # Utility tools
├── utils/          # Helper utilities
├── mongo/          # Database models and examples
├── assets/         # Static assets (sample file + README)
└── examples/       # Reference implementations
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd WhispierBot
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

4. **Run the bot**
   ```bash
   python -m ScorpiTune
   ```

## Configuration

Key environment variables to set:
- `API_ID` & `API_HASH`: Get from my.telegram.org
- `BOT_TOKEN`: Get from @BotFather
- `MONGO_DB_URI`: MongoDB connection string
- `STRING_SESSION`: Pyrogram user session (get from session generator)
- `OWNER_ID`: Your Telegram user ID
- `LOGGER_ID`: Log group/channel ID

## Ready for Whisper Implementation

The bot is now ready for implementing whisper functionality with:
- Clean codebase without music-related bloat
- Established plugin architecture for easy feature addition
- Working userbot system for message handling
- Database integration for storing whisper data
- Proper error handling and logging

## Next Steps

1. Implement whisper message functionality in `plugins/whisper/`
2. Add whisper-specific database models in `mongo/`
3. Create whisper-related utilities in `utils/`
4. Update strings for whisper-specific messages

## Support

For issues and support, refer to the original ScorpiTune documentation or create issues in this repository.