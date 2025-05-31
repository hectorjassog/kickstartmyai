"""Conversation CRUD operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate


def get_conversation(db: Session, conversation_id: int) -> Optional[Conversation]:
    """Get conversation by ID."""
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def get_conversations(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[Conversation]:
    """Get list of conversations for a user."""
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_conversations_by_user(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[Conversation]:
    """Get conversations by user ID."""
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_conversation(db: Session, obj_in: ConversationCreate) -> Conversation:
    """Create new conversation."""
    db_conversation = Conversation(
        title=obj_in.title,
        description=obj_in.description,
        is_active=obj_in.is_active,
        user_id=obj_in.user_id,
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation


def update_conversation(
    db: Session, db_obj: Conversation, obj_in: ConversationUpdate
) -> Conversation:
    """Update conversation."""
    obj_data = obj_in.dict(exclude_unset=True)
    
    for field, value in obj_data.items():
        setattr(db_obj, field, value)
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_conversation(db: Session, conversation_id: int) -> Optional[Conversation]:
    """Delete conversation."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        db.delete(conversation)
        db.commit()
    return conversation
