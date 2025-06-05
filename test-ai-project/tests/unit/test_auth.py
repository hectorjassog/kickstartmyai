"""
Unit tests for authentication system.

Tests JWT token management, password security, and authentication workflows
to ensure secure user authentication and authorization.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt

from app.core.security.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
)
from app.core.security.password import (
    get_password_hash,
    verify_password,
    is_password_strong,
)
from app.api import deps
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidTokenError,
    TokenExpiredError,
)
from app.models.user import User


class TestJWTHandler:
    """Test JWT token creation, verification, and decoding."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode to verify contents
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_access_token_with_expiry(self):
        """Test access token creation with custom expiry."""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        # Check expiry is approximately 30 minutes from now
        exp = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + expires_delta
        assert abs((exp - expected_exp).total_seconds()) < 5  # Allow 5 second tolerance

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user123"}
        token = create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"
        
        payload = verify_token(invalid_token)
        
        assert payload is None

    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        data = {"sub": "user123"}
        # Create token that expires in the past
        past_time = datetime.utcnow() - timedelta(minutes=1)
        expired_token = jwt.encode(
            {**data, "exp": past_time, "type": "access"},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        payload = verify_token(expired_token)
        
        assert payload is None

    def test_decode_token_valid(self):
        """Test token decoding with valid token."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        payload = decode_token(token)
        
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_decode_token_expired(self):
        """Test token decoding with expired token."""
        data = {"sub": "user123"}
        past_time = datetime.utcnow() - timedelta(minutes=1)
        expired_token = jwt.encode(
            {**data, "exp": past_time, "type": "access"},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(expired_token)

    def test_decode_token_invalid(self):
        """Test token decoding with invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(jwt.PyJWTError):
            decode_token(invalid_token)

    def test_decode_token_wrong_secret(self):
        """Test token decoding with wrong secret key."""
        data = {"sub": "user123"}
        wrong_token = jwt.encode(data, "wrong-secret", algorithm="HS256")
        
        with pytest.raises(jwt.InvalidSignatureError):
            decode_token(wrong_token)


class TestPasswordSecurity:
    """Test password hashing and verification."""

    def test_password_hashing(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        # Hash should be different from original password
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt format

    def test_password_verification_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True

    def test_password_verification_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False

    def test_password_hashing_different_results(self):
        """Test that same password generates different hashes."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify the password
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_password_strength_weak(self):
        """Test password strength validation with weak passwords."""
        weak_passwords = [
            "123",           # Too short
            "password",      # No numbers/symbols
            "12345678",      # Only numbers
            "PASSWORD",      # Only uppercase
            "password123",   # Common pattern
        ]
        
        for password in weak_passwords:
            is_strong, errors = is_password_strong(password)
            assert is_strong is False
            assert len(errors) > 0

    def test_password_strength_strong(self):
        """Test password strength validation with strong passwords."""
        strong_passwords = [
            "MyStr0ng!Password",
            "C0mpl3x#P@ssw0rd",
            "Secure$Pass123",
        ]
        
        for password in strong_passwords:
            is_strong, errors = is_password_strong(password)
            assert is_strong is True
            assert len(errors) == 0


class TestAuthenticationDependencies:
    """Test FastAPI authentication dependencies."""

    @pytest.mark.asyncio
    async def test_decode_token_dependency(self):
        """Test decode_token dependency function."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        payload = deps.decode_token(token)
        
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_decode_token_dependency_expired(self):
        """Test decode_token dependency with expired token."""
        data = {"sub": "user123"}
        past_time = datetime.utcnow() - timedelta(minutes=1)
        expired_token = jwt.encode(
            {**data, "exp": past_time, "type": "access"},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        with pytest.raises(TokenExpiredError):
            deps.decode_token(expired_token)

    @pytest.mark.asyncio
    async def test_decode_token_dependency_invalid(self):
        """Test decode_token dependency with invalid token."""
        with pytest.raises(InvalidTokenError):
            deps.decode_token("invalid.token")

    @pytest.mark.asyncio
    async def test_get_current_user_token(self):
        """Test get_current_user_token dependency."""
        data = {"sub": "user123"}
        token = create_access_token(data)
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        payload = await deps.get_current_user_token(credentials)
        
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"

    @pytest.mark.asyncio
    async def test_get_current_user_token_no_credentials(self):
        """Test get_current_user_token with no credentials."""
        with pytest.raises(AuthenticationError):
            await deps.get_current_user_token(None)

    @pytest.mark.asyncio
    async def test_get_current_user(self, db_session, test_user):
        """Test get_current_user dependency."""
        token_data = {"sub": str(test_user.id)}
        
        with patch('app.crud.user.user_crud.get') as mock_get:
            mock_get.return_value = test_user
            
            user = await deps.get_current_user(db_session, token_data)
            
            assert user.id == test_user.id
            assert user.email == test_user.email
            mock_get.assert_called_once_with(db_session, id=str(test_user.id))

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, db_session):
        """Test get_current_user with user not found."""
        token_data = {"sub": "nonexistent-user"}
        
        with patch('app.crud.user.user_crud.get') as mock_get:
            mock_get.return_value = None
            
            with pytest.raises(AuthenticationError):
                await deps.get_current_user(db_session, token_data)

    @pytest.mark.asyncio
    async def test_get_current_user_inactive(self, db_session, test_user):
        """Test get_current_user with inactive user."""
        test_user.is_active = False
        token_data = {"sub": str(test_user.id)}
        
        with patch('app.crud.user.user_crud.get') as mock_get:
            mock_get.return_value = test_user
            
            with pytest.raises(AuthenticationError):
                await deps.get_current_user(db_session, token_data)

    @pytest.mark.asyncio
    async def test_get_current_user_no_sub(self, db_session):
        """Test get_current_user with missing sub in token."""
        token_data = {"email": "test@example.com"}  # Missing 'sub'
        
        with pytest.raises(InvalidTokenError):
            await deps.get_current_user(db_session, token_data)

    @pytest.mark.asyncio
    async def test_get_current_active_user(self, test_user):
        """Test get_current_active_user dependency."""
        user = await deps.get_current_active_user(test_user)
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self, test_user):
        """Test get_current_active_user with inactive user."""
        test_user.is_active = False
        
        with pytest.raises(AuthenticationError):
            await deps.get_current_active_user(test_user)

    @pytest.mark.asyncio
    async def test_get_current_superuser(self, admin_user):
        """Test get_current_superuser dependency."""
        user = await deps.get_current_superuser(admin_user)
        assert user.id == admin_user.id
        assert user.is_superuser is True

    @pytest.mark.asyncio
    async def test_get_current_superuser_not_super(self, test_user):
        """Test get_current_superuser with regular user."""
        with pytest.raises(AuthorizationError):
            await deps.get_current_superuser(test_user)

    @pytest.mark.asyncio
    async def test_get_current_user_optional_with_token(self, db_session, test_user):
        """Test get_current_user_optional with valid token."""
        token = create_access_token({"sub": str(test_user.id)})
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        with patch('app.crud.user.user_crud.get') as mock_get:
            mock_get.return_value = test_user
            
            user = await deps.get_current_user_optional(credentials, db_session)
            
            assert user is not None
            assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_token(self, db_session):
        """Test get_current_user_optional without token."""
        user = await deps.get_current_user_optional(None, db_session)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_token(self, db_session):
        """Test get_current_user_optional with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token"
        )
        
        user = await deps.get_current_user_optional(credentials, db_session)
        assert user is None


class TestTokenSecurity:
    """Test token security features."""

    def test_token_type_validation(self):
        """Test that tokens include type information."""
        access_token = create_access_token({"sub": "user123"})
        refresh_token = create_refresh_token({"sub": "user123"})
        
        access_payload = verify_token(access_token)
        refresh_payload = verify_token(refresh_token)
        
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

    def test_token_expiration_times(self):
        """Test that tokens have appropriate expiration times."""
        data = {"sub": "user123"}
        
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)
        
        access_payload = verify_token(access_token)
        refresh_payload = verify_token(refresh_token)
        
        access_exp = datetime.fromtimestamp(access_payload["exp"])
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"])
        
        # Refresh token should expire after access token
        assert refresh_exp > access_exp

    def test_token_algorithm_security(self):
        """Test that tokens use secure algorithm."""
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        # Should not be decodable with different algorithm
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, settings.SECRET_KEY, algorithms=["none"])

    def test_token_secret_key_required(self):
        """Test that tokens require the correct secret key."""
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        # Should not be decodable with wrong secret
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=["HS256"])

    def test_token_replay_protection(self):
        """Test that expired tokens cannot be replayed."""
        data = {"sub": "user123"}
        # Create an already expired token
        past_time = datetime.utcnow() - timedelta(minutes=1)
        expired_token = jwt.encode(
            {**data, "exp": past_time, "type": "access"},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        # Should not verify as valid
        assert verify_token(expired_token) is None
        
        # Should raise exception when decoding
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(expired_token)
