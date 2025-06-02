"""
CRUD operations for Agent model.

This module provides comprehensive CRUD operations for agent management,
including advanced querying, filtering, and analytics.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy import and_, or_, desc, asc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.agent import Agent, AgentType, AgentStatus
from app.schemas.agent import AgentCreate, AgentUpdate


class CRUDAgent(CRUDBase[Agent, AgentCreate, AgentUpdate]):
    """CRUD operations for Agent model."""

    async def create_with_user(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: AgentCreate, 
        user_id: UUID
    ) -> Agent:
        """Create a new agent for a specific user."""
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
        include_deprecated: bool = False
    ) -> List[Agent]:
        """Get agents by user ID with pagination."""
        query = select(self.model).where(self.model.user_id == user_id)
        
        if not include_deprecated:
            query = query.where(self.model.status != AgentStatus.DEPRECATED)
        
        query = query.order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_user_with_count(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        include_deprecated: bool = False
    ) -> Tuple[List[Agent], int]:
        """Get agents by user ID with total count."""
        # Build base queries
        base_query = select(self.model).where(self.model.user_id == user_id)
        count_query = select(func.count(self.model.id)).where(self.model.user_id == user_id)
        
        if not include_deprecated:
            base_query = base_query.where(self.model.status != AgentStatus.DEPRECATED)
            count_query = count_query.where(self.model.status != AgentStatus.DEPRECATED)
        
        # Get count
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Get agents with pagination
        agents_query = base_query.order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        agents_result = await db.execute(agents_query)
        agents = agents_result.scalars().all()
        
        return agents, total_count

    async def get_by_user_and_type(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID, 
        agent_type: AgentType,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """Get agents by user ID and type."""
        query = select(self.model).where(
            and_(
                self.model.user_id == user_id,
                self.model.agent_type == agent_type,
                self.model.status != AgentStatus.DEPRECATED
            )
        ).order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_name(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID, 
        name: str
    ) -> Optional[Agent]:
        """Get agent by name for a specific user."""
        query = select(self.model).where(
            and_(
                self.model.user_id == user_id,
                self.model.name == name
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_agents(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """Get all active agents, optionally filtered by user."""
        query = select(self.model).where(self.model.status == AgentStatus.ACTIVE)
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        query = query.order_by(
            desc(self.model.last_used_at), 
            desc(self.model.created_at)
        ).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_tags(
        self, 
        db: AsyncSession, 
        *, 
        tags: List[str], 
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """Get agents by tags."""
        query = select(self.model)
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        # Filter by tags (any of the provided tags)
        if tags:
            tag_conditions = []
            for tag in tags:
                # Assuming tags is a JSON array field
                tag_conditions.append(self.model.tags.contains([tag]))
            
            if tag_conditions:
                query = query.where(or_(*tag_conditions))
        
        query = query.where(self.model.status != AgentStatus.DEPRECATED).order_by(
            desc(self.model.created_at)
        ).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def search_agents(
        self, 
        db: AsyncSession, 
        *, 
        search_term: str,
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """Search agents by name and description."""
        query = select(self.model)
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        # Search in name and description
        search_filter = or_(
            self.model.name.ilike(f"%{search_term}%"),
            self.model.description.ilike(f"%{search_term}%")
        )
        
        query = query.where(search_filter).where(
            self.model.status != AgentStatus.DEPRECATED
        ).order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_filtered(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None,
        agent_type: Optional[AgentType] = None,
        status: Optional[AgentStatus] = None,
        tags: Optional[List[str]] = None,
        search_term: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """Get agents with complex filtering."""
        query = select(self.model)
        
        # Apply filters
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        if agent_type:
            query = query.where(self.model.agent_type == agent_type)
        
        if status:
            query = query.where(self.model.status == status)
        
        if tags:
            tag_conditions = []
            for tag in tags:
                tag_conditions.append(self.model.tags.contains([tag]))
            if tag_conditions:
                query = query.where(or_(*tag_conditions))
        
        if search_term:
            search_filter = or_(
                self.model.name.ilike(f"%{search_term}%"),
                self.model.description.ilike(f"%{search_term}%")
            )
            query = query.where(search_filter)
        
        query = query.order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def count_by_user(self, db: AsyncSession, *, user_id: UUID) -> int:
        """Count agents by user."""
        query = select(func.count(self.model.id)).where(
            and_(
                self.model.user_id == user_id,
                self.model.status != AgentStatus.DEPRECATED
            )
        )
        
        result = await db.execute(query)
        return result.scalar()

    async def count_by_type(
        self, 
        db: AsyncSession, 
        *, 
        agent_type: AgentType, 
        user_id: Optional[UUID] = None
    ) -> int:
        """Count agents by type."""
        query = select(func.count(self.model.id)).where(
            self.model.agent_type == agent_type
        )
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        result = await db.execute(query)
        return result.scalar()

    async def get_most_used(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[Agent]:
        """Get most used agents."""
        query = select(self.model).where(self.model.status == AgentStatus.ACTIVE)
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        query = query.order_by(
            desc(self.model.usage_count),
            desc(self.model.last_used_at)
        ).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_recently_used(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID,
        limit: int = 10
    ) -> List[Agent]:
        """Get recently used agents for a user."""
        query = select(self.model).where(
            and_(
                self.model.user_id == user_id,
                self.model.last_used_at.is_not(None),
                self.model.status == AgentStatus.ACTIVE
            )
        ).order_by(desc(self.model.last_used_at)).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def update_usage(
        self, 
        db: AsyncSession, 
        *, 
        agent_id: UUID
    ) -> Optional[Agent]:
        """Update agent usage statistics."""
        agent = await self.get(db, id=agent_id)
        if not agent:
            return None
        
        agent.usage_count = (agent.usage_count or 0) + 1
        agent.last_used_at = datetime.utcnow()
        agent.updated_at = datetime.utcnow()
        
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        return agent

    async def set_status(
        self, 
        db: AsyncSession, 
        *, 
        agent_id: UUID, 
        status: AgentStatus
    ) -> Optional[Agent]:
        """Set agent status."""
        agent = await self.get(db, id=agent_id)
        if not agent:
            return None
        
        agent.status = status
        agent.updated_at = datetime.utcnow()
        
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        return agent

    async def get_with_executions(
        self, 
        db: AsyncSession, 
        *, 
        agent_id: UUID
    ) -> Optional[Agent]:
        """Get agent with its executions loaded."""
        query = select(self.model).where(
            self.model.id == agent_id
        ).options(selectinload(self.model.executions))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_statistics(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get agent statistics."""
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
                base_query.where(self.model.status == AgentStatus.ACTIVE).subquery()
            )
        )
        active_count = active_result.scalar()
        
        # Count by type
        type_result = await db.execute(
            select(
                self.model.agent_type,
                func.count(self.model.id)
            ).select_from(base_query.subquery()).group_by(self.model.agent_type)
        )
        type_counts = {str(agent_type): count for agent_type, count in type_result.all()}
        
        # Usage statistics
        usage_result = await db.execute(
            select(
                func.sum(self.model.usage_count),
                func.avg(self.model.usage_count),
                func.max(self.model.usage_count)
            ).select_from(base_query.subquery())
        )
        usage_stats = usage_result.first()
        
        return {
            "total_agents": total_count,
            "active_agents": active_count,
            "deprecated_agents": total_count - active_count,
            "agents_by_type": type_counts,
            "usage_statistics": {
                "total_usage": usage_stats[0] or 0,
                "average_usage": float(usage_stats[1] or 0),
                "max_usage": usage_stats[2] or 0
            }
        }

    async def duplicate_agent(
        self, 
        db: AsyncSession, 
        *, 
        agent_id: UUID, 
        new_name: str,
        user_id: UUID
    ) -> Optional[Agent]:
        """Duplicate an existing agent."""
        original_agent = await self.get(db, id=agent_id)
        if not original_agent:
            return None
        
        # Create new agent with copied data
        agent_data = {
            "name": new_name,
            "description": f"Copy of {original_agent.name}",
            "agent_type": original_agent.agent_type,
            "instructions": original_agent.instructions,
            "capabilities": original_agent.capabilities,
            "configuration": original_agent.configuration,
            "tags": original_agent.tags or [],
            "user_id": user_id,
            "status": AgentStatus.DRAFT
        }
        
        new_agent = self.model(**agent_data)
        db.add(new_agent)
        await db.commit()
        await db.refresh(new_agent)
        
        return new_agent


# Create global instance
agent_crud = CRUDAgent(Agent)
