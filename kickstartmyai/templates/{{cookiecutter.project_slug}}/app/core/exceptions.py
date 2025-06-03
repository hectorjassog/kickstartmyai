"""Custom exception classes for the application."""

from typing import Any, Dict, Optional, List
from fastapi import HTTPException, status


class BaseAppException(Exception):
    """Base exception for the application."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# Alias for backward compatibility and cleaner imports
AppException = BaseAppException


class HTTPAppException(HTTPException):
    """Custom HTTP exception with additional details."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[Dict[str, str]] = None,
        error_code: Optional[str] = None,
        error_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
        self.error_data = error_data or {}


# Authentication & Authorization Exceptions
class AuthenticationError(HTTPAppException):
    """Authentication failed."""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
            error_code="AUTH_001"
        )


class AuthorizationError(HTTPAppException):
    """Authorization failed."""
    
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTH_002"
        )


class InvalidTokenError(HTTPAppException):
    """Invalid or expired token."""
    
    def __init__(self, detail: str = "Invalid or expired token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
            error_code="AUTH_003"
        )


class TokenExpiredError(HTTPAppException):
    """Token has expired."""
    
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
            error_code="AUTH_004"
        )


# Validation Exceptions
class ValidationError(HTTPAppException):
    """Data validation failed."""
    
    def __init__(self, detail: str = "Validation failed", errors: Optional[List[Dict]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VAL_001",
            error_data={"errors": errors or []}
        )


class InvalidInputError(HTTPAppException):
    """Invalid input data."""
    
    def __init__(self, field: str, detail: str = "Invalid input"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="VAL_002",
            error_data={"field": field}
        )


# Resource Exceptions
class NotFoundError(HTTPAppException):
    """Resource not found."""
    
    def __init__(self, resource: str, detail: Optional[str] = None):
        detail = detail or f"{resource} not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="RES_001",
            error_data={"resource": resource}
        )


class ConflictError(HTTPAppException):
    """Resource conflict."""
    
    def __init__(self, resource: str, detail: Optional[str] = None):
        detail = detail or f"{resource} already exists"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="RES_002",
            error_data={"resource": resource}
        )


class DependencyError(HTTPAppException):
    """Resource dependency conflict."""
    
    def __init__(self, resource: str, dependency: str, detail: Optional[str] = None):
        detail = detail or f"Cannot delete {resource} due to dependency on {dependency}"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="RES_003",
            error_data={"resource": resource, "dependency": dependency}
        )


# Database Exceptions
class DatabaseError(BaseAppException):
    """Database operation failed."""
    
    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.operation = operation


class DatabaseConnectionError(DatabaseError):
    """Database connection failed."""
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            "Database connection failed",
            "connection",
            details
        )


class DatabaseQueryError(DatabaseError):
    """Database query failed."""
    
    def __init__(self, query: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Database query failed: {query}",
            "query",
            details
        )


# AI Service Exceptions
class AIServiceError(BaseAppException):
    """AI service operation failed."""
    
    def __init__(self, provider: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.provider = provider


class AIProviderError(HTTPAppException):
    """AI provider error."""
    
    def __init__(self, provider: str, detail: str = "AI provider error"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="AI_001",
            error_data={"provider": provider}
        )


class AIQuotaExceededError(HTTPAppException):
    """AI service quota exceeded."""
    
    def __init__(self, provider: str, detail: str = "AI service quota exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="AI_002",
            error_data={"provider": provider}
        )


class AITimeoutError(HTTPAppException):
    """AI service timeout."""
    
    def __init__(self, provider: str, detail: str = "AI service timeout"):
        super().__init__(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=detail,
            error_code="AI_003",
            error_data={"provider": provider}
        )


class AIInvalidRequestError(HTTPAppException):
    """Invalid AI request."""
    
    def __init__(self, provider: str, detail: str = "Invalid AI request"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="AI_004",
            error_data={"provider": provider}
        )


# Agent Exceptions
class AgentError(BaseAppException):
    """Agent operation failed."""
    
    def __init__(self, agent_id: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.agent_id = agent_id


class AgentNotFoundError(NotFoundError):
    """Agent not found."""
    
    def __init__(self, agent_id: str):
        super().__init__("Agent", f"Agent {agent_id} not found")


class AgentExecutionError(HTTPAppException):
    """Agent execution failed."""
    
    def __init__(self, agent_id: str, detail: str = "Agent execution failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="AGENT_001",
            error_data={"agent_id": agent_id}
        )


class AgentTimeoutError(HTTPAppException):
    """Agent execution timeout."""
    
    def __init__(self, agent_id: str, timeout: int):
        super().__init__(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Agent execution timeout after {timeout} seconds",
            error_code="AGENT_002",
            error_data={"agent_id": agent_id, "timeout": timeout}
        )


# Conversation Exceptions
class ConversationError(BaseAppException):
    """Conversation operation failed."""
    
    def __init__(self, conversation_id: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.conversation_id = conversation_id


class ConversationNotFoundError(NotFoundError):
    """Conversation not found."""
    
    def __init__(self, conversation_id: str):
        super().__init__("Conversation", f"Conversation {conversation_id} not found")


class ConversationAccessError(HTTPAppException):
    """Conversation access denied."""
    
    def __init__(self, conversation_id: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to conversation",
            error_code="CONV_001",
            error_data={"conversation_id": conversation_id}
        )


# Message Exceptions
class MessageError(BaseAppException):
    """Message operation failed."""
    
    def __init__(self, message_id: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.message_id = message_id


class MessageNotFoundError(NotFoundError):
    """Message not found."""
    
    def __init__(self, message_id: str):
        super().__init__("Message", f"Message {message_id} not found")


# Execution Exceptions
class ExecutionError(BaseAppException):
    """Execution operation failed."""
    
    def __init__(self, execution_id: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.execution_id = execution_id


class ExecutionNotFoundError(NotFoundError):
    """Execution not found."""
    
    def __init__(self, execution_id: str):
        super().__init__("Execution", f"Execution {execution_id} not found")


class ExecutionFailedError(HTTPAppException):
    """Execution failed."""
    
    def __init__(self, execution_id: str, reason: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {reason}",
            error_code="EXEC_001",
            error_data={"execution_id": execution_id, "reason": reason}
        )


# Rate Limiting Exceptions
class RateLimitExceededError(HTTPAppException):
    """Rate limit exceeded."""
    
    def __init__(self, limit: int, window: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit} requests per {window} seconds",
            error_code="RATE_001",
            error_data={"limit": limit, "window": window}
        )


# Feature Flag Exceptions
class FeatureNotEnabledError(HTTPAppException):
    """Feature not enabled."""
    
    def __init__(self, feature: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Feature '{feature}' is not enabled",
            error_code="FEAT_001",
            error_data={"feature": feature}
        )


# Cache Exceptions
class CacheError(BaseAppException):
    """Cache operation failed."""
    
    def __init__(self, operation: str, key: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Cache {operation} failed for key: {key}", details)
        self.operation = operation
        self.key = key


# File System Exceptions
class FileSystemError(BaseAppException):
    """File system operation failed."""
    
    def __init__(self, operation: str, path: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"File system {operation} failed for path: {path}", details)
        self.operation = operation
        self.path = path


class FileNotFoundError(NotFoundError):
    """File not found."""
    
    def __init__(self, path: str):
        super().__init__("File", f"File not found: {path}")


class FileTooLargeError(HTTPAppException):
    """File too large."""
    
    def __init__(self, size: int, max_size: int):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {size} bytes exceeds maximum {max_size} bytes",
            error_code="FILE_001",
            error_data={"size": size, "max_size": max_size}
        )


# External Service Exceptions
class ExternalServiceError(HTTPAppException):
    """External service error."""
    
    def __init__(self, service: str, detail: str = "External service error"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="EXT_001",
            error_data={"service": service}
        )


class WebSearchError(ExternalServiceError):
    """Web search service error."""
    
    def __init__(self, detail: str = "Web search service error"):
        super().__init__("web_search", detail)


# Business Logic Exceptions
class BusinessLogicError(HTTPAppException):
    """Business logic validation failed."""
    
    def __init__(self, rule: str, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="BIZ_001",
            error_data={"rule": rule}
        )


class InsufficientPermissionsError(HTTPAppException):
    """Insufficient permissions for operation."""
    
    def __init__(self, operation: str, resource: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for {operation} on {resource}",
            error_code="PERM_001",
            error_data={"operation": operation, "resource": resource}
        )


# Server Exceptions
class InternalServerError(HTTPAppException):
    """Internal server error."""
    
    def __init__(self, detail: str = "Internal server error", error_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="SRV_001",
            error_data={"error_id": error_id} if error_id else {}
        )


class ServiceUnavailableError(HTTPAppException):
    """Service temporarily unavailable."""
    
    def __init__(self, service: str, detail: Optional[str] = None):
        detail = detail or f"Service {service} is temporarily unavailable"
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="SRV_002",
            error_data={"service": service}
        )


class MaintenanceModeError(HTTPAppException):
    """Application is in maintenance mode."""
    
    def __init__(self, estimated_duration: Optional[int] = None):
        detail = "Application is currently under maintenance"
        if estimated_duration:
            detail += f". Estimated duration: {estimated_duration} minutes"
        
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="SYS_003",
            error_data={"estimated_duration": estimated_duration}
        )


# Aliases for backward compatibility
ResourceNotFoundError = NotFoundError
RateLimitError = RateLimitExceededError
