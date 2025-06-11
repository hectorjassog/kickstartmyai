"""
Authentication API Endpoints

This module provides REST API endpoints for authentication,
including login, logout, registration, token refresh, and password reset.
"""

from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    verify_token,
)
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.auth import (
    Token,
    TokenRefresh,
    UserRegister,
    PasswordReset,
    PasswordResetRequest,
    LoginResponse,
)
from app.schemas.user import UserResponse


router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    Args:
        db: Database session
        form_data: Login credentials (username/email and password)
        
    Returns:
        Access token and user information
    """
    # Authenticate user
    user = await user_crud.authenticate(
        db=db,
        email=form_data.username,
        password=form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )
    
    # Create access and refresh tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=refresh_token_expires
    )
    
    # Update user's last login
    await user_crud.update_last_login(db=db, user=user)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: UserRegister,
) -> Any:
    """
    Register a new user account.
    
    Args:
        db: Database session
        user_in: User registration data
        
    Returns:
        Access token and user information
    """
    # Check if user already exists
    existing_user = await user_crud.get_by_email(db=db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system"
        )
    
    # Create new user
    try:
        user = await user_crud.create_from_register(db=db, obj_in=user_in)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create user: {str(e)}"
        )
    
    # Create tokens for the new user
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=refresh_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    *,
    db: AsyncSession = Depends(deps.get_db),
    token_data: TokenRefresh,
) -> Any:
    """
    Refresh an access token using a refresh token.
    
    Args:
        db: Database session
        token_data: Refresh token data
        
    Returns:
        New access token
    """
    # Verify refresh token
    try:
        payload = verify_token(token_data.refresh_token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Get user from database
    user = await user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout")
async def logout(
    *,
    request: Request,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Logout the current user.
    
    Note: In a stateless JWT implementation, logout is primarily handled client-side
    by discarding the token. This endpoint is provided for completeness and can be
    extended to implement token blacklisting if needed.
    
    Args:
        request: HTTP request
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    # In a simple JWT implementation, we just return success
    # In production, you might want to:
    # 1. Add the token to a blacklist/revocation list
    # 2. Store revoked tokens in Redis with expiration
    # 3. Use shorter-lived tokens with refresh mechanism
    
    return {"message": "Successfully logged out"}


@router.post("/password-reset-request")
async def password_reset_request(
    *,
    db: AsyncSession = Depends(deps.get_db),
    reset_request: PasswordResetRequest,
) -> Any:
    """
    Request a password reset link.
    
    Args:
        db: Database session
        reset_request: Password reset request data
        
    Returns:
        Success message (always returns success for security)
    """
    # Always return success to prevent email enumeration attacks
    # In production, you would:
    # 1. Generate a secure reset token
    # 2. Store it in the database with expiration
    # 3. Send an email with the reset link
    
    user = await user_crud.get_by_email(db=db, email=reset_request.email)
    if user and user.is_active:
        # TODO: Generate reset token and send email
        # reset_token = generate_password_reset_token(user.id)
        # send_password_reset_email(user.email, reset_token)
        pass
    
    return {
        "message": "If an account with that email exists, you will receive a password reset link"
    }


@router.post("/password-reset")
async def password_reset(
    *,
    db: AsyncSession = Depends(deps.get_db),
    reset_data: PasswordReset,
) -> Any:
    """
    Reset password using a reset token.
    
    Args:
        db: Database session
        reset_data: Password reset data
        
    Returns:
        Success message
    """
    # TODO: Implement password reset with token verification
    # This would involve:
    # 1. Verify the reset token
    # 2. Check token expiration
    # 3. Update user password
    # 4. Invalidate the reset token
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset is not yet implemented"
    )


@router.get("/verify-token")
async def verify_user_token(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Verify that the current token is valid.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information if token is valid
    """
    return {
        "valid": True,
        "user": UserResponse.model_validate(current_user)
    } 