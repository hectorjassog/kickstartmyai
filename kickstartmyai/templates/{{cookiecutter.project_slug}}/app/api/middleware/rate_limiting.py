"""
Rate Limiting Middleware

This module provides rate limiting functionality for the FastAPI application,
including configurable rate limits, different strategies, and Redis-based storage.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Tuple, Union
from uuid import uuid4

import redis.asyncio as redis
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import RateLimitError

logger = logging.getLogger(__name__)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests based on various strategies."""
    
    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application
            redis_client: Redis client for distributed rate limiting
        """
        super().__init__(app)
        self.redis_client = redis_client
        self.local_cache: Dict[str, Dict[str, Union[int, float]]] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and apply rate limiting.
        
        Args:
            request: HTTP request
            call_next: Next middleware or endpoint
            
        Returns:
            HTTP response
        """
        # Skip rate limiting for certain paths
        if self.should_skip_rate_limiting(request):
            return await call_next(request)
        
        # Get rate limit configuration
        rate_limit_config = self.get_rate_limit_config(request)
        if not rate_limit_config:
            return await call_next(request)
        
        # Get client identifier
        client_id = self.get_client_identifier(request)
        
        # Check rate limit
        try:
            allowed, remaining, reset_time = await self.check_rate_limit(
                client_id, rate_limit_config
            )
            
            if not allowed:
                return self.create_rate_limit_response(remaining, reset_time)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            self.add_rate_limit_headers(response, remaining, reset_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue without rate limiting if there's an error
            return await call_next(request)
    
    def should_skip_rate_limiting(self, request: Request) -> bool:
        """
        Check if rate limiting should be skipped for this request.
        
        Args:
            request: HTTP request
            
        Returns:
            True if rate limiting should be skipped
        """
        path = request.url.path
        
        # Skip for health checks and internal endpoints
        skip_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def get_rate_limit_config(self, request: Request) -> Optional[Dict[str, int]]:
        """
        Get rate limit configuration for the request.
        
        Args:
            request: HTTP request
            
        Returns:
            Rate limit configuration or None
        """
        if not settings.ENABLE_RATE_LIMITING:
            return None
        
        path = request.url.path
        method = request.method
        
        # Default rate limits
        config = {
            "requests": settings.RATE_LIMIT_REQUESTS,
            "window": settings.RATE_LIMIT_WINDOW,
        }
        
        # API-specific rate limits
        if path.startswith("/api/v1/"):
            # Higher limits for authenticated users
            auth_header = request.headers.get("Authorization")
            if auth_header:
                config["requests"] = min(config["requests"] * 2, 1000)
            
            # Different limits for different endpoints
            if "/chat" in path or "/completion" in path:
                # Lower limits for AI endpoints
                config["requests"] = min(config["requests"] // 2, 50)
            elif method in ["POST", "PUT", "DELETE"]:
                # Lower limits for write operations
                config["requests"] = min(config["requests"] // 2, 100)
        
        return config
    
    def get_client_identifier(self, request: Request) -> str:
        """
        Get a unique identifier for the client.
        
        Args:
            request: HTTP request
            
        Returns:
            Client identifier
        """
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Try to get API key from headers
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key[:8]}..."
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    async def check_rate_limit(
        self, 
        client_id: str, 
        config: Dict[str, int]
    ) -> Tuple[bool, int, float]:
        """
        Check if the client has exceeded the rate limit.
        
        Args:
            client_id: Client identifier
            config: Rate limit configuration
            
        Returns:
            Tuple of (allowed, remaining_requests, reset_time)
        """
        if self.redis_client:
            return await self.check_rate_limit_redis(client_id, config)
        else:
            return await self.check_rate_limit_local(client_id, config)
    
    async def check_rate_limit_redis(
        self, 
        client_id: str, 
        config: Dict[str, int]
    ) -> Tuple[bool, int, float]:
        """
        Check rate limit using Redis sliding window.
        
        Args:
            client_id: Client identifier
            config: Rate limit configuration
            
        Returns:
            Tuple of (allowed, remaining_requests, reset_time)
        """
        try:
            current_time = time.time()
            window_start = current_time - config["window"]
            key = f"rate_limit:{client_id}"
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            request_id = str(uuid4())
            pipe.zadd(key, {request_id: current_time})
            
            # Set expiration
            pipe.expire(key, config["window"] + 1)
            
            results = await pipe.execute()
            current_requests = results[1] + 1  # +1 for the current request
            
            allowed = current_requests <= config["requests"]
            remaining = max(0, config["requests"] - current_requests)
            reset_time = current_time + config["window"]
            
            return allowed, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            # Fall back to local rate limiting
            return await self.check_rate_limit_local(client_id, config)
    
    async def check_rate_limit_local(
        self, 
        client_id: str, 
        config: Dict[str, int]
    ) -> Tuple[bool, int, float]:
        """
        Check rate limit using local memory (not suitable for distributed systems).
        
        Args:
            client_id: Client identifier
            config: Rate limit configuration
            
        Returns:
            Tuple of (allowed, remaining_requests, reset_time)
        """
        current_time = time.time()
        
        # Clean up old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            await self.cleanup_local_cache()
            self.last_cleanup = current_time
        
        # Get or create client entry
        if client_id not in self.local_cache:
            self.local_cache[client_id] = {
                "requests": [],
                "reset_time": current_time + config["window"]
            }
        
        client_data = self.local_cache[client_id]
        
        # Reset window if expired
        if current_time >= client_data["reset_time"]:
            client_data["requests"] = []
            client_data["reset_time"] = current_time + config["window"]
        
        # Remove old requests from current window
        window_start = current_time - config["window"]
        client_data["requests"] = [
            req_time for req_time in client_data["requests"]
            if req_time > window_start
        ]
        
        # Check if limit is exceeded
        current_requests = len(client_data["requests"]) + 1  # +1 for current request
        allowed = current_requests <= config["requests"]
        
        if allowed:
            client_data["requests"].append(current_time)
        
        remaining = max(0, config["requests"] - current_requests)
        reset_time = client_data["reset_time"]
        
        return allowed, remaining, reset_time
    
    async def cleanup_local_cache(self) -> None:
        """Clean up expired entries from local cache."""
        current_time = time.time()
        expired_clients = []
        
        for client_id, client_data in self.local_cache.items():
            if current_time >= client_data["reset_time"]:
                # Remove old requests
                window_start = current_time - 3600  # Keep last hour
                client_data["requests"] = [
                    req_time for req_time in client_data["requests"]
                    if req_time > window_start
                ]
                
                # Mark for deletion if no recent requests
                if not client_data["requests"]:
                    expired_clients.append(client_id)
        
        # Remove expired clients
        for client_id in expired_clients:
            del self.local_cache[client_id]
        
        logger.debug(f"Cleaned up {len(expired_clients)} expired rate limit entries")
    
    def create_rate_limit_response(
        self, 
        remaining: int, 
        reset_time: float
    ) -> JSONResponse:
        """
        Create a rate limit exceeded response.
        
        Args:
            remaining: Remaining requests
            reset_time: Reset time
            
        Returns:
            JSON response with rate limit error
        """
        retry_after = max(1, int(reset_time - time.time()))
        
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "type": "rate_limit_exceeded",
                    "code": 429,
                    "message": "Rate limit exceeded. Please try again later.",
                    "details": {
                        "retry_after": retry_after,
                        "remaining": remaining,
                    }
                }
            }
        )
        
        self.add_rate_limit_headers(response, remaining, reset_time)
        response.headers["Retry-After"] = str(retry_after)
        
        return response
    
    def add_rate_limit_headers(
        self, 
        response: Response, 
        remaining: int, 
        reset_time: float
    ) -> None:
        """
        Add rate limit headers to the response.
        
        Args:
            response: HTTP response
            remaining: Remaining requests
            reset_time: Reset time
        """
        response.headers["X-Rate-Limit-Remaining"] = str(remaining)
        response.headers["X-Rate-Limit-Reset"] = str(int(reset_time))


async def create_redis_client() -> Optional[redis.Redis]:
    """
    Create Redis client for rate limiting.
    
    Returns:
        Redis client or None if not configured
    """
    if not settings.REDIS_URL:
        return None
    
    try:
        client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        
        # Test connection
        await client.ping()
        logger.info("Redis client created for rate limiting")
        return client
        
    except Exception as e:
        logger.warning(f"Failed to create Redis client for rate limiting: {e}")
        return None


def create_rate_limiting_middleware(redis_client: Optional[redis.Redis] = None):
    """
    Create rate limiting middleware with optional Redis client.
    
    Args:
        redis_client: Redis client for distributed rate limiting
        
    Returns:
        Rate limiting middleware class
    """
    class ConfiguredRateLimitingMiddleware(RateLimitingMiddleware):
        def __init__(self, app):
            super().__init__(app, redis_client)
    
    return ConfiguredRateLimitingMiddleware
