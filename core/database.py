"""Database operations for Whispier Bot."""
from datetime import datetime
from typing import Dict, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from config import Config


class Database:
    def __init__(self, client: AsyncIOMotorClient):
        self.client = client
        self.db: AsyncIOMotorDatabase = client[Config.DB_NAME]
        self.whispers: AsyncIOMotorCollection = self.db.whispers
        self.users: AsyncIOMotorCollection = self.db.users

    @classmethod
    async def create(cls, mongodb_url: str) -> 'Database':
        try:
            import certifi
            ca_file = certifi.where()
        except ImportError:
            ca_file = None
        
        client = AsyncIOMotorClient(
            mongodb_url,
            tls=True,
            tlsCAFile=ca_file,
            tlsAllowInvalidCertificates=False,
            tlsAllowInvalidHostnames=False,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            maxPoolSize=20,
            minPoolSize=1,
            maxIdleTimeMS=60000,
            retryWrites=True,
            w='majority',
            wtimeoutMS=5000
        )
        return cls(client)

    async def initialize(self):
        try:
            # Test connection first
            await self.client.admin.command('ping')
            print("✓ MongoDB connection successful")
            
            # Create indexes
            await self.whispers.create_index("whisper_id", unique=True)
            await self.whispers.create_index("inline_message_id")
            await self.whispers.create_index([("sender_id", 1), ("created_at", -1)])
            await self.users.create_index("user_id", unique=True)
            await self.users.create_index("username")
            print("✓ Database indexes created successfully")
        except Exception as e:
            print(f"Database initialization error: {e}")
            # Don't raise the exception to allow the app to start even if DB is temporarily unavailable

    async def store_whisper(self, data: Dict[str, Any]) -> str:
        try:
            doc = {
                "whisper_id": data["whisper_id"],            # internal id used in callback
                "inline_message_id": data.get("inline_message_id"),
                "content": data["content"],
                "sender_id": data["sender_id"],
                "target_username": data.get("target_username"),
                "target_id": data.get("target_id"),
                "original_target_token": data.get("original_target_token"),
                "created_at": datetime.utcnow(),
                "read_at": None,
                "reader_id": None,
                "status": "active"
            }
            await self.whispers.insert_one(doc)
            return data["whisper_id"]
        except Exception as e:
            print(f"Error storing whisper {data.get('whisper_id')}: {e}")
            return data["whisper_id"]  # Return ID even if storage fails

    async def attach_inline_message_id(self, whisper_id: str, inline_message_id: str):
        try:
            await self.whispers.update_one(
                {"whisper_id": whisper_id},
                {"$set": {"inline_message_id": inline_message_id}}
            )
        except Exception as e:
            print(f"Error attaching inline message ID for whisper {whisper_id}: {e}")

    async def get_whisper(self, whisper_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.whispers.find_one({"whisper_id": whisper_id})
        except Exception as e:
            print(f"Error getting whisper {whisper_id}: {e}")
            return None

    async def mark_whisper_read(self, whisper_id: str, reader_id: int):
        await self.whispers.update_one(
            {"whisper_id": whisper_id},
            {"$set": {"read_at": datetime.utcnow(), "reader_id": reader_id, "status": "read"}}
        )

    async def upsert_user(self, user_data: Dict[str, Any]):
        try:
            await self.users.update_one(
                {"user_id": user_data["user_id"]},
                {"$set": {**user_data, "last_seen": datetime.utcnow()}},
                upsert=True
            )
        except Exception as e:
            print(f"Error upserting user {user_data.get('user_id')}: {e}")
            # Don't re-raise to prevent handler failures

    async def link_username_to_user(self, username: str, user_id: int):
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"username": username.lower(), "last_seen": datetime.utcnow()}},
            upsert=True
        )

    async def resolve_username(self, username: str) -> Optional[int]:
        try:
            user = await self.users.find_one({"username": username.lower()})
            return user["user_id"] if user else None
        except Exception as e:
            print(f"Error resolving username {username}: {e}")
            return None

    async def close(self):
        if hasattr(self, 'client'):
            self.client.close()
