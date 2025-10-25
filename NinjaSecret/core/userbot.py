"""
Userbot module - Removed as per requirements
This module previously handled assistant/userbot functionality.
It has been removed and replaced with direct bot API calls where needed.
"""

from ..logging import LOGGER

# Empty lists to maintain compatibility
assistants = []
assistantids = []


class Userbot:
    """
    Stub class for backward compatibility.
    Userbot functionality has been removed.
    """
    def __init__(self):
        pass

    async def start(self):
        """No-op start method for compatibility"""
        LOGGER(__name__).info("Userbot module is disabled - no assistant clients to start")
        pass

    async def stop(self):
        """No-op stop method for compatibility"""
        pass

