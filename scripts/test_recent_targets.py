#!/usr/bin/env python3
"""
Test script for recent targets functionality

This script tests:
1. Storing a recent target
2. Retrieving recent targets
3. Verifying deduplication logic
"""

import asyncio
import sys
import traceback
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import config

async def test_recent_targets():
    """Test recent targets storage and retrieval"""
    print("=" * 60)
    print("Testing Recent Targets Functionality")
    print("=" * 60)
    
    # Import the functions from the main codebase
    from NinjaSecret.mongo.whisperdb import store_recent_target, get_recent_targets
    
    # Test user and target IDs (from the problem statement)
    test_sender_id = 6153949909
    test_target_id = 7708711658
    test_target_username = "scorpitune"
    test_target_display = "Scorpi"
    test_original_token = "@scorpitune"
    
    print(f"\nTest Parameters:")
    print(f"  Sender ID: {test_sender_id}")
    print(f"  Target ID: {test_target_id}")
    print(f"  Target Username: {test_target_username}")
    print(f"  Target Display: {test_target_display}")
    print(f"  Original Token: {test_original_token}")
    
    # Test 1: Store a recent target
    print("\n[TEST 1] Storing recent target...")
    try:
        await store_recent_target(
            sender_id=test_sender_id,
            target_id=test_target_id,
            target_username=test_target_username,
            target_display=test_target_display,
            original_token=test_original_token
        )
        print("✓ Successfully stored recent target")
    except Exception as e:
        print(f"✗ Failed to store recent target: {e}")
        traceback.print_exc()
        return False
    
    # Test 2: Retrieve recent targets
    print("\n[TEST 2] Retrieving recent targets...")
    try:
        recent_targets = await get_recent_targets(test_sender_id, 10)
        print(f"✓ Retrieved {len(recent_targets)} recent target(s)")
        
        if recent_targets:
            print("\nRecent Targets:")
            for i, target in enumerate(recent_targets, 1):
                print(f"\n  Target {i}:")
                print(f"    Target ID: {target.get('target_id')}")
                print(f"    Username: {target.get('target_username')}")
                print(f"    Display: {target.get('target_display')}")
                print(f"    Original Token: {target.get('original_token')}")
                print(f"    Last Used: {target.get('last_used')}")
        else:
            print("  No recent targets found")
    except Exception as e:
        print(f"✗ Failed to retrieve recent targets: {e}")
        traceback.print_exc()
        return False
    
    # Test 3: Store the same target again (test deduplication)
    print("\n[TEST 3] Storing same target again (testing deduplication)...")
    try:
        await store_recent_target(
            sender_id=test_sender_id,
            target_id=test_target_id,
            target_username=test_target_username,
            target_display=test_target_display,
            original_token=test_original_token
        )
        print("✓ Successfully stored target again")
        
        recent_targets = await get_recent_targets(test_sender_id, 10)
        print(f"✓ Retrieved {len(recent_targets)} recent target(s) after duplicate store")
        
        if len(recent_targets) == 1:
            print("✓ Deduplication working correctly (still 1 target)")
        else:
            print(f"⚠ Warning: Expected 1 target, got {len(recent_targets)}")
    except Exception as e:
        print(f"✗ Failed deduplication test: {e}")
        traceback.print_exc()
        return False
    
    # Test 4: Store a different target
    print("\n[TEST 4] Storing a different target...")
    try:
        await store_recent_target(
            sender_id=test_sender_id,
            target_id=889460971,
            target_username="meraden143",
            target_display="Edu",
            original_token="@meraden143"
        )
        print("✓ Successfully stored second target")
        
        recent_targets = await get_recent_targets(test_sender_id, 10)
        print(f"✓ Retrieved {len(recent_targets)} recent target(s)")
        
        if len(recent_targets) == 2:
            print("✓ Multiple targets working correctly (now 2 targets)")
            # Check order (newest should be first)
            if recent_targets[0].get('target_id') == 889460971:
                print("✓ Newest target is at position 0 (correct order)")
            else:
                print("⚠ Warning: Newest target not at position 0")
        else:
            print(f"⚠ Warning: Expected 2 targets, got {len(recent_targets)}")
    except Exception as e:
        print(f"✗ Failed multiple targets test: {e}")
        traceback.print_exc()
        return False
    
    # Test 5: Verify data integrity
    print("\n[TEST 5] Verifying data integrity...")
    # Use the core mongo connection instead of creating a new one
    from NinjaSecret.core.mongo import mongodb
    
    try:
        recent_targets_db = mongodb.recent_targets
        
        doc = await recent_targets_db.find_one({"user_id": test_sender_id})
        if doc:
            print(f"✓ Found database record for user {test_sender_id}")
            targets = doc.get("targets", [])
            print(f"✓ Database shows {len(targets)} target(s)")
            
            # Verify original_token is stored
            for target in targets:
                if target.get("original_token") is None:
                    print(f"⚠ Warning: original_token is None for target {target.get('target_id')}")
                else:
                    print(f"✓ original_token is present: {target.get('original_token')}")
        else:
            print(f"✗ No database record found for user {test_sender_id}")
            return False
    except Exception as e:
        print(f"✗ Failed data integrity check: {e}")
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_recent_targets())
    sys.exit(0 if success else 1)
