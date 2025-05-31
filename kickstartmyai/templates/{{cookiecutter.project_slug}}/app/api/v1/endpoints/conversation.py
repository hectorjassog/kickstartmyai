"""Conversation API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.schemas.conversation import Conversation, ConversationCreate, ConversationUpdate
from app.crud.conversation import create_conversation, get_conversation, get_conversations, update_conversation, delete_conversation
from app.models.user import User as UserModel

router = APIRouter()


@router.post("/", response_model=Conversation, status_code=status.HTTP_201_CREATED)
def create_new_conversation(
    *,
    db: Session = Depends(get_db),
    conversation_in: ConversationCreate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Create new conversation."""
    conversation_in.user_id = current_user.id
    conversation = create_conversation(db=db, obj_in=conversation_in)
    return conversation


@router.get("/", response_model=List[Conversation])
def read_conversations(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Retrieve user's conversations."""
    conversations = get_conversations(db, user_id=current_user.id, skip=skip, limit=limit)
    return conversations


@router.get("/{conversation_id}", response_model=Conversation)
def read_conversation(
    *,
    db: Session = Depends(get_db),
    conversation_id: int,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get conversation by ID."""
    conversation = get_conversation(db=db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if user owns the conversation
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return conversation


@router.put("/{conversation_id}", response_model=Conversation)
def update_existing_conversation(
    *,
    db: Session = Depends(get_db),
    conversation_id: int,
    conversation_in: ConversationUpdate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Update conversation."""
    conversation = get_conversation(db=db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if user owns the conversation
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    conversation = update_conversation(db=db, db_obj=conversation, obj_in=conversation_in)
    return conversation


@router.delete("/{conversation_id}")
def delete_existing_conversation(
    *,
    db: Session = Depends(get_db),
    conversation_id: int,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Delete conversation."""
    conversation = get_conversation(db=db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if user owns the conversation
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    delete_conversation(db=db, conversation_id=conversation_id)
    return {"message": "Conversation deleted successfully"}
