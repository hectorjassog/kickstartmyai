"""Agent database model."""

import json
from typing import Any, Dict, List

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Agent(Base):
    """Agent model for storing AI agent configurations and metadata."""
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
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
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Configuration and context
    config = Column(JSON, default=dict, nullable=False)  # Additional configuration
    metadata = Column(JSON, default=dict, nullable=False)  # Custom metadata
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="agents")
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
    
    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', provider='{self.provider}', model='{self.model}')>"
