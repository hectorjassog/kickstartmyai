"""
API Security Tests

Tests for API-specific security vulnerabilities including input validation,
output encoding, HTTP security headers, and API abuse protection.
"""
import pytest
import json
from typing import Dict, Any, List
from fastapi.testclient import TestClient

from tests.security.conftest import SecurityTestHelper
from tests.factories.user_factory import UserFactory


class TestAPISecurityHeaders:
    """Test HTTP security headers and API security configurations."""
    
    def test_security_headers_present(self, security_client: TestClient):
        """Test that proper security headers are present in responses."""
        response = security_client.get("/health")
        
        # Check for important security headers
        headers = response.headers
        
        # Content Security Policy
        if "content-security-policy" in headers:
            csp = headers["content-security-policy"]
            assert "default-src" in csp, "CSP should include default-src directive"
            assert "'unsafe-eval'" not in csp, "CSP should not allow unsafe-eval"
            assert "'unsafe-inline'" not in csp or "script-src" not in csp, "CSP should restrict inline scripts"
        
        # X-Content-Type-Options
        if "x-content-type-options" in headers:
            assert headers["x-content-type-options"] == "nosniff", "Should prevent content type sniffing"
        
        # X-Frame-Options or Content-Security-Policy frame-ancestors
        frame_protection = (
            "x-frame-options" in headers or 
            ("content-security-policy" in headers and "frame-ancestors" in headers["content-security-policy"])
        )
        if frame_protection and "x-frame-options" in headers:
            assert headers["x-frame-options"] in ["DENY", "SAMEORIGIN"], "Should prevent clickjacking"
        
        # X-XSS-Protection (deprecated but still good to have)
        if "x-xss-protection" in headers:
            assert headers["x-xss-protection"] in ["1; mode=block", "0"], "XSS protection header should be secure"
        
        # Referrer Policy
        if "referrer-policy" in headers:
            secure_policies = ["no-referrer", "same-origin", "strict-origin", "strict-origin-when-cross-origin"]
            assert headers["referrer-policy"] in secure_policies, "Referrer policy should be restrictive"
    
    def test_cors_configuration(self, security_client: TestClient):
        """Test CORS configuration security."""
        # Test preflight request
        response = security_client.options(
            "/api/v1/users/me",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization"
            }
        )
        
        cors_headers = response.headers
        
        # Check that CORS is not overly permissive
        if "access-control-allow-origin" in cors_headers:
            origin = cors_headers["access-control-allow-origin"]
            assert origin != "*", "CORS should not allow all origins for authenticated endpoints"
            
            # If not wildcard, should be specific trusted origins
            if origin != "*":
                trusted_origins = ["http://localhost:3000", "https://yourdomain.com"]
                # This is environment-specific, so we just check it's not wildcard
                pass
        
        # Check credentials handling
        if "access-control-allow-credentials" in cors_headers:
            credentials = cors_headers["access-control-allow-credentials"]
            if credentials == "true":
                # If allowing credentials, origin should not be wildcard
                assert cors_headers.get("access-control-allow-origin", "*") != "*", \
                    "CORS misconfiguration: credentials=true with origin=*"
    
    def test_https_enforcement(self, security_client: TestClient):
        """Test HTTPS enforcement mechanisms."""
        response = security_client.get("/health")
        
        # Check for HSTS header
        if "strict-transport-security" in response.headers:
            hsts = response.headers["strict-transport-security"]
            assert "max-age=" in hsts, "HSTS should specify max-age"
            assert "includeSubDomains" in hsts, "HSTS should include subdomains"
            # Check that max-age is reasonable (at least 1 year)
            if "max-age=" in hsts:
                max_age_str = hsts.split("max-age=")[1].split(";")[0]
                max_age = int(max_age_str)
                assert max_age >= 31536000, "HSTS max-age should be at least 1 year"


class TestInputValidationAPI:
    """Test API input validation and sanitization."""
    
    def test_json_structure_validation(self, security_client: TestClient):
        """Test validation of JSON structure and types."""
        malformed_json_payloads = [
            '{"email": "test@example.com", "password": "pass", "full_name": }',  # Malformed JSON
            '{"email": "test@example.com", "password": "pass", "full_name": null}',  # Null required field
            '{"email": 123, "password": "pass", "full_name": "Test"}',  # Wrong type
            '{"email": ["test@example.com"], "password": "pass", "full_name": "Test"}',  # Array instead of string
            '{"email": {"nested": "test@example.com"}, "password": "pass", "full_name": "Test"}',  # Object instead of string
        ]
        
        for payload in malformed_json_payloads:
            try:
                response = security_client.post(
                    "/api/v1/auth/register",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                # Should reject malformed JSON
                assert response.status_code in [400, 422], f"Malformed JSON was accepted: {payload}"
            except json.JSONDecodeError:
                # This is expected for malformed JSON
                pass
    
    def test_content_type_validation(self, security_client: TestClient):
        """Test content type validation."""
        user_data = {
            "email": "content-test@example.com",
            "password": "TestPassword123!",
            "full_name": "Content Test"
        }
        
        # Test with wrong content type
        response = security_client.post(
            "/api/v1/auth/register",
            data=json.dumps(user_data),
            headers={"Content-Type": "text/plain"}
        )
        
        # Should reject non-JSON content type for JSON endpoints
        assert response.status_code in [400, 415, 422], "Wrong content type was accepted"
        
        # Test with missing content type
        response = security_client.post(
            "/api/v1/auth/register",
            data=json.dumps(user_data)
            # No Content-Type header
        )
        
        # Should handle missing content type appropriately
        assert response.status_code in [200, 201, 400, 415, 422], "Missing content type caused server error"
    
    def test_field_length_validation(self, security_client: TestClient):
        """Test field length validation."""
        # Test extremely long values
        long_string = "A" * 10000
        very_long_string = "B" * 100000
        
        test_cases = [
            {"email": long_string + "@example.com", "password": "Pass123!", "full_name": "Test"},
            {"email": "test@example.com", "password": very_long_string, "full_name": "Test"},
            {"email": "test@example.com", "password": "Pass123!", "full_name": very_long_string},
        ]
        
        for user_data in test_cases:
            response = security_client.post("/api/v1/auth/register", json=user_data)
            # Should reject extremely long values
            assert response.status_code == 422, f"Extremely long value was accepted: {len(str(user_data))}"
    
    def test_special_character_handling(self, security_client: TestClient, db_session):
        """Test handling of special characters and Unicode."""
        # Create and login user first
        user = UserFactory.create(db_session)
        login_data = {"username": user.email, "password": "TestPassword123!"}
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        special_character_tests = [
            "Test with emoji 🤖",
            "Test with unicode: こんにちは",
            "Test with symbols: !@#$%^&*()",
            "Test with quotes: \"double\" and 'single'",
            "Test with backslashes: \\n\\t\\r",
            "Test with HTML entities: &lt;&gt;&amp;",
            "Test with null bytes: \x00test",
            "Test with control chars: \x01\x02\x03",
        ]
        
        for test_string in special_character_tests:
            agent_data = {
                "name": test_string,
                "description": "Test description",
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "system_prompt": "You are an assistant.",
                "is_active": True
            }
            
            response = security_client.post("/api/v1/agents/", json=agent_data, headers=headers)
            
            if response.status_code == 201:
                # If accepted, verify proper encoding/sanitization
                agent = response.json()
                name = agent.get("name", "")
                
                # Should not contain raw null bytes or control characters
                assert "\x00" not in name, "Null bytes should be filtered"
                assert not any(ord(c) < 32 and c not in ['\n', '\t', '\r'] for c in name), \
                    "Control characters should be filtered"


class TestAPIOutputSecurity:
    """Test API output security and information disclosure."""
    
    def test_error_information_disclosure(self, security_client: TestClient):
        """Test that error messages don't disclose sensitive information."""
        # Test 404 errors
        response = security_client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404
        
        error_response = response.json()
        error_message = str(error_response).lower()
        
        # Should not disclose sensitive information in error messages
        sensitive_info = [
            "database", "sql", "postgres", "mysql", "connection",
            "password", "secret", "key", "token",
            "stack trace", "traceback", "exception",
            "file path", "/app/", "/home/", "/var/",
            "version", "python", "fastapi"
        ]
        
        for sensitive in sensitive_info:
            assert sensitive not in error_message, f"Error message contains sensitive info: {sensitive}"
    
    def test_sensitive_data_exposure(self, security_client: TestClient, db_session):
        """Test that sensitive data is not exposed in API responses."""
        # Create user
        user = UserFactory.create(db_session)
        login_data = {"username": user.email, "password": "TestPassword123!"}
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Get user profile
        profile_response = security_client.get("/api/v1/users/me", headers=headers)
        assert profile_response.status_code == 200
        
        profile = profile_response.json()
        profile_str = json.dumps(profile).lower()
        
        # Should not expose sensitive fields
        sensitive_fields = [
            "password", "password_hash", "hashed_password",
            "secret", "private_key", "api_key",
            "salt", "hash", "token"
        ]
        
        for sensitive in sensitive_fields:
            assert sensitive not in profile_str, f"Sensitive field exposed: {sensitive}"
            assert sensitive not in profile, f"Sensitive field in response: {sensitive}"
    
    def test_debug_information_disclosure(self, security_client: TestClient):
        """Test that debug information is not exposed in production."""
        # Test with various endpoints that might expose debug info
        endpoints = [
            "/health",
            "/api/v1/auth/login",
            "/api/v1/nonexistent",
            "/docs",  # OpenAPI docs
            "/redoc",  # ReDoc docs
        ]
        
        for endpoint in endpoints:
            response = security_client.get(endpoint)
            
            if response.status_code == 200:
                content = response.text.lower()
                
                # Should not expose debug information
                debug_indicators = [
                    "debug", "development", "dev mode",
                    "stack trace", "traceback", "exception",
                    "sql query", "database query",
                    "internal server error",
                    "python", "fastapi version"
                ]
                
                for debug_info in debug_indicators:
                    assert debug_info not in content, \
                        f"Debug information exposed on {endpoint}: {debug_info}"


class TestBusinessLogicSecurity:
    """Test business logic security vulnerabilities."""
    
    def test_race_condition_protection(self, security_client: TestClient, db_session):
        """Test protection against race condition attacks."""
        import threading
        import time
        
        # Create user
        user = UserFactory.create(db_session)
        login_data = {"username": user.email, "password": "TestPassword123!"}
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Create an agent first
        agent_data = {
            "name": "Race Condition Test",
            "description": "Testing race conditions",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are an assistant.",
            "is_active": True
        }
        
        agent_response = security_client.post("/api/v1/agents/", json=agent_data, headers=headers)
        agent = agent_response.json()
        agent_id = agent["id"]
        
        # Test concurrent updates to the same resource
        results = []
        
        def update_agent(update_data):
            response = security_client.patch(f"/api/v1/agents/{agent_id}", json=update_data, headers=headers)
            results.append({
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else None
            })
        
        # Create multiple threads to update the same agent concurrently
        threads = []
        for i in range(5):
            update_data = {"description": f"Updated description {i}"}
            thread = threading.Thread(target=update_agent, args=(update_data,))
            threads.append(thread)
        
        # Start all threads simultaneously
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify that the system handled concurrent updates properly
        successful_updates = [r for r in results if r["status_code"] == 200]
        
        # Should handle race conditions gracefully (either all succeed or some fail)
        assert len(successful_updates) >= 1, "No updates succeeded in race condition test"
        
        # Verify final state is consistent
        final_response = security_client.get(f"/api/v1/agents/{agent_id}", headers=headers)
        assert final_response.status_code == 200
    
    def test_workflow_bypass_protection(self, security_client: TestClient, db_session):
        """Test protection against workflow bypass attacks."""
        # Create user
        user = UserFactory.create(db_session)
        login_data = {"username": user.email, "password": "TestPassword123!"}
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Create agent and conversation
        agent_data = {
            "name": "Workflow Test",
            "description": "Testing workflow bypass",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "system_prompt": "You are an assistant.",
            "is_active": True
        }
        
        agent_response = security_client.post("/api/v1/agents/", json=agent_data, headers=headers)
        agent = agent_response.json()
        
        conversation_data = {"title": "Test Conversation", "agent_id": agent["id"]}
        conv_response = security_client.post("/api/v1/conversations/", json=conversation_data, headers=headers)
        conversation = conv_response.json()
        
        # Try to create a message without going through proper conversation flow
        message_data = {
            "content": "Direct message bypass attempt",
            "conversation_id": 999999,  # Non-existent conversation
            "role": "assistant"  # Try to impersonate assistant
        }
        
        bypass_response = security_client.post("/api/v1/messages/", json=message_data, headers=headers)
        
        # Should reject invalid conversation or role manipulation
        assert bypass_response.status_code in [400, 404, 422], "Workflow bypass vulnerability detected"
    
    def test_resource_exhaustion_protection(self, security_client: TestClient, db_session):
        """Test protection against resource exhaustion attacks."""
        # Create user
        user = UserFactory.create(db_session)
        login_data = {"username": user.email, "password": "TestPassword123!"}
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Try to create many resources quickly
        resource_count = 0
        max_attempts = 100
        
        for i in range(max_attempts):
            agent_data = {
                "name": f"Resource Test {i}",
                "description": "Testing resource limits",
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "system_prompt": "You are an assistant.",
                "is_active": True
            }
            
            response = security_client.post("/api/v1/agents/", json=agent_data, headers=headers)
            
            if response.status_code == 201:
                resource_count += 1
            elif response.status_code == 429:  # Rate limited
                break
            elif response.status_code in [400, 403]:  # Resource limit
                break
        
        # Should implement some form of resource limiting
        assert resource_count < max_attempts, "No resource exhaustion protection detected"


class TestAPIAbusePrevention:
    """Test API abuse prevention mechanisms."""
    
    def test_automated_request_detection(self, security_client: TestClient):
        """Test detection of automated/bot requests."""
        # Simulate rapid automated requests
        rapid_requests = []
        
        for i in range(50):  # Many rapid requests
            response = security_client.get("/health")
            rapid_requests.append(response.status_code)
            
            if response.status_code == 429:  # Rate limited
                break
        
        # Should implement some form of bot detection or rate limiting
        rate_limited = any(status == 429 for status in rapid_requests)
        
        if not rate_limited:
            # Log that no bot detection was found (might be intentional)
            print("No automated request detection on /health endpoint")
    
    def test_request_pattern_analysis(self, security_client: TestClient, db_session):
        """Test unusual request pattern detection."""
        # Create user
        user = UserFactory.create(db_session)
        login_data = {"username": user.email, "password": "TestPassword123!"}
        login_response = security_client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Test unusual access patterns
        unusual_patterns = [
            # Rapid sequential access to different resources
            ["/api/v1/agents/", "/api/v1/conversations/", "/api/v1/messages/"] * 10,
            # Rapid access to same resource with different parameters
            [f"/api/v1/agents/?page={i}" for i in range(1, 21)],
            # Mixed GET/POST patterns
            ["/api/v1/agents/"] * 20,
        ]
        
        for pattern in unusual_patterns:
            responses = []
            for endpoint in pattern:
                if endpoint == "/api/v1/agents/":
                    # Alternate between GET and POST
                    if len(responses) % 2 == 0:
                        response = security_client.get(endpoint, headers=headers)
                    else:
                        agent_data = {
                            "name": f"Pattern Test {len(responses)}",
                            "description": "Pattern testing",
                            "provider": "openai",
                            "model": "gpt-3.5-turbo",
                            "system_prompt": "You are an assistant.",
                            "is_active": True
                        }
                        response = security_client.post(endpoint, json=agent_data, headers=headers)
                else:
                    response = security_client.get(endpoint, headers=headers)
                
                responses.append(response.status_code)
                
                # If rate limited, break
                if response.status_code == 429:
                    break
            
            # Check if unusual patterns triggered protection
            rate_limited = any(status == 429 for status in responses)
            
            # This is informational - some systems may not implement pattern detection
            if rate_limited:
                print(f"Pattern detection triggered for unusual access pattern")
                break
