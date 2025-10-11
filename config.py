import re
import os
from os import getenv

from dotenv import load_dotenv
from pyrogram import filters

load_dotenv()
# External AI API configuration (optional)
AI_API_BASE_URL = getenv("AI_API_BASE_URL", "")
AI_API_TOKEN = getenv("AI_API_TOKEN", "")

# Get this value from my.telegram.org/apps
API_ID = int(getenv("API_ID", "24408788"))
API_HASH = getenv("API_HASH", "1c77b4a5cdbedf00286208adece69e1a")

# Get your token from @BotFather on Telegram.
BOT_TOKEN = getenv(
    "BOT_TOKEN", "8161489937:AAHefSCSjqxTlcjYXaCmntZ-WoP_NrYbf7g")

# Get your mongo url from cloud.mongodb.com
MONGO_DB_URI = getenv(
    "MONGO_DB_URI", "mongodb+srv://venopyx:venopyx@cluster0.o4ijmrr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
BOT_NAME = getenv("BOT_NAME", "Ninja Secret🥷")
PRIVATE_BOT_MODE = getenv("PRIVATE_BOT_MODE")

# Auto-promotion settings
AUTO_PROMOTE_SUDO_USERS = getenv("AUTO_PROMOTE_SUDO_USERS", "True").lower() == "true"

# Chat id of a group for logging bot's activities
LOGGER_ID = int(getenv("LOGGER_ID", "-1003029976514"))

# Logging configuration
LOG = getenv("LOG", "True").lower() == "true"
LOG_GROUP_ID = int(getenv("LOG_GROUP_ID", "-1003029976514"))

# Get this value from @BRANDRD_ROBOT on Telegram by /id
OWNER_ID = int(getenv("OWNER_ID", "6153949909"))

# Fill these variables if you're deploying on heroku.
# Your heroku app name
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")
# Get it from http://dashboard.heroku.com/account
HEROKU_API_KEY = getenv("HEROKU_API_KEY")

UPSTREAM_REPO = getenv(
    "UPSTREAM_REPO",
    "https://github.com/venopyx/ScorpiTune",
)
UPSTREAM_BRANCH = getenv("UPSTREAM_BRANCH", "main")
GIT_TOKEN = getenv(
    "GIT_TOKEN", None
)  # Fill this variable if your upstream repository is private

SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/CodeTactics")
SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/moonlight_familyplus")

# Set this to True if you want the assistant to automatically leave chats after an interval
AUTO_LEAVING_ASSISTANT = bool(getenv("AUTO_LEAVING_ASSISTANT", False))

# Auto Gcast/Broadcast Handler (True = broadcast on , False = broadcast off During Hosting, Dont Do anything here.)
AUTO_GCAST = os.getenv("AUTO_GCAST")

# Auto Broadcast Message That You Want Use In Auto Broadcast In All Groups.
AUTO_GCAST_MSG = getenv("AUTO_GCAST_MSG", "")

# Rate limiting settings to prevent FloodWait errors
# Global platform request spacing (in seconds)
# Minimum time between any two requests per platform
GLOBAL_MIN_INTERVAL_BETWEEN_REQUESTS = float(os.getenv("GLOBAL_MIN_INTERVAL_BETWEEN_REQUESTS", 0.5))
# Extra delay for 2nd and subsequent concurrent requests to same platform
GLOBAL_SECOND_REQUEST_DELAY = float(os.getenv("GLOBAL_SECOND_REQUEST_DELAY", 1.0))

# Optional per-platform overrides
# Example: PLATFORM_MIN_INTERVALS = { 'telegram': 0.2, 'youtube': 0.5, 'spotify': 0.3 }
# Example: PLATFORM_SECOND_REQUEST_DELAYS = { 'telegram': 0.5, 'youtube': 1.0, 'spotify': 0.7 }
try:
	import json as _json
	PLATFORM_MIN_INTERVALS = _json.loads(os.getenv("PLATFORM_MIN_INTERVALS", "{}"))
	PLATFORM_SECOND_REQUEST_DELAYS = _json.loads(os.getenv("PLATFORM_SECOND_REQUEST_DELAYS", "{}"))
except Exception:
	PLATFORM_MIN_INTERVALS = {}
	PLATFORM_SECOND_REQUEST_DELAYS = {}

# Backwards-compatible FloodWait settings
FLOODWAIT_BASE_DELAY = float(os.getenv("FLOODWAIT_BASE_DELAY", 1.0))
MAX_RETRIES_ON_FLOODWAIT = int(os.getenv("MAX_RETRIES_ON_FLOODWAIT", 3))
MIN_INTERVAL_BETWEEN_REQUESTS = float(os.getenv("MIN_INTERVAL_BETWEEN_REQUESTS", 0.1))

# Bot startup retry configuration for flood wait errors
BOT_STARTUP_MAX_RETRIES = int(os.getenv("BOT_STARTUP_MAX_RETRIES", 5))
USERBOT_STARTUP_MAX_RETRIES = int(os.getenv("USERBOT_STARTUP_MAX_RETRIES", 3))
HOTTY_STARTUP_MAX_RETRIES = int(os.getenv("HOTTY_STARTUP_MAX_RETRIES", 3))
FLOOD_WAIT_SAFETY_BUFFER = int(os.getenv("FLOOD_WAIT_SAFETY_BUFFER", 30))  # Extra seconds to wait beyond required time

# File size limits (in bytes)
TG_FILESIZE_LIMIT = int(getenv("TG_FILESIZE_LIMIT", 104857600))  # 100MB default


# Get your pyrogram v2 session from @BRANDEDSTRINGSESSION_BOT on Telegram
STRING1 = getenv("STRING_SESSION",  "BAF0ctQAREtr7RY46xFxPpcqgJsjfFjBjotj8b1Q_tpCBX8XoVFSLAxUth1MjXp-FZ2QOPuA0RXr-MyluJjPlHLwZCLFFwoaifi_UMNOlzsXCC4OQw8k-5EHp3fasEVdIVCWVTptU7DV8fkMkyIvdD35VeIqviTiTyWDOOuqyId5u-HkVXZjp8i69Lj07CdOtPoZFbB-qyblhn1NKgNvmJIGOs35V_l5hqkYCTTDPaqgeTuHbcWwwK85HY42TSQED5Z_QN7Q4CPp3-LRnqRLhhb7wEA6mJPs2gqVan9AD_hqVpKK9DOhJeaJDQ0D7F9L_gGjDS9KqJVPZcUUE6TdEIBBPQ3nnQAAAAHLeZrqAA")
STRING2 = getenv("STRING_SESSION2", None)
STRING3 = getenv("STRING_SESSION3", None)
STRING4 = getenv("STRING_SESSION4", None)
STRING5 = getenv("STRING_SESSION5", None)


BANNED_USERS = filters.user()
adminlist = {}
votemode = {}
autoclean = []
confirmer = {}


START_IMG_URL = getenv(
    "START_IMG_URL", "https://te.legra.ph/file/62c76ac2095332a0ede75.jpg"
)
PING_IMG_URL = getenv(
    "PING_IMG_URL", "https://te.legra.ph/file/4f59fb748e1990acfa297.jpg"
)
STATS_IMG_URL = getenv(
    "STATS_IMG_URL", "https://te.legra.ph/file/4310ea5f523520b2b765b.jpg"
)




if SUPPORT_CHANNEL:
    if not re.match("(?:http|https)://", SUPPORT_CHANNEL):
        raise SystemExit(
            "[ERROR] - Your SUPPORT_CHANNEL url is wrong. Please ensure that it starts with https://"
        )

if SUPPORT_CHAT:
    if not re.match("(?:http|https)://", SUPPORT_CHAT):
        raise SystemExit(
            "[ERROR] - Your SUPPORT_CHAT url is wrong. Please ensure that it starts with https://"
        )
