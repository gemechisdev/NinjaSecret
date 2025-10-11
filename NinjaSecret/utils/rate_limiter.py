import asyncio
import time
from functools import wraps
from typing import Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, max_calls: int = 10, time_window: float = 60.0):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in the time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self._calls: Dict[str, list] = {}
    
    def _cleanup_old_calls(self, key: str):
        """Remove calls older than the time window."""
        current_time = time.time()
        if key in self._calls:
            self._calls[key] = [
                call_time for call_time in self._calls[key] 
                if current_time - call_time < self.time_window
            ]
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if a call is allowed.
        
        Args:
            key: Unique identifier for the rate limiting (e.g., chat_id, user_id)
            
        Returns:
            True if call is allowed, False otherwise
        """
        self._cleanup_old_calls(key)
        
        if key not in self._calls:
            self._calls[key] = []
        
        if len(self._calls[key]) >= self.max_calls:
            return False
        
        self._calls[key].append(time.time())
        return True
    
    def get_wait_time(self, key: str) -> float:
        """
        Get the time to wait before next call is allowed.
        
        Args:
            key: Unique identifier for the rate limiting
            
        Returns:
            Time to wait in seconds
        """
        self._cleanup_old_calls(key)
        
        if key not in self._calls or not self._calls[key]:
            return 0.0
        
        oldest_call = min(self._calls[key])
        wait_time = self.time_window - (time.time() - oldest_call)
        return max(0.0, wait_time)

# Global rate limiter instances
chat_rate_limiter = RateLimiter(max_calls=5, time_window=10.0)  # 5 calls per 10 seconds per chat
user_rate_limiter = RateLimiter(max_calls=3, time_window=5.0)   # 3 calls per 5 seconds per user

def rate_limit_by_chat(max_calls: int = 5, time_window: float = 10.0):
    """
    Decorator to rate limit functions by chat ID.
    
    Args:
        max_calls: Maximum calls allowed in time window
        time_window: Time window in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to extract chat_id from arguments
            chat_id = None
            for arg in args:
                if hasattr(arg, 'chat_id'):
                    chat_id = arg.chat_id
                    break
            
            if not chat_id:
                # If no chat_id found, try to get it from kwargs
                chat_id = kwargs.get('chat_id') or kwargs.get('message', {}).chat.id if 'message' in kwargs else None
            
            if chat_id:
                if not chat_rate_limiter.is_allowed(str(chat_id)):
                    wait_time = chat_rate_limiter.get_wait_time(str(chat_id))
                    logger.warning(f"Rate limit exceeded for chat {chat_id}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def rate_limit_by_user(max_calls: int = 3, time_window: float = 5.0):
    """
    Decorator to rate limit functions by user ID.
    
    Args:
        max_calls: Maximum calls allowed in time window
        time_window: Time window in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to extract user_id from arguments
            user_id = None
            for arg in args:
                if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                    user_id = arg.from_user.id
                    break
                elif hasattr(arg, 'id'):
                    user_id = arg.id
                    break
            
            if not user_id:
                # If no user_id found, try to get it from kwargs
                user_id = kwargs.get('user_id') or kwargs.get('from_user', {}).id if 'from_user' in kwargs else None
            
            if user_id:
                if not user_rate_limiter.is_allowed(str(user_id)):
                    wait_time = user_rate_limiter.get_wait_time(str(user_id))
                    logger.warning(f"Rate limit exceeded for user {user_id}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def smart_rate_limit(max_calls: int = 5, time_window: float = 10.0):
    """
    Smart rate limiter that applies both chat and user rate limiting.
    
    Args:
        max_calls: Maximum calls allowed in time window
        time_window: Time window in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract both chat_id and user_id
            chat_id = None
            user_id = None
            
            for arg in args:
                if hasattr(arg, 'chat_id'):
                    chat_id = arg.chat_id
                if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                    user_id = arg.from_user.id
            
            # Apply rate limiting for both
            if chat_id:
                if not chat_rate_limiter.is_allowed(str(chat_id)):
                    wait_time = chat_rate_limiter.get_wait_time(str(chat_id))
                    logger.warning(f"Chat rate limit exceeded for chat {chat_id}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
            
            if user_id:
                if not user_rate_limiter.is_allowed(str(user_id)):
                    wait_time = user_rate_limiter.get_wait_time(str(user_id))
                    logger.warning(f"User rate limit exceeded for user {user_id}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator