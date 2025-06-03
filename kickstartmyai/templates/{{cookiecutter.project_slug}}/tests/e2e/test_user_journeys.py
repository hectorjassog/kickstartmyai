"""
End-to-End User Journey Tests

Tests complete user workflows from registration to AI interactions.
These tests simulate real user behavior and validate the entire system.
"""
import asyncio
import pytest
import httpx
from typing import Dict, Any, List

from tests.e2e.conftest import E2ETestUser


class TestCompleteUserJourney:
    """Test complete user journeys from start to finish."""
    
    async def test_new_user_complete_journey(self, e2e_client: httpx.AsyncClient):
        """Test complete journey: register → login → create agent → chat → logout."""
        user = E2ETestUser(e2e_client)
        
        # Step 1: Register new user
        user_data = await user.register(
            email="journey-test@example.com",
            password="SecurePassword123!",
            full_name="Journey Test User"
        )
        assert user_data["email"] == "journey-test@example.com"
        assert user_data["full_name"] == "Journey Test User"
        assert "id" in user_data
        
        # Step 2: Login
        tokens = await user.login("SecurePassword123!")
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        
        # Step 3: Get user profile
        profile_response = await e2e_client.get("/api/v1/users/me")
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["email"] == "journey-test@example.com"
        
        # Step 4: Create an AI agent
        agent_data = {
            "name": "Journey Test Assistant",
            "description": "An AI assistant for testing the complete journey",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are a helpful AI assistant for testing purposes.",
            "is_active": True
        }
        
        agent_response = await e2e_client.post("/api/v1/agents/", json=agent_data)
        assert agent_response.status_code == 201
        agent = agent_response.json()
        assert agent["name"] == agent_data["name"]
        assert agent["provider"] == "openai"
        agent_id = agent["id"]
        
        # Step 5: Start a conversation with the agent
        conversation_data = {
            "title": "Test Conversation",
            "agent_id": agent_id
        }
        
        conversation_response = await e2e_client.post("/api/v1/conversations/", json=conversation_data)
        assert conversation_response.status_code == 201
        conversation = conversation_response.json()
        assert conversation["title"] == "Test Conversation"
        conversation_id = conversation["id"]
        
        # Step 6: Send a message to the AI
        message_data = {
            "content": "Hello! Can you help me test this system?",
            "conversation_id": conversation_id
        }
        
        # Note: In E2E testing, we might want to mock AI responses
        # to avoid actual API calls and costs
        message_response = await e2e_client.post("/api/v1/messages/", json=message_data)
        assert message_response.status_code == 201
        message = message_response.json()
        assert message["content"] == message_data["content"]
        assert message["role"] == "user"
        
        # Step 7: Get conversation history
        history_response = await e2e_client.get(f"/api/v1/conversations/{conversation_id}/messages")
        assert history_response.status_code == 200
        messages = history_response.json()["items"]
        assert len(messages) >= 1
        assert any(msg["content"] == message_data["content"] for msg in messages)
        
        # Step 8: List user's agents
        agents_response = await e2e_client.get("/api/v1/agents/")
        assert agents_response.status_code == 200
        agents = agents_response.json()["items"]
        assert len(agents) >= 1
        assert any(agent["name"] == agent_data["name"] for agent in agents)
        
        # Step 9: Update agent
        update_data = {"description": "Updated description for testing"}
        update_response = await e2e_client.patch(f"/api/v1/agents/{agent_id}", json=update_data)
        assert update_response.status_code == 200
        updated_agent = update_response.json()
        assert updated_agent["description"] == update_data["description"]
        
        # Step 10: Logout
        logout_response = await e2e_client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200
        
        # Step 11: Verify logout (should fail to access protected endpoint)
        protected_response = await e2e_client.get("/api/v1/users/me")
        assert protected_response.status_code == 401
    
    async def test_multi_user_isolation(self, e2e_client: httpx.AsyncClient):
        """Test that multiple users' data is properly isolated."""
        # Create two users
        user1 = E2ETestUser(e2e_client)
        user2 = E2ETestUser(httpx.AsyncClient(base_url=e2e_client.base_url))
        
        # Register and login both users
        await user1.register("user1@example.com", "Password123!", "User One")
        await user1.login("Password123!")
        
        await user2.register("user2@example.com", "Password123!", "User Two")
        await user2.login("Password123!")
        
        # User 1 creates an agent
        agent_data = {
            "name": "User 1 Agent",
            "description": "Agent for user 1",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are user 1's assistant.",
            "is_active": True
        }
        
        agent_response = await user1.client.post("/api/v1/agents/", json=agent_data)
        assert agent_response.status_code == 201
        user1_agent = agent_response.json()
        
        # User 2 creates an agent
        agent_data["name"] = "User 2 Agent"
        agent_data["description"] = "Agent for user 2"
        agent_data["system_prompt"] = "You are user 2's assistant."
        
        agent_response = await user2.client.post("/api/v1/agents/", json=agent_data)
        assert agent_response.status_code == 201
        user2_agent = agent_response.json()
        
        # User 1 should only see their agent
        user1_agents_response = await user1.client.get("/api/v1/agents/")
        assert user1_agents_response.status_code == 200
        user1_agents = user1_agents_response.json()["items"]
        assert len(user1_agents) == 1
        assert user1_agents[0]["id"] == user1_agent["id"]
        
        # User 2 should only see their agent
        user2_agents_response = await user2.client.get("/api/v1/agents/")
        assert user2_agents_response.status_code == 200
        user2_agents = user2_agents_response.json()["items"]
        assert len(user2_agents) == 1
        assert user2_agents[0]["id"] == user2_agent["id"]
        
        # User 1 should not be able to access User 2's agent
        forbidden_response = await user1.client.get(f"/api/v1/agents/{user2_agent['id']}")
        assert forbidden_response.status_code == 404  # Not found (due to filtering)
        
        # User 2 should not be able to access User 1's agent
        forbidden_response = await user2.client.get(f"/api/v1/agents/{user1_agent['id']}")
        assert forbidden_response.status_code == 404  # Not found (due to filtering)
        
        # Cleanup
        await user1.logout()
        await user2.logout()
    
    async def test_session_management(self, e2e_client: httpx.AsyncClient):
        """Test session management including token refresh and expiration."""
        user = E2ETestUser(e2e_client)
        
        # Register and login
        await user.register("session-test@example.com", "Password123!", "Session Test")
        tokens = await user.login("Password123!")
        
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # Test access with valid token
        profile_response = await e2e_client.get("/api/v1/users/me")
        assert profile_response.status_code == 200
        
        # Test token refresh
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = await e2e_client.post("/api/v1/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == 200
        
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert new_tokens["access_token"] != access_token  # Should be different
        
        # Update client with new token
        new_access_token = new_tokens["access_token"]
        e2e_client.headers.update({"Authorization": f"Bearer {new_access_token}"})
        
        # Test access with new token
        profile_response = await e2e_client.get("/api/v1/users/me")
        assert profile_response.status_code == 200
        
        # Test logout invalidates tokens
        await user.logout()
        
        # Should not be able to access protected endpoints
        protected_response = await e2e_client.get("/api/v1/users/me")
        assert protected_response.status_code == 401
    
    async def test_error_handling_and_recovery(self, e2e_client: httpx.AsyncClient):
        """Test error handling and recovery scenarios."""
        user = E2ETestUser(e2e_client)
        
        # Test registration with invalid data
        invalid_user_data = {
            "email": "invalid-email",  # Invalid email format
            "password": "weak",  # Weak password
            "full_name": ""  # Empty name
        }
        
        invalid_response = await e2e_client.post("/api/v1/auth/register", json=invalid_user_data)
        assert invalid_response.status_code == 422  # Validation error
        
        # Test login with non-existent user
        login_data = {
            "username": "nonexistent@example.com",
            "password": "SomePassword123!"
        }
        
        login_response = await e2e_client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 401  # Unauthorized
        
        # Register valid user
        await user.register("recovery-test@example.com", "Password123!", "Recovery Test")
        await user.login("Password123!")
        
        # Test creating agent with invalid data
        invalid_agent_data = {
            "name": "",  # Empty name
            "provider": "invalid_provider",  # Invalid provider
            "model": "",  # Empty model
        }
        
        invalid_agent_response = await e2e_client.post("/api/v1/agents/", json=invalid_agent_data)
        assert invalid_agent_response.status_code == 422  # Validation error
        
        # Test accessing non-existent resources
        not_found_response = await e2e_client.get("/api/v1/agents/99999")
        assert not_found_response.status_code == 404
        
        # Test that user can still perform valid operations after errors
        valid_agent_data = {
            "name": "Recovery Test Agent",
            "description": "Testing error recovery",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are a recovery test assistant.",
            "is_active": True
        }
        
        valid_response = await e2e_client.post("/api/v1/agents/", json=valid_agent_data)
        assert valid_response.status_code == 201
        
        await user.logout()
    
    async def test_concurrent_operations(self, e2e_client: httpx.AsyncClient):
        """Test concurrent operations by the same user."""
        user = E2ETestUser(e2e_client)
        
        # Register and login
        await user.register("concurrent-test@example.com", "Password123!", "Concurrent Test")
        await user.login("Password123!")
        
        # Create multiple agents concurrently
        agent_tasks = []
        for i in range(5):
            agent_data = {
                "name": f"Concurrent Agent {i}",
                "description": f"Agent {i} for concurrent testing",
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "system_prompt": f"You are agent {i}.",
                "is_active": True
            }
            
            task = e2e_client.post("/api/v1/agents/", json=agent_data)
            agent_tasks.append(task)
        
        # Execute all agent creation tasks concurrently
        responses = await asyncio.gather(*agent_tasks)
        
        # Verify all agents were created successfully
        for response in responses:
            assert response.status_code == 201
        
        # Verify all agents exist
        agents_response = await e2e_client.get("/api/v1/agents/")
        assert agents_response.status_code == 200
        agents = agents_response.json()["items"]
        assert len(agents) == 5
        
        # Create conversations with each agent concurrently
        conversation_tasks = []
        for i, agent in enumerate(agents):
            conversation_data = {
                "title": f"Concurrent Conversation {i}",
                "agent_id": agent["id"]
            }
            
            task = e2e_client.post("/api/v1/conversations/", json=conversation_data)
            conversation_tasks.append(task)
        
        # Execute all conversation creation tasks concurrently
        conversation_responses = await asyncio.gather(*conversation_tasks)
        
        # Verify all conversations were created successfully
        for response in conversation_responses:
            assert response.status_code == 201
        
        await user.logout()


class TestUserExperience:
    """Test user experience aspects."""
    
    async def test_responsive_api_performance(self, e2e_client: httpx.AsyncClient):
        """Test that API endpoints respond within acceptable time limits."""
        import time
        
        user = E2ETestUser(e2e_client)
        await user.register("perf-test@example.com", "Password123!", "Performance Test")
        await user.login("Password123!")
        
        # Test health endpoint performance
        start_time = time.time()
        health_response = await e2e_client.get("/health")
        health_time = time.time() - start_time
        
        assert health_response.status_code == 200
        assert health_time < 1.0  # Should respond within 1 second
        
        # Test user profile endpoint performance
        start_time = time.time()
        profile_response = await e2e_client.get("/api/v1/users/me")
        profile_time = time.time() - start_time
        
        assert profile_response.status_code == 200
        assert profile_time < 2.0  # Should respond within 2 seconds
        
        # Test agent creation performance
        agent_data = {
            "name": "Performance Test Agent",
            "description": "Testing performance",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are a performance test assistant.",
            "is_active": True
        }
        
        start_time = time.time()
        agent_response = await e2e_client.post("/api/v1/agents/", json=agent_data)
        agent_time = time.time() - start_time
        
        assert agent_response.status_code == 201
        assert agent_time < 3.0  # Should respond within 3 seconds
        
        await user.logout()
    
    async def test_pagination_and_search(self, e2e_client: httpx.AsyncClient):
        """Test pagination and search functionality."""
        user = E2ETestUser(e2e_client)
        await user.register("pagination-test@example.com", "Password123!", "Pagination Test")
        await user.login("Password123!")
        
        # Create multiple agents for pagination testing
        agents = []
        for i in range(15):  # Create more than default page size
            agent_data = {
                "name": f"Pagination Agent {i:02d}",
                "description": f"Agent {i} for pagination testing",
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "system_prompt": f"You are pagination agent {i}.",
                "is_active": True
            }
            
            response = await e2e_client.post("/api/v1/agents/", json=agent_data)
            assert response.status_code == 201
            agents.append(response.json())
        
        # Test pagination
        page1_response = await e2e_client.get("/api/v1/agents/?page=1&size=10")
        assert page1_response.status_code == 200
        page1_data = page1_response.json()
        assert len(page1_data["items"]) == 10
        assert page1_data["total"] == 15
        assert page1_data["page"] == 1
        
        page2_response = await e2e_client.get("/api/v1/agents/?page=2&size=10")
        assert page2_response.status_code == 200
        page2_data = page2_response.json()
        assert len(page2_data["items"]) == 5  # Remaining items
        assert page2_data["page"] == 2
        
        # Test search/filtering
        search_response = await e2e_client.get("/api/v1/agents/?search=Agent 01")
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert len(search_data["items"]) >= 1
        assert any("Agent 01" in agent["name"] for agent in search_data["items"])
        
        await user.logout()


class TestDataConsistency:
    """Test data consistency and integrity."""
    
    async def test_referential_integrity(self, e2e_client: httpx.AsyncClient):
        """Test referential integrity between related entities."""
        user = E2ETestUser(e2e_client)
        await user.register("integrity-test@example.com", "Password123!", "Integrity Test")
        await user.login("Password123!")
        
        # Create agent
        agent_data = {
            "name": "Integrity Test Agent",
            "description": "Testing referential integrity",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are an integrity test assistant.",
            "is_active": True
        }
        
        agent_response = await e2e_client.post("/api/v1/agents/", json=agent_data)
        assert agent_response.status_code == 201
        agent = agent_response.json()
        agent_id = agent["id"]
        
        # Create conversation
        conversation_data = {
            "title": "Integrity Test Conversation",
            "agent_id": agent_id
        }
        
        conversation_response = await e2e_client.post("/api/v1/conversations/", json=conversation_data)
        assert conversation_response.status_code == 201
        conversation = conversation_response.json()
        conversation_id = conversation["id"]
        
        # Create message
        message_data = {
            "content": "Test message for integrity",
            "conversation_id": conversation_id
        }
        
        message_response = await e2e_client.post("/api/v1/messages/", json=message_data)
        assert message_response.status_code == 201
        message = message_response.json()
        
        # Verify relationships
        # Get conversation and verify agent relationship
        conv_detail_response = await e2e_client.get(f"/api/v1/conversations/{conversation_id}")
        assert conv_detail_response.status_code == 200
        conv_detail = conv_detail_response.json()
        assert conv_detail["agent_id"] == agent_id
        
        # Get messages and verify conversation relationship
        messages_response = await e2e_client.get(f"/api/v1/conversations/{conversation_id}/messages")
        assert messages_response.status_code == 200
        messages = messages_response.json()["items"]
        assert len(messages) >= 1
        assert any(msg["conversation_id"] == conversation_id for msg in messages)
        
        # Try to create conversation with non-existent agent (should fail)
        invalid_conversation_data = {
            "title": "Invalid Conversation",
            "agent_id": 99999  # Non-existent agent
        }
        
        invalid_response = await e2e_client.post("/api/v1/conversations/", json=invalid_conversation_data)
        assert invalid_response.status_code in [400, 422]  # Should fail validation
        
        await user.logout()
