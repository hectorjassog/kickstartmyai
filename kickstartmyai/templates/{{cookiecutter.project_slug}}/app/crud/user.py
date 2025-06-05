"""
User CRUD operations.

This module provides comprehensive CRUD operations for user management,
including authentication, profile management, and advanced querying.
"""

from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy import and_, or_, func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_password, get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.auth import UserRegister


class UserCRUD:
    """User CRUD operations class."""
    
    async def get(self, db: AsyncSession, *, id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(
            select(User).where(User.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        """Get user by username (if username field exists)."""
        # Note: Current User model doesn't have username field
        # This is here for future compatibility
        if hasattr(User, 'username'):
            result = await db.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
        return None
    
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """Get multiple users with filtering."""
        query = select(User)
        
        # Apply filters
        filters = []
        if search:
            search_filter = or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
            filters.append(search_filter)
        
        if is_active is not None:
            filters.append(User.is_active == is_active)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_multi_with_count(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[User], int]:
        """Get multiple users with total count."""
        # Build base query
        base_query = select(User)
        count_query = select(func.count(User.id))
        
        # Apply filters
        filters = []
        if search:
            search_filter = or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
            filters.append(search_filter)
        
        if is_active is not None:
            filters.append(User.is_active == is_active)
        
        if filters:
            base_query = base_query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get count
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Get users with pagination
        users_query = base_query.offset(skip).limit(limit)
        users_result = await db.execute(users_query)
        users = users_result.scalars().all()
        
        return users, total_count
    
    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create new user."""
        # Hash password
        hashed_password = get_password_hash(obj_in.password)
        
        # Create user instance
        db_user = User(
            email=obj_in.email,
            full_name=obj_in.full_name,
            hashed_password=hashed_password,
            is_active=getattr(obj_in, 'is_active', True),
            is_superuser=getattr(obj_in, 'is_superuser', False),
        )
        
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    
    async def create_from_register(self, db: AsyncSession, *, obj_in: UserRegister) -> User:
        """Create new user from registration data."""
        # Hash password
        hashed_password = get_password_hash(obj_in.password)
        
        # Create user instance
        db_user = User(
            email=obj_in.email,
            full_name=obj_in.full_name,
            hashed_password=hashed_password,
            is_active=True,  # New users are active by default
            is_superuser=False,  # Regular users are not superusers
        )
        
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        db_obj: User, 
        obj_in: UserUpdate
    ) -> User:
        """Update user."""
        obj_data = obj_in.model_dump(exclude_unset=True)
        
        # Handle password update
        if "password" in obj_data:
            hashed_password = get_password_hash(obj_data["password"])
            del obj_data["password"]
            obj_data["hashed_password"] = hashed_password
        
        # Update fields
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        
        # Update timestamp
        db_obj.updated_at = datetime.utcnow()
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, *, id: UUID) -> Optional[User]:
        """Delete user by ID."""
        result = await db.execute(
            select(User).where(User.id == id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            await db.delete(user)
            await db.commit()
        
        return user
    
    async def authenticate(
        self, 
        db: AsyncSession, 
        *, 
        email: str, 
        password: str
    ) -> Optional[User]:
        """Authenticate user by email and password."""
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    async def is_active(self, user: User) -> bool:
        """Check if user is active."""
        return user.is_active
    
    async def is_superuser(self, user: User) -> bool:
        """Check if user is superuser."""
        return user.is_superuser
    
    async def activate(self, db: AsyncSession, *, user: User) -> User:
        """Activate user."""
        user.is_active = True
        user.updated_at = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def deactivate(self, db: AsyncSession, *, user: User) -> User:
        """Deactivate user."""
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def update_last_login(self, db: AsyncSession, *, user: User) -> User:
        """Update user's last login timestamp."""
        user.last_login_at = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def change_password(
        self, 
        db: AsyncSession, 
        *, 
        user: User, 
        new_password: str
    ) -> User:
        """Change user password."""
        hashed_password = get_password_hash(new_password)
        user.hashed_password = hashed_password
        user.updated_at = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def get_users_count(self, db: AsyncSession) -> int:
        """Get total count of users."""
        result = await db.execute(select(func.count(User.id)))
        return result.scalar()
    
    async def get_active_users_count(self, db: AsyncSession) -> int:
        """Get count of active users."""
        result = await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        return result.scalar()


# Create global instance
user_crud = UserCRUD()
