"""
User API Endpoints

This module provides REST API endpoints for user management,
including CRUD operations, authentication, and profile management.
"""

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserInDB,
    UserResponse,
    UserListResponse,
    UserProfile,
    UserPreferences,
)

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
    current_user: dict = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Create a new user (admin only).
    
    Args:
        db: Database session
        user_in: User creation data
        current_user: Current authenticated admin user
        
    Returns:
        Created user
    """
    try:
        user = await user_crud.create(db=db, obj_in=user_in)
        return UserResponse.from_orm(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create user: {str(e)}"
        )


@router.get("/", response_model=UserListResponse)
async def list_users(
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of users to return"),
    search: Optional[str] = Query(None, description="Search in email or full name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: dict = Depends(deps.get_current_admin_user),
) -> Any:
    """
    List users with filtering and pagination (admin only).
    
    Args:
        db: Database session
        skip: Number of items to skip
        limit: Number of items to return
        search: Search term
        is_active: Filter by active status
        current_user: Current authenticated admin user
        
    Returns:
        List of users with pagination
    """
    # Get users with count
    users, total_count = await user_crud.get_multi_with_count(
        db=db, skip=skip, limit=limit, search=search, is_active=is_active
    )
    
    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total_count=total_count,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=(total_count + limit - 1) // limit,
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    *,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Get current user's profile.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Current user's profile
    """
    user = await user_crud.get(db=db, id=current_user["id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserProfile.from_orm(user)


@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserUpdate,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Update current user's profile.
    
    Args:
        db: Database session
        user_in: User update data
        current_user: Current authenticated user
        
    Returns:
        Updated user profile
    """
    user = await user_crud.get(db=db, id=current_user["id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        user = await user_crud.update(db=db, db_obj=user, obj_in=user_in)
        return UserProfile.from_orm(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: UUID,
    current_user: dict = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Get user by ID (admin only).
    
    Args:
        db: Database session
        user_id: User ID
        current_user: Current authenticated admin user
        
    Returns:
        User details
    """
    user = await user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: UUID,
    user_in: UserUpdate,
    current_user: dict = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Update user (admin only).
    
    Args:
        db: Database session
        user_id: User ID
        user_in: User update data
        current_user: Current authenticated admin user
        
    Returns:
        Updated user
    """
    user = await user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        user = await user_crud.update(db=db, db_obj=user, obj_in=user_in)
        return UserResponse.from_orm(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: UUID,
    current_user: dict = Depends(deps.get_current_admin_user),
) -> None:
    """
    Delete user (admin only).
    
    Args:
        db: Database session
        user_id: User ID
        current_user: Current authenticated admin user
    """
    user = await user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await user_crud.remove(db=db, id=user_id)


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: UUID,
    current_user: dict = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Activate user (admin only).
    
    Args:
        db: Database session
        user_id: User ID
        current_user: Current authenticated admin user
        
    Returns:
        Updated user
    """
    try:
        user = await user_crud.activate_user(db=db, user_id=user_id)
        return UserResponse.from_orm(user)
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to activate user: {str(e)}"
        )


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: UUID,
    current_user: dict = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Deactivate user (admin only).
    
    Args:
        db: Database session
        user_id: User ID
        current_user: Current authenticated admin user
        
    Returns:
        Updated user
    """
    try:
        user = await user_crud.deactivate_user(db=db, user_id=user_id)
        return UserResponse.from_orm(user)
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to deactivate user: {str(e)}"
        )
):
    """Retrieve users."""
    users = get_users(db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=User)
def read_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get user by ID."""
    user = get_user(db=db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=User)
def update_existing_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    user_in: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Update user."""
    user = get_user(db=db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    user = update_user(db=db, db_obj=user, obj_in=user_in)
    return user


@router.delete("/{user_id}")
def delete_existing_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Delete user."""
    user = get_user(db=db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    user = delete_user(db=db, user_id=user_id)
    return {"message": "User deleted successfully"}
