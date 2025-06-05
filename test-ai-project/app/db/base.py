"""Database configuration and session management."""

import re
import uuid
import logging
from typing import AsyncGenerator, Any, ClassVar
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Session
from sqlalchemy import event, create_engine, Column, DateTime, MetaData, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings


logger = logging.getLogger(__name__)

# Explicitly create a MetaData instance
metadata = MetaData()

@as_declarative(metadata=metadata)
class Base:
    """
    Base class for all database models with UUID primary keys and UTC timestamps.
    """
    id: ClassVar[Any]  # Use ClassVar to indicate this is not a mapped column
    __name__: str
    __allow_unmapped__ = True  # Allow legacy Column annotations
    
    # Generate __tablename__ automatically from class name
    @declared_attr
    def __tablename__(cls) -> str:
        # Convert CamelCase to snake_case
        name = cls.__name__
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    # Primary key column with UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # UTC Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

# Async engine for modern async operations
database_url = settings.get_database_url()

# Handle SQLite URLs for async operations
if database_url.startswith("sqlite"):
    # For SQLite, use aiosqlite for async support
    async_database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")
    sync_database_url = database_url
    
    # SQLite doesn't support connection pooling
    async_engine = create_async_engine(
        async_database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )
    
    # Sync engine for migration and initial setup
    sync_engine = create_engine(
        sync_database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )
else:
    # For PostgreSQL, use asyncpg for async and psycopg2 for sync
    if "postgresql+asyncpg://" not in database_url:
        async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    else:
        async_database_url = database_url
    sync_database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    async_engine = create_async_engine(
        async_database_url,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=3600,  # Recycle connections every hour
    )
    
    # Sync engine for migration and initial setup
    sync_engine = create_engine(
        sync_database_url,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

# Sync session for migrations
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting database session."""
    async with get_db_session() as session:
        yield session


def get_sync_db() -> Session:
    """Get a synchronous database session (for migrations, etc.)."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


async def init_db() -> None:
    """Initialize the database."""
    try:
        # Import all models to ensure they are registered with Base
        from app.models import (
            User, Conversation, Message, Agent, Execution
        )
        
        async with async_engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_db() -> None:
    """Close database connections."""
    try:
        await async_engine.dispose()
        sync_engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
        raise


async def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        async with async_engine.begin() as conn:
            # Use text() wrapper for raw SQL
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def create_tables() -> None:
    """Create all database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """Drop all database tables (use with caution!)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Event listeners for connection pooling
@event.listens_for(async_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance (if using SQLite)."""
    if "sqlite" in settings.get_database_url():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=1000")
        cursor.execute("PRAGMA temp_store=memory")
        cursor.close()


@event.listens_for(async_engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log database connection checkout."""
    if settings.DEBUG:
        logger.debug("Database connection checked out")


@event.listens_for(async_engine.sync_engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log database connection checkin."""
    if settings.DEBUG:
        logger.debug("Database connection checked in")


class DatabaseManager:
    """Database manager for application lifecycle."""
    
    def __init__(self):
        self.engine = async_engine
        self.session_factory = AsyncSessionLocal
        self._initialized = False
    
    async def initialize(self):
        """Initialize database manager."""
        if self._initialized:
            return
        
        try:
            await init_db()
            self._initialized = True
            logger.info("Database manager initialized")
        except Exception as e:
            logger.error(f"Database manager initialization failed: {e}")
            raise
    
    async def close(self):
        """Close database manager."""
        if not self._initialized:
            return
        
        try:
            await close_db()
            self._initialized = False
            logger.info("Database manager closed")
        except Exception as e:
            logger.error(f"Database manager close failed: {e}")
            raise
    
    async def health_check(self) -> dict:
        """Perform database health check."""
        try:
            is_healthy = await check_db_connection()
            return {
                "database": "healthy" if is_healthy else "unhealthy",
                "initialized": self._initialized,
                "url": settings.get_database_url().split("@")[-1] if "@" in settings.get_database_url() else "unknown"
            }
        except Exception as e:
            return {
                "database": "unhealthy",
                "error": str(e),
                "initialized": self._initialized
            }
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions."""
        async with self.session_factory() as session:
            async with session.begin():
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise


# Global database manager instance
db_manager = DatabaseManager()


# Utility functions for common database operations
async def execute_query(query: str, params: dict = None):
    """Execute a raw SQL query."""
    async with get_db_session() as session:
        result = await session.execute(text(query), params or {})
        return result


async def execute_scalar(query: str, params: dict = None):
    """Execute a query and return a scalar result."""
    async with get_db_session() as session:
        result = await session.execute(text(query), params or {})
        return result.scalar()


async def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    database_url = settings.get_database_url()
    
    if database_url.startswith("sqlite"):
        # SQLite query
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name = :table_name;
        """
    else:
        # PostgreSQL query
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = :table_name
        );
        """
    
    try:
        result = await execute_scalar(query, {"table_name": table_name})
        if database_url.startswith("sqlite"):
            return result is not None
        else:
            return bool(result)
    except Exception:
        return False


async def get_table_count(table_name: str) -> int:
    """Get the number of rows in a table."""
    try:
        result = await execute_scalar(f"SELECT COUNT(*) FROM {table_name}")
        return int(result) if result is not None else 0
    except Exception:
        return 0


async def backup_database(backup_path: str = None):
    """Create a database backup (PostgreSQL specific)."""
    if "postgresql" not in settings.get_database_url():
        raise NotImplementedError("Backup only supported for PostgreSQL")
    
    # This would need to be implemented with pg_dump
    # For now, just log the request
    logger.info(f"Database backup requested to: {backup_path}")
    raise NotImplementedError("Database backup not implemented yet")


async def restore_database(backup_path: str):
    """Restore database from backup."""
    # Implementation would depend on database type and backup format
    logger.info(f"Database restore from {backup_path} - implementation needed")


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
