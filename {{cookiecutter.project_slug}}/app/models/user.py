"""User database model."""

from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    """User model with authentication and profile information."""
    
    __tablename__ = "users"

    # Basic user information (id, created_at, updated_at inherited from Base)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    
    # Status flags
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Profile information
    bio = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="user")
