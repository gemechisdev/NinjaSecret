"""
Ninja Secret🥷 Database Models
Handles secret message storage, targeting, timers, and burn-after-reading functionality
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from NinjaSecret.core.mongo import mongodb
from NinjaSecret.logging import LOGGER

# Get logger for this module
logger = LOGGER(__name__)

# Constants
MAX_RECENT_TARGETS = 10  # Maximum number of recent targets to store per user

# Collections
whisperdb = mongodb.whispers
whisper_stats = mongodb.whisper_stats
whisper_achievements = mongodb.whisper_achievements

async def store_whisper(data: Dict) -> str:
    """Store a new whisper message with optional special features support"""
    try:
        logger.info(f"Storing whisper {data.get('whisper_id')} for sender {data.get('sender_id')}")
        
        whisper_data = {
            "whisper_id": data["whisper_id"],
            "inline_message_id": data.get("inline_message_id"),
            "content": data["content"],
            "sender_id": data["sender_id"],
            "target_username": data.get("target_username"),
            "target_id": data.get("target_id"),
            "original_target_token": data.get("original_target_token"),
            "all_targets": data.get("all_targets"),  # Store all targets for recent targets history
            "target_mentions": data.get("target_mentions"),  # Store formatted mentions
            "created_at": datetime.utcnow(),
            "read_at": None,
            "reader_id": None,
            "status": "active"
        }

        # Add special features settings if provided
        if data.get("modifiers"):
            settings = {}
            modifiers = data["modifiers"]

            # Handle timer expiration
            if modifiers.get("timer"):
                expires_at = datetime.utcnow() + timedelta(seconds=modifiers["timer"])
                settings["expires_at"] = expires_at

            # Handle burn after reading
            if modifiers.get("burn_after_reading"):
                settings["burn_after_reading"] = True

            # Handle styling
            if modifiers.get("style"):
                settings["style"] = modifiers["style"]

            if settings:
                whisper_data["settings"] = settings

        await whisperdb.insert_one(whisper_data)
        logger.info(f"Successfully inserted whisper {data['whisper_id']} into database")
        return data["whisper_id"]
    except Exception as e:
        logger.exception(f"Error storing whisper {data.get('whisper_id')}: {e}")
        raise

async def attach_inline_message_id(whisper_id: str, inline_message_id: str):
    """Attach inline_message_id to a whisper after it's chosen"""
    await whisperdb.update_one(
        {"whisper_id": whisper_id},
        {"$set": {"inline_message_id": inline_message_id}}
    )

async def get_whisper(whisper_id: str) -> Optional[Dict]:
    """Get whisper message by whisper_id"""
    try:
        logger.debug(f"Looking up whisper {whisper_id} in database")
        whisper = await whisperdb.find_one({"whisper_id": whisper_id})
        if whisper:
            logger.debug(f"Found whisper {whisper_id} in database, status: {whisper.get('status')}")
        else:
            logger.warning(f"Whisper {whisper_id} not found in database")
        return whisper
    except Exception as e:
        logger.exception(f"Error retrieving whisper {whisper_id}: {e}")
        return None

async def mark_whisper_read(whisper_id: str, reader_id: int):
    """Mark whisper as read"""
    await whisperdb.update_one(
        {"whisper_id": whisper_id},
        {"$set": {
            "read_at": datetime.utcnow(),
            "reader_id": reader_id,
            "status": "read"
        }}
    )

async def get_whisper_message(inline_message_id: str) -> Optional[Dict]:
    """Get whisper message by inline message ID"""
    whisper = await whisperdb.find_one({"inline_message_id": inline_message_id})

    # Check if message has expired
    if whisper and whisper.get("settings", {}).get("expires_at"):
        if datetime.utcnow() > whisper["settings"]["expires_at"]:
            await mark_whisper_expired(inline_message_id)
            return None

    return whisper

async def get_whisper_by_id(whisper_id: str) -> Optional[Dict]:
    """Get whisper message by whisper ID (UUID)"""
    whisper = await whisperdb.find_one({"whisper_id": whisper_id})

    # Check if message has expired
    if whisper and whisper.get("settings", {}).get("expires_at"):
        if datetime.utcnow() > whisper["settings"]["expires_at"]:
            await mark_whisper_expired(whisper["inline_message_id"])
            return None

    return whisper

async def mark_whisper_read_by_inline_id(inline_message_id: str, user_id: int) -> bool:
    """Mark whisper as read by a user using inline message ID"""
    whisper = await get_whisper_message(inline_message_id)
    if not whisper:
        return False

    # Update target read status
    targets = whisper.get("targets", [])
    for target in targets:
        if target.get("resolved_id") == user_id and not target.get("read_at"):
            target["read_at"] = datetime.utcnow()

    # Check if all targets have read (for burn after reading)
    all_read = all(target.get("read_at") is not None for target in targets)

    # Update analytics
    await whisperdb.update_one(
        {"inline_message_id": inline_message_id},
        {
            "$set": {"targets": targets},
            "$inc": {"analytics.completed_reads": 1}
        }
    )

    # Burn message if all have read and burn_after_reading is enabled
    if all_read and whisper.get("settings", {}).get("burn_after_reading"):
        await mark_whisper_burned(inline_message_id)
        return True

    return False

async def mark_whisper_burned(inline_message_id: str):
    """Mark whisper as burned (deleted after all read)"""
    await whisperdb.update_one(
        {"inline_message_id": inline_message_id},
        {"$set": {"status": "burned"}}
    )

async def mark_whisper_expired(inline_message_id: str):
    """Mark whisper as expired"""
    await whisperdb.update_one(
        {"inline_message_id": inline_message_id},
        {"$set": {"status": "expired"}}
    )

async def increment_whisper_view(inline_message_id: str):
    """Increment view count for analytics"""
    await whisperdb.update_one(
        {"inline_message_id": inline_message_id},
        {"$inc": {"analytics.views": 1}}
    )

async def increment_whisper_click(inline_message_id: str):
    """Increment click count for analytics"""
    await whisperdb.update_one(
        {"inline_message_id": inline_message_id},
        {"$inc": {"analytics.clicks": 1}}
    )

async def increment_whisper_click_by_id(whisper_id: str):
    """Increment click count for analytics by whisper ID"""
    await whisperdb.update_one(
        {"whisper_id": whisper_id},
        {"$inc": {"analytics.clicks": 1}}
    )

async def increment_whisper_view_by_id(whisper_id: str):
    """Increment view count for analytics by whisper ID"""
    await whisperdb.update_one(
        {"whisper_id": whisper_id},
        {"$inc": {"analytics.views": 1}}
    )

async def mark_whisper_read_complex(whisper_id: str, user_id: int) -> bool:
    """Mark whisper as read by a user using whisper ID (complex targets system)"""
    whisper = await get_whisper_by_id(whisper_id)
    if not whisper:
        return False

    # Update target read status
    targets = whisper.get("targets", [])
    for target in targets:
        if target.get("resolved_id") == user_id and not target.get("read_at"):
            target["read_at"] = datetime.utcnow()

    # Check if all targets have read (for burn after reading)
    all_read = all(target.get("read_at") is not None for target in targets)

    # Update analytics
    await whisperdb.update_one(
        {"whisper_id": whisper_id},
        {
            "$set": {"targets": targets},
            "$inc": {"analytics.completed_reads": 1}
        }
    )

    # Burn message if all have read and burn_after_reading is enabled
    if all_read and whisper.get("settings", {}).get("burn_after_reading"):
        await whisperdb.update_one(
            {"whisper_id": whisper_id},
            {"$set": {"status": "burned"}}
        )
        return True

    return False

async def is_user_target(inline_message_id: str, user_id: int) -> bool:
    """Check if user is a target for this whisper"""
    whisper = await get_whisper_message(inline_message_id)
    if not whisper:
        return False

    targets = whisper.get("targets", [])

    # Check for @all or @everyone
    for target in targets:
        if target.get("type") == "all":
            return True
        if target.get("resolved_id") == user_id:
            return True

    return False

async def is_user_target_by_id(whisper_id: str, user_id: int) -> bool:
    """Check if user is a target for this whisper by whisper ID"""
    whisper = await get_whisper_by_id(whisper_id)
    if not whisper:
        return False

    targets = whisper.get("targets", [])

    # Check for @all or @everyone
    for target in targets:
        if target.get("type") == "all":
            return True
        if target.get("resolved_id") == user_id:
            return True

    return False

async def cleanup_expired_whispers():
    """Clean up expired whispers (run periodically)"""
    current_time = datetime.utcnow()

    # Find and mark expired whispers
    expired_whispers = whisperdb.find({
        "settings.expires_at": {"$lt": current_time},
        "status": "active"
    })

    count = 0
    async for whisper in expired_whispers:
        await mark_whisper_expired(whisper["inline_message_id"])
        count += 1

    return count

# User Statistics Functions
async def get_user_whisper_stats(user_id: int) -> Dict:
    """Get user's whisper statistics"""
    stats = await whisper_stats.find_one({"user_id": user_id})
    if not stats:
        # Initialize default stats
        default_stats = {
            "user_id": user_id,
            "secrets_sent": 0,
            "secrets_received": 0,
            "secrets_burned": 0,
            "secrets_timed": 0,
            "total_targets_reached": 0,
            "favorite_targets": {},  # {user_id: count}
            "weekly_stats": {
                "secrets_sent": 0,
                "secrets_received": 0,
                "week_start": datetime.utcnow()
            },
            "achievements": []
        }
        await whisper_stats.insert_one(default_stats)
        return default_stats

    return stats

async def update_user_stats(user_id: int, stat_type: str, increment: int = 1, **kwargs):
    """Update user statistics"""
    stats = await get_user_whisper_stats(user_id)

    # Reset weekly stats if needed
    week_start = stats.get("weekly_stats", {}).get("week_start", datetime.utcnow())
    if datetime.utcnow() - week_start > timedelta(days=7):
        await whisper_stats.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "weekly_stats.secrets_sent": 0,
                    "weekly_stats.secrets_received": 0,
                    "weekly_stats.week_start": datetime.utcnow()
                }
            }
        )

    # Update specific stat
    update_data = {f"$inc": {stat_type: increment}}

    # Handle special cases
    if stat_type == "secrets_sent" and "targets" in kwargs:
        update_data["$inc"]["total_targets_reached"] = len(kwargs["targets"])
        update_data["$inc"]["weekly_stats.secrets_sent"] = increment

        # Update favorite targets
        favorite_targets = stats.get("favorite_targets", {})
        for target_id in kwargs["targets"]:
            target_key = f"favorite_targets.{target_id}"
            if target_key not in update_data.get("$inc", {}):
                update_data["$inc"][target_key] = 0
            update_data["$inc"][target_key] += 1

    elif stat_type == "secrets_received":
        update_data["$inc"]["weekly_stats.secrets_received"] = increment

    await whisper_stats.update_one(
        {"user_id": user_id},
        update_data,
        upsert=True
    )

async def get_top_whisper_users(limit: int = 10) -> List[Dict]:
    """Get top whisper users by secrets sent"""
    pipeline = [
        {"$sort": {"secrets_sent": -1}},
        {"$limit": limit}
    ]

    top_users = []
    async for user in whisper_stats.aggregate(pipeline):
        top_users.append(user)

    return top_users

# Achievement System
async def check_and_award_achievements(user_id: int):
    """Check and award achievements to user"""
    stats = await get_user_whisper_stats(user_id)
    current_achievements = set(stats.get("achievements", []))
    new_achievements = []

    # Define achievements
    achievement_rules = [
        {"id": "secret_swinger", "name": "Secret Swinger", "condition": stats["secrets_sent"] >= 50},
        {"id": "burn_master", "name": "Burn Master", "condition": stats["secrets_burned"] >= 10},
        {"id": "time_keeper", "name": "Time Keeper", "condition": stats["secrets_timed"] >= 5},
        {"id": "social_butterfly", "name": "Social Butterfly", "condition": len(stats.get("favorite_targets", {})) >= 20},
        {"id": "whisper_rookie", "name": "Whisper Rookie", "condition": stats["secrets_sent"] >= 1},
        {"id": "banana_collector", "name": "Banana Collector", "condition": stats["secrets_received"] >= 25},
    ]

    for achievement in achievement_rules:
        if achievement["condition"] and achievement["id"] not in current_achievements:
            new_achievements.append(achievement["id"])
            current_achievements.add(achievement["id"])

    if new_achievements:
        await whisper_stats.update_one(
            {"user_id": user_id},
            {"$set": {"achievements": list(current_achievements)}}
        )

    return new_achievements

async def resolve_target(token: str, app, chat_id=None) -> tuple:
    """
    Resolve a single target token to (target_id, username, display_name)
    
    Args:
        token: Target identifier (@username or user_id)
        app: Bot client
        chat_id: Chat ID where the query was made (optional, for optimization)
    
    Returns:
        tuple: (target_id, username, display_name)
    """
    username = None
    target_id = None
    display = token

    # Parse token
    if token.startswith("@"):
        username = token[1:].lower()
        # Check if we have this username cached
        cached_user = await get_user_by_username(username)
        if cached_user:
            target_id = cached_user["user_id"]
            display = cached_user.get("first_name", "") + (f" {cached_user.get('last_name', '')}" if cached_user.get("last_name") else "")
            if display.strip():
                return target_id, username, display.strip()
    elif token.isdigit() and 4 <= len(token) <= 15:
        target_id = int(token)
        # Check if we have this user ID cached
        cached_user = await get_user_by_id(target_id)
        if cached_user:
            username = cached_user.get("username")
            display = cached_user.get("first_name", "") + (f" {cached_user.get('last_name', '')}" if cached_user.get("last_name") else "")
            if display.strip():
                return target_id, username, display.strip()

    # PRIORITY: Try to resolve from chat members first if chat_id is provided
    # This gets first name, last name, and username from user ID if they're a chat member
    if chat_id and (username or target_id):
        try:
            ref = username if username else target_id
            
            # Try to get the specific member directly using get_chat_member
            try:
                member = await app.get_chat_member(chat_id, ref)
                user = member.user
                
                target_id = user.id
                if user.username:
                    username = user.username.lower()
                
                # Cache user information
                await upsert_user({
                    "user_id": user.id,
                    "username": username,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                })
                
                display = (user.first_name or "") + (f" {user.last_name}" if user.last_name else "")
                if display.strip():
                    return target_id, username, display.strip()
            except Exception:
                # Member not found in chat, continue to other methods
                pass
        except Exception:
            # Chat members fetch failed, continue to other methods
            pass

    # Fallback: Try to resolve via bot's get_users API
    ref = username if username else target_id
    if ref:
        try:
            user = await app.get_users(ref)
            target_id = user.id
            if user.username:
                username = user.username.lower()

            # Cache user information regardless of whether they have a username
            await upsert_user({
                "user_id": user.id,
                "username": username,  # Will be None if no username
                "first_name": user.first_name,
                "last_name": user.last_name
            })

            display = (user.first_name or "") + (f" {user.last_name}" if user.last_name else "")
            # Return early if bot succeeds and we have a proper display name
            if display.strip():
                return target_id, username, display.strip()
        except Exception as e:
            # Log the error for debugging user resolution issues
            print(f"Bot get_users failed for {ref}: {e}")

    # Fallback display if unresolved
    if not display or display == token:
        if target_id:
            # Try one more time to get user info from cache or API
            try:
                cached_user = await get_user_by_id(target_id)
                if cached_user:
                    first_name = cached_user.get("first_name", "")
                    last_name = cached_user.get("last_name", "")
                    if first_name:
                        display = first_name + (f" {last_name}" if last_name else "")
                    else:
                        # Return None for display - let the mention format handle it
                        # Telegram will show the real name when displayed in chat
                        display = None
                else:
                    # Return None for display - let the mention format handle it
                    display = None
            except Exception:
                # Return None for display - let the mention format handle it
                display = None
        elif username:
            display = f"@{username}"
        else:
            display = token

    return target_id, username, display

async def upsert_user(user_data: Dict):
    """Insert or update user data"""
    from NinjaSecret.core.mongo import mongodb
    users_db = mongodb.users

    await users_db.update_one(
        {"user_id": user_data["user_id"]},
        {"$set": {**user_data, "last_seen": datetime.utcnow()}},
        upsert=True
    )

async def get_user_by_username(username: str) -> Optional[Dict]:
    """Get user by username from cache"""
    from NinjaSecret.core.mongo import mongodb
    users_db = mongodb.users

    return await users_db.find_one({"username": username.lower()})

async def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user by user ID from cache"""
    from NinjaSecret.core.mongo import mongodb
    users_db = mongodb.users

    return await users_db.find_one({"user_id": user_id})


# Recent Targets Functions
async def store_recent_target(sender_id: int, target_id: int = None, target_username: str = None, target_display: str = None, original_token: str = None):
    """Store a recent target for a user (up to 10 most recent)
    
    Stores the target when a secret is sent successfully. Handles duplicates properly:
    - If same target_id exists, removes old entry and adds new at position 0
    - If same original_token exists (for unresolved targets), removes old entry and adds new at position 0
    - Maintains maximum of 10 targets
    - Newest targets appear at the top (position 0)
    
    Args:
        sender_id: User ID of the sender
        target_id: Resolved target user ID (can be None for unresolved targets)
        target_username: Target's username (can be None)
        target_display: Target's display name (can be None)
        original_token: Original token used (@username or user_id) - stored for future resolution
    """
    from NinjaSecret.core.mongo import mongodb
    recent_targets_db = mongodb.recent_targets

    # Validate sender_id
    if sender_id is None:
        logger.error("sender_id cannot be None")
        return
    try:
        sender_id = int(sender_id)
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid sender_id value '{sender_id}': {e}")
        return
    
    # Ensure target_id is an integer if provided
    if target_id:
        try:
            target_id = int(target_id)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert target_id '{target_id}' to int: {e}")
            target_id = None
    
    # We need at least target_id OR original_token to store
    if not target_id and not original_token:
        logger.warning(f"Skipping store_recent_target for user {sender_id} - both target_id and original_token are None")
        return
    
    # Try to get fresh user information from cache if we have target_id but no display
    if target_id and not target_display:
        try:
            cached_user = await get_user_by_id(target_id)
            if cached_user:
                first_name = cached_user.get("first_name", "")
                last_name = cached_user.get("last_name", "")
                if first_name:
                    target_display = first_name + (f" {last_name}" if last_name else "")
                if not target_username and cached_user.get("username"):
                    target_username = cached_user.get("username")
        except Exception:
            pass

    # Create target data
    target_data = {
        "target_id": target_id,
        "target_username": target_username,
        "target_display": target_display,
        "original_token": original_token,
        "last_used": datetime.utcnow()
    }
    
    logger.debug(f"Storing recent target for user {sender_id}: target_id={target_id}, username={target_username}, display={target_display}, token={original_token}")

    # Get current recent targets for user
    user_targets = await recent_targets_db.find_one({"user_id": sender_id})

    if not user_targets:
        # Create new record with first target at position 0
        await recent_targets_db.insert_one({
            "user_id": sender_id,
            "targets": [target_data]
        })
        logger.info(f"Created new recent targets for user {sender_id} with target {target_id or original_token}")
    else:
        targets = user_targets.get("targets", [])
        
        # Remove duplicate if exists
        # Test Case 1: Same target sent twice - check target_id match
        # Test Case 2: Unresolved then resolved - check original_token match
        # Test Case 3: Different tokens for same user - check target_id match
        # Test Case 4: Different users - no match, just add
        targets = [
            t for t in targets
            if not (
                # Match by target_id if both new and existing have it (Test Cases 1, 3)
                (target_id and t.get("target_id") and t.get("target_id") == target_id) or
                # Match by original_token if both have it (Test Case 2)
                (original_token and t.get("original_token") and t.get("original_token") == original_token)
            )
        ]
        
        # Add new target at position 0 (newest first)
        targets.insert(0, target_data)
        
        # Keep only the most recent targets
        targets = targets[:MAX_RECENT_TARGETS]
        
        # Update the record
        await recent_targets_db.update_one(
            {"user_id": sender_id},
            {"$set": {"targets": targets}}
        )
        logger.info(f"Updated recent targets for user {sender_id}, now have {len(targets)} target(s)")


async def get_recent_targets(user_id: int, limit: int = MAX_RECENT_TARGETS) -> List[Dict]:
    """Get recent targets for a user
    
    Returns targets in order from newest (position 0) to oldest.
    
    Args:
        user_id: User ID to get recent targets for
        limit: Maximum number of targets to return (default 10)
        
    Returns:
        List of target dictionaries, newest first
    """
    from NinjaSecret.core.mongo import mongodb
    recent_targets_db = mongodb.recent_targets

    # Validate user_id
    if user_id is None:
        logger.error("user_id cannot be None in get_recent_targets")
        return []
    try:
        user_id = int(user_id)
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user_id value '{user_id}' in get_recent_targets: {e}")
        return []

    user_targets = await recent_targets_db.find_one({"user_id": user_id})

    if not user_targets:
        logger.debug(f"No recent targets found for user {user_id}")
        return []

    targets = user_targets.get("targets", [])
    logger.debug(f"Retrieved {len(targets)} recent targets for user {user_id} (returning up to {limit})")
    return targets[:limit]

