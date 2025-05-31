"""
CRUD operations for Agent model.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models.agent import Agent, AgentType, AgentStatus
from app.schemas.agent import AgentCreate, AgentUpdate, AgentFilter


class CRUDAgent(CRUDBase[Agent, AgentCreate, AgentUpdate]):
    """CRUD operations for Agent model."""

    def create_with_user(
        self, 
        db: Session, 
        *, 
        obj_in: AgentCreate, 
        user_id: UUID
    ) -> Agent:
        """Create a new agent for a specific user."""
        obj_in_data = obj_in.model_dump()
        obj_in_data["user_id"] = user_id
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_user(
        self, 
        db: Session, 
        *, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Agent]:
        """Get agents by user ID with pagination."""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .filter(self.model.status != AgentStatus.DEPRECATED)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_type(
        self, 
        db: Session, 
        *, 
        user_id: UUID, 
        agent_type: AgentType,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """Get agents by user ID and type."""
        return (
            db.query(self.model)
            .filter(and_(
                self.model.user_id == user_id,
                self.model.agent_type == agent_type,
                self.model.status != AgentStatus.DEPRECATED
            ))
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_name(
        self, 
        db: Session, 
        *, 
        user_id: UUID, 
        name: str
    ) -> Optional[Agent]:
        """Get agent by name for a specific user."""
        return (
            db.query(self.model)
            .filter(and_(
                self.model.user_id == user_id,
                self.model.name == name
            ))
            .first()
        )

    def get_active_agents(
        self, 
        db: Session, 
        *, 
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """Get all active agents, optionally filtered by user."""
        query = db.query(self.model).filter(self.model.status == AgentStatus.ACTIVE)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        return (
            query
            .order_by(desc(self.model.last_used_at), desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_tags(
        self, 
        db: Session, 
        *, 
        tags: List[str], 
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """Get agents by tags."""
        query = db.query(self.model)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        # Filter by tags (any of the provided tags)
        tag_conditions = []
        for tag in tags:
            tag_conditions.append(self.model.tags.contains([tag]))
        
        if tag_conditions:
            query = query.filter(or_(*tag_conditions))
        
        return (
            query
            .filter(self.model.status != AgentStatus.DEPRECATED)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_agents(
        self, 
        db: Session, 
        *, 
        search_term: str,
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """Search agents by name and description."""
        query = db.query(self.model)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        # Search in name and description
        search_filter = or_(
            self.model.name.ilike(f"%{search_term}%"),
            self.model.description.ilike(f"%{search_term}%")
        )
        
        return (
            query
            .filter(search_filter)
            .filter(self.model.status != AgentStatus.DEPRECATED)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_filtered(
        self, 
        db: Session, 
        *, 
        filters: AgentFilter,
        skip: int = 0,
        limit: int = 100
    ) -> List[Agent]:
        """Get agents with complex filtering."""
        query = db.query(self.model)
        
        # Apply filters
        if filters.user_id:
            query = query.filter(self.model.user_id == filters.user_id)
        
        if filters.agent_type:
            query = query.filter(self.model.agent_type == filters.agent_type)
        
        if filters.status:
            query = query.filter(self.model.status == filters.status)
        
        if filters.name_contains:
            query = query.filter(self.model.name.ilike(f"%{filters.name_contains}%"))
        
        if filters.tags:
            tag_conditions = []
            for tag in filters.tags:
                tag_conditions.append(self.model.tags.contains([tag]))
            if tag_conditions:
                query = query.filter(or_(*tag_conditions))
        
        if filters.created_after:
            query = query.filter(self.model.created_at >= filters.created_after)
        
        if filters.created_before:
            query = query.filter(self.model.created_at <= filters.created_before)
        
        if filters.last_used_after:
            query = query.filter(self.model.last_used_at >= filters.last_used_after)
        
        if filters.last_used_before:
            query = query.filter(self.model.last_used_at <= filters.last_used_before)
        
        return (
            query
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_user(self, db: Session, *, user_id: UUID) -> int:
        """Count total agents for a user."""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .filter(self.model.status != AgentStatus.DEPRECATED)
            .count()
        )

    def count_by_type(
        self, 
        db: Session, 
        *, 
        agent_type: AgentType, 
        user_id: Optional[UUID] = None
    ) -> int:
        """Count agents by type."""
        query = db.query(self.model).filter(self.model.agent_type == agent_type)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        return query.filter(self.model.status != AgentStatus.DEPRECATED).count()

    def get_most_used(
        self, 
        db: Session, 
        *, 
        user_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[Agent]:
        """Get most used agents."""
        query = db.query(self.model)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        return (
            query
            .filter(self.model.status == AgentStatus.ACTIVE)
            .order_by(desc(self.model.usage_count), desc(self.model.last_used_at))
            .limit(limit)
            .all()
        )

    def get_recently_used(
        self, 
        db: Session, 
        *, 
        user_id: UUID,
        limit: int = 10
    ) -> List[Agent]:
        """Get recently used agents for a user."""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .filter(self.model.last_used_at.isnot(None))
            .filter(self.model.status == AgentStatus.ACTIVE)
            .order_by(desc(self.model.last_used_at))
            .limit(limit)
            .all()
        )

    def update_usage(
        self, 
        db: Session, 
        *, 
        agent_id: UUID
    ) -> Optional[Agent]:
        """Update agent usage statistics."""
        db_obj = db.query(self.model).filter(self.model.id == agent_id).first()
        if db_obj:
            db_obj.usage_count += 1
            db_obj.last_used_at = datetime.utcnow()
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def set_status(
        self, 
        db: Session, 
        *, 
        agent_id: UUID, 
        status: AgentStatus
    ) -> Optional[Agent]:
        """Update agent status."""
        db_obj = db.query(self.model).filter(self.model.id == agent_id).first()
        if db_obj:
            db_obj.status = status
            db_obj.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def get_with_executions(
        self, 
        db: Session, 
        *, 
        agent_id: UUID
    ) -> Optional[Agent]:
        """Get agent with its executions."""
        return (
            db.query(self.model)
            .options(selectinload(self.model.executions))
            .filter(self.model.id == agent_id)
            .first()
        )

    def get_statistics(
        self, 
        db: Session, 
        *, 
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get agent statistics."""
        query = db.query(self.model)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        # Total counts by status
        total_active = query.filter(self.model.status == AgentStatus.ACTIVE).count()
        total_inactive = query.filter(self.model.status == AgentStatus.INACTIVE).count()
        total_maintenance = query.filter(self.model.status == AgentStatus.MAINTENANCE).count()
        total_deprecated = query.filter(self.model.status == AgentStatus.DEPRECATED).count()
        
        # Counts by type
        type_counts = {}
        for agent_type in AgentType:
            type_counts[agent_type.value] = (
                query.filter(self.model.agent_type == agent_type)
                .filter(self.model.status != AgentStatus.DEPRECATED)
                .count()
            )
        
        # Usage statistics
        total_usage = db.query(func.sum(self.model.usage_count)).scalar() or 0
        avg_usage = db.query(func.avg(self.model.usage_count)).scalar() or 0
        
        return {
            "total_agents": total_active + total_inactive + total_maintenance,
            "total_active": total_active,
            "total_inactive": total_inactive,
            "total_maintenance": total_maintenance,
            "total_deprecated": total_deprecated,
            "by_type": type_counts,
            "total_usage": int(total_usage),
            "average_usage": float(avg_usage),
        }

    def duplicate_agent(
        self, 
        db: Session, 
        *, 
        agent_id: UUID, 
        new_name: str,
        user_id: UUID
    ) -> Optional[Agent]:
        """Create a duplicate of an existing agent."""
        original = db.query(self.model).filter(self.model.id == agent_id).first()
        if not original:
            return None
        
        # Create new agent with same configuration
        agent_data = {
            "name": new_name,
            "description": f"Copy of {original.name}",
            "agent_type": original.agent_type,
            "status": AgentStatus.ACTIVE,
            "system_prompt": original.system_prompt,
            "max_tokens": original.max_tokens,
            "temperature": original.temperature,
            "top_p": original.top_p,
            "tools_enabled": original.tools_enabled,
            "memory_enabled": original.memory_enabled,
            "streaming_enabled": original.streaming_enabled,
            "tags": original.tags.copy() if original.tags else [],
            "configuration": original.configuration.copy() if original.configuration else {},
            "metadata": original.metadata.copy() if original.metadata else {},
            "user_id": user_id
        }
        
        db_obj = self.model(**agent_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


agent = CRUDAgent(Agent)
