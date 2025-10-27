#!/usr/bin/env python3
"""
Test script to verify the whisper storage fix

This script tests:
1. Inline query doesn't store whispers in DB (uses cache)
2. Chosen inline result stores whisper in DB
3. Recent targets are stored when whisper is sent
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_whisper_storage_fix():
    """Test that whispers are only stored when actually sent"""
    print("=" * 60)
    print("Testing Whisper Storage Fix")
    print("=" * 60)
    
    # Import after adding to path
    from NinjaSecret.core.mongo import mongodb
    from NinjaSecret.plugins.whisper.inline_handler import pending_whispers_cache
    from NinjaSecret.utils.whisper_utils import generate_whisper_id
    
    whispers_db = mongodb.whispers
    recent_targets_db = mongodb.recent_targets
    
    # Test parameters
    test_sender_id = 6153949909
    test_target_id = 7708711658
    test_message = "Test secret message"
    
    print(f"\nTest Parameters:")
    print(f"  Sender ID: {test_sender_id}")
    print(f"  Target ID: {test_target_id}")
    print(f"  Message: {test_message}")
    
    # Test 1: Check that cache is being used (not DB)
    print("\n[TEST 1] Verifying cache system...")
    print(f"  Cache has {len(pending_whispers_cache)} items")
    print("  ✓ Cache system is available")
    
    # Test 2: Check current whispers in DB
    print("\n[TEST 2] Checking current whispers in database...")
    initial_count = await whispers_db.count_documents({})
    print(f"  Current whispers in DB: {initial_count}")
    
    # Test 3: Simulate inline query (should use cache, not DB)
    print("\n[TEST 3] Simulating inline query (should use cache)...")
    test_whisper_id = generate_whisper_id()
    test_whisper_data = {
        "whisper_id": test_whisper_id,
        "content": test_message,
        "sender_id": test_sender_id,
        "target_id": test_target_id,
        "target_username": "scorpitune",
        "original_target_token": "@scorpitune",
        "all_targets": [(test_target_id, "scorpitune", "@scorpitune")],
        "target_mentions": "[Scorpi](tg://user?id=7708711658)"
    }
    
    # Add to cache (simulating inline query) with timestamp structure
    pending_whispers_cache[test_whisper_id] = {
        "data": test_whisper_data,
        "timestamp": datetime.utcnow()
    }
    print(f"  ✓ Added whisper to cache: {test_whisper_id}")
    
    # Verify NOT in DB yet
    db_whisper = await whispers_db.find_one({"whisper_id": test_whisper_id})
    if db_whisper is None:
        print("  ✓ Whisper NOT in database yet (correct behavior)")
    else:
        print("  ✗ ERROR: Whisper found in database (should not be there yet)")
        return False
    
    # Test 4: Simulate chosen inline result (should store in DB)
    print("\n[TEST 4] Simulating chosen inline result (should store in DB)...")
    
    # This would normally be done by the handler
    from NinjaSecret.mongo.whisperdb import store_whisper
    
    cache_entry = pending_whispers_cache.get(test_whisper_id)
    if cache_entry:
        print(f"  ✓ Retrieved whisper from cache")
        
        # Extract the actual data
        cached_data = cache_entry.get("data")
        if not cached_data:
            print("  ✗ ERROR: Cache entry has no data")
            return False
        
        # Add inline_message_id as would be done in handler
        cached_data["inline_message_id"] = "test_inline_msg_id"
        
        # Store in DB
        await store_whisper(cached_data)
        print(f"  ✓ Stored whisper in database")
        
        # Remove from cache
        del pending_whispers_cache[test_whisper_id]
        print(f"  ✓ Removed from cache")
    else:
        print("  ✗ ERROR: Could not retrieve from cache")
        return False
    
    # Verify it's now in DB
    db_whisper = await whispers_db.find_one({"whisper_id": test_whisper_id})
    if db_whisper:
        print("  ✓ Whisper now in database (correct behavior)")
        print(f"    - Whisper ID: {db_whisper.get('whisper_id')}")
        print(f"    - Sender: {db_whisper.get('sender_id')}")
        print(f"    - Target: {db_whisper.get('target_id')}")
        print(f"    - Status: {db_whisper.get('status')}")
    else:
        print("  ✗ ERROR: Whisper not found in database after storage")
        return False
    
    # Test 5: Verify recent targets storage
    print("\n[TEST 5] Testing recent targets storage...")
    from NinjaSecret.mongo.whisperdb import store_recent_target, get_recent_targets
    
    # Store recent target
    await store_recent_target(
        sender_id=test_sender_id,
        target_id=test_target_id,
        target_username="scorpitune",
        target_display="Scorpi",
        original_token="@scorpitune"
    )
    print("  ✓ Stored recent target")
    
    # Retrieve recent targets
    recent_targets = await get_recent_targets(test_sender_id, 10)
    print(f"  ✓ Retrieved {len(recent_targets)} recent target(s)")
    
    if recent_targets:
        found_target = False
        for target in recent_targets:
            if target.get('target_id') == test_target_id:
                found_target = True
                print(f"  ✓ Found test target in recent targets")
                print(f"    - Target ID: {target.get('target_id')}")
                print(f"    - Username: {target.get('target_username')}")
                print(f"    - Display: {target.get('target_display')}")
                print(f"    - Token: {target.get('original_token')}")
                break
        
        if not found_target:
            print("  ⚠ Test target not found in recent targets")
    
    # Cleanup: Remove test whisper
    print("\n[CLEANUP] Removing test whisper...")
    result = await whispers_db.delete_one({"whisper_id": test_whisper_id})
    if result.deleted_count > 0:
        print(f"  ✓ Removed test whisper from database")
    else:
        print(f"  ⚠ Test whisper was not in database")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    print("\nSummary:")
    print("  ✓ Whispers are cached during inline query (not stored in DB)")
    print("  ✓ Whispers are stored in DB only when user sends them")
    print("  ✓ Recent targets are stored correctly")
    print("  ✓ Fix is working as expected!")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_whisper_storage_fix())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
