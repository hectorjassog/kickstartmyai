"""
Integration tests for complete API workflows.

Tests end-to-end user journeys including authentication, agent creation,
conversation management, and AI interactions.
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta

from app.core.config import settings
from app.models.user import User
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message


class TestCompleteUserWorkflow:
    """Test complete user workflows from registration to AI interactions."""

    async def test_complete_user_journey(
        self, 
        async_client: AsyncClient,
        db_session,
        mock_openai_client,
        mock_anthropic_client
    ):
        """Test complete user journey: register -> login -> create agent -> chat -> logout."""
        
        # Step 1: User Registration
        registration_data = {
            "email": "testuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        assert response.status_code == status.HTTP_201_CREATED
        user_data = response.json()
        assert user_data["email"] == registration_data["email"]
        
        # Step 2: User Login
        login_data = {
            "username": registration_data["email"],
            "password": registration_data["password"]
        }
        
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == status.HTTP_200_OK
        tokens = response.json()
        access_token = tokens["access_token"]
        
        # Set authorization header for subsequent requests
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 3: Create an AI Agent
        agent_data = {
            "name": "My Assistant",
            "description": "A helpful AI assistant",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are a helpful assistant.",
            "tools": ["web_search", "calculator"]
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=agent_data, 
            headers=headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        agent = response.json()
        agent_id = agent["id"]
        
        # Step 4: Start a Conversation
        conversation_data = {
            "title": "Test Conversation",
            "agent_id": agent_id
        }
        
        response = await async_client.post(
            "/api/v1/conversations", 
            json=conversation_data, 
            headers=headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        conversation = response.json()
        conversation_id = conversation["id"]
        
        # Step 5: Send Messages and Get AI Responses
        message_data = {
            "content": "Hello, can you help me with a calculation?",
            "conversation_id": conversation_id
        }
        
        # Mock AI response
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "Hello! I'd be happy to help you with calculations. What would you like me to calculate?"
        
        response = await async_client.post(
            "/api/v1/messages", 
            json=message_data, 
            headers=headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        user_message = response.json()
        assert user_message["content"] == message_data["content"]
        assert user_message["role"] == "user"
        
        # Check that AI response was created
        response = await async_client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        messages = response.json()["items"]
        assert len(messages) >= 2  # User message + AI response
        
        ai_message = next(msg for msg in messages if msg["role"] == "assistant")
        assert "calculate" in ai_message["content"].lower()
        
        # Step 6: Test Tool Usage
        tool_message_data = {
            "content": "What is 15 * 23?",
            "conversation_id": conversation_id
        }
        
        # Mock AI response with tool usage
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "I'll calculate that for you: 15 * 23 = 345"
        
        response = await async_client.post(
            "/api/v1/messages", 
            json=tool_message_data, 
            headers=headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Step 7: Test Conversation History
        response = await async_client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        messages = response.json()["items"]
        assert len(messages) >= 4  # 2 user messages + 2 AI responses
        
        # Step 8: Test Agent Management
        response = await async_client.get("/api/v1/agents", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        agents = response.json()["items"]
        assert len(agents) >= 1
        assert any(a["id"] == agent_id for a in agents)
        
        # Step 9: Update Agent
        update_data = {
            "name": "Updated Assistant",
            "description": "An updated helpful AI assistant"
        }
        
        response = await async_client.patch(
            f"/api/v1/agents/{agent_id}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        updated_agent = response.json()
        assert updated_agent["name"] == update_data["name"]
        
        # Step 10: Logout
        response = await async_client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        # Step 11: Verify token is invalidated
        response = await async_client.get("/api/v1/agents", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_multi_user_isolation(
        self, 
        async_client: AsyncClient,
        db_session,
        mock_openai_client
    ):
        """Test that users can only access their own data."""
        
        # Create two users
        users_data = [
            {
                "email": "user1@example.com",
                "password": "Password123!",
                "full_name": "User One"
            },
            {
                "email": "user2@example.com", 
                "password": "Password123!",
                "full_name": "User Two"
            }
        ]
        
        tokens = []
        agent_ids = []
        
        # Register and login both users
        for user_data in users_data:
            # Register
            response = await async_client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == status.HTTP_201_CREATED
            
            # Login
            login_data = {
                "username": user_data["email"],
                "password": user_data["password"]
            }
            response = await async_client.post("/api/v1/auth/login", data=login_data)
            assert response.status_code == status.HTTP_200_OK
            tokens.append(response.json()["access_token"])
            
            # Create agent for each user
            agent_data = {
                "name": f"Agent for {user_data['full_name']}",
                "description": "User-specific agent",
                "ai_provider": "openai",
                "model": "gpt-3.5-turbo"
            }
            
            headers = {"Authorization": f"Bearer {tokens[-1]}"}
            response = await async_client.post(
                "/api/v1/agents", 
                json=agent_data, 
                headers=headers
            )
            assert response.status_code == status.HTTP_201_CREATED
            agent_ids.append(response.json()["id"])
        
        # Test isolation: User 1 cannot access User 2's agent
        user1_headers = {"Authorization": f"Bearer {tokens[0]}"}
        user2_headers = {"Authorization": f"Bearer {tokens[1]}"}
        
        # User 1 tries to access User 2's agent
        response = await async_client.get(
            f"/api/v1/agents/{agent_ids[1]}", 
            headers=user1_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # User 2 tries to access User 1's agent
        response = await async_client.get(
            f"/api/v1/agents/{agent_ids[0]}", 
            headers=user2_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Users can access their own agents
        response = await async_client.get(
            f"/api/v1/agents/{agent_ids[0]}", 
            headers=user1_headers
        )
        assert response.status_code == status.HTTP_200_OK
        
        response = await async_client.get(
            f"/api/v1/agents/{agent_ids[1]}", 
            headers=user2_headers
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_concurrent_conversations(
        self, 
        async_client: AsyncClient,
        db_session,
        mock_openai_client
    ):
        """Test handling multiple concurrent conversations."""
        
        # Setup user and agent
        user_data = {
            "email": "concurrent@example.com",
            "password": "Password123!",
            "full_name": "Concurrent User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        access_token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Create agent
        agent_data = {
            "name": "Concurrent Agent",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo"
        }
        response = await async_client.post("/api/v1/agents", json=agent_data, headers=headers)
        agent_id = response.json()["id"]
        
        # Create multiple conversations
        conversation_ids = []
        for i in range(3):
            conversation_data = {
                "title": f"Conversation {i+1}",
                "agent_id": agent_id
            }
            response = await async_client.post(
                "/api/v1/conversations", 
                json=conversation_data, 
                headers=headers
            )
            assert response.status_code == status.HTTP_201_CREATED
            conversation_ids.append(response.json()["id"])
        
        # Mock AI responses
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "Response"
        
        # Send messages to all conversations concurrently
        async def send_message(conversation_id, content):
            message_data = {
                "content": content,
                "conversation_id": conversation_id
            }
            return await async_client.post(
                "/api/v1/messages", 
                json=message_data, 
                headers=headers
            )
        
        # Create concurrent tasks
        tasks = []
        for i, conv_id in enumerate(conversation_ids):
            task = send_message(conv_id, f"Message to conversation {i+1}")
            tasks.append(task)
        
        # Execute concurrently
        responses = await asyncio.gather(*tasks)
        
        # Verify all messages were created successfully
        for response in responses:
            assert response.status_code == status.HTTP_201_CREATED
        
        # Verify each conversation has the correct messages
        for i, conv_id in enumerate(conversation_ids):
            response = await async_client.get(
                f"/api/v1/conversations/{conv_id}/messages",
                headers=headers
            )
            assert response.status_code == status.HTTP_200_OK
            messages = response.json()["items"]
            assert len(messages) >= 2  # User message + AI response
            
            user_message = next(msg for msg in messages if msg["role"] == "user")
            assert f"conversation {i+1}" in user_message["content"]


class TestAIProviderIntegration:
    """Test integration with different AI providers."""

    async def test_openai_integration_workflow(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers,
        mock_openai_client
    ):
        """Test complete workflow with OpenAI provider."""
        
        # Create OpenAI agent
        agent_data = {
            "name": "OpenAI Agent",
            "ai_provider": "openai",
            "model": "gpt-4",
            "system_prompt": "You are a helpful assistant.",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=agent_data, 
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        agent = response.json()
        agent_id = agent["id"]
        
        # Create conversation
        conversation_data = {
            "title": "OpenAI Test",
            "agent_id": agent_id
        }
        
        response = await async_client.post(
            "/api/v1/conversations", 
            json=conversation_data, 
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        conversation_id = response.json()["id"]
        
        # Mock OpenAI response
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "Hello! I'm an OpenAI assistant."
        mock_openai_client.chat.completions.create.return_value.usage.total_tokens = 50
        
        # Send message
        message_data = {
            "content": "Hello, OpenAI!",
            "conversation_id": conversation_id
        }
        
        response = await async_client.post(
            "/api/v1/messages", 
            json=message_data, 
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify OpenAI client was called with correct parameters
        mock_openai_client.chat.completions.create.assert_called()
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["temperature"] == 0.7
        assert call_args[1]["max_tokens"] == 1000

    async def test_anthropic_integration_workflow(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers,
        mock_anthropic_client
    ):
        """Test complete workflow with Anthropic provider."""
        
        # Create Anthropic agent
        agent_data = {
            "name": "Claude Agent",
            "ai_provider": "anthropic",
            "model": "claude-3-sonnet-20240229",
            "system_prompt": "You are Claude, an AI assistant.",
            "max_tokens": 2000
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=agent_data, 
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        agent = response.json()
        agent_id = agent["id"]
        
        # Create conversation
        conversation_data = {
            "title": "Anthropic Test",
            "agent_id": agent_id
        }
        
        response = await async_client.post(
            "/api/v1/conversations", 
            json=conversation_data, 
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        conversation_id = response.json()["id"]
        
        # Mock Anthropic response
        mock_anthropic_client.messages.create.return_value.content[0].text = "Hello! I'm Claude."
        mock_anthropic_client.messages.create.return_value.usage.input_tokens = 20
        mock_anthropic_client.messages.create.return_value.usage.output_tokens = 15
        
        # Send message
        message_data = {
            "content": "Hello, Claude!",
            "conversation_id": conversation_id
        }
        
        response = await async_client.post(
            "/api/v1/messages", 
            json=message_data, 
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify Anthropic client was called with correct parameters
        mock_anthropic_client.messages.create.assert_called()
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args[1]["model"] == "claude-3-sonnet-20240229"
        assert call_args[1]["max_tokens"] == 2000


class TestErrorHandlingAndRecovery:
    """Test error handling and system recovery scenarios."""

    async def test_ai_provider_failure_handling(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers,
        mock_openai_client
    ):
        """Test handling of AI provider failures."""
        
        # Setup agent and conversation
        agent_data = {
            "name": "Test Agent",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo"
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=agent_data, 
            headers=authenticated_user_headers
        )
        agent_id = response.json()["id"]
        
        conversation_data = {
            "title": "Error Test",
            "agent_id": agent_id
        }
        
        response = await async_client.post(
            "/api/v1/conversations", 
            json=conversation_data, 
            headers=authenticated_user_headers
        )
        conversation_id = response.json()["id"]
        
        # Mock AI provider failure
        from openai import RateLimitError
        mock_openai_client.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=None,
            body=None
        )
        
        # Send message that should trigger error
        message_data = {
            "content": "This should fail",
            "conversation_id": conversation_id
        }
        
        response = await async_client.post(
            "/api/v1/messages", 
            json=message_data, 
            headers=authenticated_user_headers
        )
        
        # Should handle error gracefully
        assert response.status_code in [status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_500_INTERNAL_SERVER_ERROR]
        
        # User message should still be saved
        response = await async_client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_200_OK
        messages = response.json()["items"]
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        assert len(user_messages) >= 1

    async def test_database_constraint_violations(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers
    ):
        """Test handling of database constraint violations."""
        
        # Try to create agent with invalid data
        invalid_agent_data = {
            "name": "",  # Empty name should fail validation
            "ai_provider": "invalid_provider",  # Invalid provider
            "model": ""
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=invalid_agent_data, 
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Verify error details
        error_details = response.json()
        assert "detail" in error_details
        
        # Try to create conversation without agent
        invalid_conversation_data = {
            "title": "Test",
            "agent_id": "00000000-0000-0000-0000-000000000000"  # Non-existent agent
        }
        
        response = await async_client.post(
            "/api/v1/conversations", 
            json=invalid_conversation_data, 
            headers=authenticated_user_headers
        )
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY]

    async def test_token_expiration_handling(
        self, 
        async_client: AsyncClient,
        db_session
    ):
        """Test handling of expired authentication tokens."""
        
        # Create user and get token
        user_data = {
            "email": "expiry@example.com",
            "password": "Password123!",
            "full_name": "Expiry User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        tokens = response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # Create a manually expired token (simulate passage of time)
        from app.core.security import create_access_token
        expired_token = create_access_token(
            user_data["email"], 
            expires_delta=timedelta(seconds=-1)  # Expired 1 second ago
        )
        
        # Try to use expired token
        expired_headers = {"Authorization": f"Bearer {expired_token}"}
        response = await async_client.get("/api/v1/agents", headers=expired_headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Test token refresh
        refresh_data = {"refresh_token": refresh_token}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == status.HTTP_200_OK
        
        new_tokens = response.json()
        new_access_token = new_tokens["access_token"]
        
        # New token should work
        new_headers = {"Authorization": f"Bearer {new_access_token}"}
        response = await async_client.get("/api/v1/agents", headers=new_headers)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
class TestStreamingAndRealTime:
    """Test streaming responses and real-time features."""

    async def test_streaming_message_response(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers,
        mock_openai_client
    ):
        """Test streaming AI responses."""
        
        # Setup agent and conversation
        agent_data = {
            "name": "Streaming Agent",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo",
            "stream": True
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=agent_data, 
            headers=authenticated_user_headers
        )
        agent_id = response.json()["id"]
        
        conversation_data = {
            "title": "Streaming Test",
            "agent_id": agent_id
        }
        
        response = await async_client.post(
            "/api/v1/conversations", 
            json=conversation_data, 
            headers=authenticated_user_headers
        )
        conversation_id = response.json()["id"]
        
        # Mock streaming response
        def mock_stream():
            chunks = [
                {"choices": [{"delta": {"content": "Hello"}}]},
                {"choices": [{"delta": {"content": " there!"}}]},
                {"choices": [{"delta": {}}]}  # End of stream
            ]
            for chunk in chunks:
                yield chunk
        
        mock_openai_client.chat.completions.create.return_value = mock_stream()
        
        # Send message with streaming
        message_data = {
            "content": "Hello!",
            "conversation_id": conversation_id,
            "stream": True
        }
        
        # Note: In a real implementation, this would be a WebSocket or SSE endpoint
        # For testing, we verify the streaming setup is configured correctly
        response = await async_client.post(
            "/api/v1/messages", 
            json=message_data, 
            headers=authenticated_user_headers
        )
        
        # Should succeed even with streaming enabled
        assert response.status_code == status.HTTP_201_CREATED