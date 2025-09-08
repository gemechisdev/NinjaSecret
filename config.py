"""Configuration management for Whispier Bot."""
import os
from dataclasses import dataclass


@dataclass
class Config:
    API_ID: int = int(os.environ.get("API_ID", "0"))
    API_HASH: str = os.environ.get("API_HASH", "")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
    BOT_USERNAME: str = os.environ.get("BOT_USERNAME", "whispierbot")

    # Optional userbot (session string) to resolve usernames / user ids globally
    USER_SESSION_STRING: str = os.environ.get("USER_SESSION_STRING", "").strip()

    MONGODB_URL: str = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    DB_NAME: str = os.environ.get("DB_NAME", "whispier_bot")

    PORT: int = int(os.environ.get("PORT", "8000"))
    DEV_MODE: bool = os.environ.get("DEV_MODE", "false").lower() == "true"

    @classmethod
    def validate(cls) -> bool:
        required = [cls.API_ID, cls.API_HASH, cls.BOT_TOKEN]
        return all(required) and cls.API_ID != 0
