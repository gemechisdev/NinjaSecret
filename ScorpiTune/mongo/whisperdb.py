"""
WhispierBot Database Models
Handles secret message storage, targeting, timers, and burn-after-reading functionality
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from ScorpiTune.core.mongo import mongodb

# Collections
whisperdb = mongodb.whispers
whisper_stats = mongodb.whisper_stats
whisper_achievements = mongodb.whisper_achievements

async def create_whisper_message(
    inline_message_id: str,
    content: str,
    sender_id: int,
    sender_username: str,
    targets: List[Dict],
    burn_after_reading: bool = False,
    expires_at: Optional[datetime] = None,
    style_theme: str = "classic"
) -> str:
    """Create a new whisper message"""
    whisper_data = {
        "inline_message_id": inline_message_id,
        "content": content,
        "sender": {
            "id": sender_id,
            "username": sender_username
        },
        "targets": targets,  # [{"type": "username|id|all", "value": str, "resolved_id": int, "read_at": None}]
        "settings": {
            "burn_after_reading": burn_after_reading,
            "expires_at": expires_at,
            "style_theme": style_theme,
            "created_at": datetime.utcnow()
        },
        "analytics": {
            "views": 0,
            "clicks": 0,
            "completed_reads": 0
        },
        "status": "active"  # active, expired, burned
    }
    
    await whisperdb.insert_one(whisper_data)
    return inline_message_id

async def get_whisper_message(inline_message_id: str) -> Optional[Dict]:
    """Get whisper message by inline message ID"""
    whisper = await whisperdb.find_one({"inline_message_id": inline_message_id})
    
    # Check if message has expired
    if whisper and whisper.get("settings", {}).get("expires_at"):
        if datetime.utcnow() > whisper["settings"]["expires_at"]:
            await mark_whisper_expired(inline_message_id)
            return None
    
    return whisper

async def mark_whisper_read(inline_message_id: str, user_id: int) -> bool:
    """Mark whisper as read by a user"""
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

async def resolve_targets(target_string: str, app) -> List[Dict]:
    """Resolve target string to list of target dictionaries"""
    targets = []
    
    # Handle @all or @everyone
    if target_string.lower() in ["@all", "@everyone", "all", "everyone"]:
        return [{"type": "all", "value": "everyone", "resolved_id": None, "read_at": None}]
    
    # Split multiple targets by comma
    target_list = [t.strip() for t in target_string.split(",")]
    
    for target in target_list:
        target = target.strip()
        if not target:
            continue
        
        # Remove @ symbol if present
        if target.startswith("@"):
            target = target[1:]
        
        target_data = {
            "type": "username",
            "value": target,
            "resolved_id": None,
            "read_at": None
        }
        
        # Try to resolve username to ID
        try:
            if target.isdigit():
                # It's already an ID
                target_data["type"] = "id"
                target_data["resolved_id"] = int(target)
            else:
                # Try to get user by username
                try:
                    user = await app.get_users(target)
                    target_data["resolved_id"] = user.id
                except:
                    # Username doesn't exist, but we'll keep it for graceful handling
                    pass
        except:
            pass
        
        targets.append(target_data)
    
    return targets