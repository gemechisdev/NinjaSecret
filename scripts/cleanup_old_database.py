#!/usr/bin/env python3
"""
Database Cleanup Script for NinjaSecret

This script:
1. Removes old data from the 'whispierbot' database (if it exists)
2. Cleans up stale whisper-related collections in the NinjaSecret database
3. Ensures all collections are properly configured

Usage: python scripts/cleanup_old_database.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import config

async def cleanup_database():
    """Clean up old database and collections"""
    print("=" * 60)
    print("NinjaSecret Database Cleanup Script")
    print("=" * 60)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(config.MONGO_DB_URI)
    
    try:
        # List all databases
        databases = await client.list_database_names()
        print(f"\nFound databases: {databases}")
        
        # 1. Drop old databases if they exist
        old_databases = ['whispierbot', 'whispier_bot']
        for old_db in old_databases:
            if old_db in databases:
                print(f"\n[STEP 1] Dropping old '{old_db}' database...")
                await client.drop_database(old_db)
                print(f"✓ Dropped '{old_db}' database")
            else:
                print(f"\n[STEP 1] No '{old_db}' database found (already clean)")
        
        # 2. Clean up NinjaSecret database collections related to whispers
        ninja_db = client.NinjaSecret
        collections = await ninja_db.list_collection_names()
        print(f"\n[STEP 2] Found collections in NinjaSecret database: {collections}")
        
        # Collections to clean (keep structure, remove old data)
        whisper_collections = [
            'whispers',
            'whisper_stats', 
            'whisper_achievements',
            'recent_targets'
        ]
        
        for collection_name in whisper_collections:
            if collection_name in collections:
                collection = ninja_db[collection_name]
                count_before = await collection.count_documents({})
                
                print(f"\n[STEP 3] Cleaning '{collection_name}' collection...")
                print(f"  - Documents before cleanup: {count_before}")
                
                # For recent_targets, clean all old data to start fresh
                if collection_name == 'recent_targets':
                    print(f"  🧹 Clearing all old recent_targets data to start fresh...")
                    result = await collection.delete_many({})
                    print(f"  - Removed {result.deleted_count} old entries")
                    print(f"  ✓ recent_targets collection is now clean (will rebuild from fresh usage)")
                elif collection_name in ['whispers', 'whisper_stats', 'whisper_achievements']:
                    # For these, you might want to clean old data
                    # For now, just report
                    print(f"  ℹ Collection exists with {count_before} documents")
                    # Uncomment below to clean all data:
                    # result = await collection.delete_many({})
                    # print(f"  - Removed {result.deleted_count} documents")
                
                count_after = await collection.count_documents({})
                print(f"  - Documents after cleanup: {count_after}")
            else:
                print(f"\n[STEP 3] Collection '{collection_name}' not found (will be created on first use)")
        
        # 4. Verify the configuration
        print("\n" + "=" * 60)
        print("Database Configuration Verification")
        print("=" * 60)
        print(f"MongoDB URI: {config.MONGO_DB_URI[:50]}...")
        print(f"Target Database: NinjaSecret")
        print(f"Bot Name: {config.BOT_NAME}")
        print(f"Owner ID: {config.OWNER_ID}")
        
        # 5. Create indexes for better performance
        print("\n[STEP 4] Creating indexes for better performance...")
        
        # Index for recent_targets
        recent_targets_db = ninja_db.recent_targets
        await recent_targets_db.create_index("user_id", unique=True)
        print("✓ Created index on recent_targets.user_id")
        
        # Index for whispers
        whispers_db = ninja_db.whispers
        await whispers_db.create_index("whisper_id", unique=True)
        await whispers_db.create_index("sender_id")
        await whispers_db.create_index("inline_message_id")
        print("✓ Created indexes on whispers collection")
        
        # Index for users cache
        users_db = ninja_db.users
        await users_db.create_index("user_id", unique=True)
        await users_db.create_index("username")
        print("✓ Created indexes on users collection")
        
        print("\n" + "=" * 60)
        print("✓ Database cleanup completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start the bot")
        print("2. Test the inline query with recent targets")
        print("3. Send a secret to verify recent targets are stored correctly")
        
    except Exception as e:
        print(f"\n✗ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()
    
    return True

if __name__ == "__main__":
    print("\nStarting database cleanup...")
    success = asyncio.run(cleanup_database())
    sys.exit(0 if success else 1)
