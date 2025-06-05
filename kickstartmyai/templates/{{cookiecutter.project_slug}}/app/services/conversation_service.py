"""
Conversation Service - High-level service for conversation management.

This service provides business logic for managing conversations, including
creation, updates, search, and conversation-level operations.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc

from app.crud import conversation as conversation_crud
from app.crud import message as message_crud
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationWithMessages
)
from app.schemas.message import MessageResponse
from app.ai.services import embedding_service
from app.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class ConversationService:
    """High-level service for conversation operations."""
    
    def __init__(self):
        self.default_page_size = 20
        self.max_page_size = 100
    
    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: UUID,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationResponse:
        """
        Create a new conversation.
        
        Args:
            db: Database session
            user_id: User ID
            title: Optional conversation title
            metadata: Optional conversation metadata
            
        Returns:
            ConversationResponse object
        """
        if not title:
            title = f"Conversation - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        conversation_data = ConversationCreate(
            title=title,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        conversation = await conversation_crud.create(db, obj_in=conversation_data)
        logger.info(f"Created conversation {conversation.id} for user {user_id}")
        
        return ConversationResponse.from_orm(conversation)
    
    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None,
        include_messages: bool = False
    ) -> ConversationResponse:
        """
        Get conversation by ID.
        
        Args:
            db: Database session
            conversation_id: Conversation ID
            user_id: Optional user ID for access control
            include_messages: Whether to include messages
            
        Returns:
            ConversationResponse object
        """
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        # Check user access if user_id provided
        if user_id and conversation.user_id != user_id:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        if include_messages:
            messages = await message_crud.get_by_conversation(
                db, conversation_id=conversation_id
            )
            message_responses = [MessageResponse.from_orm(msg) for msg in messages]
            return ConversationWithMessages(
                **conversation.__dict__,
                messages=message_responses
            )
        
        return ConversationResponse.from_orm(conversation)
    
    async def update_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        updates: ConversationUpdate,
        user_id: Optional[UUID] = None
    ) -> ConversationResponse:
        """
        Update conversation.
        
        Args:
            db: Database session
            conversation_id: Conversation ID
            updates: Update data
            user_id: Optional user ID for access control
            
        Returns:
            Updated ConversationResponse
        """
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        # Check user access if user_id provided
        if user_id and conversation.user_id != user_id:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        conversation = await conversation_crud.update(
            db, db_obj=conversation, obj_in=updates
        )
        
        logger.info(f"Updated conversation {conversation_id}")
        return ConversationResponse.from_orm(conversation)
    
    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        Delete conversation and all associated messages.
        
        Args:
            db: Database session
            conversation_id: Conversation ID
            user_id: Optional user ID for access control
            
        Returns:
            True if deleted successfully
        """
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        # Check user access if user_id provided
        if user_id and conversation.user_id != user_id:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        # Delete associated messages first
        messages = await message_crud.get_by_conversation(
            db, conversation_id=conversation_id
        )
        for message in messages:
            await message_crud.remove(db, id=message.id)
        
        # Delete conversation
        await conversation_crud.remove(db, id=conversation_id)
        
        logger.info(f"Deleted conversation {conversation_id} and {len(messages)} messages")
        return True
    
    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc"
    ) -> Tuple[List[ConversationResponse], int]:
        """
        List conversations for a user.
        
        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Number of records to return
            search: Optional search term
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            Tuple of (conversations, total_count)
        """
        # Validate pagination
        limit = min(limit, self.max_page_size)
        
        # Get conversations with optional search
        conversations, total = await conversation_crud.get_multi_with_search(
            db,
            user_id=user_id,
            skip=skip,
            limit=limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        conversation_responses = [
            ConversationResponse.from_orm(conv) for conv in conversations
        ]
        
        return conversation_responses, total
    
    async def get_conversation_summary(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get conversation summary with statistics.
        
        Args:
            db: Database session
            conversation_id: Conversation ID
            user_id: Optional user ID for access control
            
        Returns:
            Conversation summary dictionary
        """
        conversation = await conversation_crud.get(db, id=conversation_id)
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        # Check user access if user_id provided
        if user_id and conversation.user_id != user_id:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        # Get message statistics
        messages = await message_crud.get_by_conversation(
            db, conversation_id=conversation_id
        )
        
        message_count = len(messages)
        user_messages = [msg for msg in messages if msg.role == MessageRole.USER]
        assistant_messages = [msg for msg in messages if msg.role == MessageRole.ASSISTANT]
        
        # Calculate conversation duration
        duration = None
        if messages:
            start_time = min(msg.created_at for msg in messages)
            end_time = max(msg.created_at for msg in messages)
            duration = (end_time - start_time).total_seconds()
        
        # Calculate total tokens if available
        total_tokens = 0
        for message in messages:
            if message.metadata and 'tokens_used' in message.metadata:
                total_tokens += message.metadata['tokens_used']
        
        return {
            "conversation_id": conversation_id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "message_count": message_count,
            "user_message_count": len(user_messages),
            "assistant_message_count": len(assistant_messages),
            "duration_seconds": duration,
            "total_tokens": total_tokens,
            "metadata": conversation.metadata
        }
    
    async def search_conversations_semantic(
        self,
        db: AsyncSession,
        user_id: UUID,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search on conversations.
        
        Args:
            db: Database session
            user_id: User ID
            query: Search query
            limit: Number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of conversation search results with similarity scores
        """
        try:
            # Get user's conversations
            conversations, _ = await conversation_crud.get_multi_with_search(
                db, user_id=user_id, limit=1000  # Get all for semantic search
            )
            
            if not conversations:
                return []
            
            # Prepare conversation texts for embedding
            conversation_texts = []
            for conv in conversations:
                # Get recent messages for context
                messages = await message_crud.get_by_conversation(
                    db, conversation_id=conv.id, limit=10
                )
                
                # Combine title and recent message content
                text_parts = [conv.title]
                for msg in messages[-5:]:  # Last 5 messages
                    text_parts.append(f"{msg.role.value}: {msg.content}")
                
                conversation_texts.append(" ".join(text_parts))
            
            # Perform semantic search
            results = await embedding_service.semantic_search(
                query=query,
                documents=conversation_texts,
                top_k=limit
            )
            
            # Filter by similarity threshold and format results
            search_results = []
            for result in results:
                if result.similarity >= similarity_threshold:
                    # Find corresponding conversation
                    conv_index = conversation_texts.index(result.text)
                    conversation = conversations[conv_index]
                    
                    search_results.append({
                        "conversation": ConversationResponse.from_orm(conversation),
                        "similarity_score": result.similarity,
                        "matched_text": result.text[:200] + "..." if len(result.text) > 200 else result.text
                    })
            
            return search_results
            
        except Exception as e:
            logger.warning(f"Semantic search failed, falling back to text search: {str(e)}")
            # Fall back to regular text search
            conversations, _ = await conversation_crud.get_multi_with_search(
                db, user_id=user_id, search=query, limit=limit
            )
            return [
                {
                    "conversation": ConversationResponse.from_orm(conv),
                    "similarity_score": 1.0,
                    "matched_text": conv.title
                }
                for conv in conversations
            ]
    
    async def archive_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None
    ) -> ConversationResponse:
        """
        Archive a conversation.
        
        Args:
            db: Database session
            conversation_id: Conversation ID
            user_id: Optional user ID for access control
            
        Returns:
            Updated ConversationResponse
        """
        updates = ConversationUpdate(
            metadata={"archived": True, "archived_at": datetime.utcnow().isoformat()}
        )
        return await self.update_conversation(db, conversation_id, updates, user_id)
    
    async def unarchive_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None
    ) -> ConversationResponse:
        """
        Unarchive a conversation.
        
        Args:
            db: Database session
            conversation_id: Conversation ID
            user_id: Optional user ID for access control
            
        Returns:
            Updated ConversationResponse
        """
        conversation = await self.get_conversation(db, conversation_id, user_id)
        metadata = conversation.metadata.copy() if conversation.metadata else {}
        metadata.pop("archived", None)
        metadata.pop("archived_at", None)
        
        updates = ConversationUpdate(metadata=metadata)
        return await self.update_conversation(db, conversation_id, updates, user_id)
    
    async def get_conversation_analytics(
        self,
        db: AsyncSession,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get conversation analytics for a user.
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Analytics dictionary
        """
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get conversations in date range
        conversations, total_conversations = await conversation_crud.get_multi_with_search(
            db,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Get all for analytics
        )
        
        if not conversations:
            return {
                "total_conversations": 0,
                "total_messages": 0,
                "avg_messages_per_conversation": 0,
                "most_active_day": None,
                "conversation_lengths": [],
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
        
        # Calculate analytics
        total_messages = 0
        conversation_lengths = []
        daily_activity = {}
        
        for conversation in conversations:
            messages = await message_crud.get_by_conversation(
                db, conversation_id=conversation.id
            )
            message_count = len(messages)
            total_messages += message_count
            conversation_lengths.append(message_count)
            
            # Track daily activity
            for message in messages:
                day_key = message.created_at.date().isoformat()
                daily_activity[day_key] = daily_activity.get(day_key, 0) + 1
        
        # Find most active day
        most_active_day = None
        if daily_activity:
            most_active_day = max(daily_activity, key=daily_activity.get)
        
        avg_messages = total_messages / len(conversations) if conversations else 0
        
        return {
            "total_conversations": len(conversations),
            "total_messages": total_messages,
            "avg_messages_per_conversation": round(avg_messages, 2),
            "most_active_day": most_active_day,
            "conversation_lengths": conversation_lengths,
            "daily_activity": daily_activity,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
    
    async def export_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: Optional[UUID] = None,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export conversation data.
        
        Args:
            db: Database session
            conversation_id: Conversation ID
            user_id: Optional user ID for access control
            format: Export format (json, markdown, txt)
            
        Returns:
            Exported conversation data
        """
        # Get conversation with messages
        conversation_with_messages = await self.get_conversation(
            db, conversation_id, user_id, include_messages=True
        )
        
        if format == "json":
            return conversation_with_messages.dict()
        
        elif format == "markdown":
            lines = [f"# {conversation_with_messages.title}", ""]
            lines.append(f"**Created:** {conversation_with_messages.created_at}")
            lines.append(f"**Updated:** {conversation_with_messages.updated_at}")
            lines.append("")
            
            for message in conversation_with_messages.messages:
                role_title = "**User:**" if message.role == MessageRole.USER else "**Assistant:**"
                lines.append(f"{role_title} {message.content}")
                lines.append("")
            
            return {"content": "\n".join(lines), "format": "markdown"}
        
        elif format == "txt":
            lines = [conversation_with_messages.title, "=" * len(conversation_with_messages.title), ""]
            lines.append(f"Created: {conversation_with_messages.created_at}")
            lines.append(f"Updated: {conversation_with_messages.updated_at}")
            lines.append("")
            
            for message in conversation_with_messages.messages:
                role = "User" if message.role == MessageRole.USER else "Assistant"
                lines.append(f"{role}: {message.content}")
                lines.append("")
            
            return {"content": "\n".join(lines), "format": "txt"}
        
        else:
            raise ValidationError(f"Unsupported export format: {format}")


# Singleton instance
conversation_service = ConversationService()
