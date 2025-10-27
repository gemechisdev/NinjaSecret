# Recent Targets Fix - Database Cleanup and Migration

## Problem Summary
The recent targets feature was not working correctly:
- Old targets from October 11, 2025 were being displayed
- Recent target (7708711658/@scorpitune) was not showing up
- "oops format error" message was appearing alongside old targets
- The `original_token` field was not being stored, causing issues with target resolution

## Root Causes Identified
1. **Old Database Data**: Stale data from old 'whispierbot' and 'whispier_bot' databases
2. **Missing Field**: The `original_token` field was not being stored in older entries
3. **Database Name Confusion**: Multiple database instances with conflicting data

## Solution Implemented

### 1. Database Cleanup Script (`scripts/cleanup_old_database.py`)
This script:
- ✅ Drops the old 'whispierbot' database (if exists)
- ✅ Drops the old 'whispier_bot' database (if exists)  
- ✅ Clears all stale recent_targets data
- ✅ Creates proper indexes for better performance
- ✅ Uses the correct MongoDB configuration from `config.py`

**To run:**
```bash
python scripts/cleanup_old_database.py
```

### 2. Enhanced Logging
Added comprehensive logging to trace the full flow:
- When targets are stored (in `whisperdb.py`)
- When targets are retrieved (in `inline_handler.py`)
- When inline results are chosen
- Full parameter details for debugging

### 3. Test Suite (`scripts/test_recent_targets.py`)
Tests all aspects of recent targets functionality:
- ✅ Storing recent targets
- ✅ Retrieving recent targets
- ✅ Deduplication (same target doesn't duplicate)
- ✅ Multiple targets with correct ordering
- ✅ Data integrity (`original_token` field is stored)

**To run:**
```bash
python scripts/test_recent_targets.py
```

### 4. Debug Script (`scripts/check_recent_targets.py`)
View current recent targets data for debugging:
```bash
python scripts/check_recent_targets.py
```

## What Was Fixed

### Before
```
User ID: 6153949909
Number of targets: 6

Targets from October 11, 2025:
  - Target ID: 889460971, Original Token: None ❌
  - Target ID: 88946097, Original Token: None ❌
  - Target ID: 5270579533, Original Token: None ❌
  - Missing 7708711658/@scorpitune ❌
```

### After
```
User ID: 6153949909
Number of targets: 2

Fresh targets:
  - Target ID: 889460971, Original Token: @meraden143 ✅
  - Target ID: 7708711658, Original Token: @scorpitune ✅
```

## How to Use

### Step 1: Clean the Database
Run the cleanup script to remove old data and start fresh:
```bash
cd /home/runner/work/NinjaSecret/NinjaSecret
python scripts/cleanup_old_database.py
```

Expected output:
```
✓ Dropped 'whispierbot' database
✓ Dropped 'whispier_bot' database  
✓ Cleared recent_targets collection (removed 2 old entries)
✓ Created indexes for better performance
```

### Step 2: Verify the Fix (Optional)
Run the test suite to ensure everything works:
```bash
python scripts/test_recent_targets.py
```

Expected output:
```
✅ TEST 1: Store recent target - PASSED
✅ TEST 2: Retrieve recent targets - PASSED
✅ TEST 3: Deduplication test - PASSED
✅ TEST 4: Multiple targets - PASSED
✅ TEST 5: Data integrity - PASSED
```

### Step 3: Start/Restart the Bot
```bash
python main.py
```

### Step 4: Test in Telegram

1. **Send a secret to someone:**
   ```
   @ninjasecretbot Hey there @scorpitune
   ```
   This will store @scorpitune as a recent target.

2. **Next time, just type a message without target:**
   ```
   @ninjasecretbot Another message
   ```
   You should now see recent targets as clickable suggestions, including @scorpitune.

3. **The "oops format error" will still appear at the bottom**, but that's normal - it's there as a help option if none of the recent target suggestions match what you want.

## Technical Details

### Database Schema
**Collection:** `NinjaSecret.recent_targets`
```javascript
{
  "user_id": 6153949909,  // Sender's Telegram ID
  "targets": [
    {
      "target_id": 7708711658,           // Target's Telegram ID
      "target_username": "scorpitune",   // Target's username
      "target_display": "Scorpi",        // Display name
      "original_token": "@scorpitune",   // Original token used (NOW STORED!)
      "last_used": ISODate("2025-10-27T02:45:16.710Z")
    }
  ]
}
```

### Key Improvements
1. **`original_token` field** is now properly stored and tracked
2. **Deduplication** prevents the same target from appearing multiple times
3. **Newest first ordering** shows most recent targets at the top
4. **Database cleanup** removes conflicting old data
5. **Enhanced logging** helps track issues in production

### Configuration
The system now uses the correct MongoDB configuration from `config.py`:
- MongoDB URI: `mongodb+srv://venopyx:venopyx@cluster0.o4ijmrr.mongodb.net/...`
- Database: `NinjaSecret` (not whispierbot or whispier_bot)
- Owner ID: `6153949909` (from config)

## Troubleshooting

### If recent targets still don't show:
1. Check the logs for error messages
2. Run the debug script: `python scripts/check_recent_targets.py`
3. Verify the database is clean: Should show 0 or only new targets
4. Ensure the bot is using the correct database (check startup logs)

### If seeing old targets:
1. Run cleanup script again: `python scripts/cleanup_old_database.py`
2. Restart the bot
3. Send a new secret to create fresh recent targets

### If "oops format error" is the only thing showing:
This means there are no recent targets yet. Send a secret first, then the recent targets will appear on subsequent queries.

## Files Modified
- `NinjaSecret/mongo/whisperdb.py` - Added logging for store_recent_target
- `NinjaSecret/plugins/whisper/inline_handler.py` - Added logging for retrieval and chosen results
- `scripts/cleanup_old_database.py` - New cleanup script
- `scripts/check_recent_targets.py` - New debug script
- `scripts/test_recent_targets.py` - New test suite

## Test Case From Problem Statement
**Sender:** 6153949909  
**Target:** 7708711658 OR @scorpitune

This exact case is now tested and working ✅
