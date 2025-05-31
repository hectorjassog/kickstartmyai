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
from app.crud import user_crud


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


# Optional Authentication Dependencies
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
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
    """Get pagination parameters."""
    return PaginationParams(skip, limit)


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
        self.sort_order = sort_order.lower()
        self.filters = filters or {}
    
    def get_sort_order(self) -> str:
        """Get validated sort order."""
        return "asc" if self.sort_order in ["asc", "ascending"] else "desc"


def get_search_params(
    q: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "asc"
) -> SearchParams:
    """Get search parameters."""
    return SearchParams(q, sort_by, sort_order)


# Feature Flag Dependencies
def require_feature(feature_name: str):
    """Dependency to require a feature flag to be enabled."""
    def feature_dependency():
        if not settings.FEATURE_FLAGS.get(feature_name, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_name}' is not enabled"
            )
    return feature_dependency


# Environment Dependencies
def require_development():
    """Dependency to require development environment."""
    if not settings.is_development():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development environment"
        )


def require_not_production():
    """Dependency to require non-production environment."""
    if settings.is_production():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is not available in production environment"
        )


# Permission Dependencies
class PermissionChecker:
    """Check user permissions."""
    
    def __init__(self, permission: str):
        self.permission = permission
    
    async def __call__(self, current_user: User = Depends(get_current_user)):
        """Check if user has the required permission."""
        # For now, superusers have all permissions
        if current_user.is_superuser:
            return current_user
        
        # TODO: Implement proper permission system
        # This would check user roles and permissions from database
        raise AuthorizationError(f"Permission '{self.permission}' required")


def require_permission(permission: str):
    """Create a permission dependency."""
    return PermissionChecker(permission)


# Resource Owner Dependencies
class ResourceOwnerChecker:
    """Check if user owns a resource."""
    
    def __init__(self, resource_type: str):
        self.resource_type = resource_type
    
    async def __call__(
        self,
        resource_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Check if user owns the resource or is superuser."""
        if current_user.is_superuser:
            return current_user
        
        # Check resource ownership based on type
        if self.resource_type == "conversation":
            from app.crud import conversation_crud
            resource = await conversation_crud.get(db, id=resource_id)
            if not resource or resource.user_id != current_user.id:
                raise AuthorizationError("Not authorized to access this conversation")
        elif self.resource_type == "agent":
            from app.crud import agent_crud
            resource = await agent_crud.get(db, id=resource_id)
            if not resource or resource.user_id != current_user.id:
                raise AuthorizationError("Not authorized to access this agent")
        else:
            raise AuthorizationError("Unknown resource type")
        
        return current_user


def require_resource_owner(resource_type: str):
    """Create a resource owner dependency."""
    return ResourceOwnerChecker(resource_type)


# Cache Dependencies
class CacheManager:
    """Cache management dependency."""
    
    def __init__(self, ttl: int = None):
        self.ttl = ttl or settings.CACHE_DEFAULT_TTL
    
    async def get(self, key: str, redis: Redis = Depends(get_redis)) -> Optional[str]:
        """Get value from cache."""
        if not settings.CACHE_ENABLED:
            return None
        
        try:
            cache_key = f"{settings.CACHE_PREFIX}:{key}"
            return await redis.get(cache_key)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        redis: Redis = Depends(get_redis)
    ):
        """Set value in cache."""
        if not settings.CACHE_ENABLED:
            return
        
        try:
            cache_key = f"{settings.CACHE_PREFIX}:{key}"
            await redis.setex(cache_key, self.ttl, value)
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    async def delete(self, key: str, redis: Redis = Depends(get_redis)):
        """Delete value from cache."""
        if not settings.CACHE_ENABLED:
            return
        
        try:
            cache_key = f"{settings.CACHE_PREFIX}:{key}"
            await redis.delete(cache_key)
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")


def get_cache_manager(ttl: int = None) -> CacheManager:
    """Get cache manager dependency."""
    return CacheManager(ttl)


# Health Check Dependencies
async def check_database_health(db: AsyncSession = Depends(get_db)):
    """Check database health."""
    try:
        await db.execute("SELECT 1")
        return {"database": "healthy"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"database": "unhealthy", "error": str(e)}


async def check_redis_health(redis: Redis = Depends(get_redis)):
    """Check Redis health."""
    try:
        await redis.ping()
        return {"redis": "healthy"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"redis": "unhealthy", "error": str(e)}


# Request Context Dependencies
class RequestContext:
    """Request context information."""
    
    def __init__(self, request: Request):
        self.request = request
        self.client_ip = request.client.host
        self.user_agent = request.headers.get("user-agent")
        self.request_id = request.headers.get("x-request-id")
        self.forwarded_for = request.headers.get("x-forwarded-for")
        self.real_ip = self.forwarded_for or self.client_ip
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "client_ip": self.client_ip,
            "real_ip": self.real_ip,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
        }


def get_request_context(request: Request) -> RequestContext:
    """Get request context dependency."""
    return RequestContext(request)


# AI Service Dependencies
class AIServiceChecker:
    """Check AI service availability."""
    
    def __init__(self, provider: str):
        self.provider = provider.lower()
    
    async def __call__(self):
        """Check if AI provider is configured."""
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
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown AI provider: {self.provider}"
            )


def require_ai_service(provider: str):
    """Create an AI service dependency."""
    return AIServiceChecker(provider)


# Authentication dependency
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user."""
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    user = get_user_by_id(db, user_id=int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user


def get_current_active_user(current_user = Depends(get_current_user)):
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user
