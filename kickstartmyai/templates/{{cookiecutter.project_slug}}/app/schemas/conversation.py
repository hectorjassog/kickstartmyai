"""Conversation Pydantic schemas."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


# Shared properties
class ConversationBase(BaseModel):
    """Conversation base schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


# Properties to receive via API on creation
class ConversationCreate(ConversationBase):
    """Conversation creation schema."""
    title: str
    user_id: Optional[int] = None  # Will be set by endpoint


# Properties to receive via API on update
class ConversationUpdate(ConversationBase):
    """Conversation update schema."""
    title: Optional[str] = None


class ConversationInDBBase(ConversationBase):
    """Conversation schema with database fields."""
    id: Optional[int] = None
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Additional properties to return via API
class Conversation(ConversationInDBBase):
    """Conversation schema for API responses."""
    pass


# Additional properties stored in DB
class ConversationInDB(ConversationInDBBase):
    """Conversation schema in database."""
    pass
