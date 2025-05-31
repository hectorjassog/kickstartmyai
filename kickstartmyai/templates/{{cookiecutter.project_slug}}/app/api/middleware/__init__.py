"""
API Middleware

This module provides all middleware components for the FastAPI application.
"""

from .cors import setup_cors, get_cors_origins, is_origin_allowed
from .error_handling import ErrorHandlingMiddleware, get_error_response
from .logging import LoggingMiddleware
from .rate_limiting import RateLimitingMiddleware, create_rate_limiting_middleware, create_redis_client
from .security import SecurityMiddleware
from .timing import TimingMiddleware

__all__ = [
    # CORS
    "setup_cors",
    "get_cors_origins", 
    "is_origin_allowed",
    
    # Error Handling
    "ErrorHandlingMiddleware",
    "get_error_response",
    
    # Logging
    "LoggingMiddleware",
    
    # Rate Limiting
    "RateLimitingMiddleware",
    "create_rate_limiting_middleware",
    "create_redis_client",
    
    # Security
    "SecurityMiddleware",
    
    # Timing
    "TimingMiddleware",
]