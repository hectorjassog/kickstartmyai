"""Message CRUD operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageUpdate


def get_message(db: Session, message_id: int) -> Optional[Message]:
    """Get message by ID."""
    return db.query(Message).filter(Message.id == message_id).first()


def get_messages(
    db: Session, conversation_id: int, skip: int = 0, limit: int = 100
) -> List[Message]:
    """Get list of messages for a conversation."""
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_messages_by_conversation(
    db: Session, conversation_id: int, skip: int = 0, limit: int = 100
) -> List[Message]:
    """Get messages by conversation ID."""
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_message(db: Session, obj_in: MessageCreate, user_id: int = None) -> Message:
    """Create new message."""
    db_message = Message(
        content=obj_in.content,
        role=obj_in.role,
        conversation_id=obj_in.conversation_id,
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


def update_message(db: Session, db_obj: Message, obj_in: MessageUpdate) -> Message:
    """Update message."""
    obj_data = obj_in.dict(exclude_unset=True)
    
    for field, value in obj_data.items():
        setattr(db_obj, field, value)
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_message(db: Session, message_id: int) -> Optional[Message]:
    """Delete message."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if message:
        db.delete(message)
        db.commit()
    return message
