"""Execution Pydantic schemas."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.execution import ExecutionStatus, ExecutionType


# Shared properties
class ExecutionBase(BaseModel):
    """Execution base schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[ExecutionType] = Field(default=ExecutionType.CHAT)
    agent_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    parent_execution_id: Optional[UUID] = None
    input_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    priority: Optional[int] = Field(default=0, ge=-10, le=10)


# Properties to receive via API on creation
class ExecutionCreate(ExecutionBase):
    """Execution creation schema."""
    name: str = Field(..., min_length=1, max_length=255)
    type: ExecutionType = Field(default=ExecutionType.CHAT)
    agent_id: UUID


# Properties to receive via API on update
class ExecutionUpdate(ExecutionBase):
    """Execution update schema."""
    status: Optional[ExecutionStatus] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    tokens_used: Optional[int] = Field(None, ge=0)
    cost: Optional[Decimal] = Field(None, ge=0)


# Schema with database fields
class ExecutionInDBBase(ExecutionBase):
    """Execution schema with database fields."""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[UUID] = None
    execution_id: Optional[str] = None
    user_id: Optional[UUID] = None
    status: Optional[ExecutionStatus] = Field(default=ExecutionStatus.PENDING)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    tokens_used: Optional[int] = Field(default=0, ge=0)
    cost: Optional[Decimal] = Field(None, ge=0)
    retry_count: Optional[int] = Field(default=0, ge=0)
    original_execution_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Additional properties to return via API
class Execution(ExecutionInDBBase):
    """Execution schema for API responses."""
    pass


# Alias for backward compatibility
ExecutionResponse = Execution


# Additional properties stored in DB
class ExecutionInDB(ExecutionInDBBase):
    """Execution schema in database."""
    pass


# Execution with children schema
class ExecutionWithChildren(Execution):
    """Execution schema with child executions."""
    children: List["ExecutionWithChildren"] = Field(default_factory=list)


# Execution statistics schema
class ExecutionStatistics(BaseModel):
    """Execution statistics schema."""
    total_executions: int
    successful_executions: int
    failed_executions: int
    pending_executions: int
    running_executions: int
    cancelled_executions: int
    success_rate: float
    average_duration_seconds: float
    total_tokens_used: int
    total_cost: Decimal
    executions_by_type: Dict[str, int]
    executions_by_status: Dict[str, int]


# Execution list response schema
class ExecutionListResponse(BaseModel):
    """Execution list response schema."""
    executions: List[Execution]
    total_count: int
    page: int
    page_size: int
    has_next: bool


# Execution filter schema
class ExecutionFilter(BaseModel):
    """Execution filter schema for complex queries."""
    user_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    parent_execution_id: Optional[UUID] = None
    status: Optional[ExecutionStatus] = None
    execution_type: Optional[ExecutionType] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    started_after: Optional[datetime] = None
    started_before: Optional[datetime] = None


# Execution performance metrics schema
class ExecutionPerformanceMetrics(BaseModel):
    """Execution performance metrics schema."""
    total_executions: int
    successful_executions: int
    success_rate: float
    average_duration_seconds: float
    max_duration_seconds: float
    min_duration_seconds: float
    total_tokens_used: int
    total_cost: Decimal
    period_days: int


# Execution retry schema
class ExecutionRetry(BaseModel):
    """Execution retry schema."""
    execution_id: UUID
    reason: Optional[str] = None


# Execution status update schema
class ExecutionStatusUpdate(BaseModel):
    """Execution status update schema."""
    status: ExecutionStatus
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None
    tokens_used: Optional[int] = Field(None, ge=0)
    cost: Optional[Decimal] = Field(None, ge=0)


# Execution batch creation schema
class ExecutionBatchCreate(BaseModel):
    """Execution batch creation schema."""
    executions: List[ExecutionCreate]
    batch_name: Optional[str] = None
    batch_description: Optional[str] = None


# Execution batch response schema
class ExecutionBatchResponse(BaseModel):
    """Execution batch response schema."""
    batch_id: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    executions: List[ExecutionResponse]


# Execution statistics response schema
class ExecutionStatsResponse(BaseModel):
    """Execution statistics response schema."""
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    average_duration_seconds: float
    total_tokens_used: int
    total_cost: Decimal
    period_days: int


# Execution tree response schema
class ExecutionTreeResponse(BaseModel):
    """Execution tree response schema."""
    execution: ExecutionResponse
    children: List["ExecutionTreeResponse"] = Field(default_factory=list)
    depth: int = 0


# Forward reference resolution
ExecutionWithChildren.model_rebuild()
ExecutionTreeResponse.model_rebuild() 