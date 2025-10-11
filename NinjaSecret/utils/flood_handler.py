import asyncio
import logging
from typing import Any, Callable, Optional
from pyrogram.errors import FloodWait

logger = logging.getLogger(__name__)

import config
from NinjaSecret.utils.platform_gate import platform_gate

class FloodWaitHandler:
    def __init__(self, max_retries: int = None, base_delay: float = None):
        self.max_retries = max_retries or getattr(config, 'MAX_RETRIES_ON_FLOODWAIT', 3)
        self.base_delay = base_delay or getattr(config, 'FLOODWAIT_BASE_DELAY', 1.0)
        self._last_request_time = 0
        self._min_interval = getattr(config, 'MIN_INTERVAL_BETWEEN_REQUESTS', 0.1)  # Minimum interval between requests
    
    async def execute_with_flood_protection(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """
        Execute a function with FloodWait protection and rate limiting.
        
        Args:
            func: The function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function execution
            
        Raises:
            Exception: If the function fails after max retries
        """
        platform_name = kwargs.pop('_platform_name', 'telegram')
        for attempt in range(self.max_retries):
            try:
                # New pre-wait gate for concurrent/platform spacing
                await platform_gate.wait(platform_name)

                # Legacy local min-interval spacing (kept for safety)
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - self._last_request_time
                if time_since_last < self._min_interval:
                    await asyncio.sleep(self._min_interval - time_since_last)
                
                result = await func(*args, **kwargs)
                self._last_request_time = asyncio.get_event_loop().time()
                await platform_gate.done(platform_name)
                return result
                
            except FloodWait as fw:
                await platform_gate.done(platform_name)
                wait_time = int(fw.value)
                logger.warning(f"FloodWait detected: waiting {wait_time} seconds (attempt {attempt + 1}/{self.max_retries})")
                
                if wait_time > 300:  # If wait time > 5 minutes, skip
                    logger.error(f"FloodWait too long ({wait_time}s), skipping request")
                    raise fw
                
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                await platform_gate.done(platform_name)
                if attempt == self.max_retries - 1:
                    logger.error(f"Function failed after {self.max_retries} attempts: {e}")
                    raise e
                logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying...")
                await asyncio.sleep(self.base_delay * (2 ** attempt))  # Exponential backoff
        
        raise Exception(f"Function failed after {self.max_retries} attempts")

# Global instance
flood_handler = FloodWaitHandler()

async def safe_execute(func: Callable, *args, **kwargs) -> Any:
    """
    Convenience function to execute any function with FloodWait protection.
    
    Args:
        func: The function to execute
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        The result of the function execution
    """
    platform_name = kwargs.pop('_platform_name', 'telegram')
    return await flood_handler.execute_with_flood_protection(func, *args, _platform_name=platform_name, **kwargs)

async def safe_send_photo(client, chat_id: int, photo: str, **kwargs) -> Any:
    """
    Safely send a photo with FloodWait protection.
    
    Args:
        client: The Pyrogram client
        chat_id: Target chat ID
        photo: Photo to send
        **kwargs: Additional arguments for send_photo
        
    Returns:
        The sent message
    """
    return await safe_execute(client.send_photo, chat_id, photo, _platform_name='telegram', **kwargs)

async def safe_send_message(client, chat_id: int, text: str, **kwargs) -> Any:
    """
    Safely send a message with FloodWait protection.
    
    Args:
        client: The Pyrogram client
        chat_id: Target chat ID
        text: Message text
        **kwargs: Additional arguments for send_message
        
    Returns:
        The sent message
    """
    return await safe_execute(client.send_message, chat_id, text, _platform_name='telegram', **kwargs)

async def safe_edit_message_text(client, chat_id: int, message_id: int, text: str, **kwargs) -> Any:
    """
    Safely edit a message with FloodWait protection.
    
    Args:
        client: The Pyrogram client
        chat_id: Target chat ID
        message_id: Message ID to edit
        text: New text
        **kwargs: Additional arguments for edit_message_text
        
    Returns:
        The edited message
    """
    return await safe_execute(client.edit_message_text, chat_id, message_id, text, _platform_name='telegram', **kwargs)