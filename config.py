import json
import os
import re

from dotenv import load_dotenv
from pyrogram import filters


load_dotenv()


def get_env(name, default=None, required=False):
    """Retrieve a configuration value from the environment."""
    value = os.getenv(name)

    if value is not None:
        value = value.strip()

    if value:
        return value

    if required:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return default


def get_bool(name, default=False):
    """Retrieve a boolean configuration value."""
    value = get_env(name)

    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}


def get_int(name, default=None, required=False):
    """Retrieve an integer configuration value."""
    value = get_env(name, required=required)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Environment variable {name} must be an integer."
        ) from exc


def get_float(name, default=None):
    """Retrieve a floating-point configuration value."""
    value = get_env(name)

    if value is None:
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Environment variable {name} must be a number."
        ) from exc


def get_json(name, default=None):
    """Retrieve a JSON configuration value."""
    value = get_env(name)

    if value is None:
        return {} if default is None else default

    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Environment variable {name} contains invalid JSON."
        ) from exc


AI_API_BASE_URL = get_env("AI_API_BASE_URL", "")
AI_API_TOKEN = get_env("AI_API_TOKEN", "")

API_ID = get_int("API_ID", required=True)
API_HASH = get_env("API_HASH", required=True)

BOT_TOKEN = get_env("BOT_TOKEN", required=True)

MONGO_DB_URI = get_env("MONGO_DB_URI", required=True)

BOT_NAME = get_env("BOT_NAME", "Ninja Secret🥷")
PRIVATE_BOT_MODE = get_env("PRIVATE_BOT_MODE")

AUTO_PROMOTE_SUDO_USERS = get_bool(
    "AUTO_PROMOTE_SUDO_USERS",
    True,
)

LOGGER_ID = get_int(
    "LOGGER_ID",
    -1003029976514,
)

LOG = get_bool(
    "LOG",
    True,
)

LOG_GROUP_ID = get_int(
    "LOG_GROUP_ID",
    -1003029976514,
)

OWNER_ID = get_int(
    "OWNER_ID",
    required=True,
)

UPSTREAM_REPO = get_env(
    "UPSTREAM_REPO",
    "https://github.com/gemechisdev/ninjasecretbot",
)

UPSTREAM_BRANCH = get_env(
    "UPSTREAM_BRANCH",
    "main",
)

GIT_TOKEN = get_env("GIT_TOKEN")

SUPPORT_CHANNEL = get_env(
    "SUPPORT_CHANNEL",
    "https://t.me/CodeTactics",
)

SUPPORT_CHAT = get_env(
    "SUPPORT_CHAT",
    "https://t.me/moonlight_familyplus",
)

PORT = get_int(
    "PORT",
    8000,
)

AUTO_GCAST = get_env("AUTO_GCAST")

AUTO_GCAST_MSG = get_env(
    "AUTO_GCAST_MSG",
    "",
)

GLOBAL_MIN_INTERVAL_BETWEEN_REQUESTS = get_float(
    "GLOBAL_MIN_INTERVAL_BETWEEN_REQUESTS",
    0.5,
)

GLOBAL_SECOND_REQUEST_DELAY = get_float(
    "GLOBAL_SECOND_REQUEST_DELAY",
    1.0,
)

PLATFORM_MIN_INTERVALS = get_json(
    "PLATFORM_MIN_INTERVALS",
    {},
)

PLATFORM_SECOND_REQUEST_DELAYS = get_json(
    "PLATFORM_SECOND_REQUEST_DELAYS",
    {},
)

FLOODWAIT_BASE_DELAY = get_float(
    "FLOODWAIT_BASE_DELAY",
    1.0,
)

MAX_RETRIES_ON_FLOODWAIT = get_int(
    "MAX_RETRIES_ON_FLOODWAIT",
    3,
)

MIN_INTERVAL_BETWEEN_REQUESTS = get_float(
    "MIN_INTERVAL_BETWEEN_REQUESTS",
    0.1,
)

BOT_STARTUP_MAX_RETRIES = get_int(
    "BOT_STARTUP_MAX_RETRIES",
    5,
)

FLOOD_WAIT_SAFETY_BUFFER = get_int(
    "FLOOD_WAIT_SAFETY_BUFFER",
    30,
)

TG_FILESIZE_LIMIT = get_int(
    "TG_FILESIZE_LIMIT",
    104857600,
)

BANNED_USERS = filters.user()
adminlist = {}
votemode = {}
autoclean = []
confirmer = {}

START_IMG_URL = get_env(
    "START_IMG_URL",
    "https://te.legra.ph/file/62c76ac2095332a0ede75.jpg",
)

PING_IMG_URL = get_env(
    "PING_IMG_URL",
    "https://te.legra.ph/file/4f59fb748e1990acfa297.jpg",
)

STATS_IMG_URL = get_env(
    "STATS_IMG_URL",
    "https://te.legra.ph/file/4310ea5f523520b2b765b.jpg",
)


if SUPPORT_CHANNEL and not re.match(
    r"^(?:http|https)://",
    SUPPORT_CHANNEL,
):
    raise SystemExit(
        "[ERROR] - Your SUPPORT_CHANNEL URL is invalid. "
        "It must start with https://"
    )


if SUPPORT_CHAT and not re.match(
    r"^(?:http|https)://",
    SUPPORT_CHAT,
):
    raise SystemExit(
        "[ERROR] - Your SUPPORT_CHAT URL is invalid. "
        "It must start with https://"
    )