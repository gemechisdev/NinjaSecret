import asyncio
import importlib
import time
import psutil
import os
from sys import argv
from pyrogram import idle

import config
from NinjaSecret import LOGGER, app
from NinjaSecret.misc import sudo
from NinjaSecret.plugins import ALL_MODULES
from NinjaSecret.utils.database import get_banned_users, get_gbanned
from NinjaSecret.web_server import start_health_server, stop_health_server
from config import BANNED_USERS


def get_memory_usage():
    """Get current memory usage information"""
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent()
        }
    except:
        return {'rss': 0, 'vms': 0, 'percent': 0}


def get_disk_usage():
    """Get disk usage information"""
    try:
        downloads_dir = os.path.join(os.getcwd(), "downloads")
        playback_dir = os.path.join(os.getcwd(), "playback")

        downloads_size = 0
        playback_size = 0

        if os.path.exists(downloads_dir):
            for root, dirs, files in os.walk(downloads_dir):
                for file in files:
                    try:
                        downloads_size += os.path.getsize(os.path.join(root, file))
                    except:
                        pass

        if os.path.exists(playback_dir):
            for root, dirs, files in os.walk(playback_dir):
                for file in files:
                    try:
                        playback_size += os.path.getsize(os.path.join(root, file))
                    except:
                        pass

        return {
            'downloads_mb': downloads_size / 1024 / 1024,
            'playback_mb': playback_size / 1024 / 1024,
            'total_mb': (downloads_size + playback_size) / 1024 / 1024
        }
    except:
        return {'downloads_mb': 0, 'playback_mb': 0, 'total_mb': 0}


async def memory_cleanup_task():
    """Periodic memory cleanup task"""
    while True:
        try:
            # Log memory and disk usage
            memory_usage = get_memory_usage()
            disk_usage = get_disk_usage()

            LOGGER(__name__).info(
                f"Memory cleanup completed - "
                f"Memory: {memory_usage['rss']:.1f}MB RSS, "
                f"Disk: {disk_usage['total_mb']:.1f}MB total "
                f"({disk_usage['downloads_mb']:.1f}MB downloads, "
                f"{disk_usage['playback_mb']:.1f}MB playback)"
            )

        except Exception as e:
            LOGGER(__name__).error(f"Memory cleanup error: {e}")

        # Wait 10 minutes before next cleanup
        await asyncio.sleep(600)


async def handle_flood_wait_error(error, attempt, max_retries, component_name):
    """Handle flood wait errors with proper parsing and logging"""
    error_msg = str(error)

    # Check for specific auth.ImportBotAuthorization error
    if "auth.ImportBotAuthorization" in error_msg:
        LOGGER(__name__).warning(
            f"{component_name} encountered auth.ImportBotAuthorization flood wait error. "
            "This usually happens when redeploying too frequently."
        )

    # Try to extract wait time from different error message formats
    wait_time = None

    # Format 1: "A wait of X seconds is required"
    if "A wait of" in error_msg and "seconds" in error_msg:
        try:
            wait_time = int(error_msg.split("A wait of")[1].split("seconds")[0].strip())
        except:
            pass

    # Format 2: "FLOOD_WAIT_X" where X is the wait time
    if wait_time is None and "FLOOD_WAIT" in error_msg:
        try:
            import re
            # Look for FLOOD_WAIT_X pattern
            match = re.search(r'FLOOD_WAIT_(\d+)', error_msg)
            if match:
                wait_time = int(match.group(1))
        except:
            pass

    # Format 3: Any number followed by "seconds"
    if wait_time is None:
        try:
            import re
            match = re.search(r'(\d+)\s*seconds?', error_msg)
            if match:
                wait_time = int(match.group(1))
        except:
            pass

    # Default fallback
    if wait_time is None:
        wait_time = 60

    # Add buffer time for safety (configurable)
    safe_wait_time = wait_time + config.FLOOD_WAIT_SAFETY_BUFFER

    LOGGER(__name__).warning(
        f"{component_name} flood wait error (attempt {attempt + 1}/{max_retries}). "
        f"Required wait: {wait_time}s, Safe wait: {safe_wait_time}s"
    )

    if attempt < max_retries - 1:
        LOGGER(__name__).info(f"Waiting {safe_wait_time} seconds before retry...")
        await asyncio.sleep(safe_wait_time)
        return True  # Continue retrying
    else:
        LOGGER(__name__).error(
            f"Failed to start {component_name} after {max_retries} attempts due to flood wait errors. "
            f"Please wait longer before redeploying."
        )
        return False  # Stop retrying


async def start_bot_with_retry(max_retries=None, base_delay=1):
    """Start the bot with retry mechanism for flood wait errors"""
    if max_retries is None:
        max_retries = config.BOT_STARTUP_MAX_RETRIES
    for attempt in range(max_retries):
        try:
            await app.start()
            LOGGER(__name__).info("Bot started successfully!")
            return True
        except Exception as e:
            error_msg = str(e)
            if "FLOOD_WAIT" in error_msg or "420" in error_msg:
                should_continue = await handle_flood_wait_error(e, attempt, max_retries, "Bot")
                if should_continue:
                    continue
                else:
                    raise e
            else:
                # Non-flood wait error, re-raise immediately
                LOGGER(__name__).error(f"Non-flood wait error during bot start: {e}")
                raise e

    return False







async def init():
    LOGGER(__name__).info("Starting NinjaSecret initialization...")

    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass

    LOGGER(__name__).info("Starting bot with retry mechanism...")
    # Use retry mechanism for bot start
    await start_bot_with_retry()

    LOGGER(__name__).info("Importing modules...")
    for all_module in ALL_MODULES:
        importlib.import_module("NinjaSecret.plugins" + all_module)
    LOGGER("NinjaSecret.plugins").info("Successfully Imported Modules...")

    # Start memory cleanup task
    asyncio.create_task(memory_cleanup_task())
    LOGGER(__name__).info("Memory cleanup task started")

    # Start whisper cleanup and timer countdown tasks
    # These are started explicitly here after the bot is running and event loop is active
    from NinjaSecret.plugins.whisper.cleanup_task import start_cleanup_task, start_timer_countdown_task
    start_cleanup_task()
    start_timer_countdown_task()

    # Start health server for deployment platforms like Render
    try:
        await start_health_server()
        LOGGER(__name__).info("Health server started successfully")
    except Exception as e:
        LOGGER(__name__).error(f"Failed to start health server: {e}")
        # Don't exit on health server failure, bot can still work

    LOGGER("NinjaSecret").info(
        "Bot started successfully! Ready for whisper functionality."
    )
    await idle()
    
    # Cleanup
    LOGGER("NinjaSecret").info("Stopping Bot...")
    await stop_health_server()
    await app.stop()
    LOGGER("NinjaSecret").info("Bot stopped successfully")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
