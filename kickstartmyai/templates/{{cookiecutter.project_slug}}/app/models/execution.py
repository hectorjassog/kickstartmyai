"""Execution model for tracking agent execution instances."""
from enum import Enum
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, ForeignKey, JSON, Enum as SQLEnum, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExecutionType(str, Enum):
    """Execution type enumeration."""
    CHAT = "chat"
    WORKFLOW = "workflow"
    TOOL = "tool"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    CUSTOM = "custom"


class Execution(Base):
    """Model for tracking agent execution instances."""
    
    # Execution identification
    execution_id = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Execution type and status
    type = Column(SQLEnum(ExecutionType), nullable=False, default=ExecutionType.CHAT)
    status = Column(SQLEnum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING)
    
    # Relationships
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    parent_execution_id = Column(UUID(as_uuid=True), ForeignKey("executions.id"), nullable=True)
    
    # Execution configuration
    input_data = Column(JSON, nullable=True)  # Input parameters and data
    config = Column(JSON, nullable=True)  # Execution-specific configuration
    context = Column(JSON, nullable=True)  # Execution context and variables
    
    # Execution timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # Execution duration
    
    # Execution results
    output_data = Column(JSON, nullable=True)  # Execution results
    error_message = Column(Text, nullable=True)  # Error details if failed
    error_type = Column(String(255), nullable=True)  # Error type classification
    stack_trace = Column(Text, nullable=True)  # Full stack trace for debugging
    
    # Performance metrics
    tokens_used = Column(Integer, nullable=True, default=0)
    cost = Column(DECIMAL(10, 6), nullable=True)  # Cost in USD with 6 decimal precision
    
    # Execution metadata
    priority = Column(Integer, nullable=False, default=0)  # Execution priority
    retry_count = Column(Integer, nullable=False, default=0)  # Number of retries
    original_execution_id = Column(UUID(as_uuid=True), ForeignKey("executions.id"), nullable=True)  # Original execution for retries
    
    # Relationships
    agent = relationship("Agent", back_populates="executions")
    user = relationship("User", back_populates="executions")
    conversation = relationship("Conversation", back_populates="executions")
    
    # Self-referential relationship for parent/child executions
    parent_execution = relationship("Execution", remote_side=[id], back_populates="child_executions")
    child_executions = relationship("Execution", back_populates="parent_execution")
    
    # Self-referential relationship for original/retry executions
    original_execution = relationship("Execution", remote_side=[id], foreign_keys=[original_execution_id])
    
    @property
    def is_completed(self) -> bool:
        """Check if execution is completed (success or failure)."""
        return self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]
    
    @property
    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.status == ExecutionStatus.RUNNING
    
    @property
    def cost_decimal(self) -> Optional[Decimal]:
        """Get cost as Decimal object."""
        return self.cost if self.cost is not None else None
    
    def set_cost(self, cost_value: Decimal) -> None:
        """Set cost from Decimal value."""
        self.cost = cost_value
    
    def __repr__(self) -> str:
        return f"<Execution(id={self.id}, execution_id='{self.execution_id}', status='{self.status}', type='{self.type}')>"