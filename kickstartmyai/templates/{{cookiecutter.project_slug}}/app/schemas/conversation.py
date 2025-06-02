"""Conversation Pydantic schemas."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Shared properties
class ConversationBase(BaseModel):
    """Conversation base schema."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    agent_id: Optional[UUID] = None
    is_active: Optional[bool] = Field(default=True)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Properties to receive via API on creation
class ConversationCreate(ConversationBase):
    """Conversation creation schema."""
    title: str = Field(..., min_length=1, max_length=255)
    agent_id: Optional[UUID] = None


# Properties to receive via API on update
class ConversationUpdate(ConversationBase):
    """Conversation update schema."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)


# Schema with database fields
class ConversationInDBBase(ConversationBase):
    """Conversation schema with database fields."""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    message_count: Optional[int] = Field(default=0, ge=0)
    last_message_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Additional properties to return via API
class Conversation(ConversationInDBBase):
    """Conversation schema for API responses."""
    pass


# Additional properties stored in DB
class ConversationInDB(ConversationInDBBase):
    """Conversation schema in database."""
    pass


# Conversation with messages schema
class ConversationWithMessages(Conversation):
    """Conversation schema with messages included."""
    messages: List[Dict[str, Any]] = Field(default_factory=list)


# Conversation with full context schema
class ConversationWithFullContext(Conversation):
    """Conversation schema with all related data."""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    agent: Optional[Dict[str, Any]] = None
    executions: List[Dict[str, Any]] = Field(default_factory=list)


# Conversation statistics schema
class ConversationStatistics(BaseModel):
    """Conversation statistics schema."""
    total_conversations: int
    active_conversations: int
    inactive_conversations: int
    conversations_by_agent: Dict[str, int]
    average_messages_per_conversation: float
    most_active_conversations: List[Dict[str, Any]]
    conversations_created_today: int
    conversations_created_this_week: int
    conversations_created_this_month: int


# Conversation list response schema
class ConversationListResponse(BaseModel):
    """Conversation list response schema."""
    conversations: List[Conversation]
    total_count: int
    page: int
    page_size: int
    has_next: bool


# Conversation filter schema
class ConversationFilter(BaseModel):
    """Conversation filter schema for complex queries."""
    user_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    search_term: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    has_messages: Optional[bool] = None


# Conversation summary schema
class ConversationSummary(BaseModel):
    """Conversation summary schema."""
    id: UUID
    title: str
    message_count: int
    last_message_at: Optional[datetime]
    agent_name: Optional[str] = None
    created_at: datetime
