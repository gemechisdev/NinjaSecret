# NinjaSecret — Implementation Architecture

A standalone, end-to-end technical overview of the **NinjaSecret** Telegram bot. Written so any developer can read it and understand the whole codebase without digging through every file.

---

## 1. What Is NinjaSecret

NinjaSecret is a Python Telegram bot built with **Pyrogram** (async Telegram client library). Its core feature is **stealth "whisper" messaging** — sending secrets in any chat that only specific targets can read, with optional burn-after-reading, reveal-on-read, timers, and dual public/private messages.

Beyond whispers, it ships standard Telegram bot utilities:

- **Admin tools** — auth users, chat control (forward/links/slowmode), blacklist/whitelist chats, block/unblock users
- **Sudo tools** — global ban, sudoers management, auto-promote, maintenance mode, logger, restart, git pull, logs
- **Group tools** — broadcast to served chats/users, language settings, stats, ping, info
- **Health server** — FastAPI `/health`, `/ping` endpoints for deployment platforms (Render, Railway, Heroku)

**Owner:** Gemechis (@gemechisdev)  
**Repo:** `github.com/gemechisdev/NinjaSecret`  
**Language:** Python 3.11  
**Bot framework:** Pyrogram v2.1.23  
**Database:** MongoDB (Motor async driver)

---

## 2. Project Structure

```
NinjaSecret/
├── __init__.py          # Package init: creates bot client, loads DB, sudoers, heroku
├── __main__.py          # Entry point: boot sequence, imports plugins, starts event loop
├── logging.py           # Logging configuration (LOGGER factory)
├── misc.py              # Shared state: SUDOERS, _boot_, heroku app handle
├── config.py            # Environment-variable config with type coercion
├── web_server.py        # FastAPI health/ping server for deployment platforms
├── core/
│   ├── bot.py           # Hotty Pyrogram Client subclass (the bot)
│   ├── call.py          # Stub compatibility layer (music-call code removed)
│   ├── dir.py           # Creates downloads/ cache/, cleans image files on boot
│   └── mongo.py         # MongoDB async + sync clients (mongodb / pymongodb)
├── plugins/             # All bot command handlers (auto-loaded via glob)
│   ├── admins/          # auth, chat_control
│   ├── bot/             # help, start
│   ├── misc/            # broadcast, info, mongochk
│   ├── sudo/            # autoend, autopromote, autopromote_control, blchat, block,
│   │                    # gban, logger, maintenance, restart, sudoers
│   ├── tools/           # id, language, ping, stats
│   └── whisper/         # THE CORE: callbacks, cleanup_task, inline_handler, start_integration
├── strings/
│   ├── __init__.py      # Loads YAML language files into memory
│   ├── helpers.py       # HELP_1…HELP_15 command-help text blocks
│   ├── instruction.py   # AI system prompt (NinjaSecret AI persona)
│   └── langs/en.yml     # English localization strings
├── tests/
│   └── test_modifier_parsing.py  # Standalone unit tests for whisper modifier parsing
├── assets/              # Static media (fonts, images used by /info command)
├── strings/             # Localization (en.yml + loader)
├── config.py            # Env-var config
├── main.py              # Deployment wrapper: runs bot + uvicorn health server
├── Dockerfile           # Container build
├── setup                # Interactive install script (bash)
├── start                # `python3 -m NinjaSecret` launcher
└── requirements.txt     # Python dependencies
```

### Directories added by cleanup
- **`docs/`** — All project documentation (architecture, cleanup summaries, command flow, etc.)
- **`tmp/`** — Platform-locked deployment configs moved out of root (Heroku, Railway, etc.)

---

## 3. Bootstrap & Entry Points

### `start` / `main.py` — How the bot runs

**`start`** (shell script):
```bash
python3 -m NinjaSecret
```

**`main.py`** — Deployment wrapper (used by Docker/Procfile):
1. Starts a background daemon thread running `run_bot()` — spawns `python3 -m NinjaSecret` as a subprocess, restarts it every 5s on crash
2. Starts uvicorn serving the FastAPI app from `web_server.py` on `PORT` (default 8000)
3. Exposes `/`, `/health`, `/ping` endpoints for the hosting platform

**`__main__.py`** — The actual bot boot sequence (`python3 -m NinjaSecret`):
1. `sudo()` — loads sudo users from MongoDB + config `OWNER_ID` into `SUDOERS` filter
2. Loads globally banned + banned users into `BANNED_USERS` set
3. `start_bot_with_retry()` — starts Pyrogram client with flood-wait retry logic (up to `BOT_STARTUP_MAX_RETRIES` attempts)
4. Auto-discovers and imports every module under `plugins/*/*.py` via `plugins/__init__.py` (`ALL_MODULES`)
5. Starts whisper background tasks: `cleanup_pending_whispers_cache()` + `timer_countdown_update_task()`
6. Starts FastAPI health server
7. Calls `idle()` — keeps the event loop alive until SIGINT/SIGTERM

### `config.py` — Environment Configuration

All configuration comes from environment variables (loaded via `python-dotenv` from `.env`). Uses typed getters:

| Getter | Example usage |
|--------|--------------|
| `get_int(name, required=)` | `API_ID`, `OWNER_ID`, `LOGGER_ID` |
| `get_env(name, required=)` | `API_HASH`, `BOT_TOKEN`, `MONGO_DB_URI` |
| `get_bool(name, default=)` | `AUTO_PROMOTE_SUDO_USERS`, `LOG` |
| `get_float(name, default=)` | `GLOBAL_MIN_INTERVAL_BETWEEN_REQUESTS` |
| `get_json(name, default=)` | `PLATFORM_MIN_INTERVALS` |

Key config values:
- `API_ID` / `API_HASH` / `BOT_TOKEN` — Telegram bot credentials (required)
- `MONGO_DB_URI` — MongoDB connection string (required)
- `OWNER_ID` — Bot owner's Telegram user ID (required)
- `LOGGER_ID` / `LOG_GROUP_ID` — Log group channel ID
- `UPSTREAM_REPO` — Git repo for auto-updates (`https://github.com/gemechisdev/ninjasecret`)
- `SUPPORT_CHANNEL` / `SUPPORT_CHAT` — Support links
- `START_IMG_URL` / `PING_IMG_URL` / `STATS_IMG_URL` — Telegraph image URLs

---

## 4. Core Components

### `core/bot.py` — `Hotty` Pyrogram Client

Subclasses `pyrogram.Client`. The singleton bot instance (`app`) is created in `__init__.py`:

```python
app = Hotty()
```

On `start()`:
- Fetches bot identity (`id`, `name`, `username`, `mention`)
- Sends a startup message to `LOGGER_ID`
- Verifies bot is administrator in the log group
- Stores `self.me` info for use across handlers

### `core/mongo.py` — Database Clients

Creates two clients from `config.MONGO_DB_URI`:
- `_mongo_async_` — Motor `AsyncIOMotorClient` (async, used by all handlers)
- `_mongo_sync_` — PyMongo `MongoClient` (sync, used by clone feature)

Database: `_mongo_async_.NinjaSecret`

If no `MONGO_DB_URI` is set, it falls back to a temp bot-client flow to derive a username for a temp MongoDB (development-only path).

### `core/dir.py` — Directory Setup

On import, runs `dirr()`:
- Deletes `.jpg`, `.jpeg`, `.png` files from cwd (cleans stale images)
- Creates `downloads/` and `cache/` directories if missing

### `core/call.py` — Stub

Minimal compatibility stub for a removed music/call system. All methods are no-ops. Kept so imports elsewhere don't break.

### `misc.py` — Shared Mutable State

```python
SUDOERS = filters.user()      # Dynamically populated sudo user filter
HAPP = None                   # Heroku app handle (if deployed on Heroku)
_boot_ = time.time()          # Bot start timestamp for uptime
db = {}                       # In-memory cache dict (populated by dbb())
```

`dbb()` initializes `db = {}`. `heroku()` configures the Heroku app handle if `HEROKU_API_KEY` + `HEROKU_APP_NAME` are set and running on Heroku.

### `logging.py` — Logging

Configures Python `logging` with:
- File handler → `log.txt`
- Stream handler → stdout
- Suppresses noisy loggers (`httpx`, `pyrogram`, `pymongo`, etc.)

`LOGGER(name)` returns a `logging.getLogger(name)` instance.

---

## 5. Plugin System

### Auto-discovery

`plugins/__init__.py` globs `plugins/*/*.py` (all `.py` files in subdirectories, excluding `__init__.py`) and builds `ALL_MODULES` — a sorted list of import paths like:

```
plugins.admins.auth
plugins.admins.chat_control
plugins.bot.help
plugins.bot.start
plugins.misc.broadcast
plugins.misc.info
plugins.misc.mongochk
plugins.sudo.autoend
plugins.sudo.autopromote
plugins.sudo.autopromote_control
plugins.sudo.blchat
plugins.sudo.block
plugins.sudo.gban
plugins.sudo.logger
plugins.sudo.maintenance
plugins.sudo.restart
plugins.sudo.sudoers
plugins.tools.id
plugins.tools.language
plugins.tools.ping
plugins.tools.stats
plugins.whisper.callbacks
plugins.whisper.cleanup_task
plugins.whisper.inline_handler
plugins.whisper.start_integration
```

`__main__.py` imports each via `importlib.import_module("NinjaSecret.plugins" + all_module)`. Every module registers its handlers at import time via `@app.on_message(...)` / `@app.on_callback_query(...)` / `@app.on_inline_query(...)` decorators.

### Plugin Categories

| Directory | Purpose |
|-----------|---------|
| `plugins/admins/` | Admin/moderation commands usable in groups (`/auth`, `/unauth`, `/authlist`, forward/links/slowmode control) |
| `plugins/bot/` | Core user-facing commands (`/start`, `/help`) |
| `plugins/misc/` | Cross-cutting utilities (broadcast, info, mongochk) |
| `plugins/sudo/` | Owner/sudo-only commands (gban, auto-promote, maintenance, restart, logs, sudoers) |
| `plugins/tools/` | Utility commands (`/id`, `/language`, `/ping`, `/stats`) |
| `plugins/whisper/` | **Core whisper feature** — inline secret creation, callbacks, cleanup, /whisper dashboard |

---

## 6. The Whisper Feature (Core Product)

Whispers let users send secrets that only targeted recipients can read. The entire feature lives in `plugins/whisper/` and `NinjaSecret/mongo/whisperdb.py`, with helpers in `NinjaSecret/utils/whisper_utils.py`.

### 6.1 Inline Query Flow (`plugins/whisper/inline_handler.py`)

User types `@ninjasecretbot [message] [targets] [modifiers]` in any chat's inline field.

1. **`handle_inline_query()`** parses the query:
   - Strips `@botname` prefix
   - Parses **modifiers** with word-boundary regex (prevents false positives like `!revealme` matching `!reveal`):
     - `!reveal` / `!r` — show who read the secret
     - `!delete` / `!del` / `!d` — burn after reading (silent, no reader shown)
     - `!burn` / `!b` — reveal + burn (maximum security)
     - `!vip` / `!v` — VIP styling (crown emoji)
     - `!cute` / `!c` / `!l` / `!love` — cute styling (heart emoji)
     - `!timer:N` / `!t:N` — auto-expire after N seconds
   - Splits on `|` for **dual messages** (public part → public targets, private part → private targets)
   - Validates message length against Telegram's 200-char callback alert limit
   - Resolves targets via `resolve_target()` (checks MongoDB user cache first, then `app.get_users()`)

2. Caches whisper data in memory (`pending_whispers` dict) keyed by whisper ID — **not yet saved to DB**

3. Returns an `InlineQueryResultArticle` with a "Read Secret" button (`whisper_view_{id}`)

4. **`handle_chosen_inline_result()`** — fires when the user taps the inline result (requires BotFather "Inline Feedback" enabled):
   - Persists the whisper to MongoDB via `store_whisper()`
   - Attaches `inline_message_id`
   - Adds each target to the sender's `recent_targets` list (max 10, stored in `users` collection)

### 6.2 Callback Handling (`plugins/whisper/callbacks.py`)

Handles all `whisper_*` callback queries:

| Callback | Action |
|----------|--------|
| `whisper_view_{id}` | View secret content (auth check: sender, target, owner, or sudo) |
| `whisper_targets_{id}` | Show who the whisper is for + read status |
| `whisper_dashboard` | User's whisper dashboard (stats + quick actions) |
| `whisper_stats` / `whisper_full_stats_{id}` | Detailed whisper statistics |
| `whisper_tutorial` | How-to guide |
| `whisper_styles` | Available style modifiers |
| `whisper_help` | Help tree |
| `whisper_settings` | Settings placeholder |
| `whisper_recent_targets` | Recent recipients quick-send |
| `whisper_clear_recent_targets` | Clear recent targets history |
| `whisper_clean_history` | Delete read/burned/expired whispers sent by user |

**Authorization model** for viewing:
- Sender → always can view
- Target user → can view (matched by user_id, username, or `@all`/`@everyone`)
- `OWNER_ID` → can view any whisper
- `SUDOERS` → can view any whisper
- Otherwise → "unauthorized" alert

**Read lifecycle:**
1. Target taps "Read Secret" → `mark_whisper_read()` sets `read_at`, `reader_id`, status=`read`
2. If `burn_after_reading` → status becomes `burned`, message edited to show burn text (or silently deleted)
3. If `reveal_on_read` (without burn) → message edited to show who read it

### 6.3 Background Tasks (`plugins/whisper/cleanup_task.py`)

Two `asyncio` tasks started after bot boot:

1. **`whisper_cleanup_task()`** (runs every 10 min):
   - `cleanup_expired_whispers()` — marks whispers whose `settings.expires_at` has passed as `expired`
   - `cleanup_pending_whispers_cache()` — removes in-memory pending whispers older than 5 min that were never sent

2. **`timer_countdown_update_task()`** (runs every 5s, smart-interval):
   - For active timed whispers with `inline_message_id`, edits the inline message to show updated time remaining
   - Update frequency scales with urgency: <5 min → every 5s; 5–30 min → every 1 min; 30–60 min → every 3 min; >1 hr → every 5 min

### 6.4 Whisper Start Integration (`plugins/whisper/start_integration.py`)

`/whisper` command in private chat opens the whisper dashboard with stats and quick-action buttons. Also provides `get_whisper_integration_button()` to add a "Ninja Mode" button to the start panel.

### 6.5 Database Models (`NinjaSecret/mongo/whisperdb.py`)

Collections:
- **`whispers`** — Each whisper document: `whisper_id`, `inline_message_id`, `content`, `sender_id`, `target_username`, `target_id`, `original_target_token`, `all_targets`, `target_mentions`, `created_at`, `read_at`, `reader_id`, `status` (`active`/`read`/`burned`/`expired`), `settings` (`expires_at`, `burn_after_reading`, `reveal_on_read`, `style`)
- **`whisper_stats`** — Aggregated user stats (calculated in real-time, not stored)
- **`whisper_achievements`** — User achievements (secret_swinger, burn_master, time_keeper, etc.)

Key functions:
- `store_whisper(data)` — insert new whisper
- `get_whisper(whisper_id)` / `get_whisper_by_id(whisper_id)` — fetch by ID
- `get_whisper_message(inline_message_id)` — fetch by inline message ID (with expiry check)
- `mark_whisper_read(whisper_id, reader_id)` — mark read + burn logic
- `cleanup_expired_whispers()` — mark expired whispers
- `get_active_timed_whispers()` — fetch whispers with active timers for countdown updates
- `get_user_whisper_stats(user_id)` — real-time stats: sent/received/burned/timed counts, weekly breakdown, achievements
- `resolve_target(token, app)` — resolve @username or user_id to `(id, username, display_name)` with DB caching
- `upsert_user(user_data)` — insert/update user profile cache
- `add_recent_target(sender_id, target_data)` / `get_recent_targets(user_id)` / `clear_recent_targets(user_id)` — recent recipients list (max 10)

### 6.6 Whisper Utils (`NinjaSecret/utils/whisper_utils.py`)

Pure helper functions (no DB):
- `generate_whisper_id()` — UUID4 string
- `char_length(s)` — UTF-16-LE aware length (Telegram's counting method)
- `get_max_whisper_content_length(modifiers)` — 200 minus style/timer overhead
- `parse_whisper_command(text)` — extracts message, targets, modifiers dict
- `get_modifier_type(modifiers)` — classifies: `vip`, `cute`, `burn`, `delete`, `reveal`, `timer`, `base`
- `create_whisper_inline_result(...)` — builds the inline query result payload
- `create_whisper_posted_message(...)` — builds the message posted to chat when secret is sent
- `create_timer_countdown_message(...)` — builds updated countdown text
- `create_whisper_keyboard(whisper_id)` — "Read Secret" button markup
- `create_dashboard_keyboard()` — dashboard inline keyboard
- `format_targets_display(targets)` — human-readable target list
- `get_content_for_user(content, user_id, ...)` — dual-message access control logic
- `format_user_stats(stats)` — formatted stats text
- `NINJA_EMOJIS` — themed emoji constants (ninja, shuriken, scroll, fire, timer, crown, heart, etc.)

---

## 7. Database Layer (Core DB)

`NinjaSecret/utils/database/database.py` is the main DB module. All collections live in the `NinjaSecret` database:

| Collection | Purpose |
|------------|---------|
| `adminauth` / `authuser` | Authorized users per chat (auth system) |
| `autoend` | Auto-end stream toggle |
| `blacklistChat` | Blacklisted chats |
| `blockedusers` | Globally blocked users |
| `chats` | Served chats |
| `language` | Per-chat language setting |
| `onoffper` | On/off toggles (logging, maintenance) |
| `sudoers` | Sudo user list |
| `tgusersdb` | Served users |
| `privatechats` | Private served chats |
| `queries` | Query counter |
| `userstats` | User stats + recent_targets |
| `forward_control` / `links_control` / `slowmode_control` | Chat control settings |

In-memory caches (fall back to DB): `active`, `activevideo`, `autoend`, `count`, `channelconnect`, `langm`, `loop`, `maintenance`, `nonadmin`, `pause`, `playmode`, `playtype`, `skipmode`, `privatechats`, `cleanmode`, `suggestion`, `mute`, `audio`, `video`

Key functions used across plugins:
- `get_lang(chat_id)` / `set_lang(chat_id, lang)` — per-chat language
- `get_served_chats()` / `add_served_chat(chat_id)` — track served chats
- `get_served_users()` / `add_served_user(user_id)` — track served users
- `get_banned_users()` / `add_banned_user(user_id)` — blocked users
- `get_gbanned()` / `add_gban_user(user_id)` — global bans
- `get_sudoers()` / `add_sudo(user_id)` / `remove_sudo(user_id)` — sudo list
- `is_on_off(n)` / `add_on(n)` / `add_off(n)` — toggle flags (2 = logging, 1 = maintenance)
- `is_maintenance()` / `maintenance_on()` / `maintenance_off()` — maintenance mode
- `get_authuser_names(chat_id)` / `save_authuser(...)` / `delete_authuser(...)` — authorized users
- `blacklist_chat(chat_id)` / `whitelist_chat(chat_id)` / `blacklisted_chats()` — chat blacklist
- `get_active_chats()` / `add_active_chat(chat_id)` / `remove_active_chat(chat_id)` — active voice chats
- `get_queries()` / `set_queries(mode)` — query counter

`clonedb.py` (clone-bot DB) was removed during cleanup — its functions were never called by any runtime code.

---

## 8. Utilities

| Module | Purpose |
|--------|---------|
| `utils/formatters.py` | `get_readable_time()`, `convert_bytes()`, `int_to_alpha()`, `alpha_to_int()`, `check_duration()`, `speed_converter()` |
| `utils/sys.py` | `bot_sys_stats()` — uptime, CPU, RAM, disk; `bot_up_time()` |
| `utils/extraction.py` | `extract_user(message)` — resolve user from reply, mention entity, or ID/username argument |
| `utils/admin_check.py` | `admin_check(message)` — check if user is chat admin |
| `utils/decorators/admins.py` | `AdminRightsCheck`, `AdminActual`, `ActualAdminCB` — permission decorators for handlers |
| `utils/decorators/language.py` | `language`, `languageCB`, `LanguageStart` — i18n decorators that inject localized strings |
| `utils/decorators/__init__.py` | Re-exports admin + language decorators |
| `utils/inline/__init__.py` | Re-exports all inline keyboard builders |
| `utils/inline/extras.py` | `close_markup()`, `supp_markup()`, `botplaylist_markup()` |
| `utils/inline/help.py` | `help_pannel()`, `help_back_markup()`, `private_help_panel()` |
| `utils/inline/settings.py` | `setting_markup()`, `vote_mode_markup()`, `auth_users_markup()`, `playmode_users_markup()`, `audio_quality_markup()`, `video_quality_markup()` |
| `utils/inline/start.py` | `start_panel()`, `private_panel()` |
| `utils/inline/stats.py` | `stats_buttons()`, `back_stats_buttons()` |
| `utils/inline/sudolist.py` | (empty) |
| `utils/stuffs/buttons.py` | `BUTTONS` class — static inline button layouts for help menu |
| `utils/stuffs/helper.py` | `Helper` class — help text strings + promotion privilege presets |
| `utils/whisper_utils.py` | Whisper formatting & parsing (see §6.6) |

### Removed during cleanup (dead code)

These were never imported by any runtime module:
- `utils/events.py` — Telethon decorator (Telethon not in requirements, `telethn` undefined)
- `utils/flood_handler.py` — FloodWait handler (imported non-existent `platform_gate`)
- `utils/external/ai_api_client.py` — External AI API client (never imported)
- `utils/filters_func.py` — Filter message sender (imported non-existent `msg_types`/`notes_func`)
- `utils/inlinequery.py` — Legacy inline tutorial (superseded by whisper inline_handler)
- `utils/mongo.py` — Duplicate DB connection (superseded by `core/mongo.py`)
- `utils/rate_limiter.py` — Rate limiter decorators (never imported)
- `utils/logger.py` — Play logs helper (never imported)
- `utils/cmdforac.py` — Filter helpers (never imported)
- `utils/autopromote_helpers.py` — Permission text helpers (logic duplicated inline)
- `utils/errors.py` — `capture_err` decorator (never imported)
- `utils/exceptions.py` — `AssistantErr` (never imported)
- `mongo/readable_time.py` — Duplicate of `utils/formatters.py:get_readable_time`
- `utils/database/clonedb.py` — Clone-bot DB (never called)
- `core/git.py` — Git auto-update (all logic commented out)
- `examples/telegram_platform_example.py` — Example TeleAPI class (never imported)

---

## 9. Strings & Localization

### `strings/__init__.py`

Loads all `./strings/langs/*.yml` files into memory at import:
- `languages[lang_code]` — parsed YAML dict
- `languages_present[lang_code]` — human-readable language name
- Falls back to English strings for missing keys in non-English files
- `get_string(lang)` returns the language dict

### `strings/langs/en.yml`

English strings for all bot messages. Keys are referenced by plugins via `_["key"]` pattern after applying the `language` decorator.

### `strings/helpers.py`

`HELP_1` through `HELP_15` — formatted help text blocks for each command category (chat control, auth users, broadcast, blacklist, block users, autopromote, global ban, language, maintenance, ping/stats, system management, sudo management, bot info, advanced features, utility).

### `strings/instruction.py`

`Instruction.system_prompt()` — AI persona system prompt used by the (removed) external AI client. Defines "NinjaSecret AI" behavior: confident, direct, concise, truthful.

---

## 10. Command Lifecycle (Data Flow)

Example: User sends `/gban @spammer` in a group:

1. **Telegram** → Pyrogram dispatches to `plugins/sudo/gban.py` handler (`@app.on_message(filters.command(["gban", "globalban"]) & SUDOERS)`)
2. **Decorator chain** — `@language` decorator:
   - Checks maintenance mode (blocks non-sudo if under maintenance)
   - Deletes command message if clean mode enabled (`should_delete_command`)
   - Loads chat language → `_ = get_string(language)`
3. **Handler logic**:
   - `extract_user(message)` resolves the target from reply or argument
   - Validation: can't gban self, bot, or sudo users
   - Checks `is_banned_user(user.id)` — skip if already banned
   - Adds to `BANNED_USERS` in-memory set
   - Fetches `get_served_chats()` — all tracked chats
   - Loops through chats, `app.ban_chat_member(chat_id, user.id)` with FloodWait handling
   - `add_banned_user(user.id)` — persists to MongoDB
   - Replies with summary message

Example: User sends `@ninjasecretbot hello @alice !burn` inline:

1. **Telegram inline query** → `plugins/whisper/inline_handler.py:handle_inline_query()`
2. Parse: message=`hello`, targets=`@alice`, modifiers=`{burn_after_reading: True, reveal_on_read: True}`
3. `resolve_target("@alice", app)` → `(user_id, username, display_name)` with DB caching
4. Cache whisper in `pending_whispers[whisper_id]` (memory only)
5. Return `InlineQueryResultArticle` with "Read Secret" button
6. User taps button → `handle_chosen_inline_result()` → `store_whisper()` → MongoDB
7. Target taps "Read Secret" → `callbacks.py:handle_whisper_view()` → auth check → show content → `mark_whisper_read()` → status=`burned` → message edited to burn text

---

## 11. Deployment & Configuration

### Supported platforms (from moved configs in `tmp/`)

- **Heroku** — `Procfile` (`worker: bash start`), `app.json`, `heroku.yml`
- **Railway** — `railway.json` (Dockerfile builder, V2 runtime, europe-west4 region)
- **Docker** — `Dockerfile` (python3.11-nodejs19 base, non-root user `appuser`, ffmpeg installed)

### `Dockerfile` highlights

```dockerfile
FROM nikolaik/python-nodejs:python3.11-nodejs19
RUN useradd -m -u 10014 -s /bin/bash appuser
RUN apt-get install -y ffmpeg  # for media duration probing
COPY --chown=appuser:appuser . /app/
WORKDIR /app/
RUN pip3 install --no-cache-dir --upgrade --requirement requirements.txt
USER appuser
CMD ["python3", "main.py"]
```

### `.env.example` — Required environment variables

```
API_ID=...
API_HASH=...
BOT_TOKEN=...
MONGO_DB_URI=mongodb+srv://...
OWNER_ID=...
LOGGER_ID=-100...
LOG_GROUP_ID=-100...
STRING_SESSION=...
UPSTREAM_REPO=https://github.com/gemechisdev/ninjasecret
SUPPORT_CHANNEL=https://t.me/...
SUPPORT_CHAT=https://t.me/...
PORT=8000
```

### `.dockerignore`

Ignores `.env`, `.cache`, `log.txt`, `*.session`, `raw_files/`, `cache/`, `downloads/`, `__pycache__/`

---

## 12. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Pyrogram over python-telegram-bot | Async-first, inline query + callback query support, userbot-style flexibility |
| MongoDB (Motor) | Async driver, flexible schema for whisper targets/settings |
| Inline-mode whispers | Secrets sent without polluting public chat; only targets can read |
| In-memory `pending_whispers` cache | Whispers not persisted until user actually sends (avoids DB clutter from abandoned drafts) |
| Word-boundary modifier regex | Prevents `!revealme` from falsely matching `!reveal` |
| Smart timer update intervals | Reduces Telegram API calls: urgent whispers updated frequently, long-lived ones less often |
| Decorator-based auth (`@language`, `@AdminActual`) | Consistent permission + i18n handling across all handlers |
| `main.py` subprocess wrapper | Bot process supervised by health server; restarts automatically on crash |

---

## 13. How to Extend

1. **Add a new command:** Create `plugins/<category>/<name>.py`, register handlers with `@app.on_message(...)`, it's auto-discovered via `ALL_MODULES`.
2. **Add a new whisper modifier:** Add a regex pattern + handler in `utils/whisper_utils.py:parse_whisper_command()`, update `get_modifier_type()` and `create_whisper_posted_message()`.
3. **Add a new DB collection:** Add to `utils/database/database.py` following existing patterns (collection var + async CRUD functions).
4. **Add a new language:** Create `strings/langs/<code>.yml`, it's auto-loaded by `strings/__init__.py`.
5. **Deploy:** Copy `.env.example` to `.env`, fill in values, run `bash start` or `docker build`.

---

## 14. Files Removed During Cleanup

The following dead code was removed (docs in `memory/removed-files-audit.md`):

- `core/git.py`, `examples/telegram_platform_example.py`
- `utils/events.py`, `flood_handler.py`, `external/ai_api_client.py`, `filters_func.py`, `inlinequery.py`, `mongo.py`, `rate_limiter.py`, `logger.py`, `cmdforac.py`, `autopromote_helpers.py`, `errors.py`, `exceptions.py`, `stuffs/_init.py_`
- `mongo/readable_time.py` (duplicate of `utils/formatters.py`)
- `utils/database/clonedb.py` (unused clone feature)
- `tests/test_modifier_parsing.py` (standalone test)

No runtime imports reference any removed file — verified by import-resolution check after cleanup.

---

*End of architecture document.*