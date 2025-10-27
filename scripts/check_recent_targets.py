#!/usr/bin/env python3
"""
Check recent targets in the database for debugging
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
import config

async def check_recent_targets():
    """Check recent targets data"""
    client = AsyncIOMotorClient(config.MONGO_DB_URI)
    
    try:
        ninja_db = client.NinjaSecret
        recent_targets_db = ninja_db.recent_targets
        
        print("=" * 60)
        print("Recent Targets Data")
        print("=" * 60)
        
        # Get all recent targets
        cursor = recent_targets_db.find({})
        async for doc in cursor:
            user_id = doc.get("user_id")
            targets = doc.get("targets", [])
            
            print(f"\nUser ID: {user_id}")
            print(f"Number of targets: {len(targets)}")
            print("\nTargets:")
            for i, target in enumerate(targets, 1):
                print(f"  {i}. Target ID: {target.get('target_id')}")
                print(f"     Username: {target.get('target_username')}")
                print(f"     Display: {target.get('target_display')}")
                print(f"     Original Token: {target.get('original_token')}")
                print(f"     Last Used: {target.get('last_used')}")
                print()
        
        print("=" * 60)
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_recent_targets())
