"""
Unit of Work pattern implementation for managing database transactions.

Provides atomic operations across multiple repositories and services,
particularly useful for AI operations that involve multiple database updates.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar, Generic, AsyncContextManager
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.db.base import get_db_session
from app.core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AbstractUnitOfWork(ABC):
    """
    Abstract Unit of Work interface.
    
    Defines the contract for unit of work implementations across different
    database backends or storage systems.
    """
    
    def __init__(self):
        self._committed = False
        self._rolled_back = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with transaction handling."""
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
    
    @abstractmethod
    async def commit(self):
        """Commit the transaction."""
        pass
    
    @abstractmethod
    async def rollback(self):
        """Rollback the transaction."""
        pass
    
    @property
    def committed(self) -> bool:
        """Check if transaction has been committed."""
        return self._committed
    
    @property
    def rolled_back(self) -> bool:
        """Check if transaction has been rolled back."""
        return self._rolled_back


class AbstractRepository(ABC, Generic[T]):
    """
    Abstract repository interface for the Unit of Work pattern.
    
    Provides a contract for repository implementations that work with
    the Unit of Work pattern.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @abstractmethod
    async def get(self, id: Any) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    async def delete(self, entity: T) -> bool:
        """Delete an entity."""
        pass
    
    @abstractmethod
    async def list(self, **filters) -> list[T]:
        """List entities with optional filters."""
        pass


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """
    SQLAlchemy-specific Unit of Work implementation.
    
    Manages database transactions for SQLAlchemy async sessions,
    providing atomic operations across multiple repositories.
    """
    
    def __init__(self, session_factory=None):
        super().__init__()
        self.session_factory = session_factory or get_db_session
        self.session: Optional[AsyncSession] = None
        self._repositories: Dict[str, Any] = {}
    
    async def __aenter__(self):
        """Initialize database session and begin transaction."""
        try:
            # Create session using the context manager
            self._session_cm = self.session_factory()
            self.session = await self._session_cm.__aenter__()
            
            # Begin transaction explicitly
            await self.session.begin()
            
            # Initialize repositories
            await self._init_repositories()
            
            return self
        except Exception as e:
            logger.error(f"Failed to initialize UnitOfWork: {e}")
            raise DatabaseConnectionError(f"Failed to initialize database transaction: {e}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Handle transaction cleanup and session closure."""
        try:
            # Handle transaction first
            if exc_type is not None:
                await self.rollback()
            elif not self._committed and not self._rolled_back:
                await self.commit()
            
            # Close the session context manager
            if hasattr(self, '_session_cm'):
                await self._session_cm.__aexit__(exc_type, exc_val, exc_tb)
                
        except Exception as e:
            logger.error(f"Error during UnitOfWork cleanup: {e}")
            # Re-raise the original exception if it exists, otherwise raise the cleanup error
            if exc_type is not None:
                return False
            raise
    
    async def commit(self):
        """Commit the database transaction."""
        if self._committed or self._rolled_back:
            return
        
        try:
            if self.session:
                await self.session.commit()
            self._committed = True
            logger.debug("Transaction committed successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to commit transaction: {e}")
            await self.rollback()
            raise DatabaseConnectionError(f"Failed to commit transaction: {e}")
    
    async def rollback(self):
        """Rollback the database transaction."""
        if self._rolled_back:
            return
        
        try:
            if self.session:
                await self.session.rollback()
            self._rolled_back = True
            logger.debug("Transaction rolled back successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to rollback transaction: {e}")
            raise DatabaseConnectionError(f"Failed to rollback transaction: {e}")
    
    async def flush(self):
        """Flush changes to the database without committing."""
        if self.session:
            try:
                await self.session.flush()
                logger.debug("Session flushed successfully")
            except SQLAlchemyError as e:
                logger.error(f"Failed to flush session: {e}")
                raise DatabaseConnectionError(f"Failed to flush session: {e}")
    
    async def refresh(self, entity):
        """Refresh an entity from the database."""
        if self.session:
            try:
                await self.session.refresh(entity)
                logger.debug(f"Entity {entity} refreshed successfully")
            except SQLAlchemyError as e:
                logger.error(f"Failed to refresh entity: {e}")
                raise DatabaseConnectionError(f"Failed to refresh entity: {e}")
    
    def add_repository(self, name: str, repository_class: Type, *args, **kwargs):
        """Add a repository to the unit of work."""
        if self.session:
            repository = repository_class(self.session, *args, **kwargs)
            self._repositories[name] = repository
            setattr(self, name, repository)
            return repository
        raise RuntimeError("Cannot add repository without active session")
    
    def get_repository(self, name: str):
        """Get a repository by name."""
        return self._repositories.get(name)
    
    async def _init_repositories(self):
        """Initialize repositories. Override in subclasses to add specific repositories."""
        pass
    
    async def execute_raw(self, query: str, params: Dict[str, Any] = None):
        """Execute a raw SQL query within the transaction."""
        if not self.session:
            raise RuntimeError("No active session")
        
        try:
            from sqlalchemy import text
            result = await self.session.execute(text(query), params or {})
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to execute raw query: {e}")
            raise DatabaseConnectionError(f"Failed to execute query: {e}")
    
    async def execute_scalar(self, query: str, params: Dict[str, Any] = None):
        """Execute a query and return scalar result within the transaction."""
        result = await self.execute_raw(query, params)
        return result.scalar()


class AIUnitOfWork(SQLAlchemyUnitOfWork):
    """
    AI-specific Unit of Work implementation.
    
    Pre-configured with repositories commonly used in AI operations,
    such as agents, conversations, messages, executions, and users.
    """
    
    async def _init_repositories(self):
        """Initialize AI-specific repositories."""
        from app.crud.agent import agent_crud
        from app.crud.conversation import conversation_crud
        from app.crud.message import message_crud
        from app.crud.execution import execution_crud
        from app.crud.user import user_crud
        
        # Add repositories with session injection
        self.agents = self._create_crud_wrapper(agent_crud)
        self.conversations = self._create_crud_wrapper(conversation_crud)
        self.messages = self._create_crud_wrapper(message_crud)
        self.executions = self._create_crud_wrapper(execution_crud)
        self.users = self._create_crud_wrapper(user_crud)
        
        logger.debug("AI repositories initialized")
    
    def _create_crud_wrapper(self, crud_instance):
        """Create a wrapper that injects the session into CRUD operations."""
        class CRUDWrapper:
            def __init__(self, crud, session):
                self.crud = crud
                self.session = session
            
            async def get(self, id: Any):
                return await self.crud.get(self.session, id=id)
            
            async def get_multi(self, *, skip: int = 0, limit: int = 100):
                return await self.crud.get_multi(self.session, skip=skip, limit=limit)
            
            async def create(self, *, obj_in):
                return await self.crud.create(self.session, obj_in=obj_in)
            
            async def update(self, *, db_obj, obj_in):
                return await self.crud.update(self.session, db_obj=db_obj, obj_in=obj_in)
            
            async def remove(self, *, id: Any):
                return await self.crud.remove(self.session, id=id)
            
            def __getattr__(self, name):
                """Delegate other method calls to the original CRUD instance."""
                method = getattr(self.crud, name)
                if callable(method):
                    # If it's a method that expects a session as first parameter
                    async def wrapper(*args, **kwargs):
                        return await method(self.session, *args, **kwargs)
                    return wrapper
                return method
        
        return CRUDWrapper(crud_instance, self.session)


# Utility functions for creating Unit of Work instances
@asynccontextmanager
async def get_unit_of_work() -> AsyncContextManager[SQLAlchemyUnitOfWork]:
    """Get a standard Unit of Work instance."""
    async with SQLAlchemyUnitOfWork() as uow:
        yield uow


@asynccontextmanager
async def get_ai_unit_of_work() -> AsyncContextManager[AIUnitOfWork]:
    """Get an AI-specific Unit of Work instance."""
    async with AIUnitOfWork() as uow:
        yield uow


# Dependency injection for FastAPI
async def get_uow_dependency() -> AsyncContextManager[SQLAlchemyUnitOfWork]:
    """FastAPI dependency for Unit of Work."""
    async with get_unit_of_work() as uow:
        yield uow


async def get_ai_uow_dependency() -> AsyncContextManager[AIUnitOfWork]:
    """FastAPI dependency for AI Unit of Work."""
    async with get_ai_unit_of_work() as uow:
        yield uow


# Decorator for automatic Unit of Work management
def with_unit_of_work(uow_type: Type[AbstractUnitOfWork] = SQLAlchemyUnitOfWork):
    """
    Decorator to automatically manage Unit of Work for service methods.
    
    Usage:
        @with_unit_of_work(AIUnitOfWork)
        async def some_service_method(data, uow: AIUnitOfWork):
            # Use uow.agents, uow.conversations, etc.
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with uow_type() as uow:
                # Inject uow as the last parameter
                return await func(*args, uow=uow, **kwargs)
        return wrapper
    return decorator


# Exception handling wrapper
class TransactionError(Exception):
    """Exception raised when transaction operations fail."""
    pass


async def safe_execute(uow: AbstractUnitOfWork, operation, *args, **kwargs):
    """
    Safely execute an operation within a Unit of Work with error handling.
    
    Args:
        uow: Unit of Work instance
        operation: Async function to execute
        *args, **kwargs: Arguments for the operation
    
    Returns:
        Result of the operation or raises TransactionError
    """
    try:
        result = await operation(*args, **kwargs)
        return result
    except Exception as e:
        logger.error(f"Operation failed, rolling back transaction: {e}")
        await uow.rollback()
        raise TransactionError(f"Transaction failed: {e}") from e