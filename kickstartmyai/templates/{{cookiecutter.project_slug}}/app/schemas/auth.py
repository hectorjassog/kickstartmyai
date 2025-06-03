"""
Authentication schemas for request/response validation.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

from .user import UserResponse


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenRefresh(BaseModel):
    """Token refresh request schema."""
    refresh_token: str = Field(..., description="Refresh token")


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse


class UserRegister(BaseModel):
    """User registration request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    full_name: str = Field(..., min_length=1, max_length=100, description="User full name")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        
        return v


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr = Field(..., description="Email address to send reset link to")


class PasswordReset(BaseModel):
    """Password reset schema."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        
        return v


class ChangePassword(BaseModel):
    """Change password schema."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        
        return v


class TokenVerification(BaseModel):
    """Token verification response schema."""
    valid: bool
    user: Optional[UserResponse] = None


class AuthError(BaseModel):
    """Authentication error response schema."""
    detail: str
    error_code: Optional[str] = None


# Token data schema for JWT payload
class TokenData(BaseModel):
    """Token data schema for JWT payload."""
    sub: Optional[str] = None
    email: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    token_type: Optional[str] = None


# Login request schema
class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


# Refresh token request schema
class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str = Field(..., description="Refresh token")


# Registration request schema
class RegisterRequest(BaseModel):
    """User registration request schema."""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=100, description="User full name")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


# Registration response schema
class RegisterResponse(BaseModel):
    """User registration response schema."""
    message: str = Field(..., description="Registration success message")
    user: UserResponse = Field(..., description="Created user information")
    access_token: Optional[str] = Field(None, description="Access token if auto-login enabled")
    refresh_token: Optional[str] = Field(None, description="Refresh token if auto-login enabled")


# Logout request schema
class LogoutRequest(BaseModel):
    """Logout request schema."""
    refresh_token: Optional[str] = Field(None, description="Refresh token to invalidate") 