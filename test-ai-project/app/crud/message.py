"""
Message CRUD operations.

This module provides comprehensive CRUD operations for message management,
including conversation threading, role-based filtering, and content search.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy import and_, or_, desc, asc, func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.message import Message, MessageRole
from app.schemas.message import MessageCreate, MessageUpdate


class CRUDMessage(CRUDBase[Message, MessageCreate, MessageUpdate]):
    """CRUD operations for Message model."""

    async def create_with_conversation(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: MessageCreate, 
        conversation_id: UUID
    ) -> Message:
        """Create a new message for a specific conversation."""
        obj_in_data = obj_in.model_dump()
        obj_in_data["conversation_id"] = conversation_id
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_conversation(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        order_by_desc: bool = False
    ) -> List[Message]:
        """Get messages by conversation ID with pagination."""
        query = select(self.model).where(self.model.conversation_id == conversation_id)
        
        if order_by_desc:
            query = query.order_by(desc(self.model.created_at))
        else:
            query = query.order_by(asc(self.model.created_at))
        
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_conversation_with_count(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        order_by_desc: bool = False
    ) -> Tuple[List[Message], int]:
        """Get messages by conversation ID with total count."""
        # Build base queries
        base_query = select(self.model).where(self.model.conversation_id == conversation_id)
        count_query = select(func.count(self.model.id)).where(self.model.conversation_id == conversation_id)
        
        # Get count
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Get messages with pagination
        if order_by_desc:
            messages_query = base_query.order_by(desc(self.model.created_at))
        else:
            messages_query = base_query.order_by(asc(self.model.created_at))
        
        messages_query = messages_query.offset(skip).limit(limit)
        messages_result = await db.execute(messages_query)
        messages = messages_result.scalars().all()
        
        return messages, total_count

    async def get_by_role(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID,
        role: MessageRole,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Message]:
        """Get messages by conversation ID and role."""
        query = select(self.model).where(
            and_(
                self.model.conversation_id == conversation_id,
                self.model.role == role
            )
        ).order_by(asc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_recent_messages(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID,
        minutes: int = 60,
        limit: int = 50
    ) -> List[Message]:
        """Get recent messages from a conversation."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        query = select(self.model).where(
            and_(
                self.model.conversation_id == conversation_id,
                self.model.created_at >= cutoff_time
            )
        ).order_by(desc(self.model.created_at)).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def search_messages(
        self, 
        db: AsyncSession, 
        *, 
        search_term: str,
        conversation_id: Optional[UUID] = None,
        role: Optional[MessageRole] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """Search messages by content."""
        query = select(self.model)
        
        # Search in content
        search_filter = self.model.content.ilike(f"%{search_term}%")
        query = query.where(search_filter)
        
        # Apply additional filters
        if conversation_id:
            query = query.where(self.model.conversation_id == conversation_id)
        
        if role:
            query = query.where(self.model.role == role)
        
        query = query.order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_conversation_context(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID,
        max_messages: int = 20,
        include_system: bool = True
    ) -> List[Message]:
        """Get conversation context for AI processing."""
        query = select(self.model).where(self.model.conversation_id == conversation_id)
        
        if not include_system:
            query = query.where(self.model.role != MessageRole.SYSTEM)
        
        # Get most recent messages
        query = query.order_by(desc(self.model.created_at)).limit(max_messages)
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        # Return in chronological order for context
        return list(reversed(messages))

    async def get_last_message(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID,
        role: Optional[MessageRole] = None
    ) -> Optional[Message]:
        """Get the last message in a conversation."""
        query = select(self.model).where(self.model.conversation_id == conversation_id)
        
        if role:
            query = query.where(self.model.role == role)
        
        query = query.order_by(desc(self.model.created_at)).limit(1)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_message_thread(
        self, 
        db: AsyncSession, 
        *, 
        parent_message_id: UUID,
        max_depth: int = 10
    ) -> List[Message]:
        """Get message thread (if threading is implemented)."""
        # This is a placeholder for future message threading functionality
        # For now, just return the parent message
        parent_message = await self.get(db, id=parent_message_id)
        return [parent_message] if parent_message else []

    async def count_by_conversation(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID
    ) -> int:
        """Count messages in a conversation."""
        query = select(func.count(self.model.id)).where(
            self.model.conversation_id == conversation_id
        )
        
        result = await db.execute(query)
        return result.scalar()

    async def count_by_role(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID,
        role: MessageRole
    ) -> int:
        """Count messages by role in a conversation."""
        query = select(func.count(self.model.id)).where(
            and_(
                self.model.conversation_id == conversation_id,
                self.model.role == role
            )
        )
        
        result = await db.execute(query)
        return result.scalar()

    async def get_message_statistics(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get message statistics."""
        base_query = select(self.model)
        if conversation_id:
            base_query = base_query.where(self.model.conversation_id == conversation_id)
        
        # Total count
        total_result = await db.execute(
            select(func.count(self.model.id)).select_from(base_query.subquery())
        )
        total_count = total_result.scalar()
        
        # Count by role
        role_result = await db.execute(
            select(
                self.model.role,
                func.count(self.model.id)
            ).select_from(base_query.subquery()).group_by(self.model.role)
        )
        role_counts = {str(role): count for role, count in role_result.all()}
        
        # Content length statistics
        length_result = await db.execute(
            select(
                func.avg(func.length(self.model.content)),
                func.max(func.length(self.model.content)),
                func.min(func.length(self.model.content))
            ).select_from(base_query.subquery())
        )
        length_stats = length_result.first()
        
        return {
            "total_messages": total_count,
            "messages_by_role": role_counts,
            "content_length_statistics": {
                "average_length": float(length_stats[0] or 0),
                "max_length": length_stats[1] or 0,
                "min_length": length_stats[2] or 0
            }
        }

    async def delete_conversation_messages(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID
    ) -> int:
        """Delete all messages in a conversation."""
        result = await db.execute(
            delete(self.model).where(self.model.conversation_id == conversation_id)
        )
        await db.commit()
        return result.rowcount

    async def update_message_metadata(
        self, 
        db: AsyncSession, 
        *, 
        message_id: UUID,
        metadata: Dict[str, Any]
    ) -> Optional[Message]:
        """Update message metadata."""
        message = await self.get(db, id=message_id)
        if not message:
            return None
        
        # Merge new metadata with existing
        existing_metadata = message.metadata or {}
        existing_metadata.update(metadata)
        
        message.metadata = existing_metadata
        message.updated_at = datetime.utcnow()
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        
        return message

    async def get_filtered(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: Optional[UUID] = None,
        role: Optional[MessageRole] = None,
        search_term: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """Get messages with complex filtering."""
        query = select(self.model)
        
        # Apply filters
        if conversation_id:
            query = query.where(self.model.conversation_id == conversation_id)
        
        if role:
            query = query.where(self.model.role == role)
        
        if search_term:
            search_filter = self.model.content.ilike(f"%{search_term}%")
            query = query.where(search_filter)
        
        if created_after:
            query = query.where(self.model.created_at >= created_after)
        
        if created_before:
            query = query.where(self.model.created_at <= created_before)
        
        query = query.order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def bulk_create_messages(
        self, 
        db: AsyncSession, 
        *, 
        messages: List[MessageCreate],
        conversation_id: UUID
    ) -> List[Message]:
        """Create multiple messages in bulk for a conversation."""
        db_objs = []
        for message_data in messages:
            obj_in_data = message_data.model_dump()
            obj_in_data["conversation_id"] = conversation_id
            db_obj = self.model(**obj_in_data)
            db_objs.append(db_obj)
        
        db.add_all(db_objs)
        await db.commit()
        
        for db_obj in db_objs:
            await db.refresh(db_obj)
        
        return db_objs


# Create global instance
message_crud = CRUDMessage(Message)
