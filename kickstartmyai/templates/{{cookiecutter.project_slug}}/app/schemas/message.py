"""Message Pydantic schemas."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.message import MessageRole


# Shared properties
class MessageBase(BaseModel):
    """Message base schema."""
    content: Optional[str] = None
    role: Optional[MessageRole] = None


# Properties to receive via API on creation
class MessageCreate(MessageBase):
    """Message creation schema."""
    content: str
    role: MessageRole
    conversation_id: int


# Properties to receive via API on update
class MessageUpdate(MessageBase):
    """Message update schema."""
    content: Optional[str] = None


class MessageInDBBase(MessageBase):
    """Message schema with database fields."""
    id: Optional[int] = None
    conversation_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Additional properties to return via API
class Message(MessageInDBBase):
    """Message schema for API responses."""
    pass


# Additional properties stored in DB
class MessageInDB(MessageInDBBase):
    """Message schema in database."""
    pass
