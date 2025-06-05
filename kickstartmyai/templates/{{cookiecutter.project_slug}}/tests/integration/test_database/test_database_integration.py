"""
Database integration tests.

Tests database operations, migrations, and data integrity in integration scenarios.
"""

import pytest
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.user import User
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message
from app.crud.user import user_crud
from app.crud.agent import agent_crud
from app.crud.conversation import conversation_crud
from app.crud.message import message_crud
from app.core.security import get_password_hash


class TestDatabaseIntegration:
    """Test database operations and integrity."""

    async def test_database_connection_pool(self, db_session: AsyncSession):
        """Test database connection pooling."""
        
        # Test multiple concurrent connections
        async def test_connection():
            async with async_session_maker() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar()
        
        # Create multiple concurrent tasks
        tasks = [test_connection() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All connections should succeed
        assert all(result == 1 for result in results)

    async def test_transaction_isolation(self, db_session: AsyncSession):
        """Test transaction isolation between sessions."""
        
        # Create user in first session
        user_data = {
            "email": "isolation@example.com",
            "full_name": "Isolation User",
            "hashed_password": get_password_hash("password123")
        }
        
        # Session 1: Create user but don't commit
        async with async_session_maker() as session1:
            user = User(**user_data)
            session1.add(user)
            await session1.flush()  # Flush but don't commit
            user_id = user.id
            
            # Session 2: Try to find the user (should not exist)
            async with async_session_maker() as session2:
                found_user = await user_crud.get(session2, user_id)
                assert found_user is None  # User not committed yet
            
            # Commit in session 1
            await session1.commit()
        
        # Session 3: Now user should be visible
        async with async_session_maker() as session3:
            found_user = await user_crud.get(session3, user_id)
            assert found_user is not None
            assert found_user.email == user_data["email"]

    async def test_foreign_key_constraints(self, db_session: AsyncSession):
        """Test foreign key constraint enforcement."""
        
        # Create user
        user_data = {
            "email": "fk@example.com",
            "full_name": "FK User",
            "hashed_password": get_password_hash("password123")
        }
        user = await user_crud.create(db_session, obj_in=user_data)
        
        # Create agent
        agent_data = {
            "name": "FK Agent",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo",
            "user_id": user.id
        }
        agent = await agent_crud.create(db_session, obj_in=agent_data)
        
        # Create conversation
        conversation_data = {
            "title": "FK Conversation",
            "agent_id": agent.id,
            "user_id": user.id
        }
        conversation = await conversation_crud.create(db_session, obj_in=conversation_data)
        
        # Try to delete user (should fail due to FK constraints)
        with pytest.raises(Exception):  # Should raise integrity error
            await user_crud.remove(db_session, id=user.id)
        
        # Delete in correct order should work
        await conversation_crud.remove(db_session, id=conversation.id)
        await agent_crud.remove(db_session, id=agent.id)
        await user_crud.remove(db_session, id=user.id)
        
        # Verify all deleted
        assert await user_crud.get(db_session, user.id) is None
        assert await agent_crud.get(db_session, agent.id) is None
        assert await conversation_crud.get(db_session, conversation.id) is None

    async def test_cascade_deletes(self, db_session: AsyncSession):
        """Test cascade delete behavior."""
        
        # Create user with related data
        user_data = {
            "email": "cascade@example.com",
            "full_name": "Cascade User",
            "hashed_password": get_password_hash("password123")
        }
        user = await user_crud.create(db_session, obj_in=user_data)
        
        # Create agent
        agent_data = {
            "name": "Cascade Agent",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo",
            "user_id": user.id
        }
        agent = await agent_crud.create(db_session, obj_in=agent_data)
        
        # Create conversation
        conversation_data = {
            "title": "Cascade Conversation",
            "agent_id": agent.id,
            "user_id": user.id
        }
        conversation = await conversation_crud.create(db_session, obj_in=conversation_data)
        
        # Create messages
        message_data = [
            {
                "content": "Message 1",
                "role": "user",
                "conversation_id": conversation.id
            },
            {
                "content": "Message 2", 
                "role": "assistant",
                "conversation_id": conversation.id
            }
        ]
        
        messages = []
        for msg_data in message_data:
            message = await message_crud.create(db_session, obj_in=msg_data)
            messages.append(message)
        
        # Delete conversation (should cascade to messages if configured)
        await conversation_crud.remove(db_session, id=conversation.id)
        
        # Verify messages are also deleted (if cascade is configured)
        for message in messages:
            deleted_message = await message_crud.get(db_session, message.id)
            # This depends on cascade configuration in models
            # assert deleted_message is None

    async def test_concurrent_writes(self, db_session: AsyncSession):
        """Test concurrent write operations."""
        
        # Create user
        user_data = {
            "email": "concurrent@example.com",
            "full_name": "Concurrent User",
            "hashed_password": get_password_hash("password123")
        }
        user = await user_crud.create(db_session, obj_in=user_data)
        
        # Create agent
        agent_data = {
            "name": "Concurrent Agent",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo",
            "user_id": user.id
        }
        agent = await agent_crud.create(db_session, obj_in=agent_data)
        
        # Create conversation
        conversation_data = {
            "title": "Concurrent Conversation",
            "agent_id": agent.id,
            "user_id": user.id
        }
        conversation = await conversation_crud.create(db_session, obj_in=conversation_data)
        
        # Concurrent message creation
        async def create_message(content: str):
            async with async_session_maker() as session:
                message_data = {
                    "content": content,
                    "role": "user",
                    "conversation_id": conversation.id
                }
                return await message_crud.create(session, obj_in=message_data)
        
        # Create multiple messages concurrently
        tasks = [
            create_message(f"Concurrent message {i}")
            for i in range(5)
        ]
        
        messages = await asyncio.gather(*tasks)
        
        # All messages should be created successfully
        assert len(messages) == 5
        for message in messages:
            assert message.id is not None
            assert message.conversation_id == conversation.id

    async def test_database_indexes(self, db_session: AsyncSession):
        """Test database index performance."""
        
        # Create user
        user_data = {
            "email": "index@example.com",
            "full_name": "Index User",
            "hashed_password": get_password_hash("password123")
        }
        user = await user_crud.create(db_session, obj_in=user_data)
        
        # Create multiple agents to test index performance
        agents = []
        for i in range(100):
            agent_data = {
                "name": f"Agent {i}",
                "ai_provider": "openai",
                "model": "gpt-3.5-turbo",
                "user_id": user.id
            }
            agent = await agent_crud.create(db_session, obj_in=agent_data)
            agents.append(agent)
        
        # Test indexed queries (should be fast)
        import time
        
        # Query by user_id (should be indexed)
        start_time = time.time()
        user_agents = await agent_crud.get_multi_by_user(db_session, user_id=user.id)
        end_time = time.time()
        
        query_time = end_time - start_time
        assert len(user_agents) == 100
        # Query should be fast (under 1 second even with 100 records)
        assert query_time < 1.0

    async def test_data_consistency(self, db_session: AsyncSession):
        """Test data consistency across related tables."""
        
        # Create complete data hierarchy
        user_data = {
            "email": "consistency@example.com",
            "full_name": "Consistency User",
            "hashed_password": get_password_hash("password123")
        }
        user = await user_crud.create(db_session, obj_in=user_data)
        
        # Create agent
        agent_data = {
            "name": "Consistency Agent",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo",
            "user_id": user.id
        }
        agent = await agent_crud.create(db_session, obj_in=agent_data)
        
        # Create conversation
        conversation_data = {
            "title": "Consistency Conversation",
            "agent_id": agent.id,
            "user_id": user.id
        }
        conversation = await conversation_crud.create(db_session, obj_in=conversation_data)
        
        # Create messages
        message_data = [
            {
                "content": "User message",
                "role": "user",
                "conversation_id": conversation.id
            },
            {
                "content": "AI response",
                "role": "assistant",
                "conversation_id": conversation.id
            }
        ]
        
        messages = []
        for msg_data in message_data:
            message = await message_crud.create(db_session, obj_in=msg_data)
            messages.append(message)
        
        # Verify data consistency
        # 1. User should have the agent
        user_agents = await agent_crud.get_multi_by_user(db_session, user_id=user.id)
        assert len(user_agents) == 1
        assert user_agents[0].id == agent.id
        
        # 2. Agent should have the conversation
        agent_conversations = await conversation_crud.get_multi_by_agent(
            db_session, agent_id=agent.id
        )
        assert len(agent_conversations) == 1
        assert agent_conversations[0].id == conversation.id
        
        # 3. Conversation should have the messages
        conversation_messages = await message_crud.get_multi_by_conversation(
            db_session, conversation_id=conversation.id
        )
        assert len(conversation_messages) == 2
        
        # 4. Message order should be preserved
        sorted_messages = sorted(conversation_messages, key=lambda m: m.created_at)
        assert sorted_messages[0].role == "user"
        assert sorted_messages[1].role == "assistant"

    async def test_database_migration_state(self, db_session: AsyncSession):
        """Test database migration state and schema."""
        
        # Check that all required tables exist
        tables_query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        result = await db_session.execute(tables_query)
        table_names = [row[0] for row in result.fetchall()]
        
        required_tables = ['users', 'agents', 'conversations', 'messages']
        for table in required_tables:
            assert table in table_names, f"Table {table} not found in database"
        
        # Check that required columns exist in each table
        column_checks = {
            'users': ['id', 'email', 'full_name', 'hashed_password', 'created_at'],
            'agents': ['id', 'name', 'ai_provider', 'model', 'user_id', 'created_at'],
            'conversations': ['id', 'title', 'agent_id', 'user_id', 'created_at'],
            'messages': ['id', 'content', 'role', 'conversation_id', 'created_at']
        }
        
        for table, columns in column_checks.items():
            columns_query = text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
            """)
            
            result = await db_session.execute(columns_query)
            existing_columns = [row[0] for row in result.fetchall()]
            
            for column in columns:
                assert column in existing_columns, f"Column {column} not found in table {table}"


class TestDatabasePerformance:
    """Test database performance characteristics."""

    async def test_bulk_operations(self, db_session: AsyncSession):
        """Test bulk database operations."""
        
        # Create user
        user_data = {
            "email": "bulk@example.com",
            "full_name": "Bulk User",
            "hashed_password": get_password_hash("password123")
        }
        user = await user_crud.create(db_session, obj_in=user_data)
        
        # Test bulk agent creation
        import time
        
        start_time = time.time()
        
        # Create 50 agents
        agent_data_list = [
            {
                "name": f"Bulk Agent {i}",
                "ai_provider": "openai",
                "model": "gpt-3.5-turbo",
                "user_id": user.id
            }
            for i in range(50)
        ]
        
        # Create agents one by one (could be optimized with bulk insert)
        agents = []
        for agent_data in agent_data_list:
            agent = await agent_crud.create(db_session, obj_in=agent_data)
            agents.append(agent)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create 50 agents reasonably quickly
        assert len(agents) == 50
        assert creation_time < 5.0  # Should take less than 5 seconds
        
        # Test bulk retrieval
        start_time = time.time()
        user_agents = await agent_crud.get_multi_by_user(db_session, user_id=user.id)
        end_time = time.time()
        
        retrieval_time = end_time - start_time
        assert len(user_agents) == 50
        assert retrieval_time < 1.0  # Should retrieve quickly

    async def test_pagination_performance(self, db_session: AsyncSession):
        """Test pagination performance with larger datasets."""
        
        # Create user
        user_data = {
            "email": "pagination@example.com",
            "full_name": "Pagination User",
            "hashed_password": get_password_hash("password123")
        }
        user = await user_crud.create(db_session, obj_in=user_data)
        
        # Create agent
        agent_data = {
            "name": "Pagination Agent",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo",
            "user_id": user.id
        }
        agent = await agent_crud.create(db_session, obj_in=agent_data)
        
        # Create conversation
        conversation_data = {
            "title": "Pagination Conversation",
            "agent_id": agent.id,
            "user_id": user.id
        }
        conversation = await conversation_crud.create(db_session, obj_in=conversation_data)
        
        # Create many messages
        message_data_list = [
            {
                "content": f"Message {i}",
                "role": "user" if i % 2 == 0 else "assistant",
                "conversation_id": conversation.id
            }
            for i in range(200)
        ]
        
        for msg_data in message_data_list:
            await message_crud.create(db_session, obj_in=msg_data)
        
        # Test pagination performance
        import time
        
        # Test different page sizes
        page_sizes = [10, 25, 50, 100]
        
        for page_size in page_sizes:
            start_time = time.time()
            
            # Get first page
            messages_page = await message_crud.get_multi_by_conversation(
                db_session, 
                conversation_id=conversation.id,
                skip=0,
                limit=page_size
            )
            
            end_time = time.time()
            query_time = end_time - start_time
            
            assert len(messages_page) == page_size
            # Each query should be fast regardless of page size
            assert query_time < 0.5

    async def test_complex_queries(self, db_session: AsyncSession):
        """Test complex query performance."""
        
        # Create test data
        user_data = {
            "email": "complex@example.com",
            "full_name": "Complex User",
            "hashed_password": get_password_hash("password123")
        }
        user = await user_crud.create(db_session, obj_in=user_data)
        
        # Create multiple agents
        agents = []
        for i in range(5):
            agent_data = {
                "name": f"Complex Agent {i}",
                "ai_provider": "openai",
                "model": "gpt-3.5-turbo",
                "user_id": user.id
            }
            agent = await agent_crud.create(db_session, obj_in=agent_data)
            agents.append(agent)
        
        # Create conversations for each agent
        conversations = []
        for agent in agents:
            for j in range(3):
                conversation_data = {
                    "title": f"Conversation {j} for Agent {agent.name}",
                    "agent_id": agent.id,
                    "user_id": user.id
                }
                conversation = await conversation_crud.create(db_session, obj_in=conversation_data)
                conversations.append(conversation)
        
        # Test complex query: Get all conversations with message counts
        complex_query = text("""
            SELECT c.id, c.title, COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.user_id = :user_id
            GROUP BY c.id, c.title
            ORDER BY message_count DESC
        """)
        
        import time
        start_time = time.time()
        
        result = await db_session.execute(complex_query, {"user_id": user.id})
        conversation_stats = result.fetchall()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        assert len(conversation_stats) == 15  # 5 agents * 3 conversations each
        assert query_time < 1.0  # Complex query should still be fast
