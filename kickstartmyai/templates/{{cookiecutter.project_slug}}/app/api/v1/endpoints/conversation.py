"""Conversation API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.crud import conversation_crud
from app.models import User
from app.schemas import (
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    ConversationListResponse,
    ConversationWithMessages,
    ConversationWithFullContext,
    ConversationStatistics,
    ConversationFilter,
    ConversationSummary
)

router = APIRouter()


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_inactive: bool = False,
    agent_id: Optional[UUID] = None,
    search_term: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List conversations for the current user."""
    try:
        if search_term:
            conversations = await conversation_crud.search_conversations(
                db, search_term=search_term, user_id=current_user.id, skip=skip, limit=limit
            )
            total_count = len(conversations)  # For search, we'll use simple count
        else:
            conversations, total_count = await conversation_crud.get_by_user_with_count(
                db, user_id=current_user.id, skip=skip, limit=limit, 
                include_inactive=include_inactive
            )
        
        return ConversationListResponse(
            conversations=conversations,
            total_count=total_count,
            page=skip // limit + 1,
            page_size=limit,
            has_next=(skip + limit) < total_count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}"
        )


@router.post("/", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new conversation."""
    try:
        # Check if conversation with same title exists for user (optional uniqueness)
        if conversation_data.title:
            existing_conversation = await conversation_crud.get_by_title(
                db, user_id=current_user.id, title=conversation_data.title
            )
            if existing_conversation:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Conversation with title '{conversation_data.title}' already exists"
                )
        
        conversation = await conversation_crud.create_with_user(
            db, obj_in=conversation_data, user_id=current_user.id
        )
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific conversation."""
    try:
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Check ownership
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}"
        )


@router.put("/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: UUID,
    conversation_data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a conversation."""
    try:
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Check ownership
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this conversation"
            )
        
        # Check if updating title and it conflicts
        if conversation_data.title and conversation_data.title != conversation.title:
            existing_conversation = await conversation_crud.get_by_title(
                db, user_id=current_user.id, title=conversation_data.title
            )
            if existing_conversation and existing_conversation.id != conversation_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Conversation with title '{conversation_data.title}' already exists"
                )
        
        updated_conversation = await conversation_crud.update(
            db, db_obj=conversation, obj_in=conversation_data
        )
        return updated_conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation: {str(e)}"
        )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation."""
    try:
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Check ownership
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this conversation"
            )
        
        await conversation_crud.remove(db, id=conversation_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )


@router.get("/{conversation_id}/messages", response_model=ConversationWithMessages)
async def get_conversation_with_messages(
    conversation_id: UUID,
    message_limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conversation with its messages."""
    try:
        conversation = await conversation_crud.get_with_messages(
            db, conversation_id=conversation_id, message_limit=message_limit
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Check ownership
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation with messages: {str(e)}"
        )


@router.get("/{conversation_id}/full", response_model=ConversationWithFullContext)
async def get_conversation_full_context(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conversation with full context (messages, agent, executions)."""
    try:
        conversation = await conversation_crud.get_with_full_context(
            db, conversation_id=conversation_id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Check ownership
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation full context: {str(e)}"
        )


@router.patch("/{conversation_id}/activate", response_model=Conversation)
async def activate_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activate a conversation."""
    try:
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Check ownership
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to activate this conversation"
            )
        
        activated_conversation = await conversation_crud.activate_conversation(
            db, conversation_id=conversation_id
        )
        return activated_conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate conversation: {str(e)}"
        )


@router.patch("/{conversation_id}/deactivate", response_model=Conversation)
async def deactivate_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deactivate a conversation."""
    try:
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # Check ownership
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to deactivate this conversation"
            )
        
        deactivated_conversation = await conversation_crud.deactivate_conversation(
            db, conversation_id=conversation_id
        )
        return deactivated_conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate conversation: {str(e)}"
        )


@router.get("/recent/list", response_model=List[Conversation])
async def list_recent_conversations(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recent conversations for the current user."""
    try:
        conversations = await conversation_crud.get_recent_conversations(
            db, user_id=current_user.id, days=days, limit=limit
        )
        return conversations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list recent conversations: {str(e)}"
        )


@router.get("/statistics/overview", response_model=dict)
async def get_conversation_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conversation statistics for the current user."""
    try:
        stats = await conversation_crud.get_conversation_statistics(
            db, user_id=current_user.id
        )
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation statistics: {str(e)}"
        )
