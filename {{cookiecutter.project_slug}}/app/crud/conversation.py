"""
Conversation CRUD operations.

This module provides comprehensive CRUD operations for conversation management,
including message threading, metadata management, and search functionality.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy import and_, or_, desc, asc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate


class CRUDConversation(CRUDBase[Conversation, ConversationCreate, ConversationUpdate]):
    """CRUD operations for Conversation model."""

    async def create_with_user(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: ConversationCreate, 
        user_id: UUID
    ) -> Conversation:
        """Create a new conversation for a specific user."""
        obj_in_data = obj_in.model_dump()
        obj_in_data["user_id"] = user_id
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_user(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[Conversation]:
        """Get conversations by user ID with pagination."""
        query = select(self.model).where(self.model.user_id == user_id)
        
        if not include_inactive:
            query = query.where(self.model.is_active == True)
        
        query = query.order_by(desc(self.model.updated_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_user_with_count(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        include_inactive: bool = False
    ) -> Tuple[List[Conversation], int]:
        """Get conversations by user ID with total count."""
        # Build base queries
        base_query = select(self.model).where(self.model.user_id == user_id)
        count_query = select(func.count(self.model.id)).where(self.model.user_id == user_id)
        
        if not include_inactive:
            base_query = base_query.where(self.model.is_active == True)
            count_query = count_query.where(self.model.is_active == True)
        
        # Get count
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Get conversations with pagination
        conversations_query = base_query.order_by(desc(self.model.updated_at)).offset(skip).limit(limit)
        conversations_result = await db.execute(conversations_query)
        conversations = conversations_result.scalars().all()
        
        return conversations, total_count

    async def get_by_agent(
        self, 
        db: AsyncSession, 
        *, 
        agent_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Conversation]:
        """Get conversations by agent ID."""
        query = select(self.model).where(
            and_(
                self.model.agent_id == agent_id,
                self.model.is_active == True
            )
        ).order_by(desc(self.model.updated_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_title(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID, 
        title: str
    ) -> Optional[Conversation]:
        """Get conversation by title for a specific user."""
        query = select(self.model).where(
            and_(
                self.model.user_id == user_id,
                self.model.title == title
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def search_conversations(
        self, 
        db: AsyncSession, 
        *, 
        search_term: str,
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Conversation]:
        """Search conversations by title and description."""
        query = select(self.model)
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        # Search in title and description
        search_filter = or_(
            self.model.title.ilike(f"%{search_term}%"),
            self.model.description.ilike(f"%{search_term}%")
        )
        
        query = query.where(search_filter).where(
            self.model.is_active == True
        ).order_by(desc(self.model.updated_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_recent_conversations(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID,
        days: int = 7,
        limit: int = 10
    ) -> List[Conversation]:
        """Get recent conversations for a user."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(self.model).where(
            and_(
                self.model.user_id == user_id,
                self.model.updated_at >= cutoff_date,
                self.model.is_active == True
            )
        ).order_by(desc(self.model.updated_at)).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_with_messages(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID,
        message_limit: int = 100
    ) -> Optional[Conversation]:
        """Get conversation with its messages loaded."""
        query = select(self.model).where(
            self.model.id == conversation_id
        ).options(
            selectinload(self.model.messages).limit(message_limit)
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_full_context(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID
    ) -> Optional[Conversation]:
        """Get conversation with all related data loaded."""
        query = select(self.model).where(
            self.model.id == conversation_id
        ).options(
            selectinload(self.model.messages),
            selectinload(self.model.agent),
            selectinload(self.model.user)
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def activate_conversation(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID
    ) -> Optional[Conversation]:
        """Activate a conversation."""
        conversation = await self.get(db, id=conversation_id)
        if not conversation:
            return None
        
        conversation.is_active = True
        conversation.updated_at = datetime.utcnow()
        
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        return conversation

    async def deactivate_conversation(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID
    ) -> Optional[Conversation]:
        """Deactivate a conversation."""
        conversation = await self.get(db, id=conversation_id)
        if not conversation:
            return None
        
        conversation.is_active = False
        conversation.updated_at = datetime.utcnow()
        
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        return conversation

    async def update_metadata(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID,
        metadata: Dict[str, Any]
    ) -> Optional[Conversation]:
        """Update conversation metadata."""
        conversation = await self.get(db, id=conversation_id)
        if not conversation:
            return None
        
        # Merge new metadata with existing
        existing_metadata = conversation.metadata or {}
        existing_metadata.update(metadata)
        
        conversation.metadata = existing_metadata
        conversation.updated_at = datetime.utcnow()
        
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        return conversation

    async def get_conversation_statistics(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get conversation statistics."""
        base_query = select(self.model)
        if user_id:
            base_query = base_query.where(self.model.user_id == user_id)
        
        # Total count
        total_result = await db.execute(
            select(func.count(self.model.id)).select_from(base_query.subquery())
        )
        total_count = total_result.scalar()
        
        # Active count
        active_result = await db.execute(
            select(func.count(self.model.id)).select_from(
                base_query.where(self.model.is_active == True).subquery()
            )
        )
        active_count = active_result.scalar()
        
        # Get message counts per conversation
        from app.models.message import Message
        message_stats_result = await db.execute(
            select(
                func.count(Message.id),
                func.avg(func.count(Message.id)),
                func.max(func.count(Message.id))
            ).select_from(
                base_query.join(Message).subquery()
            ).group_by(self.model.id)
        )
        message_stats = message_stats_result.first()
        
        return {
            "total_conversations": total_count,
            "active_conversations": active_count,
            "inactive_conversations": total_count - active_count,
            "message_statistics": {
                "total_messages": message_stats[0] if message_stats else 0,
                "average_messages_per_conversation": float(message_stats[1] or 0),
                "max_messages_in_conversation": message_stats[2] if message_stats else 0
            }
        }

    async def count_by_user(self, db: AsyncSession, *, user_id: UUID) -> int:
        """Count conversations by user."""
        query = select(func.count(self.model.id)).where(
            and_(
                self.model.user_id == user_id,
                self.model.is_active == True
            )
        )
        
        result = await db.execute(query)
        return result.scalar()

    async def count_by_agent(self, db: AsyncSession, *, agent_id: UUID) -> int:
        """Count conversations by agent."""
        query = select(func.count(self.model.id)).where(
            and_(
                self.model.agent_id == agent_id,
                self.model.is_active == True
            )
        )
        
        result = await db.execute(query)
        return result.scalar()

    async def get_filtered(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        search_term: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Conversation]:
        """Get conversations with complex filtering."""
        query = select(self.model)
        
        # Apply filters
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        if agent_id:
            query = query.where(self.model.agent_id == agent_id)
        
        if is_active is not None:
            query = query.where(self.model.is_active == is_active)
        
        if search_term:
            search_filter = or_(
                self.model.title.ilike(f"%{search_term}%"),
                self.model.description.ilike(f"%{search_term}%")
            )
            query = query.where(search_filter)
        
        query = query.order_by(desc(self.model.updated_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()


# Create global instance
conversation_crud = CRUDConversation(Conversation)
