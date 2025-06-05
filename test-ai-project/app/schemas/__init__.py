"""Schemas package."""

# User schemas
from .user import (
    User,
    UserCreate,
    UserUpdate,
    UserInDB,
    UserStatistics,
    UserListResponse,
    UserFilter,
    UserActivation
)

# Agent schemas
from .agent import (
    Agent,
    AgentCreate,
    AgentUpdate,
    AgentInDB,
    AgentStatistics,
    AgentListResponse,
    AgentWithExecutions,
    AgentFilter
)

# Conversation schemas
from .conversation import (
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    ConversationInDB,
    ConversationWithMessages,
    ConversationWithFullContext,
    ConversationStatistics,
    ConversationListResponse,
    ConversationFilter,
    ConversationSummary
)

# Message schemas
from .message import (
    Message,
    MessageCreate,
    MessageUpdate,
    MessageInDB,
    MessageListResponse,
    MessageStatistics,
    MessageFilter,
    MessageContext,
    BulkMessageCreate
)

# Execution schemas
from .execution import (
    Execution,
    ExecutionCreate,
    ExecutionUpdate,
    ExecutionInDB,
    ExecutionWithChildren,
    ExecutionStatistics,
    ExecutionListResponse,
    ExecutionFilter,
    ExecutionPerformanceMetrics,
    ExecutionRetry,
    ExecutionStatusUpdate
)

# Auth schemas
from .auth import (
    Token,
    TokenData,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    LogoutRequest
)

__all__ = [
    # User schemas
    "User",
    "UserCreate", 
    "UserUpdate",
    "UserInDB",
    "UserStatistics",
    "UserListResponse",
    "UserFilter",
    "UserActivation",
    
    # Agent schemas
    "Agent",
    "AgentCreate",
    "AgentUpdate", 
    "AgentInDB",
    "AgentStatistics",
    "AgentListResponse",
    "AgentWithExecutions",
    "AgentFilter",
    
    # Conversation schemas
    "Conversation",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationInDB",
    "ConversationWithMessages",
    "ConversationWithFullContext",
    "ConversationStatistics", 
    "ConversationListResponse",
    "ConversationFilter",
    "ConversationSummary",
    
    # Message schemas
    "Message",
    "MessageCreate",
    "MessageUpdate",
    "MessageInDB",
    "MessageListResponse",
    "MessageStatistics",
    "MessageFilter",
    "MessageContext",
    "BulkMessageCreate",
    
    # Execution schemas
    "Execution",
    "ExecutionCreate",
    "ExecutionUpdate",
    "ExecutionInDB",
    "ExecutionWithChildren",
    "ExecutionStatistics",
    "ExecutionListResponse",
    "ExecutionFilter",
    "ExecutionPerformanceMetrics",
    "ExecutionRetry",
    "ExecutionStatusUpdate",
    
    # Auth schemas
    "Token",
    "TokenData",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "RegisterRequest",
    "RegisterResponse",
    "LogoutRequest"
]