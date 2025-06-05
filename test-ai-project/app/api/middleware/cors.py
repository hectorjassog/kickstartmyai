"""
CORS (Cross-Origin Resource Sharing) Middleware Configuration

This module provides CORS configuration for the FastAPI application,
handling cross-origin requests with appropriate security measures.
"""

from typing import List, Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def setup_cors(app: FastAPI) -> None:
    """
    Configure CORS middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Development origins
    dev_origins = [
        "http://localhost:3000",  # React dev server
        "http://localhost:3001",  # Alternative dev port
        "http://localhost:8000",  # FastAPI dev server
        "http://localhost:8080",  # Alternative dev port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    # Production origins from settings
    allowed_origins = []
    
    if settings.ENVIRONMENT == "development":
        # Allow all origins in development
        allowed_origins = ["*"]
    elif settings.BACKEND_CORS_ORIGINS:
        # Use configured origins in production
        if isinstance(settings.BACKEND_CORS_ORIGINS, str):
            allowed_origins = [
                origin.strip() for origin in settings.BACKEND_CORS_ORIGINS.split(",")
                if origin.strip()
            ]
        else:
            allowed_origins = settings.BACKEND_CORS_ORIGINS
    else:
        # Default to development origins if not configured
        allowed_origins = dev_origins
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Requested-With",
            "Accept",
            "Origin",
            "Access-Control-Request-Method",
            "Access-Control-Request-Headers",
            "X-API-Key",
            "X-Request-ID",
            "X-User-ID",
            "X-Organization-ID",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Response-Time",
            "X-Rate-Limit-Remaining",
            "X-Rate-Limit-Reset",
            "X-Total-Count",
            "X-Page-Count",
        ],
        max_age=3600,  # Cache preflight requests for 1 hour
    )


def get_cors_origins() -> List[str]:
    """
    Get the configured CORS origins.
    
    Returns:
        List of allowed CORS origins
    """
    if settings.ENVIRONMENT == "development":
        return ["*"]
    
    if settings.BACKEND_CORS_ORIGINS:
        if isinstance(settings.BACKEND_CORS_ORIGINS, str):
            return [
                origin.strip() for origin in settings.BACKEND_CORS_ORIGINS.split(",")
                if origin.strip()
            ]
        return settings.BACKEND_CORS_ORIGINS
    
    return []


def is_origin_allowed(origin: str) -> bool:
    """
    Check if an origin is allowed by CORS configuration.
    
    Args:
        origin: Origin to check
        
    Returns:
        True if origin is allowed, False otherwise
    """
    allowed_origins = get_cors_origins()
    
    # Allow all origins if "*" is in the list
    if "*" in allowed_origins:
        return True
    
    # Check exact match
    if origin in allowed_origins:
        return True
    
    # Check wildcard patterns (basic implementation)
    for allowed_origin in allowed_origins:
        if allowed_origin.endswith("*"):
            pattern = allowed_origin[:-1]
            if origin.startswith(pattern):
                return True
    
    return False
