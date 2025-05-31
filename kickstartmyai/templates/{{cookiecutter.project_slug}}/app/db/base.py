"""Database configuration and session management."""

import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy import event, create_engine
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings


logger = logging.getLogger(__name__)

# Create the declarative base
Base = declarative_base()

# Async engine for modern async operations
async_engine = create_async_engine(
    settings.get_database_url(),
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections every hour
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

# Sync engine for migration and initial setup
sync_engine = create_engine(
    settings.get_database_url().replace("postgresql://", "postgresql://"),
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
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
            await conn.execute("SELECT 1")
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
        result = await session.execute(query, params or {})
        return result


async def execute_scalar(query: str, params: dict = None):
    """Execute a query and return a scalar result."""
    async with get_db_session() as session:
        result = await session.execute(query, params or {})
        return result.scalar()


async def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = :table_name
    );
    """
    try:
        result = await execute_scalar(query, {"table_name": table_name})
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
    """Restore database from backup (PostgreSQL specific)."""
    if "postgresql" not in settings.get_database_url():
        raise NotImplementedError("Restore only supported for PostgreSQL")
    
    # This would need to be implemented with pg_restore
    # For now, just log the request
    logger.info(f"Database restore requested from: {backup_path}")
    raise NotImplementedError("Database restore not implemented yet")
