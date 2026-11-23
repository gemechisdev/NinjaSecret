"""
Ninja Secret🥷 Database Models
Handles secret message storage, targeting, timers, and burn-after-reading functionality
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Any
from NinjaSecret.core.mongo import mongodb
from NinjaSecret.logging import LOGGER

# Get logger for this module
logger = LOGGER(__name__)

# Log when module is loaded
logger.info("Whisper database module loaded - recent_targets functions available")

# Collections
whisperdb = mongodb.whispers
whisper_stats = mongodb.whisper_stats
whisper_achievements = mongodb.whisper_achievements

async def store_whisper(data: Dict) -> str:
    """Store a new whisper message with optional special features support"""
    # Convert all_targets tuples to targets dicts for clickable mentions in display
    raw_targets = data.get("all_targets") or []
    targets_list = []
    if raw_targets:
        for t in raw_targets:
            if isinstance(t, dict):
                targets_list.append(t)
            elif isinstance(t, (list, tuple)) and len(t) >= 4:
                target_id, target_username, original_token, target_display_name = t
                if original_token.lower() in ["@all", "@everyone"]:
                    targets_list.append({
                        "display_name": target_display_name,
                        "type": "all",
                        "resolved_id": None,
                    })
                else:
                    targets_list.append({
                        "display_name": target_display_name,
                        "type": "user",
                        "resolved_id": target_id,
                        "target_id": target_id,
                        "username": target_username,
                    })

    whisper_data = {
        "whisper_id": data["whisper_id"],
        "inline_message_id": data.get("inline_message_id"),
        "content": data["content"],
        "sender_id": data["sender_id"],
        "target_username": data.get("target_username"),
        "target_id": data.get("target_id"),
        "original_target_token": data.get("original_target_token"),
        "all_targets": data.get("all_targets"),  # Store all targets as tuples for recent targets history
        "targets": targets_list,  # Store targets as dicts for clickable mentions in display
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

        # Handle reveal on read
        if modifiers.get("reveal_on_read"):
            settings["reveal_on_read"] = True

        # Handle styling
        if modifiers.get("style"):
            settings["style"] = modifiers["style"]

        if settings:
            whisper_data["settings"] = settings

    await whisperdb.insert_one(whisper_data)
    return data["whisper_id"]

async def attach_inline_message_id(whisper_id: str, inline_message_id: str):
    """Attach inline_message_id to a whisper after it's chosen"""
    await whisperdb.update_one(
        {"whisper_id": whisper_id},
        {"$set": {"inline_message_id": inline_message_id}}
    )

async def get_whisper(whisper_id: str) -> Optional[Dict]:
    """Get whisper message by whisper_id"""
    return await whisperdb.find_one({"whisper_id": whisper_id})

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

    # Check if message has expired (only if timer was set)
    if whisper and whisper.get("settings", {}).get("expires_at"):
        if datetime.utcnow() > whisper["settings"]["expires_at"]:
            # Only mark as expired if inline_message_id exists
            if whisper.get("inline_message_id"):
                await mark_whisper_expired(whisper["inline_message_id"])
            else:
                # Mark as expired using whisper_id
                await whisperdb.update_one(
                    {"whisper_id": whisper_id},
                    {"$set": {"status": "expired"}}
                )
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


async def get_active_timed_whispers() -> List[Dict]:
    """Get all active whispers with timers that have inline_message_id attached.
    
    Returns whispers that:
    - Have status = "active"
    - Have settings.expires_at set (timer feature)
    - Have inline_message_id attached (so we can edit the message)
    - Have not expired yet
    
    Returns:
        List of whisper documents with timer information
    """
    current_time = datetime.utcnow()
    
    cursor = whisperdb.find({
        "status": "active",
        "settings.expires_at": {"$gt": current_time},  # Not expired yet
        "inline_message_id": {"$exists": True, "$ne": None}  # Has inline_message_id attached
    })
    
    whispers = []
    async for whisper in cursor:
        whispers.append(whisper)
    
    return whispers


# User Statistics Functions
async def get_user_whisper_stats(user_id: int) -> Dict:
    """Get user's whisper statistics by counting directly from the database in real-time"""
    from datetime import datetime, timedelta
    
    # Calculate week start (7 days ago)
    week_start = datetime.utcnow() - timedelta(days=7)
    
    # Count secrets sent (this week and total)
    secrets_sent_total = await whisperdb.count_documents({"sender_id": user_id})
    secrets_sent_week = await whisperdb.count_documents({
        "sender_id": user_id,
        "created_at": {"$gte": week_start}
    })
    
    # Count secrets received (this week and total)
    # Use MongoDB aggregation pipeline for better performance
    # Note: all_targets is stored as an array of tuples/lists where:
    #   - First element (index 0) is the target_id (int)
    #   - Second element (index 1) is the username (str or None)
    #   - Third element (index 2) is the original_token (str)
    # We unwind the array and match on the first element to find user_id
    pipeline_total = [
        {"$match": {"all_targets": {"$exists": True, "$ne": None}}},
        {"$unwind": "$all_targets"},
        {"$match": {"all_targets.0": user_id}},
        {"$count": "total"}
    ]
    
    pipeline_week = [
        {"$match": {
            "all_targets": {"$exists": True, "$ne": None},
            "created_at": {"$gte": week_start}
        }},
        {"$unwind": "$all_targets"},
        {"$match": {"all_targets.0": user_id}},
        {"$count": "total"}
    ]
    
    # Execute aggregation pipelines
    received_total_result = await whisperdb.aggregate(pipeline_total).to_list(length=1)
    received_week_result = await whisperdb.aggregate(pipeline_week).to_list(length=1)
    
    secrets_received_total = received_total_result[0]["total"] if received_total_result else 0
    secrets_received_week = received_week_result[0]["total"] if received_week_result else 0
    
    # Also count from simple target_id field (for backwards compatibility)
    # Only count whispers that DON'T have all_targets to avoid double-counting
    secrets_received_total += await whisperdb.count_documents({
        "target_id": user_id,
        "$or": [
            {"all_targets": {"$exists": False}},
            {"all_targets": None}
        ]
    })
    secrets_received_week += await whisperdb.count_documents({
        "target_id": user_id,
        "created_at": {"$gte": week_start},
        "$or": [
            {"all_targets": {"$exists": False}},
            {"all_targets": None}
        ]
    })
    
    # Count burned secrets (status = "burned")
    secrets_burned = await whisperdb.count_documents({
        "sender_id": user_id,
        "status": "burned"
    })
    
    # Count timed secrets (those with timer set)
    secrets_timed = await whisperdb.count_documents({
        "sender_id": user_id,
        "settings.expires_at": {"$exists": True}
    })
    
    # Get achievements (calculated based on milestones)
    achievements = []
    if secrets_sent_total >= 50:
        achievements.append("secret_swinger")
    if secrets_burned >= 10:
        achievements.append("burn_master")
    if secrets_timed >= 5:
        achievements.append("time_keeper")
    if secrets_sent_total >= 1:
        achievements.append("whisper_rookie")
    if secrets_received_total >= 25:
        achievements.append("banana_collector")
    
    return {
        "user_id": user_id,
        "secrets_sent": secrets_sent_total,
        "secrets_received": secrets_received_total,
        "secrets_burned": secrets_burned,
        "secrets_timed": secrets_timed,
        "weekly_stats": {
            "secrets_sent": secrets_sent_week,
            "secrets_received": secrets_received_week,
            "week_start": week_start
        },
        "achievements": achievements,
        "favorite_targets": {}  # Can be calculated if needed
    }

async def update_user_stats(user_id: int, stat_type: str, increment: int = 1, **kwargs):
    """
    Legacy function for updating user statistics.
    Now deprecated since stats are calculated in real-time from the database.
    Kept for backward compatibility but does nothing.
    """
    # Stats are now calculated in real-time from the whispers database
    # This function is kept for backward compatibility with existing code
    pass

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
            logger.error(f"Bot get_users failed for {ref}: {e}")

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



async def add_recent_target(sender_id: int, target_data: Dict[str, Any]):
    """
    Add a target to the user's recent targets list.
    Maintains a list of up to 10 recent targets, with most recent first.
    
    Args:
        sender_id: The user ID of the sender
        target_data: Dict containing target info (user_id, username, display_name)
    """
    try:
        from NinjaSecret.core.mongo import mongodb
        users_db = mongodb.users
        
        logger.info(f"add_recent_target called: sender_id={sender_id}, target={target_data.get('display_name')}")
        
        # Get current user document
        user_doc = await users_db.find_one({"user_id": sender_id})
        
        if not user_doc:
            # Create new user document with recent_targets
            logger.info(f"Creating new user document for {sender_id} with recent_targets")
            await users_db.insert_one({
                "user_id": sender_id,
                "recent_targets": [target_data],
                "last_updated": datetime.utcnow()
            })
            logger.info(f"Successfully created user document with recent_targets")
            return
        
        # Get existing recent_targets or initialize empty list
        recent_targets = user_doc.get("recent_targets", [])
        logger.info(f"User {sender_id} currently has {len(recent_targets)} recent targets")
        
        # Remove any existing entry for this target (by user_id)
        target_user_id = target_data.get("user_id")
        if target_user_id:
            old_len = len(recent_targets)
            recent_targets = [t for t in recent_targets if t.get("user_id") != target_user_id]
            if len(recent_targets) < old_len:
                logger.info(f"Removed duplicate target with user_id={target_user_id}")
        else:
            # If no user_id, try to match by username
            target_username = target_data.get("username")
            if target_username:
                old_len = len(recent_targets)
                recent_targets = [t for t in recent_targets if t.get("username") != target_username]
                if len(recent_targets) < old_len:
                    logger.info(f"Removed duplicate target with username={target_username}")
        
        # Add the new target at the beginning (most recent first)
        recent_targets.insert(0, target_data)
        logger.info(f"Added new target to beginning of list, now have {len(recent_targets)} targets")
        
        # Keep only the last 10 targets
        recent_targets = recent_targets[:10]
        
        # Update the database
        result = await users_db.update_one(
            {"user_id": sender_id},
            {
                "$set": {
                    "recent_targets": recent_targets,
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )
        logger.info(f"Database update result: matched={result.matched_count}, modified={result.modified_count}, upserted_id={result.upserted_id}")
    except Exception as e:
        logger.exception(f"Error in add_recent_target for sender {sender_id}: {e}")

async def get_recent_targets(user_id: int) -> List[Dict[str, Any]]:
    """
    Get the list of recent targets for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        List of recent target dicts (up to 10), most recent first
    """
    from NinjaSecret.core.mongo import mongodb
    users_db = mongodb.users
    
    user_doc = await users_db.find_one({"user_id": user_id})
    
    if not user_doc:
        return []
    
    return user_doc.get("recent_targets", [])

async def clear_recent_targets(user_id: int):
    """
    Clear all recent targets for a user.
    
    Args:
        user_id: The user ID
    """
    from NinjaSecret.core.mongo import mongodb
    users_db = mongodb.users
    
    await users_db.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "recent_targets": [],
                "last_updated": datetime.utcnow()
            }
        }
    )
