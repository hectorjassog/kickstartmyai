"""
Health Checks

This module provides health check endpoints and utilities for monitoring
the application's health and dependencies.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

# Conditional Redis import
{% if cookiecutter.include_redis == "y" %}
import redis.asyncio as redis
{% endif %}

from app.core.config import settings
from app.core.events import get_service
from app.db.base import async_engine{% if cookiecutter.include_redis == "y" %}, get_redis_client{% endif %}

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthStatus(str, Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class ComponentHealth(BaseModel):
    """Health status of a system component."""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    response_time: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    """Overall health check response."""
    status: HealthStatus
    timestamp: float
    version: str
    environment: str
    components: List[ComponentHealth]
    summary: Dict[str, int]


class HealthChecker:
    """Health checker for various system components."""
    
    def __init__(self):
        self.checks = {
            "database": self.check_database,
{% if cookiecutter.include_redis == "y" %}
            "redis": self.check_redis,
{% endif %}
            "ai_services": self.check_ai_services,
            "disk_space": self.check_disk_space,
            "memory": self.check_memory,
        }
    
    async def run_all_checks(self) -> HealthCheckResponse:
        """
        Run all health checks and return comprehensive status.
        
        Returns:
            Health check response with all component statuses
        """
        components = []
        summary = {"healthy": 0, "unhealthy": 0, "degraded": 0}
        
        # Run all checks concurrently
        tasks = []
        for name, check_func in self.checks.items():
            task = asyncio.create_task(self.run_check(name, check_func))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, ComponentHealth):
                components.append(result)
                summary[result.status.value] += 1
            else:
                # Handle exceptions
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed with exception: {result}",
                ))
                summary["unhealthy"] += 1
        
        # Determine overall status
        if summary["unhealthy"] > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif summary["degraded"] > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return HealthCheckResponse(
            status=overall_status,
            timestamp=time.time(),
            version=settings.VERSION,
            environment=settings.ENVIRONMENT,
            components=components,
            summary=summary,
        )
    
    async def run_check(self, name: str, check_func: callable) -> ComponentHealth:
        """
        Run a single health check with timeout and error handling.
        
        Args:
            name: Check name
            check_func: Check function
            
        Returns:
            Component health status
        """
        start_time = time.time()
        
        try:
            # Run check with timeout
            result = await asyncio.wait_for(check_func(), timeout=10.0)
            response_time = time.time() - start_time
            
            if isinstance(result, ComponentHealth):
                result.response_time = response_time
                return result
            else:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    response_time=response_time,
                )
        
        except asyncio.TimeoutError:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message="Health check timed out",
                response_time=time.time() - start_time,
            )
        
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time=time.time() - start_time,
            )
    
    async def check_database(self) -> ComponentHealth:
        """Check database connectivity and performance."""
        try:
            # Test connection and basic query
            async with async_engine.connect() as conn:
                start_time = time.time()
                await conn.execute("SELECT 1")
                query_time = time.time() - start_time
            
            # Check connection pool status
            pool = async_engine.pool
            pool_status = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }
            
            # Determine status based on query time and pool utilization
            if query_time > 1.0:  # Slow query
                status = HealthStatus.DEGRADED
                message = f"Database responding slowly ({query_time:.2f}s)"
            elif pool_status["checked_out"] / pool.size() > 0.8:  # High pool utilization
                status = HealthStatus.DEGRADED
                message = "Database connection pool utilization high"
            else:
                status = HealthStatus.HEALTHY
                message = "Database is healthy"
            
            return ComponentHealth(
                name="database",
                status=status,
                message=message,
                details={
                    "query_time": query_time,
                    "pool_status": pool_status,
                }
            )
        
        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
            )
    
    {% if cookiecutter.include_redis == "y" %}
    async def check_redis(self) -> ComponentHealth:
        """Check Redis connectivity and performance."""
        try:
            if not settings.REDIS_URL:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis not configured (optional)",
                )
            
            # Get Redis client
            redis_client = get_service("redis") or await get_redis_client()
            if not redis_client:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.UNHEALTHY,
                    message="Redis client not available",
                )
            
            # Test basic operations
            start_time = time.time()
            await redis_client.ping()
            ping_time = time.time() - start_time
            
            # Test set/get operation
            test_key = "health_check_test"
            await redis_client.set(test_key, "test_value", ex=30)
            value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            if value != "test_value":
                raise Exception("Redis set/get test failed")
            
            # Get Redis info
            info = await redis_client.info()
            memory_usage = info.get("used_memory_human", "unknown")
            connected_clients = info.get("connected_clients", 0)
            
            # Determine status
            if ping_time > 0.1:  # Slow response
                status = HealthStatus.DEGRADED
                message = f"Redis responding slowly ({ping_time:.3f}s)"
            elif connected_clients > 100:  # High client count
                status = HealthStatus.DEGRADED
                message = "Redis has high client connection count"
            else:
                status = HealthStatus.HEALTHY
                message = "Redis is healthy"
            
            return ComponentHealth(
                name="redis",
                status=status,
                message=message,
                details={
                    "ping_time": ping_time,
                    "memory_usage": memory_usage,
                    "connected_clients": connected_clients,
                }
            )
        
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis check failed: {str(e)}",
            )
    {% endif %}
    
    async def check_ai_services(self) -> ComponentHealth:
        """Check AI service configurations and availability."""
        try:
            providers = []
            issues = []
            
            # Check OpenAI configuration
            if settings.OPENAI_API_KEY:
                if len(settings.OPENAI_API_KEY) < 20:
                    issues.append("OpenAI API key appears invalid")
                else:
                    providers.append("OpenAI")
            
            # Check Anthropic configuration
            if settings.ANTHROPIC_API_KEY:
                if len(settings.ANTHROPIC_API_KEY) < 20:
                    issues.append("Anthropic API key appears invalid")
                else:
                    providers.append("Anthropic")
            
            # Check Gemini configuration
            if settings.GEMINI_API_KEY:
                if len(settings.GEMINI_API_KEY) < 20:
                    issues.append("Gemini API key appears invalid")
                else:
                    providers.append("Gemini")
            
            # Determine status
            if not providers:
                status = HealthStatus.UNHEALTHY
                message = "No AI providers configured"
            elif issues:
                status = HealthStatus.DEGRADED
                message = f"AI service issues: {', '.join(issues)}"
            else:
                status = HealthStatus.HEALTHY
                message = f"AI providers available: {', '.join(providers)}"
            
            return ComponentHealth(
                name="ai_services",
                status=status,
                message=message,
                details={
                    "providers": providers,
                    "issues": issues,
                }
            )
        
        except Exception as e:
            return ComponentHealth(
                name="ai_services",
                status=HealthStatus.UNHEALTHY,
                message=f"AI services check failed: {str(e)}",
            )
    
    async def check_disk_space(self) -> ComponentHealth:
        """Check available disk space."""
        try:
            import shutil
            
            # Check disk usage
            total, used, free = shutil.disk_usage("/")
            
            # Convert to GB
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            usage_percent = (used / total) * 100
            
            # Determine status
            if usage_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Disk space critically low ({usage_percent:.1f}% used)"
            elif usage_percent > 85:
                status = HealthStatus.DEGRADED
                message = f"Disk space running low ({usage_percent:.1f}% used)"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space adequate ({usage_percent:.1f}% used)"
            
            return ComponentHealth(
                name="disk_space",
                status=status,
                message=message,
                details={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "usage_percent": round(usage_percent, 1),
                }
            )
        
        except Exception as e:
            return ComponentHealth(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk space check failed: {str(e)}",
            )
    
    async def check_memory(self) -> ComponentHealth:
        """Check memory usage."""
        try:
            import psutil
            
            # Get memory info
            memory = psutil.virtual_memory()
            
            # Convert to GB
            total_gb = memory.total / (1024**3)
            available_gb = memory.available / (1024**3)
            used_gb = (memory.total - memory.available) / (1024**3)
            usage_percent = memory.percent
            
            # Determine status
            if usage_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Memory usage critically high ({usage_percent:.1f}%)"
            elif usage_percent > 85:
                status = HealthStatus.DEGRADED
                message = f"Memory usage high ({usage_percent:.1f}%)"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal ({usage_percent:.1f}%)"
            
            return ComponentHealth(
                name="memory",
                status=status,
                message=message,
                details={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "available_gb": round(available_gb, 2),
                    "usage_percent": round(usage_percent, 1),
                }
            )
        
        except ImportError:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.DEGRADED,
                message="psutil not available for memory monitoring",
            )
        except Exception as e:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check failed: {str(e)}",
            )


# Global health checker instance
health_checker = HealthChecker()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Returns:
        Detailed health status of all system components
    """
    return await health_checker.run_all_checks()


@router.get("/health/live")
async def liveness_check():
    """
    Simple liveness check for load balancers.
    
    Returns:
        Basic status indicating the application is running
    """
    return {"status": "ok", "timestamp": time.time()}


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes deployments.
    
    Returns:
        Status indicating if the application is ready to serve traffic
    """
    # Check critical components only
    try:
        # Check database
        async with async_engine.connect() as conn:
            await conn.execute("SELECT 1")
        
        return {"status": "ready", "timestamp": time.time()}
    
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@router.get("/health/startup")
async def startup_check():
    """
    Startup check for Kubernetes deployments.
    
    Returns:
        Status indicating if the application has started successfully
    """
    try:
        # Minimal check to ensure the application is functional
        return {"status": "started", "timestamp": time.time()}
    
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not started"
        )
    # Add more comprehensive checks here
    return {"status": "ready"}


async def liveness_check():
    """Liveness check for Kubernetes."""
    return {"status": "alive"}
