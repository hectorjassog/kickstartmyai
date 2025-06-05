"""Message API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.crud import message_crud, conversation_crud
from app.models import User
from app.models.message import MessageRole
from app.schemas import (
    Message,
    MessageCreate,
    MessageUpdate,
    MessageListResponse,
    MessageStatistics,
    MessageContext,
    BulkMessageCreate
)

router = APIRouter()


@router.get("/", response_model=MessageListResponse)
async def list_messages(
    conversation_id: Optional[UUID] = None,
    role: Optional[MessageRole] = None,
    search_term: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    order_by_desc: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List messages with filtering."""
    try:
        if search_term:
            messages = await message_crud.search_messages(
                db, search_term=search_term, conversation_id=conversation_id,
                role=role, skip=skip, limit=limit
            )
            total_count = len(messages)
        elif conversation_id:
            # Check conversation ownership
            conversation = await conversation_crud.get(db, id=conversation_id)
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
            if conversation.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this conversation"
                )
            
            messages, total_count = await message_crud.get_by_conversation_with_count(
                db, conversation_id=conversation_id, skip=skip, limit=limit,
                order_by_desc=order_by_desc
            )
        else:
            # Without conversation_id, we can't determine ownership, so reject
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="conversation_id is required"
            )
        
        return MessageListResponse(
            messages=messages,
            total_count=total_count,
            page=skip // limit + 1,
            page_size=limit,
            has_next=(skip + limit) < total_count
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list messages: {str(e)}"
        )


@router.post("/", response_model=Message, status_code=status.HTTP_201_CREATED)
async def create_message(
    message_data: MessageCreate,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new message in a conversation."""
    try:
        # Check conversation ownership
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to add messages to this conversation"
            )
        
        message = await message_crud.create_with_conversation(
            db, obj_in=message_data, conversation_id=conversation_id
        )
        return message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create message: {str(e)}"
        )


@router.get("/{message_id}", response_model=Message)
async def get_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific message."""
    try:
        message = await message_crud.get(db, id=message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found"
            )
        
        # Check conversation ownership
        conversation = await conversation_crud.get(db, id=message.conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this message"
            )
        
        return message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get message: {str(e)}"
        )


@router.put("/{message_id}", response_model=Message)
async def update_message(
    message_id: UUID,
    message_data: MessageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a message."""
    try:
        message = await message_crud.get(db, id=message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found"
            )
        
        # Check conversation ownership
        conversation = await conversation_crud.get(db, id=message.conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this message"
            )
        
        updated_message = await message_crud.update(db, db_obj=message, obj_in=message_data)
        return updated_message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update message: {str(e)}"
        )


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a message."""
    try:
        message = await message_crud.get(db, id=message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found"
            )
        
        # Check conversation ownership
        conversation = await conversation_crud.get(db, id=message.conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this message"
            )
        
        await message_crud.remove(db, id=message_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete message: {str(e)}"
        )


@router.get("/conversation/{conversation_id}/context", response_model=MessageContext)
async def get_conversation_context(
    conversation_id: UUID,
    max_messages: int = Query(20, ge=1, le=100),
    include_system: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conversation context for AI processing."""
    try:
        # Check conversation ownership
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )
        
        messages = await message_crud.get_conversation_context(
            db, conversation_id=conversation_id, max_messages=max_messages,
            include_system=include_system
        )
        
        return MessageContext(
            messages=messages,
            max_tokens=max_messages * 500,  # Rough estimate
            include_system=include_system
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation context: {str(e)}"
        )


@router.get("/conversation/{conversation_id}/recent", response_model=List[Message])
async def get_recent_messages(
    conversation_id: UUID,
    minutes: int = Query(60, ge=1, le=1440),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent messages from a conversation."""
    try:
        # Check conversation ownership
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )
        
        messages = await message_crud.get_recent_messages(
            db, conversation_id=conversation_id, minutes=minutes, limit=limit
        )
        return messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent messages: {str(e)}"
        )


@router.get("/conversation/{conversation_id}/last", response_model=Message)
async def get_last_message(
    conversation_id: UUID,
    role: Optional[MessageRole] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the last message in a conversation."""
    try:
        # Check conversation ownership
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )
        
        message = await message_crud.get_last_message(
            db, conversation_id=conversation_id, role=role
        )
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No messages found"
            )
        
        return message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get last message: {str(e)}"
        )


@router.post("/bulk", response_model=List[Message], status_code=status.HTTP_201_CREATED)
async def create_bulk_messages(
    bulk_data: BulkMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create multiple messages in bulk."""
    try:
        # Check conversation ownership
        conversation = await conversation_crud.get(db, id=bulk_data.conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to add messages to this conversation"
            )
        
        messages = await message_crud.bulk_create_messages(
            db, messages=bulk_data.messages, conversation_id=bulk_data.conversation_id
        )
        return messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk messages: {str(e)}"
        )


@router.get("/statistics/overview", response_model=dict)
async def get_message_statistics(
    conversation_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get message statistics."""
    try:
        if conversation_id:
            # Check conversation ownership
            conversation = await conversation_crud.get(db, id=conversation_id)
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
            if conversation.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this conversation"
                )
        
        stats = await message_crud.get_message_statistics(
            db, conversation_id=conversation_id
        )
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get message statistics: {str(e)}"
        )
