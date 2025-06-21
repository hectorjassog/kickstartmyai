"""
Unit tests for CRUD operations.

Tests all database CRUD operations to ensure they work correctly
with proper error handling, validation, and data consistency.
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.crud.user import user_crud
from app.crud.agent import agent_crud
from app.crud.conversation import conversation_crud
from app.crud.message import message_crud
from app.models.user import User
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.agent import AgentCreate, AgentUpdate
from app.schemas.conversation import ConversationCreate, ConversationUpdate
from app.schemas.message import MessageCreate, MessageUpdate


class TestUserCRUD:
    """Test user CRUD operations."""

    @pytest_asyncio.fixture
    async def user_data(self) -> UserCreate:
        """Create test user data."""
        return UserCreate(
            email="test@example.com",
            password="testpassword123",
            full_name="Test User"
        )

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession, user_data: UserCreate):
        """Test user creation."""
        user = await user_crud.create(db_session, obj_in=user_data)
        
        assert user.email == user_data.email
        assert user.full_name == user_data.full_name
        assert user.id is not None
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.hashed_password != user_data.password  # Should be hashed

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session: AsyncSession, test_user: User):
        """Test getting user by ID."""
        user = await user_crud.get(db_session, id=test_user.id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session: AsyncSession, test_user: User):
        """Test getting user by email."""
        user = await user_crud.get_by_email(db_session, email=test_user.email)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, db_session: AsyncSession):
        """Test getting non-existent user."""
        user = await user_crud.get(db_session, id=uuid4())
        assert user is None
        
        user = await user_crud.get_by_email(db_session, email="nonexistent@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_update_user(self, db_session: AsyncSession, test_user: User):
        """Test user update."""
        update_data = UserUpdate(
            full_name="Updated Name",
            email="updated@example.com"
        )
        
        updated_user = await user_crud.update(db_session, db_obj=test_user, obj_in=update_data)
        
        assert updated_user.full_name == "Updated Name"
        assert updated_user.email == "updated@example.com"
        assert updated_user.id == test_user.id

    @pytest.mark.asyncio
    async def test_update_user_password(self, db_session: AsyncSession, test_user: User):
        """Test user password update."""
        old_password = test_user.hashed_password
        
        update_data = UserUpdate(password="newpassword123")
        updated_user = await user_crud.update(db_session, db_obj=test_user, obj_in=update_data)
        
        assert updated_user.hashed_password != old_password
        assert updated_user.hashed_password != "newpassword123"  # Should be hashed

    @pytest.mark.asyncio
    async def test_delete_user(self, db_session: AsyncSession, test_user: User):
        """Test user deletion."""
        user_id = test_user.id
        
        await user_crud.remove(db_session, id=user_id)
        
        # User should no longer exist
        deleted_user = await user_crud.get(db_session, id=user_id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_list_users_with_pagination(self, db_session: AsyncSession):
        """Test listing users with pagination."""
        # Create multiple users
        for i in range(5):
            user_data = UserCreate(
                email=f"user{i}@example.com",
                password="password123",
                full_name=f"User {i}"
            )
            await user_crud.create(db_session, obj_in=user_data)
        
        # Test pagination
        users = await user_crud.get_multi(db_session, skip=0, limit=3)
        assert len(users) == 3
        
        users = await user_crud.get_multi(db_session, skip=3, limit=3)
        assert len(users) >= 2  # At least 2 remaining

    @pytest.mark.asyncio
    async def test_duplicate_email_error(self, db_session: AsyncSession, test_user: User):
        """Test duplicate email constraint."""
        duplicate_data = UserCreate(
            email=test_user.email,  # Same email
            password="password123",
            full_name="Duplicate User"
        )
        
        with pytest.raises(IntegrityError):
            await user_crud.create(db_session, obj_in=duplicate_data)

    @pytest.mark.asyncio
    async def test_authenticate_user(self, db_session: AsyncSession):
        """Test user authentication."""
        # Create user with known password
        user_data = UserCreate(
            email="auth@example.com",
            password="knownpassword123",
            full_name="Auth User"
        )
        user = await user_crud.create(db_session, obj_in=user_data)
        
        # Test successful authentication
        auth_user = await user_crud.authenticate(
            db_session, 
            email="auth@example.com", 
            password="knownpassword123"
        )
        assert auth_user is not None
        assert auth_user.id == user.id
        
        # Test failed authentication
        auth_user = await user_crud.authenticate(
            db_session, 
            email="auth@example.com", 
            password="wrongpassword"
        )
        assert auth_user is None

    @pytest.mark.asyncio
    async def test_is_superuser(self, db_session: AsyncSession):
        """Test superuser check."""
        user_data = UserCreate(
            email="super@example.com",
            password="password123",
            full_name="Super User"
        )
        user = await user_crud.create(db_session, obj_in=user_data)
        
        # Initially not superuser
        assert user_crud.is_superuser(user) is False
        
        # Update to superuser
        user.is_superuser = True
        db_session.add(user)
        await db_session.commit()
        
        assert user_crud.is_superuser(user) is True

    @pytest.mark.asyncio
    async def test_update_last_login(self, db_session: AsyncSession, test_user: User):
        """Test updating last login time."""
        original_last_login = test_user.last_login_at
        
        await user_crud.update_last_login(db_session, user=test_user)
        
        await db_session.refresh(test_user)
        assert test_user.last_login_at != original_last_login
        assert test_user.last_login_at is not None


class TestAgentCRUD:
    """Test agent CRUD operations."""

    @pytest_asyncio.fixture
    async def agent_data(self, test_user: User) -> AgentCreate:
        """Create test agent data."""
        return AgentCreate(
            name="Test Agent",
            description="A test AI agent",
            provider="openai",
            model="gpt-4",
            system_prompt="You are a helpful assistant.",
            temperature=0.7,
            max_tokens=1000,
            tools_enabled=True
        )

    @pytest.mark.asyncio
    async def test_create_agent(self, db_session: AsyncSession, test_user: User, agent_data: AgentCreate):
        """Test agent creation."""
        agent = await agent_crud.create_with_owner(
            db_session, 
            obj_in=agent_data, 
            owner_id=test_user.id
        )
        
        assert agent.name == agent_data.name
        assert agent.description == agent_data.description
        assert agent.provider == agent_data.provider
        assert agent.model == agent_data.model
        assert agent.owner_id == test_user.id
        assert agent.id is not None

    @pytest.mark.asyncio
    async def test_get_agent_by_id(self, db_session: AsyncSession, test_user: User, agent_data: AgentCreate):
        """Test getting agent by ID."""
        agent = await agent_crud.create_with_owner(
            db_session, 
            obj_in=agent_data, 
            owner_id=test_user.id
        )
        
        retrieved_agent = await agent_crud.get(db_session, id=agent.id)
        
        assert retrieved_agent is not None
        assert retrieved_agent.id == agent.id
        assert retrieved_agent.name == agent.name

    @pytest.mark.asyncio
    async def test_get_agents_by_owner(self, db_session: AsyncSession, test_user: User):
        """Test getting agents by owner."""
        # Create multiple agents for the user
        for i in range(3):
            agent_data = AgentCreate(
                name=f"Agent {i}",
                description=f"Test agent {i}",
                provider="openai",
                model="gpt-4"
            )
            await agent_crud.create_with_owner(
                db_session, 
                obj_in=agent_data, 
                owner_id=test_user.id
            )
        
        agents = await agent_crud.get_multi_by_owner(
            db_session, 
            owner_id=test_user.id
        )
        
        assert len(agents) == 3
        for agent in agents:
            assert agent.owner_id == test_user.id

    @pytest.mark.asyncio
    async def test_update_agent(self, db_session: AsyncSession, test_user: User, agent_data: AgentCreate):
        """Test agent update."""
        agent = await agent_crud.create_with_owner(
            db_session, 
            obj_in=agent_data, 
            owner_id=test_user.id
        )
        
        update_data = AgentUpdate(
            name="Updated Agent",
            temperature=0.9,
            max_tokens=2000
        )
        
        updated_agent = await agent_crud.update(
            db_session, 
            db_obj=agent, 
            obj_in=update_data
        )
        
        assert updated_agent.name == "Updated Agent"
        assert updated_agent.temperature == 0.9
        assert updated_agent.max_tokens == 2000
        assert updated_agent.id == agent.id

    @pytest.mark.asyncio
    async def test_delete_agent(self, db_session: AsyncSession, test_user: User, agent_data: AgentCreate):
        """Test agent deletion."""
        agent = await agent_crud.create_with_owner(
            db_session, 
            obj_in=agent_data, 
            owner_id=test_user.id
        )
        agent_id = agent.id
        
        await agent_crud.remove(db_session, id=agent_id)
        
        deleted_agent = await agent_crud.get(db_session, id=agent_id)
        assert deleted_agent is None

    @pytest.mark.asyncio
    async def test_agent_tools_configuration(self, db_session: AsyncSession, test_user: User):
        """Test agent tools configuration."""
        agent_data = AgentCreate(
            name="Tool Agent",
            description="Agent with specific tools",
            provider="openai",
            model="gpt-4",
            tools_enabled=True,
            enabled_tools=["web_search", "calculator"]
        )
        
        agent = await agent_crud.create_with_owner(
            db_session, 
            obj_in=agent_data, 
            owner_id=test_user.id
        )
        
        assert agent.tools_enabled is True
        assert agent.enabled_tools == ["web_search", "calculator"]


class TestConversationCRUD:
    """Test conversation CRUD operations."""

    @pytest_asyncio.fixture
    async def agent(self, db_session: AsyncSession, test_user: User) -> Agent:
        """Create test agent."""
        agent_data = AgentCreate(
            name="Test Agent",
            description="Test agent for conversations",
            provider="openai",
            model="gpt-4"
        )
        return await agent_crud.create_with_owner(
            db_session, 
            obj_in=agent_data, 
            owner_id=test_user.id
        )

    @pytest_asyncio.fixture
    async def conversation_data(self, test_user: User, agent: Agent) -> ConversationCreate:
        """Create test conversation data."""
        return ConversationCreate(
            title="Test Conversation",
            agent_id=agent.id
        )

    @pytest.mark.asyncio
    async def test_create_conversation(
        self, 
        db_session: AsyncSession, 
        test_user: User, 
        agent: Agent, 
        conversation_data: ConversationCreate
    ):
        """Test conversation creation."""
        conversation = await conversation_crud.create_with_owner(
            db_session, 
            obj_in=conversation_data, 
            owner_id=test_user.id
        )
        
        assert conversation.title == conversation_data.title
        assert conversation.agent_id == agent.id
        assert conversation.owner_id == test_user.id
        assert conversation.id is not None

    @pytest.mark.asyncio
    async def test_get_conversations_by_owner(
        self, 
        db_session: AsyncSession, 
        test_user: User, 
        agent: Agent
    ):
        """Test getting conversations by owner."""
        # Create multiple conversations
        for i in range(3):
            conv_data = ConversationCreate(
                title=f"Conversation {i}",
                agent_id=agent.id
            )
            await conversation_crud.create_with_owner(
                db_session, 
                obj_in=conv_data, 
                owner_id=test_user.id
            )
        
        conversations = await conversation_crud.get_multi_by_owner(
            db_session, 
            owner_id=test_user.id
        )
        
        assert len(conversations) == 3
        for conv in conversations:
            assert conv.owner_id == test_user.id

    @pytest.mark.asyncio
    async def test_update_conversation(
        self, 
        db_session: AsyncSession, 
        test_user: User, 
        agent: Agent, 
        conversation_data: ConversationCreate
    ):
        """Test conversation update."""
        conversation = await conversation_crud.create_with_owner(
            db_session, 
            obj_in=conversation_data, 
            owner_id=test_user.id
        )
        
        update_data = ConversationUpdate(title="Updated Conversation")
        
        updated_conversation = await conversation_crud.update(
            db_session, 
            db_obj=conversation, 
            obj_in=update_data
        )
        
        assert updated_conversation.title == "Updated Conversation"
        assert updated_conversation.id == conversation.id


class TestMessageCRUD:
    """Test message CRUD operations."""

    @pytest_asyncio.fixture
    async def conversation(
        self, 
        db_session: AsyncSession, 
        test_user: User
    ) -> Conversation:
        """Create test conversation."""
        # Create agent first
        agent_data = AgentCreate(
            name="Message Agent",
            description="Agent for message testing",
            provider="openai",
            model="gpt-4"
        )
        agent = await agent_crud.create_with_owner(
            db_session, 
            obj_in=agent_data, 
            owner_id=test_user.id
        )
        
        # Create conversation
        conv_data = ConversationCreate(
            title="Message Conversation",
            agent_id=agent.id
        )
        return await conversation_crud.create_with_owner(
            db_session, 
            obj_in=conv_data, 
            owner_id=test_user.id
        )

    @pytest_asyncio.fixture
    async def message_data(self, conversation: Conversation) -> MessageCreate:
        """Create test message data."""
        return MessageCreate(
            content="Hello, world!",
            role="user",
            conversation_id=conversation.id
        )

    @pytest.mark.asyncio
    async def test_create_message(
        self, 
        db_session: AsyncSession, 
        conversation: Conversation, 
        message_data: MessageCreate
    ):
        """Test message creation."""
        message = await message_crud.create(db_session, obj_in=message_data)
        
        assert message.content == message_data.content
        assert message.role == message_data.role
        assert message.conversation_id == conversation.id
        assert message.id is not None

    @pytest.mark.asyncio
    async def test_get_messages_by_conversation(
        self, 
        db_session: AsyncSession, 
        conversation: Conversation
    ):
        """Test getting messages by conversation."""
        # Create multiple messages
        messages_data = [
            {"content": "Hello", "role": "user"},
            {"content": "Hi there!", "role": "assistant"},
            {"content": "How are you?", "role": "user"},
        ]
        
        for msg_data in messages_data:
            message = MessageCreate(
                content=msg_data["content"],
                role=msg_data["role"],
                conversation_id=conversation.id
            )
            await message_crud.create(db_session, obj_in=message)
        
        messages = await message_crud.get_by_conversation(
            db_session, 
            conversation_id=conversation.id
        )
        
        assert len(messages) == 3
        assert messages[0].content == "Hello"
        assert messages[1].content == "Hi there!"
        assert messages[2].content == "How are you?"

    @pytest.mark.asyncio
    async def test_message_with_tool_calls(
        self, 
        db_session: AsyncSession, 
        conversation: Conversation
    ):
        """Test message with tool calls."""
        tool_calls = [
            {
                "name": "web_search",
                "arguments": {"query": "test query"},
                "result": {"success": True}
            }
        ]
        
        message_data = MessageCreate(
            content="I'll search for that",
            role="assistant",
            conversation_id=conversation.id,
            tool_calls=tool_calls
        )
        
        message = await message_crud.create(db_session, obj_in=message_data)
        
        assert message.tool_calls == tool_calls
        assert len(message.tool_calls) == 1
        assert message.tool_calls[0]["name"] == "web_search"

    @pytest.mark.asyncio
    async def test_message_token_counting(
        self, 
        db_session: AsyncSession, 
        conversation: Conversation
    ):
        """Test message token counting."""
        message_data = MessageCreate(
            content="This is a test message for token counting",
            role="user",
            conversation_id=conversation.id,
            token_count=10
        )
        
        message = await message_crud.create(db_session, obj_in=message_data)
        
        assert message.token_count == 10

    @pytest.mark.asyncio
    async def test_delete_message(
        self, 
        db_session: AsyncSession, 
        conversation: Conversation, 
        message_data: MessageCreate
    ):
        """Test message deletion."""
        message = await message_crud.create(db_session, obj_in=message_data)
        message_id = message.id
        
        await message_crud.remove(db_session, id=message_id)
        
        deleted_message = await message_crud.get(db_session, id=message_id)
        assert deleted_message is None


class TestCRUDErrorHandling:
    """Test CRUD error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_create_with_invalid_foreign_key(self, db_session: AsyncSession):
        """Test creating object with invalid foreign key."""
        invalid_agent_data = AgentCreate(
            name="Invalid Agent",
            description="Agent with invalid owner",
            provider="openai",
            model="gpt-4"
        )
        
        # Try to create agent with non-existent owner
        with pytest.raises(Exception):  # Should raise foreign key constraint error
            await agent_crud.create_with_owner(
                db_session, 
                obj_in=invalid_agent_data, 
                owner_id=uuid4()  # Non-existent user ID
            )

    @pytest.mark.asyncio
    async def test_update_nonexistent_object(self, db_session: AsyncSession):
        """Test updating non-existent object."""
        # Create a fake user object that doesn't exist in DB
        fake_user = User(
            id=uuid4(),
            email="fake@example.com",
            full_name="Fake User",
            hashed_password="fake_hash"
        )
        
        update_data = UserUpdate(full_name="Updated Fake")
        
        # This should not crash but may not update anything
        result = await user_crud.update(db_session, db_obj=fake_user, obj_in=update_data)
        
        # The object should be updated in memory but not persisted
        assert result.full_name == "Updated Fake"

    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self, db_session: AsyncSession):
        """Test pagination edge cases."""
        # Test with skip > total records
        users = await user_crud.get_multi(db_session, skip=1000, limit=10)
        assert len(users) == 0
        
        # Test with limit = 0
        users = await user_crud.get_multi(db_session, skip=0, limit=0)
        assert len(users) == 0
        
        # Test with negative values (should be handled gracefully)
        users = await user_crud.get_multi(db_session, skip=-1, limit=-1)
        # Should either return empty list or handle gracefully
        assert isinstance(users, list)
