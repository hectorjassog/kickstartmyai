"""Message database model."""

from sqlalchemy import Column, String, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class MessageRole(str, enum.Enum):
    """Message role enum."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    """Message model."""

    content = Column(Text, nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    
    # Foreign keys
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
