"""Agent database model."""

import json
from typing import Any, Dict, List
from enum import Enum

from sqlalchemy import Boolean, Column, String, Text, ForeignKey, JSON, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class AgentStatus(str, Enum):
    """Agent status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class AgentType(str, Enum):
    """Agent type enumeration."""
    PERSONAL = "personal"
    SHARED = "shared"
    PUBLIC = "public"
    SYSTEM = "system"


class Agent(Base):
    """Agent model for storing AI agent configurations and metadata."""

    # Basic information (id, created_at, updated_at inherited from Base)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Agent configuration
    system_prompt = Column(Text, nullable=False)
    provider = Column(String, default="openai", nullable=False)
    model = Column(String, default="gpt-4", nullable=False)
    temperature = Column(String, default="0.7", nullable=False)  # Stored as string for precision
    max_tokens = Column(Integer, default=2000, nullable=False)
    max_iterations = Column(Integer, default=10, nullable=False)
    
    # Features and capabilities
    enable_memory = Column(Boolean, default=True, nullable=False)
    memory_types = Column(JSON, default=lambda: ["conversation"], nullable=False)
    available_tools = Column(JSON, default=list, nullable=False)
    tools_enabled = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    agent_type = Column(SQLEnum(AgentType), default=AgentType.PERSONAL, nullable=False)
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.ACTIVE, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Configuration and context
    config = Column(JSON, default=dict, nullable=False)  # Additional configuration
    metadata = Column(JSON, default=dict, nullable=False)  # Custom metadata
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="agents")
    conversations = relationship("Conversation", back_populates="agent")
    executions = relationship("Execution", back_populates="agent", cascade="all, delete-orphan", order_by="Execution.created_at.desc()")
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set_config_value(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        if self.config is None:
            self.config = {}
        self.config[key] = value
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get a metadata value."""
        return self.metadata.get(key, default)
    
    def set_metadata_value(self, key: str, value: Any) -> None:
        """Set a metadata value."""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
    
    def increment_usage(self) -> None:
        """Increment the usage count."""
        self.usage_count += 1
    
    def get_temperature_float(self) -> float:
        """Get temperature as float."""
        try:
            return float(self.temperature)
        except (ValueError, TypeError):
            return 0.7
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return self.available_tools or []
    
    def add_tool(self, tool_name: str) -> None:
        """Add a tool to the available tools list."""
        if self.available_tools is None:
            self.available_tools = []
        if tool_name not in self.available_tools:
            self.available_tools.append(tool_name)
    
    def remove_tool(self, tool_name: str) -> None:
        """Remove a tool from the available tools list."""
        if self.available_tools and tool_name in self.available_tools:
            self.available_tools.remove(tool_name)
    
    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', provider='{self.provider}', model='{self.model}')>"
