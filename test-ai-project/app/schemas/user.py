"""User Pydantic schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# Base schemas
class UserBase(BaseModel):
    """User base schema with common fields."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False


# Creation schemas
class UserCreate(UserBase):
    """User creation schema for admin use."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)
    is_active: bool = True
    is_superuser: bool = False


# Update schemas
class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None


# Response schemas
class UserResponse(BaseModel):
    """User response schema for API responses."""
    id: UUID
    email: EmailStr
    full_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_superuser: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class UserProfile(BaseModel):
    """User profile schema for current user."""
    id: UUID
    email: EmailStr
    full_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """User list response with pagination."""
    users: List[UserResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class UserPreferences(BaseModel):
    """User preferences schema."""
    theme: str = "light"
    language: str = "en"
    timezone: str = "UTC"
    notifications_enabled: bool = True
    email_notifications: bool = True
    
    model_config = ConfigDict(from_attributes=True)


# Database schemas
class UserInDBBase(UserBase):
    """User schema with database fields."""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    """User schema for internal use."""
    pass


class UserInDB(UserInDBBase):
    """User schema with sensitive fields."""
    hashed_password: str


# Statistics schema
class UserStatistics(BaseModel):
    """User statistics schema."""
    total_users: int
    active_users: int
    inactive_users: int
    verified_users: int
    superusers: int
    users_created_today: int
    users_created_this_week: int
    users_created_this_month: int


# Filter schema
class UserFilter(BaseModel):
    """User filter schema for complex queries."""
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


# Activation schema
class UserActivation(BaseModel):
    """User activation schema."""
    user_id: UUID
    activation_token: str
    is_active: bool = True
