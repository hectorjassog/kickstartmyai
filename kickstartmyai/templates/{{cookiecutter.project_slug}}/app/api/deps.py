"""FastAPI dependencies for the application."""

import logging
from typing import AsyncGenerator, Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
import jwt
from jwt import PyJWTError

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidTokenError,
    TokenExpiredError,
    RateLimitExceededError,
    DatabaseConnectionError,
)
from app.db.base import get_db_session
from app.models import User
from app.crud.user import user_crud


logger = logging.getLogger(__name__)
security = HTTPBearer()


# Database Dependencies
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    try:
        async with get_db_session() as session:
            yield session
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise DatabaseConnectionError({"error": str(e)})


# Redis Dependencies
async def get_redis() -> AsyncGenerator[Redis, None]:
    """Get Redis connection dependency."""
    redis = None
    try:
        redis = Redis.from_url(settings.REDIS_URL)
        await redis.ping()
        yield redis
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service unavailable"
        )
    finally:
        if redis:
            await redis.close()


# Authentication Dependencies
def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except PyJWTError:
        raise InvalidTokenError()


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get and validate current user token."""
    if not credentials:
        raise AuthenticationError()
    
    return decode_token(credentials.credentials)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token_data: Dict[str, Any] = Depends(get_current_user_token)
) -> User:
    """Get current authenticated user."""
    user_id = token_data.get("sub")
    if not user_id:
        raise InvalidTokenError("Invalid token payload")
    
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise AuthenticationError("User not found")
    
    if not user.is_active:
        raise AuthenticationError("Inactive user")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise AuthenticationError("Inactive user")
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise AuthorizationError("Not enough permissions")
    return current_user


# Alias for compatibility with existing endpoints
async def get_current_admin_user(
    current_user: User = Depends(get_current_superuser)
) -> User:
    """Get current admin user (alias for superuser)."""
    return current_user


# Optional Authentication Dependencies
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None
    
    try:
        token_data = decode_token(credentials.credentials)
        user_id = token_data.get("sub")
        if not user_id:
            return None
        
        user = await user_crud.get(db, id=user_id)
        if not user or not user.is_active:
            return None
        
        return user
    except (AuthenticationError, InvalidTokenError, TokenExpiredError):
        return None


# Rate Limiting Dependencies
class RateLimiter:
    """Rate limiter dependency."""
    
    def __init__(self, requests_per_minute: int = None, burst_size: int = None):
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self.burst_size = burst_size or settings.RATE_LIMIT_BURST_SIZE
    
    async def __call__(
        self,
        request: Request,
        redis: Redis = Depends(get_redis)
    ):
        """Check rate limit for the request."""
        if not settings.RATE_LIMIT_ENABLED:
            return
        
        # Get client identifier (IP or user ID)
        client_id = request.client.host
        
        # Check if user is authenticated
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                token_data = decode_token(token)
                client_id = f"user:{token_data.get('sub', client_id)}"
            except (InvalidTokenError, TokenExpiredError):
                pass  # Use IP-based rate limiting
        
        # Rate limiting logic using Redis
        key = f"rate_limit:{client_id}"
        current = await redis.get(key)
        
        if current is None:
            await redis.setex(key, 60, 1)  # 1 minute window
        else:
            current_count = int(current)
            if current_count >= self.requests_per_minute:
                raise RateLimitExceededError(self.requests_per_minute, 60)
            await redis.incr(key)


# Default rate limiter
rate_limiter = RateLimiter()


# Pagination Dependencies
class PaginationParams:
    """Pagination parameters."""
    
    def __init__(self, skip: int = 0, limit: int = 100):
        self.skip = max(0, skip)
        self.limit = min(max(1, limit), 1000)  # Max 1000 items per page


def get_pagination_params(skip: int = 0, limit: int = 100) -> PaginationParams:
    """Get pagination parameters dependency."""
    return PaginationParams(skip=skip, limit=limit)


# Search Dependencies
class SearchParams:
    """Search parameters."""
    
    def __init__(
        self,
        q: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None
    ):
        self.query = q
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order else "asc"
        self.filters = filters or {}
    
    def get_sort_order(self) -> str:
        """Get validated sort order."""
        return "desc" if self.sort_order == "desc" else "asc"


def get_search_params(
    q: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "asc"
) -> SearchParams:
    """Get search parameters dependency."""
    return SearchParams(q=q, sort_by=sort_by, sort_order=sort_order)


# Feature Flag Dependencies
def require_feature(feature_name: str):
    """Require a feature flag to be enabled."""
    def feature_dependency():
        if not settings.FEATURE_FLAGS.get(feature_name, False):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature '{feature_name}' is not available"
            )
    return feature_dependency


def require_development():
    """Require development environment."""
    if settings.is_production():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This endpoint is only available in development"
        )


def require_not_production():
    """Require non-production environment."""
    if settings.is_production():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation is not allowed in production"
        )


# Permission Dependencies
class PermissionChecker:
    """Permission checker dependency."""
    
    def __init__(self, permission: str):
        self.permission = permission
    
    async def __call__(self, current_user: User = Depends(get_current_user)):
        """Check if user has required permission."""
        # TODO: Implement proper permission system
        # For now, just check if user is active
        if not current_user.is_active:
            raise AuthorizationError(f"Permission '{self.permission}' required")
        
        # Superusers have all permissions
        if current_user.is_superuser:
            return current_user
        
        # TODO: Check user permissions from database
        return current_user


def require_permission(permission: str):
    """Require a specific permission."""
    return PermissionChecker(permission)


# Resource Ownership Dependencies
class ResourceOwnerChecker:
    """Resource ownership checker dependency."""
    
    def __init__(self, resource_type: str):
        self.resource_type = resource_type
    
    async def __call__(
        self,
        resource_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Check if user owns the resource."""
        # Superusers can access all resources
        if current_user.is_superuser:
            return current_user
        
        # TODO: Implement resource ownership checks
        # This would typically involve checking if the resource
        # belongs to the current user
        
        # For now, just return the current user
        # In a real implementation, you would:
        # 1. Query the resource from the database
        # 2. Check if current_user.id == resource.user_id
        # 3. Raise AuthorizationError if not owned
        
        return current_user


def require_resource_owner(resource_type: str):
    """Require ownership of a resource."""
    return ResourceOwnerChecker(resource_type)


# Cache Dependencies
class CacheManager:
    """Cache manager dependency."""
    
    def __init__(self, ttl: int = None):
        self.ttl = ttl or settings.CACHE_DEFAULT_TTL
    
    async def get(self, key: str, redis: Redis = Depends(get_redis)) -> Optional[str]:
        """Get value from cache."""
        try:
            cache_key = f"{settings.CACHE_PREFIX}:{key}"
            return await redis.get(cache_key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        redis: Redis = Depends(get_redis)
    ):
        """Set value in cache."""
        try:
            cache_key = f"{settings.CACHE_PREFIX}:{key}"
            await redis.setex(cache_key, self.ttl, value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def delete(self, key: str, redis: Redis = Depends(get_redis)):
        """Delete value from cache."""
        try:
            cache_key = f"{settings.CACHE_PREFIX}:{key}"
            await redis.delete(cache_key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")


def get_cache_manager(ttl: int = None) -> CacheManager:
    """Get cache manager dependency."""
    return CacheManager(ttl=ttl)


# Health Check Dependencies
async def check_database_health(db: AsyncSession = Depends(get_db)):
    """Check database health."""
    try:
        await db.execute("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unhealthy: {str(e)}"
        )


async def check_redis_health(redis: Redis = Depends(get_redis)):
    """Check Redis health."""
    try:
        await redis.ping()
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis unhealthy: {str(e)}"
        )


# Request Context Dependencies
class RequestContext:
    """Request context dependency."""
    
    def __init__(self, request: Request):
        self.request = request
        self.client_ip = request.client.host
        self.user_agent = request.headers.get("user-agent")
        self.path = request.url.path
        self.method = request.method
        self.query_params = dict(request.query_params)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "path": self.path,
            "method": self.method,
            "query_params": self.query_params,
        }


def get_request_context(request: Request) -> RequestContext:
    """Get request context dependency."""
    return RequestContext(request)


# AI Service Dependencies
class AIServiceChecker:
    """AI service checker dependency."""
    
    def __init__(self, provider: str):
        self.provider = provider.lower()
    
    async def __call__(self):
        """Check if AI service is available."""
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="OpenAI service not configured"
                )
        elif self.provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Anthropic service not configured"
                )
        elif self.provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Gemini service not configured"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown AI provider: {self.provider}"
            )


def require_ai_service(provider: str):
    """Require an AI service to be available."""
    return AIServiceChecker(provider)
