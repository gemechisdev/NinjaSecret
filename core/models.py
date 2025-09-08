"""Data models for Whispier Bot."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class WhisperMessage:
    """Whisper message data model."""
    
    inline_message_id: str
    content: str
    sender_id: int
    target_username: str
    target_id: Optional[int] = None
    created_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    reader_id: Optional[int] = None
    status: str = "active"


@dataclass
class User:
    """User data model."""
    
    user_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    last_seen: Optional[datetime] = None
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name or ''}".strip()
    
    @property
    def mention(self) -> str:
        """Get user mention."""
        return f"@{self.username}" if self.username else self.full_name