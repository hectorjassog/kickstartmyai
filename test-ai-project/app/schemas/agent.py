"""Agent Pydantic schemas."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.agent import AgentType, AgentStatus


# Shared properties
class AgentBase(BaseModel):
    """Agent base schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    provider: Optional[str] = Field(default="openai")
    model: Optional[str] = Field(default="gpt-4")
    temperature: Optional[str] = Field(default="0.7")
    max_tokens: Optional[int] = Field(default=2000, ge=1, le=128000)
    max_iterations: Optional[int] = Field(default=10, ge=1, le=100)
    enable_memory: Optional[bool] = Field(default=True)
    memory_types: Optional[List[str]] = Field(default_factory=lambda: ["conversation"])
    available_tools: Optional[List[str]] = Field(default_factory=list)
    agent_type: Optional[AgentType] = Field(default=AgentType.PERSONAL)
    status: Optional[AgentStatus] = Field(default=AgentStatus.ACTIVE)
    is_public: Optional[bool] = Field(default=False)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v: str) -> str:
        """Validate temperature is a valid float string."""
        try:
            temp = float(v)
            if not 0.0 <= temp <= 2.0:
                raise ValueError("Temperature must be between 0.0 and 2.0")
            return v
        except ValueError as e:
            if "could not convert" in str(e):
                raise ValueError("Temperature must be a valid number")
            raise e


# Properties to receive via API on creation
class AgentCreate(AgentBase):
    """Agent creation schema."""
    name: str = Field(..., min_length=1, max_length=255)
    system_prompt: str = Field(..., min_length=1)


# Properties to receive via API on update
class AgentUpdate(AgentBase):
    """Agent update schema."""
    pass


# Schema with database fields
class AgentInDBBase(AgentBase):
    """Agent schema with database fields."""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    usage_count: Optional[int] = Field(default=0, ge=0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Additional properties to return via API
class Agent(AgentInDBBase):
    """Agent schema for API responses."""
    pass


# Additional properties stored in DB
class AgentInDB(AgentInDBBase):
    """Agent schema in database."""
    pass


# Agent statistics schema
class AgentStatistics(BaseModel):
    """Agent statistics schema."""
    total_agents: int
    active_agents: int
    inactive_agents: int
    archived_agents: int
    agents_by_type: Dict[str, int]
    most_used_agents: List[Dict[str, Any]]
    average_usage: float
    total_usage: int


# Agent list response schema
class AgentListResponse(BaseModel):
    """Agent list response schema."""
    agents: List[Agent]
    total_count: int
    page: int
    page_size: int
    has_next: bool


# Agent with executions schema
class AgentWithExecutions(Agent):
    """Agent schema with executions included."""
    executions: List[Dict[str, Any]] = Field(default_factory=list)


# Agent filter schema
class AgentFilter(BaseModel):
    """Agent filter schema for complex queries."""
    user_id: Optional[UUID] = None
    agent_type: Optional[AgentType] = None
    status: Optional[AgentStatus] = None
    provider: Optional[str] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None
    search_term: Optional[str] = None
    include_deprecated: Optional[bool] = Field(default=False) 