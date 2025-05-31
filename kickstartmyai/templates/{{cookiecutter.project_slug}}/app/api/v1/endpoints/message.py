"""Message API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.schemas.message import Message, MessageCreate, MessageUpdate
from app.crud.message import create_message, get_message, get_messages, update_message, delete_message
from app.models.user import User as UserModel

router = APIRouter()


@router.post("/", response_model=Message, status_code=status.HTTP_201_CREATED)
def create_new_message(
    *,
    db: Session = Depends(get_db),
    message_in: MessageCreate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Create new message."""
    message = create_message(db=db, obj_in=message_in, user_id=current_user.id)
    return message


@router.get("/", response_model=List[Message])
def read_messages(
    db: Session = Depends(get_db),
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Retrieve messages for a conversation."""
    messages = get_messages(db, conversation_id=conversation_id, skip=skip, limit=limit)
    return messages


@router.get("/{message_id}", response_model=Message)
def read_message(
    *,
    db: Session = Depends(get_db),
    message_id: int,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get message by ID."""
    message = get_message(db=db, message_id=message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    return message
