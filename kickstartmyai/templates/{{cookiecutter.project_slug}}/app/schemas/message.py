"""Message Pydantic schemas."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.message import MessageRole


# Shared properties
class MessageBase(BaseModel):
    """Message base schema."""
    content: Optional[str] = Field(None, min_length=1)
    role: Optional[MessageRole] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Properties to receive via API on creation
class MessageCreate(MessageBase):
    """Message creation schema."""
    content: str = Field(..., min_length=1)
    role: MessageRole


# Properties to receive via API on update
class MessageUpdate(MessageBase):
    """Message update schema."""
    content: Optional[str] = Field(None, min_length=1)


# Schema with database fields
class MessageInDBBase(MessageBase):
    """Message schema with database fields."""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Additional properties to return via API
class Message(MessageInDBBase):
    """Message schema for API responses."""
    pass


# Message response schema for API responses
class MessageResponse(MessageInDBBase):
    """Message response schema for API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    # Include all required fields
    id: UUID
    conversation_id: UUID
    content: str
    role: MessageRole
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None


# Additional properties stored in DB
class MessageInDB(MessageInDBBase):
    """Message schema in database."""
    pass


# Message list response schema
class MessageListResponse(BaseModel):
    """Message list response schema."""
    messages: List[Message]
    total_count: int
    page: int
    page_size: int
    has_next: bool


# Message statistics schema
class MessageStatistics(BaseModel):
    """Message statistics schema."""
    total_messages: int
    messages_by_role: Dict[str, int]
    content_length_statistics: Dict[str, float]
    messages_created_today: int
    messages_created_this_week: int
    messages_created_this_month: int


# Message filter schema
class MessageFilter(BaseModel):
    """Message filter schema for complex queries."""
    conversation_id: Optional[UUID] = None
    role: Optional[MessageRole] = None
    search_term: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


# Message context schema for AI processing
class MessageContext(BaseModel):
    """Message context schema for AI processing."""
    messages: List[Message]
    max_tokens: Optional[int] = None
    include_system: bool = True


# Bulk message creation schema
class BulkMessageCreate(BaseModel):
    """Bulk message creation schema."""
    messages: List[MessageCreate]
    conversation_id: UUID
