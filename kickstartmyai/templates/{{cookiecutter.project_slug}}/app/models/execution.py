"""
Execution model for tracking agent execution instances.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

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
    """
    Model for tracking agent execution instances.
    
    Tracks individual runs of agent tasks, including execution details,
    performance metrics, and results.
    """
    __tablename__ = "executions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Execution identification
    execution_id = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Execution type and status
    type = Column(SQLEnum(ExecutionType), nullable=False, default=ExecutionType.CHAT)
    status = Column(SQLEnum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING)
    
    # Relationships
    agent_id = Column(PostgresUUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    conversation_id = Column(PostgresUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    parent_execution_id = Column(PostgresUUID(as_uuid=True), ForeignKey("executions.id"), nullable=True)
    
    # Execution configuration
    input_data = Column(JSON, nullable=True)  # Input parameters and data
    config = Column(JSON, nullable=True)  # Execution-specific configuration
    context = Column(JSON, nullable=True)  # Execution context and variables
    
    # Execution timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # Execution duration
    timeout_seconds = Column(Integer, nullable=True, default=300)  # 5 minutes default
    
    # Execution results
    output_data = Column(JSON, nullable=True)  # Execution results
    error_message = Column(Text, nullable=True)  # Error details if failed
    error_type = Column(String(100), nullable=True)  # Error classification
    stack_trace = Column(Text, nullable=True)  # Full error stack trace
    
    # Performance metrics
    tokens_used = Column(Integer, nullable=True, default=0)
    cost_usd = Column(String(20), nullable=True)  # String to avoid floating point issues
    memory_usage_mb = Column(Integer, nullable=True)
    cpu_usage_percent = Column(Integer, nullable=True)
    
    # Tool and function usage
    tools_used = Column(JSON, nullable=True)  # List of tools used
    function_calls = Column(JSON, nullable=True)  # Function call details
    external_apis = Column(JSON, nullable=True)  # External API calls made
    
    # Execution metadata
    priority = Column(Integer, nullable=False, default=0)  # Execution priority
    retry_count = Column(Integer, nullable=False, default=0)  # Number of retries
    max_retries = Column(Integer, nullable=False, default=3)  # Maximum retries allowed
    
    # Monitoring and debugging
    is_monitored = Column(Boolean, nullable=False, default=True)
    debug_mode = Column(Boolean, nullable=False, default=False)
    log_level = Column(String(20), nullable=False, default="INFO")
    trace_id = Column(String(255), nullable=True)  # Distributed tracing ID
    
    # Execution environment
    environment = Column(String(50), nullable=True, default="production")
    version = Column(String(50), nullable=True)  # Agent/system version
    platform_info = Column(JSON, nullable=True)  # Platform and environment info
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    agent = relationship("Agent", back_populates="executions")
    user = relationship("User", back_populates="executions")
    conversation = relationship("Conversation", back_populates="executions")
    
    # Self-referential relationship for parent/child executions
    parent_execution = relationship("Execution", remote_side=[id], back_populates="child_executions")
    child_executions = relationship("Execution", back_populates="parent_execution")
    
    def __repr__(self) -> str:
        return (
            f"<Execution(id={self.id}, execution_id='{self.execution_id}', "
            f"type='{self.type}', status='{self.status}', agent_id={self.agent_id})>"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert execution to dictionary."""
        return {
            "id": str(self.id),
            "execution_id": self.execution_id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "status": self.status.value,
            "agent_id": str(self.agent_id),
            "user_id": str(self.user_id),
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "parent_execution_id": str(self.parent_execution_id) if self.parent_execution_id else None,
            "input_data": self.input_data,
            "config": self.config,
            "context": self.context,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "timeout_seconds": self.timeout_seconds,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "tools_used": self.tools_used,
            "function_calls": self.function_calls,
            "external_apis": self.external_apis,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "is_monitored": self.is_monitored,
            "debug_mode": self.debug_mode,
            "log_level": self.log_level,
            "trace_id": self.trace_id,
            "environment": self.environment,
            "version": self.version,
            "platform_info": self.platform_info,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @property
    def is_completed(self) -> bool:
        """Check if execution is completed (success or failure)."""
        return self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]
    
    @property
    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.status == ExecutionStatus.RUNNING
    
    @property
    def is_successful(self) -> bool:
        """Check if execution completed successfully."""
        return self.status == ExecutionStatus.COMPLETED
    
    @property
    def execution_time(self) -> Optional[float]:
        """Calculate execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def calculate_cost(self) -> Optional[float]:
        """Calculate execution cost from cost_usd string."""
        if self.cost_usd:
            try:
                return float(self.cost_usd)
            except (ValueError, TypeError):
                return None
        return None
