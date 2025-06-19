"""
Unit tests for Unit of Work pattern implementation.

Tests the core functionality of the Unit of Work pattern including
transaction management, repository integration, and error handling.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.core.unit_of_work import (
    SQLAlchemyUnitOfWork,
    AIUnitOfWork,
    AbstractUnitOfWork,
    AbstractRepository,
    get_unit_of_work,
    get_ai_unit_of_work,
    TransactionError,
    safe_execute,
    with_unit_of_work
)
from app.core.exceptions import DatabaseConnectionError


class TestAbstractUnitOfWork:
    """Test abstract Unit of Work interface."""
    
    def test_abstract_uow_cannot_be_instantiated(self):
        """Test that abstract UoW cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AbstractUnitOfWork()


class TestSQLAlchemyUnitOfWork:
    """Test SQLAlchemy Unit of Work implementation."""
    
    @pytest.fixture
    async def mock_session(self):
        """Create mock async session."""
        session = AsyncMock(spec=AsyncSession)
        session.begin = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        session.flush = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_session_factory(self, mock_session):
        """Create mock session factory."""
        factory = AsyncMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=None)
        return factory
    
    async def test_uow_initialization(self, mock_session_factory):
        """Test UoW initialization."""
        uow = SQLAlchemyUnitOfWork(session_factory=mock_session_factory)
        
        async with uow:
            assert uow.session is not None
            assert not uow.committed
            assert not uow.rolled_back
    
    async def test_uow_commit(self, mock_session_factory, mock_session):
        """Test UoW commit operation."""
        uow = SQLAlchemyUnitOfWork(session_factory=mock_session_factory)
        
        async with uow:
            await uow.commit()
            
        mock_session.commit.assert_called_once()
        assert uow.committed
        assert not uow.rolled_back
    
    async def test_uow_rollback(self, mock_session_factory, mock_session):
        """Test UoW rollback operation."""
        uow = SQLAlchemyUnitOfWork(session_factory=mock_session_factory)
        
        async with uow:
            await uow.rollback()
            
        mock_session.rollback.assert_called_once()
        assert not uow.committed
        assert uow.rolled_back
    
    async def test_uow_auto_commit_on_success(self, mock_session_factory, mock_session):
        """Test UoW automatically commits on successful context exit."""
        uow = SQLAlchemyUnitOfWork(session_factory=mock_session_factory)
        
        async with uow:
            pass  # No exceptions
            
        mock_session.commit.assert_called_once()
    
    async def test_uow_auto_rollback_on_exception(self, mock_session_factory, mock_session):
        """Test UoW automatically rolls back on exception."""
        uow = SQLAlchemyUnitOfWork(session_factory=mock_session_factory)
        
        with pytest.raises(ValueError):
            async with uow:
                raise ValueError("Test exception")
                
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
    
    async def test_uow_flush(self, mock_session_factory, mock_session):
        """Test UoW flush operation."""
        uow = SQLAlchemyUnitOfWork(session_factory=mock_session_factory)
        
        async with uow:
            await uow.flush()
            
        mock_session.flush.assert_called_once()
    
    async def test_uow_refresh_entity(self, mock_session_factory, mock_session):
        """Test UoW entity refresh operation."""
        uow = SQLAlchemyUnitOfWork(session_factory=mock_session_factory)
        entity = Mock()
        
        async with uow:
            await uow.refresh(entity)
            
        mock_session.refresh.assert_called_once_with(entity)
    
    async def test_uow_execute_raw_query(self, mock_session_factory, mock_session):
        """Test UoW raw query execution."""
        uow = SQLAlchemyUnitOfWork(session_factory=mock_session_factory)
        mock_result = Mock()
        mock_session.execute.return_value = mock_result
        
        async with uow:
            result = await uow.execute_raw("SELECT 1", {"param": "value"})
            
        assert result == mock_result
        mock_session.execute.assert_called_once()
    
    async def test_uow_execute_scalar_query(self, mock_session_factory, mock_session):
        """Test UoW scalar query execution."""
        uow = SQLAlchemyUnitOfWork(session_factory=mock_session_factory)
        mock_result = Mock()
        mock_result.scalar.return_value = "scalar_value"
        mock_session.execute.return_value = mock_result
        
        async with uow:
            result = await uow.execute_scalar("SELECT COUNT(*)")
            
        assert result == "scalar_value"
    
    async def test_uow_add_repository(self, mock_session_factory, mock_session):
        """Test adding repositories to UoW."""
        uow = SQLAlchemyUnitOfWork(session_factory=mock_session_factory)
        
        class MockRepository:
            def __init__(self, session):
                self.session = session
        
        async with uow:
            repo = uow.add_repository("test_repo", MockRepository)
            
        assert hasattr(uow, "test_repo")
        assert uow.test_repo == repo
        assert repo.session == mock_session
    
    async def test_uow_database_error_handling(self, mock_session_factory, mock_session):
        """Test UoW handles database errors properly."""
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        uow = SQLAlchemyUnitOfWork(session_factory=mock_session_factory)
        
        with pytest.raises(DatabaseConnectionError):
            async with uow:
                pass
    
    async def test_uow_connection_error(self):
        """Test UoW handles connection errors."""
        def failing_factory():
            raise SQLAlchemyError("Connection failed")
        
        uow = SQLAlchemyUnitOfWork(session_factory=failing_factory)
        
        with pytest.raises(DatabaseConnectionError):
            async with uow:
                pass


class TestAIUnitOfWork:
    """Test AI-specific Unit of Work implementation."""
    
    @pytest.fixture
    async def mock_session(self):
        """Create mock async session."""
        session = AsyncMock(spec=AsyncSession)
        session.begin = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_session_factory(self, mock_session):
        """Create mock session factory."""
        factory = AsyncMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=None)
        return factory
    
    @patch('app.core.unit_of_work.agent_crud')
    @patch('app.core.unit_of_work.conversation_crud')
    @patch('app.core.unit_of_work.message_crud')
    @patch('app.core.unit_of_work.execution_crud')
    @patch('app.core.unit_of_work.user_crud')
    async def test_ai_uow_repositories_initialized(self, mock_user_crud, mock_execution_crud, 
                                                  mock_message_crud, mock_conversation_crud, 
                                                  mock_agent_crud, mock_session_factory):
        """Test that AI UoW initializes all required repositories."""
        uow = AIUnitOfWork(session_factory=mock_session_factory)
        
        async with uow:
            assert hasattr(uow, 'agents')
            assert hasattr(uow, 'conversations')
            assert hasattr(uow, 'messages')
            assert hasattr(uow, 'executions')
            assert hasattr(uow, 'users')
    
    @patch('app.core.unit_of_work.agent_crud')
    async def test_ai_uow_crud_wrapper_methods(self, mock_agent_crud, mock_session_factory, mock_session):
        """Test that AI UoW CRUD wrappers work correctly."""
        mock_agent_crud.get = AsyncMock(return_value="agent")
        mock_agent_crud.create = AsyncMock(return_value="new_agent")
        
        uow = AIUnitOfWork(session_factory=mock_session_factory)
        
        async with uow:
            # Test get method
            result = await uow.agents.get(id="test_id")
            assert result == "agent"
            mock_agent_crud.get.assert_called_once_with(mock_session, id="test_id")
            
            # Test create method
            obj_in = {"name": "test"}
            result = await uow.agents.create(obj_in=obj_in)
            assert result == "new_agent"
            mock_agent_crud.create.assert_called_once_with(mock_session, obj_in=obj_in)


class TestUnitOfWorkUtilities:
    """Test Unit of Work utility functions."""
    
    @patch('app.core.unit_of_work.get_db_session')
    async def test_get_unit_of_work(self, mock_get_db_session):
        """Test get_unit_of_work utility function."""
        mock_session = AsyncMock()
        mock_get_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        async with get_unit_of_work() as uow:
            assert isinstance(uow, SQLAlchemyUnitOfWork)
            assert uow.session == mock_session
    
    @patch('app.core.unit_of_work.get_db_session')
    async def test_get_ai_unit_of_work(self, mock_get_db_session):
        """Test get_ai_unit_of_work utility function."""
        mock_session = AsyncMock()
        mock_get_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        async with get_ai_unit_of_work() as uow:
            assert isinstance(uow, AIUnitOfWork)
            assert uow.session == mock_session
    
    async def test_safe_execute_success(self):
        """Test safe_execute with successful operation."""
        uow = Mock()
        uow.rollback = AsyncMock()
        
        async def success_operation():
            return "success"
        
        result = await safe_execute(uow, success_operation)
        assert result == "success"
        uow.rollback.assert_not_called()
    
    async def test_safe_execute_failure(self):
        """Test safe_execute with failing operation."""
        uow = Mock()
        uow.rollback = AsyncMock()
        
        async def failing_operation():
            raise ValueError("Operation failed")
        
        with pytest.raises(TransactionError) as exc_info:
            await safe_execute(uow, failing_operation)
        
        assert "Transaction failed" in str(exc_info.value)
        uow.rollback.assert_called_once()
    
    async def test_with_unit_of_work_decorator(self):
        """Test with_unit_of_work decorator."""
        @with_unit_of_work(SQLAlchemyUnitOfWork)
        async def decorated_function(data, uow):
            assert isinstance(uow, SQLAlchemyUnitOfWork)
            return f"processed_{data}"
        
        with patch('app.core.unit_of_work.get_db_session') as mock_get_db_session:
            mock_session = AsyncMock()
            mock_get_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await decorated_function("test_data")
            assert result == "processed_test_data"


class TestAbstractRepository:
    """Test abstract repository interface."""
    
    def test_abstract_repository_cannot_be_instantiated(self):
        """Test that abstract repository cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AbstractRepository(Mock())


class TestErrorHandling:
    """Test error handling in Unit of Work."""
    
    async def test_transaction_error_creation(self):
        """Test TransactionError creation."""
        original_error = ValueError("Original error")
        transaction_error = TransactionError("Transaction failed")
        
        assert str(transaction_error) == "Transaction failed"
        assert isinstance(transaction_error, Exception)
    
    async def test_database_connection_error_propagation(self):
        """Test that database connection errors are properly propagated."""
        def failing_session_factory():
            raise SQLAlchemyError("Connection failed")
        
        uow = SQLAlchemyUnitOfWork(session_factory=failing_session_factory)
        
        with pytest.raises(DatabaseConnectionError):
            async with uow:
                pass


@pytest.mark.integration
class TestUnitOfWorkIntegration:
    """Integration tests for Unit of Work pattern."""
    
    async def test_nested_operations(self):
        """Test that nested operations work correctly within UoW."""
        with patch('app.core.unit_of_work.get_db_session') as mock_get_db_session:
            mock_session = AsyncMock()
            mock_session.begin = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_get_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            async with get_unit_of_work() as uow:
                # Perform multiple operations
                await uow.execute_raw("INSERT INTO test_table VALUES (1)")
                await uow.flush()
                await uow.execute_raw("UPDATE test_table SET value = 2")
                
            # Should commit once at the end
            mock_session.commit.assert_called_once()
    
    async def test_rollback_on_nested_failure(self):
        """Test that nested failures trigger rollback."""
        with patch('app.core.unit_of_work.get_db_session') as mock_get_db_session:
            mock_session = AsyncMock()
            mock_session.begin = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_get_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with pytest.raises(ValueError):
                async with get_unit_of_work() as uow:
                    await uow.execute_raw("INSERT INTO test_table VALUES (1)")
                    await uow.flush()
                    raise ValueError("Simulated failure")
                    
            # Should rollback, not commit
            mock_session.rollback.assert_called_once()
            mock_session.commit.assert_not_called()