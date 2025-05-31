"""Security middleware for HTTP headers and protection."""

import re
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers and protection."""
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.sensitive_headers = {
            "authorization", "cookie", "x-api-key", "x-auth-token"
        }
        self.sensitive_params = {
            "password", "token", "secret", "key", "credentials"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add security headers to response."""
        
        # Process the request
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response)
        
        # Remove sensitive information from logs
        self._sanitize_request(request)
        
        return response
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to the response."""
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy (basic)
        if not settings.is_development():
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
            response.headers["Content-Security-Policy"] = csp
        
        # HSTS (HTTPS only)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=(), "
            "vibrate=(), "
            "fullscreen=(self), "
            "payment=()"
        )
        
        # Remove server information
        response.headers.pop("server", None)
        response.headers.pop("x-powered-by", None)
    
    def _sanitize_request(self, request: Request) -> None:
        """Remove sensitive information from request for logging."""
        
        # Sanitize headers
        if hasattr(request.state, "logging_context"):
            headers = dict(request.headers)
            for header_name in self.sensitive_headers:
                if header_name in headers:
                    headers[header_name] = "[REDACTED]"
            request.state.sanitized_headers = headers
        
        # Sanitize query parameters
        query_params = dict(request.query_params)
        for param_name in query_params:
            if any(sensitive in param_name.lower() for sensitive in self.sensitive_params):
                query_params[param_name] = "[REDACTED]"
        request.state.sanitized_query_params = query_params


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with additional security checks."""
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.allowed_origins = kwargs.get("allowed_origins", [])
        self.allow_credentials = kwargs.get("allow_credentials", False)
        self.allowed_methods = kwargs.get("allowed_methods", ["GET", "POST", "PUT", "DELETE"])
        self.allowed_headers = kwargs.get("allowed_headers", ["*"])
        self.max_age = kwargs.get("max_age", 86400)  # 24 hours
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS for the request."""
        
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, origin)
            return response
        
        # Process normal request
        response = await call_next(request)
        self._add_cors_headers(response, origin)
        
        return response
    
    def _add_cors_headers(self, response: Response, origin: str = None) -> None:
        """Add CORS headers to response."""
        
        # Check if origin is allowed
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif not self.allowed_origins or "*" in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        # Add other CORS headers
        if self.allow_credentials and origin:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
        
        if self.allowed_headers:
            if "*" in self.allowed_headers:
                response.headers["Access-Control-Allow-Headers"] = "*"
            else:
                response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
        
        response.headers["Access-Control-Max-Age"] = str(self.max_age)
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if the origin is allowed."""
        if not self.allowed_origins:
            return False
        
        for allowed_origin in self.allowed_origins:
            if allowed_origin == "*":
                return True
            if allowed_origin == origin:
                return True
            # Support wildcard subdomains
            if allowed_origin.startswith("*."):
                domain = allowed_origin[2:]
                if origin.endswith(f".{domain}") or origin == domain:
                    return True
        
        return False


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware (basic implementation)."""
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.requests_per_minute = kwargs.get("requests_per_minute", 60)
        self.burst_size = kwargs.get("burst_size", 100)
        self.client_requests = {}  # In-memory store (use Redis in production)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit and process request."""
        
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if self._is_rate_limited(client_id):
            response = Response(
                content='{"error": {"message": "Rate limit exceeded", "code": "RATE_001"}}',
                status_code=429,
                media_type="application/json"
            )
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["Retry-After"] = "60"
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self._get_remaining_requests(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user ID from auth
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        return f"ip:{request.client.host}"
    
    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""
        import time
        current_time = time.time()
        
        # Clean up old entries
        self._cleanup_old_entries(current_time)
        
        # Get or create client entry
        if client_id not in self.client_requests:
            self.client_requests[client_id] = []
        
        client_entries = self.client_requests[client_id]
        
        # Remove entries older than 1 minute
        one_minute_ago = current_time - 60
        self.client_requests[client_id] = [
            entry for entry in client_entries if entry > one_minute_ago
        ]
        
        # Check if rate limit exceeded
        if len(self.client_requests[client_id]) >= self.requests_per_minute:
            return True
        
        # Add current request
        self.client_requests[client_id].append(current_time)
        return False
    
    def _get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for client."""
        if client_id not in self.client_requests:
            return self.requests_per_minute
        
        return max(0, self.requests_per_minute - len(self.client_requests[client_id]))
    
    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old rate limit entries."""
        one_hour_ago = current_time - 3600
        
        # Remove clients with no recent requests
        clients_to_remove = []
        for client_id, entries in self.client_requests.items():
            if not entries or max(entries) < one_hour_ago:
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self.client_requests[client_id]


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size."""
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check request size and process."""
        
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return Response(
                content='{"error": {"message": "Request entity too large", "code": "REQ_001"}}',
                status_code=413,
                media_type="application/json"
            )
        
        return await call_next(request)


def setup_cors(app):
    """Setup CORS middleware with configuration from settings."""
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allowed_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            allowed_headers=["*"],
        )
