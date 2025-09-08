"""Database operations for Whispier Bot."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId
from config import Config


class Database:
    """MongoDB database wrapper."""

    def __init__(self, client: AsyncIOMotorClient):
        self.client = client
        self.db: AsyncIOMotorDatabase = client[Config.DB_NAME]
        self.whispers: AsyncIOMotorCollection = self.db.whispers
        self.users: AsyncIOMotorCollection = self.db.users

    @classmethod
    async def create(cls, mongodb_url: str) -> 'Database':
        """Create database instance with proper SSL configuration."""
        client = AsyncIOMotorClient(
            mongodb_url,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            maxPoolSize=10,
            minPoolSize=1,
            maxIdleTimeMS=30000,
            retryWrites=True,
            w='majority',
            wtimeoutMS=5000
        )
        return cls(client)

    async def initialize(self):
        """Create indexes and setup database."""
        try:
            await self.whispers.create_index("inline_message_id", unique=True)
            await self.whispers.create_index("expires_at", expireAfterSeconds=0)
            await self.whispers.create_index([("sender_id", 1), ("created_at", -1)])
            await self.users.create_index("user_id", unique=True)
        except Exception as e:
            print(f"Index creation warning (may already exist): {e}")

    async def store_whisper(self, data: Dict[str, Any]) -> str:
        """Store whisper in database."""
        whisper_doc = {
            "inline_message_id": data["inline_message_id"],
            "content": data["content"],
            "sender_id": data["sender_id"],
            "target_username": data["target_username"],
            "target_id": data.get("target_id"),
            "created_at": datetime.utcnow(),
            "read_at": None,
            "status": "active"
        }

        result = await self.whispers.insert_one(whisper_doc)
        return str(result.inserted_id)

    async def get_whisper(self, inline_message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve whisper by inline message ID."""
        return await self.whispers.find_one({"inline_message_id": inline_message_id})

    async def mark_whisper_read(self, inline_message_id: str, reader_id: int):
        """Mark whisper as read."""
        await self.whispers.update_one(
            {"inline_message_id": inline_message_id},
            {
                "$set": {
                    "read_at": datetime.utcnow(),
                    "reader_id": reader_id,
                    "status": "read"
                }
            }
        )

    async def upsert_user(self, user_data: Dict[str, Any]):
        """Insert or update user data."""
        await self.users.update_one(
            {"user_id": user_data["user_id"]},
            {"$set": {**user_data, "last_seen": datetime.utcnow()}},
            upsert=True
        )

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return await self.users.find_one({"user_id": user_id})

    async def link_username_to_user(self, username: str, user_id: int):
        """Link username to user ID for future resolution."""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"username": username.lower()}},
            upsert=True
        )

    async def resolve_username(self, username: str) -> Optional[int]:
        """Resolve username to user ID."""
        user = await self.users.find_one({"username": username.lower()})
        return user["user_id"] if user else None

    async def close(self):
        """Close database connection."""
        if hasattr(self, 'client'):
            self.client.close()
