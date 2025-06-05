"""
Application Events

This module handles application startup and shutdown events,
including database initialization, service setup, and cleanup.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable

from app.core.config import settings
from app.db.base import sync_engine, async_engine, Base
from app.services import agent_service, conversation_service, tool_service
from sqlalchemy import text

logger = logging.getLogger(__name__)


class EventManager:
    """Manages application lifecycle events."""
    
    def __init__(self):
        self.startup_tasks: List[callable] = []
        self.shutdown_tasks: List[callable] = []
        self.background_tasks: List[asyncio.Task] = []
        self.services: Dict[str, Any] = {}
    
    def add_startup_task(self, task: callable) -> None:
        """Add a task to run during startup."""
        self.startup_tasks.append(task)
    
    def add_shutdown_task(self, task: callable) -> None:
        """Add a task to run during shutdown."""
        self.shutdown_tasks.append(task)
    
    async def startup(self) -> None:
        """Execute all startup tasks."""
        logger.info("Starting application...")
        
        for task in self.startup_tasks:
            try:
                await task()
                logger.info(f"Completed startup task: {task.__name__}")
            except Exception as e:
                logger.error(f"Failed startup task {task.__name__}: {e}")
                raise
        
        logger.info("Application started successfully")
    
    async def shutdown(self) -> None:
        """Execute all shutdown tasks."""
        logger.info("Shutting down application...")
        
        # Cancel background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Run shutdown tasks
        for task in self.shutdown_tasks:
            try:
                await task()
                logger.info(f"Completed shutdown task: {task.__name__}")
            except Exception as e:
                logger.error(f"Failed shutdown task {task.__name__}: {e}")
        
        logger.info("Application shutdown complete")


# Global event manager instance
event_manager = EventManager()


async def initialize_database() -> None:
    """Initialize database connections and create tables if needed."""
    try:
        # Skip database initialization in Docker testing without real DB
        if settings.ENVIRONMENT == "testing" and "localhost" in settings.get_database_url():
            logger.warning("Skipping database initialization in testing environment with localhost DB")
            return
            
        # Test async database connection
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        
        # Create tables if needed (in development)
        if settings.ENVIRONMENT == "development" and settings.CREATE_TABLES_ON_STARTUP:
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
            
    except Exception as e:
        # In testing environment, don't fail if database is not available
        if settings.ENVIRONMENT == "testing":
            logger.warning(f"Database not available in testing environment: {e}")
            return
        logger.error(f"Database initialization failed: {e}")
        raise


async def get_redis_client():
    """Get Redis client if configured."""
    try:
        if settings.REDIS_URL:
            import aioredis
            return await aioredis.from_url(settings.REDIS_URL)
        return None
    except ImportError:
        logger.warning("aioredis not installed, Redis functionality disabled")
        return None
    except Exception as e:
        logger.error(f"Failed to create Redis client: {e}")
        return None


async def initialize_redis() -> None:
    """Initialize Redis connection."""
    try:
        if settings.REDIS_URL:
            redis_client = await get_redis_client()
            if redis_client:
                await redis_client.ping()
                logger.info("Redis connection successful")
                event_manager.services["redis"] = redis_client
            else:
                logger.warning("Redis client not available")
        else:
            logger.info("Redis not configured, skipping initialization")
    except Exception as e:
        logger.error(f"Redis initialization failed: {e}")
        # Don't raise - Redis is optional for basic functionality


async def initialize_ai_services() -> None:
    """Initialize AI services and validate configurations."""
    try:
        # Validate AI provider configurations
        providers_configured = []
        
        if settings.OPENAI_API_KEY:
            providers_configured.append("OpenAI")
        
        if settings.ANTHROPIC_API_KEY:
            providers_configured.append("Anthropic")
        
        if settings.GEMINI_API_KEY:
            providers_configured.append("Gemini")
        
        if not providers_configured:
            logger.warning("No AI providers configured")
        else:
            logger.info(f"AI providers configured: {', '.join(providers_configured)}")
        
        # Initialize AI services
        # Note: Services are initialized lazily, so we just log here
        logger.info("AI services initialized")
        
    except Exception as e:
        logger.error(f"AI services initialization failed: {e}")
        raise


async def initialize_background_services() -> None:
    """Initialize background services and tasks."""
    try:
        # Initialize cleanup tasks
        if getattr(settings, 'ENABLE_CLEANUP_TASKS', False):
            cleanup_task = asyncio.create_task(run_cleanup_tasks())
            event_manager.background_tasks.append(cleanup_task)
            logger.info("Background cleanup tasks started")
        
        # Initialize monitoring tasks
        if getattr(settings, 'ENABLE_MONITORING', False):
            monitoring_task = asyncio.create_task(run_monitoring_tasks())
            event_manager.background_tasks.append(monitoring_task)
            logger.info("Background monitoring tasks started")
        
    except Exception as e:
        logger.error(f"Background services initialization failed: {e}")
        raise


async def run_cleanup_tasks() -> None:
    """Run periodic cleanup tasks."""
    while True:
        try:
            # Clean up old executions
            if hasattr(agent_service, 'cleanup_old_executions'):
                cleaned = await agent_service.cleanup_old_executions()
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} old executions")
            
            # Clean up old conversations
            if hasattr(conversation_service, 'cleanup_old_conversations'):
                cleaned = await conversation_service.cleanup_old_conversations()
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} old conversations")
            
            # Wait for next cleanup cycle
            await asyncio.sleep(getattr(settings, 'CLEANUP_INTERVAL', 3600))
            
        except asyncio.CancelledError:
            logger.info("Cleanup tasks cancelled")
            break
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying


async def run_monitoring_tasks() -> None:
    """Run periodic monitoring tasks."""
    while True:
        try:
            # Log system metrics
            logger.info("System monitoring check")
            
            # Check database health
            try:
                async with async_engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                logger.debug("Database health check passed")
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
            
            # Check Redis health
            if "redis" in event_manager.services:
                try:
                    await event_manager.services["redis"].ping()
                    logger.debug("Redis health check passed")
                except Exception as e:
                    logger.error(f"Redis health check failed: {e}")
            
            # Wait for next monitoring cycle
            await asyncio.sleep(settings.MONITORING_INTERVAL)
            
        except asyncio.CancelledError:
            logger.info("Monitoring tasks cancelled")
            break
        except Exception as e:
            logger.error(f"Monitoring task error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying


async def cleanup_database() -> None:
    """Clean up database connections."""
    try:
        await async_engine.dispose()
        sync_engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")


async def cleanup_redis() -> None:
    """Clean up Redis connections."""
    try:
        if "redis" in event_manager.services:
            await event_manager.services["redis"].close()
            logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Redis cleanup failed: {e}")


async def cleanup_ai_services() -> None:
    """Clean up AI services."""
    try:
        # AI services cleanup (if needed)
        logger.info("AI services cleaned up")
    except Exception as e:
        logger.error(f"AI services cleanup failed: {e}")


# Register startup tasks
event_manager.add_startup_task(initialize_database)
event_manager.add_startup_task(initialize_redis)
event_manager.add_startup_task(initialize_ai_services)
event_manager.add_startup_task(initialize_background_services)

# Register shutdown tasks
event_manager.add_shutdown_task(cleanup_ai_services)
event_manager.add_shutdown_task(cleanup_redis)
event_manager.add_shutdown_task(cleanup_database)


async def startup_handler() -> None:
    """Application startup handler."""
    await event_manager.startup()


async def shutdown_handler() -> None:
    """Application shutdown handler."""
    await event_manager.shutdown()


def get_service(name: str) -> Optional[Any]:
    """
    Get a service by name.
    
    Args:
        name: Service name
        
    Returns:
        Service instance or None
    """
    return event_manager.services.get(name)


def register_service(name: str, service: Any) -> None:
    """
    Register a service.
    
    Args:
        name: Service name
        service: Service instance
    """
    event_manager.services[name] = service
