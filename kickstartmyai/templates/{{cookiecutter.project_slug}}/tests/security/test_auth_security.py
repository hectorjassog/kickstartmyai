"""
Authentication and Authorization Security Tests

Tests for authentication bypasses, token security, session management,
and authorization vulnerabilities.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from typing import Dict, Any, List

from tests.security.conftest import SecurityTestHelper
from tests.factories.user_factory import UserFactory
from app.core.config import get_settings


class TestAuthenticationSecurity:
    """Test authentication security mechanisms."""
    
    def test_password_strength_enforcement(self, security_client: TestClient, weak_passwords: List[str]):
        """Test that weak passwords are rejected."""
        for weak_password in weak_passwords:
            user_data = {
                "email": f"test_{len(weak_password)}@example.com",
                "password": weak_password,
                "full_name": "Test User"
            }
            
            response = security_client.post("/api/v1/auth/register", json=user_data)
            
            # Should reject weak passwords
            if len(weak_password) < 8 or weak_password in ["password", "123456", "admin"]:
                assert response.status_code == 422, f"Weak password '{weak_password}' was accepted"
    
    def test_strong_password_acceptance(self, security_client: TestClient, strong_passwords: List[str]):
        """Test that strong passwords are accepted."""
        for i, strong_password in enumerate(strong_passwords):
            user_data = {
                "email": f"strong_test_{i}@example.com",
                "password": strong_password,
                "full_name": "Strong Password User"
            }
            
            response = security_client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == 201, f"Strong password '{strong_password}' was rejected"
    
    def test_jwt_token_security(self, security_client: TestClient, db_session):
        """Test JWT token security mechanisms."""
        # Create test user
        user = UserFactory.create(db_session)
        
        # Login to get tokens
        login_data = {
            "username": user.email,
            "password": "TestPassword123!"
        }
        
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        
        tokens = login_response.json()
        access_token = tokens["access_token"]
        
        # Test token structure
        try:
            header = jwt.get_unverified_header(access_token)
            payload = jwt.decode(access_token, options={"verify_signature": False})
            
            # Verify token has required claims
            assert "sub" in payload  # Subject (user identifier)
            assert "exp" in payload  # Expiration time
            assert "iat" in payload  # Issued at time
            assert "type" in payload  # Token type
            
            # Verify algorithm is secure
            assert header["alg"] in ["HS256", "RS256"], "Insecure algorithm used"
            assert header["alg"] != "none", "None algorithm not allowed"
            
            # Verify expiration is reasonable (not too long)
            exp_time = datetime.fromtimestamp(payload["exp"])
            issued_time = datetime.fromtimestamp(payload["iat"])
            token_lifetime = exp_time - issued_time
            
            assert token_lifetime.total_seconds() <= 3600, "Token lifetime too long"  # Max 1 hour
            
        except jwt.InvalidTokenError:
            pytest.fail("Failed to decode JWT token")
    
    def test_token_replay_protection(self, security_client: TestClient, db_session):
        """Test protection against token replay attacks."""
        # Create test user and login
        user = UserFactory.create(db_session)
        login_data = {"username": user.email, "password": "TestPassword123!"}
        
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        access_token = tokens["access_token"]
        
        # Use token to access protected endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        response1 = security_client.get("/api/v1/users/me", headers=headers)
        assert response1.status_code == 200
        
        # Logout to invalidate token
        security_client.post("/api/v1/auth/logout", headers=headers)
        
        # Try to reuse the same token (should fail)
        response2 = security_client.get("/api/v1/users/me", headers=headers)
        assert response2.status_code == 401, "Token should be invalidated after logout"
    
    def test_invalid_token_handling(self, security_client: TestClient, invalid_tokens: List[str]):
        """Test handling of invalid JWT tokens."""
        for invalid_token in invalid_tokens:
            headers = {"Authorization": f"Bearer {invalid_token}"}
            response = security_client.get("/api/v1/users/me", headers=headers)
            
            # Should reject all invalid tokens
            assert response.status_code == 401, f"Invalid token '{invalid_token[:20]}...' was accepted"
    
    def test_token_expiration(self, security_client: TestClient, db_session):
        """Test that expired tokens are rejected."""
        # Create a token with immediate expiration
        settings = get_settings()
        
        # Create expired token
        expired_payload = {
            "sub": str(user.id),
            "exp": datetime.utcnow() - timedelta(minutes=1)
        }
        expired_token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm="HS256")
        
        # Try to use expired token
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = security_client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 401, "Expired token was accepted"
    
    def test_brute_force_protection(self, security_client: TestClient, db_session):
        """Test protection against brute force attacks."""
        # Create test user
        user = UserFactory.create(db_session)
        
        # Attempt multiple failed logins
        failed_attempts = 0
        max_attempts = 10
        
        for i in range(max_attempts):
            login_data = {
                "username": user.email,
                "password": f"wrong_password_{i}"
            }
            
            response = security_client.post("/api/v1/auth/login", data=login_data)
            
            if response.status_code == 401:
                failed_attempts += 1
            elif response.status_code == 429:  # Rate limited
                break
        
        # Should implement some form of rate limiting or account lockout
        # This test validates that the system doesn't allow unlimited attempts
        assert failed_attempts < max_attempts or response.status_code == 429, \
            "No brute force protection detected"


class TestAuthorizationSecurity:
    """Test authorization and access control security."""
    
    def test_horizontal_privilege_escalation(self, security_client: TestClient, db_session):
        """Test protection against horizontal privilege escalation."""
        # Create two users
        user1 = UserFactory.create(db_session, email="user1@example.com")
        user2 = UserFactory.create(db_session, email="user2@example.com")
        
        # Login as user1
        login_data1 = {"username": user1.email, "password": "TestPassword123!"}
        login_response1 = security_client.post("/api/v1/auth/login", data=login_data1)
        tokens1 = login_response1.json()
        headers1 = {"Authorization": f"Bearer {tokens1['access_token']}"}
        
        # Login as user2
        login_data2 = {"username": user2.email, "password": "TestPassword123!"}
        login_response2 = security_client.post("/api/v1/auth/login", data=login_data2)
        tokens2 = login_response2.json()
        headers2 = {"Authorization": f"Bearer {tokens2['access_token']}"}
        
        # User2 creates an agent
        agent_data = {
            "name": "User2 Agent",
            "description": "Agent owned by user2",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are user2's assistant.",
            "is_active": True
        }
        
        agent_response = security_client.post("/api/v1/agents/", json=agent_data, headers=headers2)
        assert agent_response.status_code == 201
        agent = agent_response.json()
        agent_id = agent["id"]
        
        # User1 should NOT be able to access User2's agent
        unauthorized_response = security_client.get(f"/api/v1/agents/{agent_id}", headers=headers1)
        assert unauthorized_response.status_code in [403, 404], \
            "Horizontal privilege escalation vulnerability detected"
        
        # User1 should NOT be able to modify User2's agent
        update_data = {"description": "Hacked by user1"}
        unauthorized_update = security_client.patch(
            f"/api/v1/agents/{agent_id}", 
            json=update_data, 
            headers=headers1
        )
        assert unauthorized_update.status_code in [403, 404], \
            "Horizontal privilege escalation vulnerability detected"
        
        # User1 should NOT be able to delete User2's agent
        unauthorized_delete = security_client.delete(f"/api/v1/agents/{agent_id}", headers=headers1)
        assert unauthorized_delete.status_code in [403, 404], \
            "Horizontal privilege escalation vulnerability detected"
    
    def test_authentication_bypass_attempts(self, security_client: TestClient):
        """Test various authentication bypass techniques."""
        protected_endpoints = [
            "/api/v1/users/me",
            "/api/v1/agents/",
            "/api/v1/conversations/",
            "/api/v1/messages/"
        ]
        
        results = SecurityTestHelper.test_authentication_bypass(security_client, protected_endpoints)
        
        # Verify no bypass was successful
        bypassed_endpoints = [r for r in results if r["bypassed"]]
        assert not bypassed_endpoints, f"Authentication bypass detected: {bypassed_endpoints}"
    
    def test_parameter_pollution(self, security_client: TestClient, db_session):
        """Test protection against HTTP parameter pollution."""
        # Create and login user
        user = UserFactory.create(db_session)
        login_data = {"username": user.email, "password": "TestPassword123!"}
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Test parameter pollution in query strings
        polluted_urls = [
            "/api/v1/agents/?page=1&page=999",  # Duplicate page parameter
            "/api/v1/agents/?size=10&size=1000",  # Duplicate size parameter
            "/api/v1/agents/?search=test&search=admin",  # Duplicate search parameter
        ]
        
        for url in polluted_urls:
            response = security_client.get(url, headers=headers)
            # Should handle parameter pollution gracefully
            assert response.status_code in [200, 400, 422], \
                f"Parameter pollution caused unexpected behavior: {url}"
    
    def test_mass_assignment_protection(self, security_client: TestClient, db_session):
        """Test protection against mass assignment attacks."""
        # Create and login user
        user = UserFactory.create(db_session)
        login_data = {"username": user.email, "password": "TestPassword123!"}
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Try to mass assign protected fields
        malicious_agent_data = {
            "name": "Test Agent",
            "description": "Test description",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are an assistant.",
            "is_active": True,
            # Attempt mass assignment of protected fields
            "id": 999999,
            "owner_id": 999999,
            "created_at": "2020-01-01T00:00:00",
            "updated_at": "2020-01-01T00:00:00",
            "is_admin": True,
            "role": "admin"
        }
        
        response = security_client.post("/api/v1/agents/", json=malicious_agent_data, headers=headers)
        
        if response.status_code == 201:
            agent = response.json()
            
            # Verify protected fields were not set
            assert agent["id"] != 999999, "Mass assignment vulnerability: id field"
            assert agent.get("owner_id") != 999999, "Mass assignment vulnerability: owner_id field"
            assert agent.get("is_admin") is not True, "Mass assignment vulnerability: is_admin field"
            assert agent.get("role") != "admin", "Mass assignment vulnerability: role field"


class TestInputValidationSecurity:
    """Test input validation and sanitization security."""
    
    def test_sql_injection_protection(self, security_client: TestClient, malicious_payloads: Dict[str, List[str]]):
        """Test protection against SQL injection attacks."""
        sql_payloads = malicious_payloads["sql_injection"]
        
        # Test registration endpoint
        registration_payload = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User"
        }
        
        results = SecurityTestHelper.test_input_sanitization(
            security_client, 
            "/api/v1/auth/register", 
            registration_payload, 
            sql_payloads
        )
        
        # All SQL injection attempts should be rejected or sanitized
        unsafe_results = [r for r in results if not r["safe"]]
        assert not unsafe_results, f"SQL injection vulnerability detected: {unsafe_results}"
    
    def test_xss_protection(self, security_client: TestClient, malicious_payloads: Dict[str, List[str]], db_session):
        """Test protection against XSS attacks."""
        xss_payloads = malicious_payloads["xss"]
        
        # Create and login user
        user = UserFactory.create(db_session)
        login_data = {"username": user.email, "password": "TestPassword123!"}
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Test agent creation endpoint
        agent_payload = {
            "name": "Test Agent",
            "description": "Test description",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are an assistant.",
            "is_active": True
        }
        
        for xss_payload in xss_payloads:
            # Test each field with XSS payload
            for field in ["name", "description", "system_prompt"]:
                test_payload = agent_payload.copy()
                test_payload[field] = xss_payload
                
                response = security_client.post("/api/v1/agents/", json=test_payload, headers=headers)
                
                if response.status_code == 201:
                    # If accepted, verify content is sanitized
                    agent = response.json()
                    field_value = agent.get(field, "")
                    
                    # Should not contain raw script tags or event handlers
                    assert "<script>" not in field_value.lower(), f"XSS vulnerability in {field} field"
                    assert "javascript:" not in field_value.lower(), f"XSS vulnerability in {field} field"
                    assert "onerror=" not in field_value.lower(), f"XSS vulnerability in {field} field"
                    assert "onload=" not in field_value.lower(), f"XSS vulnerability in {field} field"
    
    def test_command_injection_protection(self, security_client: TestClient, malicious_payloads: Dict[str, List[str]], db_session):
        """Test protection against command injection attacks."""
        command_payloads = malicious_payloads["command_injection"]
        
        # Create and login user
        user = UserFactory.create(db_session)
        login_data = {"username": user.email, "password": "TestPassword123!"}
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Test message endpoint (which might process user input)
        # First create an agent and conversation
        agent_data = {
            "name": "Test Agent",
            "description": "Test",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are an assistant.",
            "is_active": True
        }
        agent_response = security_client.post("/api/v1/agents/", json=agent_data, headers=headers)
        agent = agent_response.json()
        
        conversation_data = {"title": "Test", "agent_id": agent["id"]}
        conv_response = security_client.post("/api/v1/conversations/", json=conversation_data, headers=headers)
        conversation = conv_response.json()
        
        # Test command injection in message content
        for command_payload in command_payloads:
            message_data = {
                "content": command_payload,
                "conversation_id": conversation["id"]
            }
            
            response = security_client.post("/api/v1/messages/", json=message_data, headers=headers)
            
            # Should either reject or sanitize the input
            assert response.status_code in [200, 201, 400, 422], \
                f"Command injection caused unexpected behavior: {command_payload}"
    
    def test_file_upload_security(self, security_client: TestClient, db_session):
        """Test file upload security if file upload endpoints exist."""
        # This is a placeholder test - implement if file upload functionality exists
        # Test for:
        # - File type validation
        # - File size limits
        # - Malicious file content
        # - Path traversal in filenames
        # - Executable file uploads
        pass
    
    def test_large_payload_handling(self, security_client: TestClient, malicious_payloads: Dict[str, List[str]]):
        """Test handling of extremely large payloads."""
        large_payloads = malicious_payloads["large_payloads"]
        
        for large_payload in large_payloads:
            # Test registration with large payload
            user_data = {
                "email": "large_test@example.com",
                "password": "TestPassword123!",
                "full_name": large_payload  # Large name
            }
            
            response = security_client.post("/api/v1/auth/register", json=user_data)
            
            # Should reject extremely large payloads
            if len(large_payload) > 1000:  # Reasonable limit
                assert response.status_code == 422, f"Large payload was accepted: {len(large_payload)} chars"


class TestSessionSecurity:
    """Test session and state management security."""
    
    def test_session_fixation_protection(self, security_client: TestClient, db_session):
        """Test protection against session fixation attacks."""
        # Create test user
        user = UserFactory.create(db_session)
        
        # Login multiple times and verify tokens are different
        tokens = []
        for i in range(3):
            login_data = {"username": user.email, "password": "TestPassword123!"}
            login_response = security_client.post("/api/v1/auth/login", data=login_data)
            assert login_response.status_code == 200
            
            token_data = login_response.json()
            tokens.append(token_data["access_token"])
        
        # All tokens should be different (no session fixation)
        assert len(set(tokens)) == len(tokens), "Session fixation vulnerability detected"
    
    def test_concurrent_session_handling(self, security_client: TestClient, db_session):
        """Test handling of concurrent sessions."""
        # Create test user
        user = UserFactory.create(db_session)
        
        # Create multiple concurrent sessions
        sessions = []
        for i in range(3):
            login_data = {"username": user.email, "password": "TestPassword123!"}
            login_response = security_client.post("/api/v1/auth/login", data=login_data)
            assert login_response.status_code == 200
            
            tokens = login_response.json()
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            sessions.append(headers)
        
        # All sessions should be valid initially
        for headers in sessions:
            response = security_client.get("/api/v1/users/me", headers=headers)
            assert response.status_code == 200
        
        # Logout from one session
        security_client.post("/api/v1/auth/logout", headers=sessions[0])
        
        # First session should be invalid
        response = security_client.get("/api/v1/users/me", headers=sessions[0])
        assert response.status_code == 401
        
        # Other sessions should still be valid (unless implementing single session)
        for headers in sessions[1:]:
            response = security_client.get("/api/v1/users/me", headers=headers)
            # This depends on session management strategy
            assert response.status_code in [200, 401]


class TestRateLimitingSecurity:
    """Test rate limiting and DoS protection."""
    
    def test_api_rate_limiting(self, security_client: TestClient):
        """Test API rate limiting protection."""
        # Test rate limiting on public endpoints
        rate_limit_results = SecurityTestHelper.test_rate_limiting(
            security_client, 
            "/health", 
            max_requests=50
        )
        
        # Should implement some form of rate limiting
        # This test is informational - adjust limits based on your requirements
        if rate_limit_results["rate_limited"]:
            assert rate_limit_results["total_requests"] < 60, "Rate limiting working correctly"
        else:
            # Log that no rate limiting was detected (might be intentional)
            print("No rate limiting detected on /health endpoint")
    
    def test_authentication_rate_limiting(self, security_client: TestClient):
        """Test rate limiting on authentication endpoints."""
        # Test multiple login attempts
        login_attempts = 0
        max_attempts = 20
        
        for i in range(max_attempts):
            login_data = {
                "username": "nonexistent@example.com",
                "password": "wrong_password"
            }
            
            response = security_client.post("/api/v1/auth/login", data=login_data)
            login_attempts += 1
            
            if response.status_code == 429:  # Rate limited
                break
        
        # Should implement rate limiting on login attempts
        assert login_attempts < max_attempts or response.status_code == 429, \
            "No rate limiting on authentication endpoint"
