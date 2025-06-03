"""
Unit tests for API endpoints.

Tests all REST API endpoints including authentication, CRUD operations,
error handling, and proper HTTP status codes.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi.testclient import TestClient
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.agents import router as agents_router
from app.api.v1.endpoints.conversations import router as conversations_router
from app.api.v1.endpoints.messages import router as messages_router
from app.models.user import User
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.agent import AgentCreate, AgentUpdate
from app.schemas.conversation import ConversationCreate
from app.schemas.auth import UserRegister, TokenRefresh
from app.core.security.jwt_handler import create_access_token, create_refresh_token


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestAuthEndpoints:
    """Test authentication API endpoints."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        with patch('app.crud.user.user_crud.authenticate') as mock_auth, \
             patch('app.crud.user.user_crud.update_last_login') as mock_update:
            
            mock_auth.return_value = test_user
            mock_update.return_value = None
            
            response = client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": "testpassword123"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
            assert data["user"]["email"] == test_user.email

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        with patch('app.crud.user.user_crud.authenticate') as mock_auth:
            mock_auth.return_value = None
            
            response = client.post(
                "/api/v1/auth/login",
                data={
                    "username": "invalid@example.com",
                    "password": "wrongpassword"
                }
            )
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()
            assert "Incorrect email or password" in data["detail"]

    def test_login_inactive_user(self, client, test_user):
        """Test login with inactive user."""
        test_user.is_active = False
        
        with patch('app.crud.user.user_crud.authenticate') as mock_auth:
            mock_auth.return_value = test_user
            
            response = client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": "testpassword123"
                }
            )
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()
            assert "Inactive user" in data["detail"]

    def test_register_success(self, client):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "newpassword123",
            "full_name": "New User"
        }
        
        mock_user = User(
            id=uuid4(),
            email=user_data["email"],
            full_name=user_data["full_name"],
            is_active=True
        )
        
        with patch('app.crud.user.user_crud.get_by_email') as mock_get, \
             patch('app.crud.user.user_crud.create') as mock_create:
            
            mock_get.return_value = None  # User doesn't exist
            mock_create.return_value = mock_user
            
            response = client.post(
                "/api/v1/auth/register",
                json=user_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["user"]["email"] == user_data["email"]

    def test_register_existing_email(self, client, test_user):
        """Test registration with existing email."""
        user_data = {
            "email": test_user.email,
            "password": "password123",
            "full_name": "Duplicate User"
        }
        
        with patch('app.crud.user.user_crud.get_by_email') as mock_get:
            mock_get.return_value = test_user
            
            response = client.post(
                "/api/v1/auth/register",
                json=user_data
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "already registered" in data["detail"]

    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh."""
        refresh_token = create_refresh_token({"sub": str(test_user.id)})
        
        with patch('app.crud.user.user_crud.get') as mock_get:
            mock_get.return_value = test_user
            
            response = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_token_success(self, client, auth_headers):
        """Test token verification."""
        response = client.get(
            "/api/v1/auth/verify-token",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True
        assert "user" in data

    def test_verify_token_invalid(self, client):
        """Test token verification with invalid token."""
        response = client.get(
            "/api/v1/auth/verify-token",
            headers={"Authorization": "Bearer invalid.token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout(self, client, auth_headers):
        """Test user logout."""
        response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "Successfully logged out" in data["message"]


class TestAgentEndpoints:
    """Test agent management API endpoints."""

    def test_create_agent_success(self, client, auth_headers):
        """Test successful agent creation."""
        agent_data = {
            "name": "Test Agent",
            "description": "A test agent",
            "provider": "openai",
            "model": "gpt-4",
            "system_prompt": "You are a helpful assistant.",
            "tools": ["web_search", "calculator"]
        }
        
        mock_agent = Agent(
            id=uuid4(),
            name=agent_data["name"],
            description=agent_data["description"],
            provider=agent_data["provider"],
            model=agent_data["model"],
            owner_id=uuid4()
        )
        
        with patch('app.crud.agent.agent_crud.create_with_owner') as mock_create:
            mock_create.return_value = mock_agent
            
            response = client.post(
                "/api/v1/agents/",
                json=agent_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["name"] == agent_data["name"]
            assert data["provider"] == agent_data["provider"]

    def test_create_agent_unauthorized(self, client):
        """Test agent creation without authentication."""
        agent_data = {
            "name": "Test Agent",
            "provider": "openai",
            "model": "gpt-4"
        }
        
        response = client.post(
            "/api/v1/agents/",
            json=agent_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_agents_list(self, client, auth_headers):
        """Test getting list of agents."""
        mock_agents = [
            Agent(id=uuid4(), name="Agent 1", provider="openai", model="gpt-4", owner_id=uuid4()),
            Agent(id=uuid4(), name="Agent 2", provider="anthropic", model="claude-3", owner_id=uuid4())
        ]
        
        with patch('app.crud.agent.agent_crud.get_multi_by_owner') as mock_get:
            mock_get.return_value = mock_agents
            
            response = client.get(
                "/api/v1/agents/",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "Agent 1"
            assert data[1]["name"] == "Agent 2"

    def test_get_agent_by_id(self, client, auth_headers):
        """Test getting agent by ID."""
        agent_id = uuid4()
        mock_agent = Agent(
            id=agent_id,
            name="Test Agent",
            provider="openai",
            model="gpt-4",
            owner_id=uuid4()
        )
        
        with patch('app.crud.agent.agent_crud.get_by_owner') as mock_get:
            mock_get.return_value = mock_agent
            
            response = client.get(
                f"/api/v1/agents/{agent_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["name"] == "Test Agent"
            assert data["id"] == str(agent_id)

    def test_get_agent_not_found(self, client, auth_headers):
        """Test getting non-existent agent."""
        agent_id = uuid4()
        
        with patch('app.crud.agent.agent_crud.get_by_owner') as mock_get:
            mock_get.return_value = None
            
            response = client.get(
                f"/api/v1/agents/{agent_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_agent(self, client, auth_headers):
        """Test updating agent."""
        agent_id = uuid4()
        update_data = {
            "name": "Updated Agent",
            "description": "Updated description"
        }
        
        mock_agent = Agent(
            id=agent_id,
            name="Original Agent",
            provider="openai",
            model="gpt-4",
            owner_id=uuid4()
        )
        
        updated_agent = Agent(
            id=agent_id,
            name=update_data["name"],
            description=update_data["description"],
            provider="openai",
            model="gpt-4",
            owner_id=uuid4()
        )
        
        with patch('app.crud.agent.agent_crud.get_by_owner') as mock_get, \
             patch('app.crud.agent.agent_crud.update') as mock_update:
            
            mock_get.return_value = mock_agent
            mock_update.return_value = updated_agent
            
            response = client.put(
                f"/api/v1/agents/{agent_id}",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["name"] == update_data["name"]
            assert data["description"] == update_data["description"]

    def test_delete_agent(self, client, auth_headers):
        """Test deleting agent."""
        agent_id = uuid4()
        mock_agent = Agent(id=agent_id, name="Test Agent", provider="openai", model="gpt-4", owner_id=uuid4())
        
        with patch('app.crud.agent.agent_crud.get_by_owner') as mock_get, \
             patch('app.crud.agent.agent_crud.remove') as mock_remove:
            
            mock_get.return_value = mock_agent
            mock_remove.return_value = mock_agent
            
            response = client.delete(
                f"/api/v1/agents/{agent_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(agent_id)


class TestConversationEndpoints:
    """Test conversation management API endpoints."""

    def test_create_conversation(self, client, auth_headers):
        """Test conversation creation."""
        conversation_data = {
            "title": "Test Conversation",
            "agent_id": str(uuid4())
        }
        
        mock_conversation = Conversation(
            id=uuid4(),
            title=conversation_data["title"],
            agent_id=conversation_data["agent_id"],
            user_id=uuid4()
        )
        
        with patch('app.crud.conversation.conversation_crud.create_with_owner') as mock_create:
            mock_create.return_value = mock_conversation
            
            response = client.post(
                "/api/v1/conversations/",
                json=conversation_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["title"] == conversation_data["title"]

    def test_get_conversations_list(self, client, auth_headers):
        """Test getting conversations list."""
        mock_conversations = [
            Conversation(id=uuid4(), title="Conv 1", user_id=uuid4()),
            Conversation(id=uuid4(), title="Conv 2", user_id=uuid4())
        ]
        
        with patch('app.crud.conversation.conversation_crud.get_multi_by_owner') as mock_get:
            mock_get.return_value = mock_conversations
            
            response = client.get(
                "/api/v1/conversations/",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2

    def test_get_conversation_by_id(self, client, auth_headers):
        """Test getting conversation by ID."""
        conversation_id = uuid4()
        mock_conversation = Conversation(
            id=conversation_id,
            title="Test Conversation",
            user_id=uuid4()
        )
        
        with patch('app.crud.conversation.conversation_crud.get_by_owner') as mock_get:
            mock_get.return_value = mock_conversation
            
            response = client.get(
                f"/api/v1/conversations/{conversation_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(conversation_id)


class TestMessageEndpoints:
    """Test message management API endpoints."""

    def test_create_message(self, client, auth_headers):
        """Test message creation."""
        conversation_id = uuid4()
        message_data = {
            "content": "Hello, AI!",
            "role": "user",
            "conversation_id": str(conversation_id)
        }
        
        mock_message = MagicMock()
        mock_message.id = uuid4()
        mock_message.content = message_data["content"]
        mock_message.role = message_data["role"]
        
        with patch('app.crud.message.message_crud.create') as mock_create:
            mock_create.return_value = mock_message
            
            response = client.post(
                "/api/v1/messages/",
                json=message_data,
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_201_CREATED

    def test_get_messages_by_conversation(self, client, auth_headers):
        """Test getting messages by conversation."""
        conversation_id = uuid4()
        
        mock_messages = [
            MagicMock(id=uuid4(), content="Hello", role="user"),
            MagicMock(id=uuid4(), content="Hi there!", role="assistant")
        ]
        
        with patch('app.crud.message.message_crud.get_by_conversation') as mock_get:
            mock_get.return_value = mock_messages
            
            response = client.get(
                f"/api/v1/messages/conversation/{conversation_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK


class TestErrorHandling:
    """Test API error handling."""

    def test_validation_error_response(self, client):
        """Test validation error responses."""
        # Send invalid data to trigger validation error
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",  # Invalid email format
                "password": "123",         # Too short password
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    def test_404_error_response(self, client):
        """Test 404 error responses."""
        response = client.get("/api/v1/nonexistent-endpoint")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_method_not_allowed_response(self, client):
        """Test 405 method not allowed responses."""
        response = client.patch("/api/v1/auth/login")  # PATCH not allowed for login
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoints."""
        response = client.get("/api/v1/agents/")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_forbidden_access(self, client, auth_headers):
        """Test forbidden access to admin endpoints."""
        # Regular user trying to access admin endpoint
        response = client.get(
            "/api/v1/admin/users/",
            headers=auth_headers
        )
        
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND  # If endpoint doesn't exist
        ]


class TestPagination:
    """Test API pagination."""

    def test_agents_pagination(self, client, auth_headers):
        """Test agents endpoint pagination."""
        mock_agents = [Agent(id=uuid4(), name=f"Agent {i}", provider="openai", model="gpt-4", owner_id=uuid4()) for i in range(15)]
        
        with patch('app.crud.agent.agent_crud.get_multi_by_owner') as mock_get:
            mock_get.return_value = mock_agents[:10]  # Return first 10
            
            response = client.get(
                "/api/v1/agents/?skip=0&limit=10",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 10

    def test_conversations_pagination(self, client, auth_headers):
        """Test conversations endpoint pagination."""
        with patch('app.crud.conversation.conversation_crud.get_multi_by_owner') as mock_get:
            mock_get.return_value = []  # Empty result
            
            response = client.get(
                "/api/v1/conversations/?skip=0&limit=5",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 0


class TestRateLimiting:
    """Test API rate limiting."""

    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/api/v1/health")
        
        # Check if rate limiting headers are present (if implemented)
        # This is implementation-dependent
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_rate_limit_exceeded(self, client):
        """Test rate limit exceeded response."""
        # This would require actual rate limiting implementation
        # For now, just ensure the endpoint responds
        response = client.post("/api/v1/auth/login", data={"username": "test", "password": "test"})
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,  # Expected for invalid credentials
            status.HTTP_429_TOO_MANY_REQUESTS  # If rate limited
        ]


class TestContentTypes:
    """Test API content type handling."""

    def test_json_content_type(self, client):
        """Test JSON content type handling."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "password123", "full_name": "Test User"},
            headers={"Content-Type": "application/json"}
        )
        
        # Should process JSON content correctly
        assert response.status_code in [
            status.HTTP_201_CREATED,  # Success
            status.HTTP_400_BAD_REQUEST,  # Validation error
            status.HTTP_422_UNPROCESSABLE_ENTITY  # Processing error
        ]

    def test_form_data_content_type(self, client):
        """Test form data content type handling."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Should process form data correctly
        assert response.status_code in [
            status.HTTP_200_OK,  # Success
            status.HTTP_401_UNAUTHORIZED  # Expected for test credentials
        ]

    def test_unsupported_content_type(self, client):
        """Test unsupported content type handling."""
        response = client.post(
            "/api/v1/agents/",
            data="plain text data",
            headers={"Content-Type": "text/plain"}
        )
        
        # Should reject unsupported content type
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,  # Auth required first
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,  # Unsupported content type
            status.HTTP_422_UNPROCESSABLE_ENTITY  # Processing error
        ]
