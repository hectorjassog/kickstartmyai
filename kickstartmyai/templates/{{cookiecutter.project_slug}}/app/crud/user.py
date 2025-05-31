"""User CRUD operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security.authentication import get_password_hash


def get_user(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Get list of users."""
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, obj_in: UserCreate) -> User:
    """Create new user."""
    hashed_password = get_password_hash(obj_in.password)
    db_user = User(
        email=obj_in.email,
        username=obj_in.username,
        full_name=obj_in.full_name,
        hashed_password=hashed_password,
        is_active=obj_in.is_active,
        is_superuser=obj_in.is_superuser,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, db_obj: User, obj_in: UserUpdate) -> User:
    """Update user."""
    obj_data = obj_in.dict(exclude_unset=True)
    
    if "password" in obj_data:
        hashed_password = get_password_hash(obj_data["password"])
        del obj_data["password"]
        obj_data["hashed_password"] = hashed_password
    
    for field, value in obj_data.items():
        setattr(db_obj, field, value)
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_user(db: Session, user_id: int) -> User:
    """Delete user."""
    user = db.query(User).filter(User.id == user_id).first()
    db.delete(user)
    db.commit()
    return user
