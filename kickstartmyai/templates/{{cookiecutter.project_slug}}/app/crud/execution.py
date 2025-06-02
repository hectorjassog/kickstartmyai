"""
CRUD operations for Execution model.

This module provides comprehensive CRUD operations for execution management,
including status tracking, performance monitoring, and execution tree management.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from decimal import Decimal

from sqlalchemy import and_, or_, desc, asc, func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.execution import Execution, ExecutionStatus, ExecutionType
from app.schemas.execution import ExecutionCreate, ExecutionUpdate, ExecutionFilter


class CRUDExecution(CRUDBase[Execution, ExecutionCreate, ExecutionUpdate]):
    """CRUD operations for Execution model."""

    async def create_with_user(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: ExecutionCreate, 
        user_id: UUID
    ) -> Execution:
        """Create a new execution for a specific user."""
        obj_in_data = obj_in.model_dump()
        obj_in_data["user_id"] = user_id
        obj_in_data["execution_id"] = f"exec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
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
        limit: int = 100
    ) -> List[Execution]:
        """Get executions by user ID with pagination."""
        query = select(self.model).where(
            self.model.user_id == user_id
        ).order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_user_with_count(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> Tuple[List[Execution], int]:
        """Get executions by user ID with total count."""
        # Build base queries
        base_query = select(self.model).where(self.model.user_id == user_id)
        count_query = select(func.count(self.model.id)).where(self.model.user_id == user_id)
        
        # Get count
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Get executions with pagination
        executions_query = base_query.order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        executions_result = await db.execute(executions_query)
        executions = executions_result.scalars().all()
        
        return executions, total_count

    async def get_by_agent(
        self, 
        db: AsyncSession, 
        *, 
        agent_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Execution]:
        """Get executions by agent ID."""
        query = select(self.model).where(
            self.model.agent_id == agent_id
        ).order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_conversation(
        self, 
        db: AsyncSession, 
        *, 
        conversation_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Execution]:
        """Get executions by conversation ID."""
        query = select(self.model).where(
            self.model.conversation_id == conversation_id
        ).order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_status(
        self, 
        db: AsyncSession, 
        *, 
        status: ExecutionStatus,
        user_id: Optional[UUID] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Execution]:
        """Get executions by status."""
        query = select(self.model).where(self.model.status == status)
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        query = query.order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_running_executions(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None
    ) -> List[Execution]:
        """Get all currently running executions."""
        query = select(self.model).where(self.model.status == ExecutionStatus.RUNNING)
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        query = query.order_by(asc(self.model.started_at))
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_pending_executions(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[Execution]:
        """Get pending executions ordered by priority and creation time."""
        query = select(self.model).where(self.model.status == ExecutionStatus.PENDING)
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        query = query.order_by(
            desc(self.model.priority), 
            asc(self.model.created_at)
        ).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_execution_id(
        self, 
        db: AsyncSession, 
        *, 
        execution_id: str
    ) -> Optional[Execution]:
        """Get execution by execution_id."""
        query = select(self.model).where(self.model.execution_id == execution_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_filtered(
        self, 
        db: AsyncSession, 
        *, 
        filters: ExecutionFilter,
        skip: int = 0,
        limit: int = 100
    ) -> List[Execution]:
        """Get executions with complex filtering."""
        query = select(self.model)
        
        # Apply filters
        if filters.user_id:
            query = query.where(self.model.user_id == filters.user_id)
        
        if filters.agent_id:
            query = query.where(self.model.agent_id == filters.agent_id)
        
        if filters.conversation_id:
            query = query.where(self.model.conversation_id == filters.conversation_id)
        
        if filters.parent_execution_id:
            query = query.where(self.model.parent_execution_id == filters.parent_execution_id)
        
        if filters.status:
            query = query.where(self.model.status == filters.status)
        
        if filters.execution_type:
            query = query.where(self.model.type == filters.execution_type)
        
        # Date filters
        if filters.created_after:
            query = query.where(self.model.created_at >= filters.created_after)
        
        if filters.created_before:
            query = query.where(self.model.created_at <= filters.created_before)
        
        if filters.started_after:
            query = query.where(self.model.started_at >= filters.started_after)
        
        if filters.started_before:
            query = query.where(self.model.started_at <= filters.started_before)
        
        query = query.order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def start_execution(
        self, 
        db: AsyncSession, 
        *, 
        execution_id: UUID
    ) -> Optional[Execution]:
        """Start an execution (update status to running)."""
        execution = await self.get(db, id=execution_id)
        if not execution:
            return None
        
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        
        db.add(execution)
        await db.commit()
        await db.refresh(execution)
        
        return execution

    async def complete_execution(
        self, 
        db: AsyncSession, 
        *, 
        execution_id: UUID,
        output_data: Optional[Dict[str, Any]] = None,
        tokens_used: Optional[int] = None,
        cost: Optional[Decimal] = None
    ) -> Optional[Execution]:
        """Complete an execution with results."""
        execution = await self.get(db, id=execution_id)
        if not execution:
            return None
        
        execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        
        if output_data:
            execution.output_data = output_data
        
        if tokens_used is not None:
            execution.tokens_used = tokens_used
        
        if cost is not None:
            execution.cost = cost
        
        # Calculate duration
        if execution.started_at:
            duration = execution.completed_at - execution.started_at
            execution.duration_seconds = duration.total_seconds()
        
        db.add(execution)
        await db.commit()
        await db.refresh(execution)
        
        return execution

    async def fail_execution(
        self, 
        db: AsyncSession, 
        *, 
        execution_id: UUID,
        error_message: str,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None
    ) -> Optional[Execution]:
        """Mark an execution as failed."""
        execution = await self.get(db, id=execution_id)
        if not execution:
            return None
        
        execution.status = ExecutionStatus.FAILED
        execution.completed_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        execution.error_message = error_message
        execution.error_type = error_type
        execution.stack_trace = stack_trace
        
        # Calculate duration if started
        if execution.started_at:
            duration = execution.completed_at - execution.started_at
            execution.duration_seconds = duration.total_seconds()
        
        db.add(execution)
        await db.commit()
        await db.refresh(execution)
        
        return execution

    async def cancel_execution(
        self, 
        db: AsyncSession, 
        *, 
        execution_id: UUID
    ) -> Optional[Execution]:
        """Cancel a pending or running execution."""
        execution = await self.get(db, id=execution_id)
        if not execution:
            return None
        
        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        
        # Calculate duration if started
        if execution.started_at:
            duration = execution.completed_at - execution.started_at
            execution.duration_seconds = duration.total_seconds()
        
        db.add(execution)
        await db.commit()
        await db.refresh(execution)
        
        return execution

    async def get_execution_tree(
        self, 
        db: AsyncSession, 
        *, 
        root_execution_id: UUID
    ) -> Optional[Execution]:
        """Get execution with all child executions loaded."""
        query = select(self.model).where(
            self.model.id == root_execution_id
        ).options(selectinload(self.model.children))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_children(
        self, 
        db: AsyncSession, 
        *, 
        parent_execution_id: UUID
    ) -> List[Execution]:
        """Get child executions of a parent execution."""
        query = select(self.model).where(
            self.model.parent_execution_id == parent_execution_id
        ).order_by(asc(self.model.created_at))
        
        result = await db.execute(query)
        return result.scalars().all()

    async def count_by_status(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None
    ) -> Dict[str, int]:
        """Get count of executions by status."""
        query = select(
            self.model.status,
            func.count(self.model.id)
        )
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        query = query.group_by(self.model.status)
        
        result = await db.execute(query)
        status_counts = {str(status): count for status, count in result.all()}
        
        return status_counts

    async def get_performance_stats(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get performance statistics for executions."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(self.model).where(self.model.created_at >= cutoff_date)
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        if agent_id:
            query = query.where(self.model.agent_id == agent_id)
        
        # Get basic stats
        stats_query = select(
            func.count(self.model.id),
            func.avg(self.model.duration_seconds),
            func.max(self.model.duration_seconds),
            func.min(self.model.duration_seconds),
            func.sum(self.model.tokens_used),
            func.sum(self.model.cost)
        ).select_from(query.subquery())
        
        stats_result = await db.execute(stats_query)
        stats = stats_result.first()
        
        # Get success rate
        success_query = select(func.count(self.model.id)).select_from(
            query.where(self.model.status == ExecutionStatus.COMPLETED).subquery()
        )
        success_result = await db.execute(success_query)
        success_count = success_result.scalar()
        
        total_count = stats[0] or 0
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        return {
            "total_executions": total_count,
            "successful_executions": success_count,
            "success_rate": success_rate,
            "average_duration_seconds": float(stats[1] or 0),
            "max_duration_seconds": float(stats[2] or 0),
            "min_duration_seconds": float(stats[3] or 0),
            "total_tokens_used": stats[4] or 0,
            "total_cost": float(stats[5] or 0),
            "period_days": days
        }

    async def get_recent_failures(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[Execution]:
        """Get recent failed executions."""
        query = select(self.model).where(self.model.status == ExecutionStatus.FAILED)
        
        if user_id:
            query = query.where(self.model.user_id == user_id)
        
        query = query.order_by(desc(self.model.completed_at)).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def cleanup_old_executions(
        self, 
        db: AsyncSession, 
        *, 
        days_old: int = 90,
        batch_size: int = 1000
    ) -> int:
        """Clean up old completed executions."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Delete old completed executions in batches
        query = select(self.model.id).where(
            and_(
                self.model.status.in_([
                    ExecutionStatus.COMPLETED, 
                    ExecutionStatus.FAILED, 
                    ExecutionStatus.CANCELLED
                ]),
                self.model.completed_at < cutoff_date
            )
        ).limit(batch_size)
        
        result = await db.execute(query)
        execution_ids = result.scalars().all()
        
        if not execution_ids:
            return 0
        
        # Delete the executions
        delete_query = delete(self.model).where(self.model.id.in_(execution_ids))
        delete_result = await db.execute(delete_query)
        await db.commit()
        
        return delete_result.rowcount

    async def retry_execution(
        self, 
        db: AsyncSession, 
        *, 
        execution_id: UUID
    ) -> Optional[Execution]:
        """Create a retry of a failed execution."""
        original_execution = await self.get(db, id=execution_id)
        if not original_execution or original_execution.status != ExecutionStatus.FAILED:
            return None
        
        # Create new execution based on the original
        retry_data = {
            "user_id": original_execution.user_id,
            "agent_id": original_execution.agent_id,
            "conversation_id": original_execution.conversation_id,
            "parent_execution_id": original_execution.parent_execution_id,
            "type": original_execution.type,
            "input_data": original_execution.input_data,
            "priority": original_execution.priority,
            "retry_count": (original_execution.retry_count or 0) + 1,
            "original_execution_id": original_execution.id
        }
        
        retry_execution = self.model(**retry_data)
        retry_execution.execution_id = f"exec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        db.add(retry_execution)
        await db.commit()
        await db.refresh(retry_execution)
        
        return retry_execution

    async def get_execution_statistics(
        self, 
        db: AsyncSession, 
        *, 
        user_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get comprehensive execution statistics."""
        base_query = select(self.model)
        
        if user_id:
            base_query = base_query.where(self.model.user_id == user_id)
        
        if agent_id:
            base_query = base_query.where(self.model.agent_id == agent_id)
        
        # Get status counts
        status_counts = await self.count_by_status(db, user_id=user_id)
        
        # Get performance stats for last 30 days
        performance_stats = await self.get_performance_stats(
            db, user_id=user_id, agent_id=agent_id, days=30
        )
        
        # Get type distribution
        type_result = await db.execute(
            select(
                self.model.type,
                func.count(self.model.id)
            ).select_from(base_query.subquery()).group_by(self.model.type)
        )
        type_counts = {str(exec_type): count for exec_type, count in type_result.all()}
        
        return {
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "performance_metrics": performance_stats
        }


# Create global instance
execution_crud = CRUDExecution(Execution)
