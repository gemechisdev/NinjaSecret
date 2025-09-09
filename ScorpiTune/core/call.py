"""
Minimal call.py stub for non-music bot functionality
This file is kept for compatibility but most functions are stubbed out
"""

import asyncio
from pyrogram import Client
import config
from ScorpiTune import LOGGER, app


class Hotty:
    """Minimal Hotty class for compatibility"""
    
    def __init__(self):
        self.app = app
    
    @staticmethod
    async def start():
        """Stub method for compatibility"""
        LOGGER(__name__).info("Call handler initialized (stub)")
        pass
    
    @staticmethod 
    async def stop():
        """Stub method for compatibility"""
        pass
    
    @staticmethod
    async def ping():
        """Return a stub ping value"""
        return "0ms"
    
    @staticmethod
    async def decorators():
        """Stub method for compatibility"""
        pass
    
    @staticmethod
    async def stop_stream_force(chat_id):
        """Stub method for compatibility"""
        pass