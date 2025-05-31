"""
Error Handling Middleware

This module provides comprehensive error handling middleware for the FastAPI application,
including custom exception handling, validation error formatting, and error logging.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from fastapi import HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    ValidationError as AppValidationError,
    ResourceNotFoundError,
    ConflictError,
    RateLimitError,
    ServiceUnavailableError,
    DatabaseError,
    AIServiceError,
    AgentError,
    ConversationError,
    BusinessLogicError,
)

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors and exceptions across the application."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and handle any exceptions that occur.
        
        Args:
            request: HTTP request
            call_next: Next middleware or endpoint
            
        Returns:
            HTTP response
        """
        # Generate request ID for error tracking
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self.handle_exception(request, exc, request_id)
    
    async def handle_exception(
        self, 
        request: Request, 
        exc: Exception, 
        request_id: str
    ) -> JSONResponse:
        """
        Handle different types of exceptions and return appropriate responses.
        
        Args:
            request: HTTP request
            exc: Exception that occurred
            request_id: Request ID for tracking
            
        Returns:
            JSON response with error details
        """
        # Log the exception
        await self.log_exception(request, exc, request_id)
        
        # Handle different exception types
        if isinstance(exc, HTTPException):
            return await self.handle_http_exception(exc, request_id)
        elif isinstance(exc, RequestValidationError):
            return await self.handle_validation_error(exc, request_id)
        elif isinstance(exc, ValidationError):
            return await self.handle_pydantic_validation_error(exc, request_id)
        elif isinstance(exc, AppException):
            return await self.handle_app_exception(exc, request_id)
        else:
            return await self.handle_unexpected_exception(exc, request_id)
    
    async def handle_http_exception(
        self, 
        exc: HTTPException, 
        request_id: str
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_error",
                    "code": exc.status_code,
                    "message": exc.detail,
                    "request_id": request_id,
                }
            },
            headers=getattr(exc, "headers", None),
        )
    
    async def handle_validation_error(
        self, 
        exc: RequestValidationError, 
        request_id: str
    ) -> JSONResponse:
        """Handle FastAPI request validation errors."""
        errors = []
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "validation_error",
                    "code": 422,
                    "message": "Request validation failed",
                    "details": errors,
                    "request_id": request_id,
                }
            },
        )
    
    async def handle_pydantic_validation_error(
        self, 
        exc: ValidationError, 
        request_id: str
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        errors = []
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "pydantic_validation_error",
                    "code": 422,
                    "message": "Data validation failed",
                    "details": errors,
                    "request_id": request_id,
                }
            },
        )
    
    async def handle_app_exception(
        self, 
        exc: AppException, 
        request_id: str
    ) -> JSONResponse:
        """Handle custom application exceptions."""
        error_data = {
            "type": exc.__class__.__name__,
            "code": exc.status_code,
            "message": exc.message,
            "request_id": request_id,
        }
        
        # Add additional data if available
        if exc.error_data:
            error_data["details"] = exc.error_data
        
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": error_data},
        )
    
    async def handle_unexpected_exception(
        self, 
        exc: Exception, 
        request_id: str
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        error_data = {
            "type": "internal_server_error",
            "code": 500,
            "message": "An unexpected error occurred",
            "request_id": request_id,
        }
        
        # Include exception details in development
        if settings.ENVIRONMENT == "development":
            error_data["details"] = {
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc(),
            }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": error_data},
        )
    
    async def log_exception(
        self, 
        request: Request, 
        exc: Exception, 
        request_id: str
    ) -> None:
        """
        Log exception details for monitoring and debugging.
        
        Args:
            request: HTTP request
            exc: Exception that occurred
            request_id: Request ID for tracking
        """
        # Get request details
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Log different exception types with appropriate levels
        if isinstance(exc, (AuthenticationError, AuthorizationError)):
            logger.warning(
                f"Security error: {exc.__class__.__name__}: {exc}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "url": url,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "exception_type": exc.__class__.__name__,
                }
            )
        elif isinstance(exc, (ValidationError, AppValidationError, RequestValidationError)):
            logger.info(
                f"Validation error: {exc.__class__.__name__}: {exc}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "url": url,
                    "client_ip": client_ip,
                    "exception_type": exc.__class__.__name__,
                }
            )
        elif isinstance(exc, (ResourceNotFoundError, ConflictError)):
            logger.info(
                f"Client error: {exc.__class__.__name__}: {exc}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "url": url,
                    "client_ip": client_ip,
                    "exception_type": exc.__class__.__name__,
                }
            )
        elif isinstance(exc, RateLimitError):
            logger.warning(
                f"Rate limit exceeded: {exc}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "url": url,
                    "client_ip": client_ip,
                    "exception_type": exc.__class__.__name__,
                }
            )
        elif isinstance(exc, (DatabaseError, AIServiceError, ServiceUnavailableError)):
            logger.error(
                f"Service error: {exc.__class__.__name__}: {exc}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "url": url,
                    "client_ip": client_ip,
                    "exception_type": exc.__class__.__name__,
                },
                exc_info=True
            )
        elif isinstance(exc, HTTPException):
            if exc.status_code >= 500:
                logger.error(
                    f"HTTP error {exc.status_code}: {exc.detail}",
                    extra={
                        "request_id": request_id,
                        "method": method,
                        "url": url,
                        "client_ip": client_ip,
                        "status_code": exc.status_code,
                    }
                )
            else:
                logger.info(
                    f"HTTP error {exc.status_code}: {exc.detail}",
                    extra={
                        "request_id": request_id,
                        "method": method,
                        "url": url,
                        "client_ip": client_ip,
                        "status_code": exc.status_code,
                    }
                )
        else:
            logger.error(
                f"Unexpected error: {exc.__class__.__name__}: {exc}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "url": url,
                    "client_ip": client_ip,
                    "exception_type": exc.__class__.__name__,
                },
                exc_info=True
            )


def get_error_response(
    message: str,
    status_code: int = 500,
    error_type: str = "error",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        status_code: HTTP status code
        error_type: Type of error
        details: Additional error details
        request_id: Request ID for tracking
        
    Returns:
        JSON response with error details
    """
    error_data = {
        "type": error_type,
        "code": status_code,
        "message": message,
    }
    
    if details:
        error_data["details"] = details
    
    if request_id:
        error_data["request_id"] = request_id
    
    return JSONResponse(
        status_code=status_code,
        content={"error": error_data},
    )
