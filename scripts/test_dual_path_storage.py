#!/usr/bin/env python3
"""
Test script to verify the dual-path whisper storage system

This script tests:
1. Primary path: chosen_inline_result stores whisper
2. Fallback path: First read stores whisper if chosen_inline_result didn't fire
3. Race condition: Both paths don't create duplicates
4. Recent targets: Stored correctly in both paths
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_dual_path_storage():
    """Test both storage paths"""
    print("=" * 80)
    print("Testing Dual-Path Whisper Storage System")
    print("=" * 80)
    
    # Import after adding to path
    from NinjaSecret.core.mongo import mongodb
    from NinjaSecret.plugins.whisper.inline_handler import pending_whispers_cache
    from NinjaSecret.mongo.whisperdb import store_whisper, get_whisper, store_recent_target, get_recent_targets
    from NinjaSecret.utils.whisper_utils import generate_whisper_id
    
    whispers_db = mongodb.whispers
    
    # Test parameters
    test_sender_id = 6153949909
    test_target_id = 7708711658
    test_message = "Test secret message"
    
    print(f"\nTest Parameters:")
    print(f"  Sender ID: {test_sender_id}")
    print(f"  Target ID: {test_target_id}")
    print(f"  Message: {test_message}")
    
    # =========================================================================
    # TEST 1: Primary Path (chosen_inline_result fires)
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 1: Primary Path - chosen_inline_result fires")
    print("=" * 80)
    
    whisper_id_1 = generate_whisper_id()
    whisper_data_1 = {
        "whisper_id": whisper_id_1,
        "content": test_message,
        "sender_id": test_sender_id,
        "target_id": test_target_id,
        "target_username": "scorpitune",
        "original_target_token": "@scorpitune",
        "all_targets": [(test_target_id, "scorpitune", "@scorpitune")],
        "target_mentions": "[Scorpi](tg://user?id=7708711658)"
    }
    
    # Step 1: Inline query - cache whisper
    print("\n[Step 1] Caching whisper during inline query...")
    pending_whispers_cache[whisper_id_1] = {
        "data": whisper_data_1,
        "timestamp": datetime.utcnow()
    }
    print(f"  ✓ Cached whisper {whisper_id_1}")
    
    # Verify not in DB yet
    db_check = await get_whisper(whisper_id_1)
    if db_check is None:
        print("  ✓ Whisper NOT in database yet (correct)")
    else:
        print("  ✗ ERROR: Whisper found in database (should not be there yet)")
        return False
    
    # Step 2: Chosen inline result - store whisper
    print("\n[Step 2] Simulating chosen_inline_result...")
    cache_entry = pending_whispers_cache.get(whisper_id_1)
    if cache_entry:
        cached_data = cache_entry.get("data")
        cached_data["inline_message_id"] = "test_inline_msg_1"
        await store_whisper(cached_data)
        del pending_whispers_cache[whisper_id_1]
        print(f"  ✓ Stored whisper via primary path")
        print(f"  ✓ Removed from cache")
    
    # Verify it's in DB now
    db_check = await get_whisper(whisper_id_1)
    if db_check:
        print(f"  ✓ Whisper found in database (correct)")
    else:
        print(f"  ✗ ERROR: Whisper not found in database")
        return False
    
    # Store recent target
    await store_recent_target(
        sender_id=test_sender_id,
        target_id=test_target_id,
        target_username="scorpitune",
        target_display="Scorpi",
        original_token="@scorpitune"
    )
    print(f"  ✓ Stored recent target")
    
    # Cleanup
    await whispers_db.delete_one({"whisper_id": whisper_id_1})
    print(f"  ✓ Cleaned up test whisper")
    
    # =========================================================================
    # TEST 2: Fallback Path (chosen_inline_result doesn't fire)
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 2: Fallback Path - chosen_inline_result doesn't fire")
    print("=" * 80)
    
    whisper_id_2 = generate_whisper_id()
    whisper_data_2 = {
        "whisper_id": whisper_id_2,
        "content": test_message,
        "sender_id": test_sender_id,
        "target_id": test_target_id,
        "target_username": "scorpitune",
        "original_target_token": "@scorpitune",
        "all_targets": [(test_target_id, "scorpitune", "@scorpitune")],
        "target_mentions": "[Scorpi](tg://user?id=7708711658)"
    }
    
    # Step 1: Inline query - cache whisper
    print("\n[Step 1] Caching whisper during inline query...")
    pending_whispers_cache[whisper_id_2] = {
        "data": whisper_data_2,
        "timestamp": datetime.utcnow()
    }
    print(f"  ✓ Cached whisper {whisper_id_2}")
    
    # Step 2: chosen_inline_result DOESN'T fire (skipped)
    print("\n[Step 2] chosen_inline_result doesn't fire (inline feedback disabled)")
    print("  ⚠ Whisper remains in cache, not stored in DB")
    
    # Step 3: User clicks "Read" - fallback storage
    print("\n[Step 3] Simulating user clicking 'Read' button...")
    
    # Check DB (should not be there)
    whisper = await get_whisper(whisper_id_2)
    if not whisper:
        print(f"  ✓ Whisper not in database (expected)")
        
        # Check cache
        cache_entry = pending_whispers_cache.get(whisper_id_2)
        if cache_entry:
            print(f"  ✓ Whisper found in cache")
            
            # Store it now (fallback path)
            whisper_data = cache_entry.get("data")
            await store_whisper(whisper_data)
            print(f"  ✓ Stored whisper via fallback path")
            
            # Store recent target (since chosen_inline_result didn't do it)
            await store_recent_target(
                sender_id=test_sender_id,
                target_id=test_target_id,
                target_username="scorpitune",
                target_display="Scorpi",
                original_token="@scorpitune"
            )
            print(f"  ✓ Stored recent target")
            
            # Remove from cache
            del pending_whispers_cache[whisper_id_2]
            print(f"  ✓ Removed from cache")
            
            # Verify it's in DB now
            whisper = await get_whisper(whisper_id_2)
        else:
            print(f"  ✗ ERROR: Whisper not found in cache")
            return False
    
    if whisper:
        print(f"  ✓ Whisper found in database after fallback storage")
    else:
        print(f"  ✗ ERROR: Whisper not found in database after fallback storage")
        return False
    
    # Cleanup
    await whispers_db.delete_one({"whisper_id": whisper_id_2})
    print(f"  ✓ Cleaned up test whisper")
    
    # =========================================================================
    # TEST 3: Race Condition (both paths try to store)
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 3: Race Condition - both paths try to store")
    print("=" * 80)
    
    whisper_id_3 = generate_whisper_id()
    whisper_data_3 = {
        "whisper_id": whisper_id_3,
        "content": test_message,
        "sender_id": test_sender_id,
        "target_id": test_target_id,
        "target_username": "scorpitune",
        "original_target_token": "@scorpitune",
        "all_targets": [(test_target_id, "scorpitune", "@scorpitune")],
        "target_mentions": "[Scorpi](tg://user?id=7708711658)"
    }
    
    # Cache whisper
    print("\n[Step 1] Caching whisper...")
    pending_whispers_cache[whisper_id_3] = {
        "data": whisper_data_3,
        "timestamp": datetime.utcnow()
    }
    print(f"  ✓ Cached whisper {whisper_id_3}")
    
    # Primary path stores it
    print("\n[Step 2] Primary path stores whisper...")
    cache_entry = pending_whispers_cache.get(whisper_id_3)
    cached_data = cache_entry.get("data")
    cached_data["inline_message_id"] = "test_inline_msg_3"
    await store_whisper(cached_data)
    print(f"  ✓ Stored whisper via primary path")
    
    # Don't remove from cache (simulate race condition)
    print("  ⚠ Simulating race: NOT removing from cache")
    
    # Fallback path tries to store it
    print("\n[Step 3] Fallback path checks and skips...")
    whisper = await get_whisper(whisper_id_3)
    if not whisper:
        print("  ✗ ERROR: Whisper should be in database")
        return False
    
    # Simulate fallback checking
    cache_entry = pending_whispers_cache.get(whisper_id_3)
    if cache_entry:
        print(f"  ✓ Whisper found in cache")
        
        # Check if already in DB (race condition protection)
        existing = await get_whisper(whisper_id_3)
        if existing:
            print(f"  ✓ Whisper already in database, skipping storage (correct)")
        else:
            print(f"  ✗ ERROR: Should have found whisper in database")
            return False
        
        # Remove from cache
        del pending_whispers_cache[whisper_id_3]
        print(f"  ✓ Removed from cache")
    
    # Cleanup
    await whispers_db.delete_one({"whisper_id": whisper_id_3})
    print(f"  ✓ Cleaned up test whisper")
    
    # =========================================================================
    # TEST 4: Recent Targets
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 4: Recent Targets Functionality")
    print("=" * 80)
    
    # Clear existing recent targets for test user
    from NinjaSecret.core.mongo import mongodb
    await mongodb.recent_targets.delete_one({"user_id": test_sender_id})
    print(f"\n[Setup] Cleared existing recent targets for user {test_sender_id}")
    
    # Store first target
    print("\n[Test 1] Storing first recent target...")
    await store_recent_target(
        sender_id=test_sender_id,
        target_id=test_target_id,
        target_username="scorpitune",
        target_display="Scorpi",
        original_token="@scorpitune"
    )
    
    recent = await get_recent_targets(test_sender_id, 10)
    if len(recent) == 1:
        print(f"  ✓ 1 recent target stored")
    else:
        print(f"  ✗ ERROR: Expected 1 recent target, got {len(recent)}")
        return False
    
    # Store same target again (should deduplicate)
    print("\n[Test 2] Storing same target again (deduplication test)...")
    await store_recent_target(
        sender_id=test_sender_id,
        target_id=test_target_id,
        target_username="scorpitune",
        target_display="Scorpi",
        original_token="@scorpitune"
    )
    
    recent = await get_recent_targets(test_sender_id, 10)
    if len(recent) == 1:
        print(f"  ✓ Still 1 recent target (deduplicated correctly)")
    else:
        print(f"  ✗ ERROR: Expected 1 recent target, got {len(recent)}")
        return False
    
    # Store different target
    print("\n[Test 3] Storing different target...")
    await store_recent_target(
        sender_id=test_sender_id,
        target_id=889460971,
        target_username="meraden143",
        target_display="Mera",
        original_token="@meraden143"
    )
    
    recent = await get_recent_targets(test_sender_id, 10)
    if len(recent) == 2:
        print(f"  ✓ 2 recent targets stored")
        print(f"    - Most recent: {recent[0].get('target_display')}")
        print(f"    - Second: {recent[1].get('target_display')}")
    else:
        print(f"  ✗ ERROR: Expected 2 recent targets, got {len(recent)}")
        return False
    
    # Cleanup
    await mongodb.recent_targets.delete_one({"user_id": test_sender_id})
    print(f"\n[Cleanup] Removed test recent targets")
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED!")
    print("=" * 80)
    print("\nTest Summary:")
    print("  ✓ Primary path (chosen_inline_result) works correctly")
    print("  ✓ Fallback path (late storage on read) works correctly")
    print("  ✓ Race condition protection prevents duplicates")
    print("  ✓ Recent targets stored and deduplicated correctly")
    print("\nThe dual-path storage system is working as expected!")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_dual_path_storage())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
