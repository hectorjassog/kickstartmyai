"""
CRUD operations for Execution model.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from decimal import Decimal

from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models.execution import Execution, ExecutionStatus, ExecutionType
from app.schemas.execution import ExecutionCreate, ExecutionUpdate, ExecutionFilter


class CRUDExecution(CRUDBase[Execution, ExecutionCreate, ExecutionUpdate]):
    """CRUD operations for Execution model."""

    def create_with_user(
        self, 
        db: Session, 
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
    ) -> List[Execution]:
        """Get executions by user ID with pagination."""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_agent(
        self, 
        db: Session, 
        *, 
        agent_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Execution]:
        """Get executions by agent ID."""
        return (
            db.query(self.model)
            .filter(self.model.agent_id == agent_id)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_conversation(
        self, 
        db: Session, 
        *, 
        conversation_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Execution]:
        """Get executions by conversation ID."""
        return (
            db.query(self.model)
            .filter(self.model.conversation_id == conversation_id)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_status(
        self, 
        db: Session, 
        *, 
        status: ExecutionStatus,
        user_id: Optional[UUID] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Execution]:
        """Get executions by status."""
        query = db.query(self.model).filter(self.model.status == status)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        return (
            query
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_running_executions(
        self, 
        db: Session, 
        *, 
        user_id: Optional[UUID] = None
    ) -> List[Execution]:
        """Get all currently running executions."""
        query = db.query(self.model).filter(self.model.status == ExecutionStatus.RUNNING)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        return query.order_by(asc(self.model.started_at)).all()

    def get_pending_executions(
        self, 
        db: Session, 
        *, 
        user_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[Execution]:
        """Get pending executions ordered by priority and creation time."""
        query = db.query(self.model).filter(self.model.status == ExecutionStatus.PENDING)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        return (
            query
            .order_by(desc(self.model.priority), asc(self.model.created_at))
            .limit(limit)
            .all()
        )

    def get_by_execution_id(
        self, 
        db: Session, 
        *, 
        execution_id: str
    ) -> Optional[Execution]:
        """Get execution by execution_id."""
        return (
            db.query(self.model)
            .filter(self.model.execution_id == execution_id)
            .first()
        )

    def get_filtered(
        self, 
        db: Session, 
        *, 
        filters: ExecutionFilter,
        skip: int = 0,
        limit: int = 100
    ) -> List[Execution]:
        """Get executions with complex filtering."""
        query = db.query(self.model)
        
        # Apply filters
        if filters.user_id:
            query = query.filter(self.model.user_id == filters.user_id)
        
        if filters.agent_id:
            query = query.filter(self.model.agent_id == filters.agent_id)
        
        if filters.conversation_id:
            query = query.filter(self.model.conversation_id == filters.conversation_id)
        
        if filters.parent_execution_id:
            query = query.filter(self.model.parent_execution_id == filters.parent_execution_id)
        
        if filters.status:
            query = query.filter(self.model.status == filters.status)
        
        if filters.execution_type:
            query = query.filter(self.model.type == filters.execution_type)
        
        # Date filters
        if filters.created_after:
            query = query.filter(self.model.created_at >= filters.created_after)
        
        if filters.created_before:
            query = query.filter(self.model.created_at <= filters.created_before)
        
        if filters.started_after:
            query = query.filter(self.model.started_at >= filters.started_after)
        
        if filters.started_before:
            query = query.filter(self.model.started_at <= filters.started_before)
        
        if filters.ended_after:
            query = query.filter(self.model.completed_at >= filters.ended_after)
        
        if filters.ended_before:
            query = query.filter(self.model.completed_at <= filters.ended_before)
        
        # Performance filters
        if filters.min_execution_time_ms:
            query = query.filter(self.model.duration_seconds >= filters.min_execution_time_ms / 1000)
        
        if filters.max_execution_time_ms:
            query = query.filter(self.model.duration_seconds <= filters.max_execution_time_ms / 1000)
        
        if filters.min_tokens_used:
            query = query.filter(self.model.tokens_used >= filters.min_tokens_used)
        
        if filters.max_tokens_used:
            query = query.filter(self.model.tokens_used <= filters.max_tokens_used)
        
        if filters.min_cost:
            query = query.filter(self.model.cost_usd >= str(filters.min_cost))
        
        if filters.max_cost:
            query = query.filter(self.model.cost_usd <= str(filters.max_cost))
        
        # Error filters
        if filters.has_errors is not None:
            if filters.has_errors:
                query = query.filter(self.model.error_message.isnot(None))
            else:
                query = query.filter(self.model.error_message.is_(None))
        
        if filters.error_contains:
            query = query.filter(self.model.error_message.ilike(f"%{filters.error_contains}%"))
        
        return (
            query
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def start_execution(
        self, 
        db: Session, 
        *, 
        execution_id: UUID
    ) -> Optional[Execution]:
        """Mark execution as started."""
        db_obj = db.query(self.model).filter(self.model.id == execution_id).first()
        if db_obj and db_obj.status == ExecutionStatus.PENDING:
            db_obj.status = ExecutionStatus.RUNNING
            db_obj.started_at = datetime.utcnow()
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def complete_execution(
        self, 
        db: Session, 
        *, 
        execution_id: UUID,
        output_data: Optional[Dict[str, Any]] = None,
        tokens_used: Optional[int] = None,
        cost: Optional[Decimal] = None
    ) -> Optional[Execution]:
        """Mark execution as completed."""
        db_obj = db.query(self.model).filter(self.model.id == execution_id).first()
        if db_obj and db_obj.status == ExecutionStatus.RUNNING:
            now = datetime.utcnow()
            db_obj.status = ExecutionStatus.COMPLETED
            db_obj.completed_at = now
            
            if db_obj.started_at:
                db_obj.duration_seconds = int((now - db_obj.started_at).total_seconds())
            
            if output_data is not None:
                db_obj.output_data = output_data
            
            if tokens_used is not None:
                db_obj.tokens_used = tokens_used
            
            if cost is not None:
                db_obj.cost_usd = str(cost)
            
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def fail_execution(
        self, 
        db: Session, 
        *, 
        execution_id: UUID,
        error_message: str,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None
    ) -> Optional[Execution]:
        """Mark execution as failed."""
        db_obj = db.query(self.model).filter(self.model.id == execution_id).first()
        if db_obj and db_obj.status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            now = datetime.utcnow()
            db_obj.status = ExecutionStatus.FAILED
            db_obj.completed_at = now
            db_obj.error_message = error_message
            db_obj.error_type = error_type
            db_obj.stack_trace = stack_trace
            
            if db_obj.started_at:
                db_obj.duration_seconds = int((now - db_obj.started_at).total_seconds())
            
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def cancel_execution(
        self, 
        db: Session, 
        *, 
        execution_id: UUID
    ) -> Optional[Execution]:
        """Cancel a pending or running execution."""
        db_obj = db.query(self.model).filter(self.model.id == execution_id).first()
        if db_obj and db_obj.status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            now = datetime.utcnow()
            db_obj.status = ExecutionStatus.CANCELLED
            db_obj.completed_at = now
            
            if db_obj.started_at:
                db_obj.duration_seconds = int((now - db_obj.started_at).total_seconds())
            
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def get_execution_tree(
        self, 
        db: Session, 
        *, 
        root_execution_id: UUID
    ) -> Optional[Execution]:
        """Get execution with all its child executions."""
        return (
            db.query(self.model)
            .options(selectinload(self.model.child_executions))
            .filter(self.model.id == root_execution_id)
            .first()
        )

    def get_children(
        self, 
        db: Session, 
        *, 
        parent_execution_id: UUID
    ) -> List[Execution]:
        """Get child executions of a parent execution."""
        return (
            db.query(self.model)
            .filter(self.model.parent_execution_id == parent_execution_id)
            .order_by(asc(self.model.created_at))
            .all()
        )

    def count_by_status(
        self, 
        db: Session, 
        *, 
        user_id: Optional[UUID] = None
    ) -> Dict[str, int]:
        """Count executions by status."""
        query = db.query(self.model)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        counts = {}
        for status in ExecutionStatus:
            counts[status.value] = query.filter(self.model.status == status).count()
        
        return counts

    def get_performance_stats(
        self, 
        db: Session, 
        *, 
        user_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get performance statistics for executions."""
        query = db.query(self.model)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        if agent_id:
            query = query.filter(self.model.agent_id == agent_id)
        
        # Filter by date range
        start_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(self.model.created_at >= start_date)
        
        # Get basic counts
        total_executions = query.count()
        successful_executions = query.filter(self.model.status == ExecutionStatus.COMPLETED).count()
        failed_executions = query.filter(self.model.status == ExecutionStatus.FAILED).count()
        
        # Calculate success rate
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
        
        # Get performance metrics (only for completed executions)
        completed_query = query.filter(self.model.status == ExecutionStatus.COMPLETED)
        
        avg_duration = completed_query.with_entities(func.avg(self.model.duration_seconds)).scalar() or 0
        total_tokens = completed_query.with_entities(func.sum(self.model.tokens_used)).scalar() or 0
        avg_tokens = completed_query.with_entities(func.avg(self.model.tokens_used)).scalar() or 0
        
        # Calculate total cost
        cost_query = completed_query.filter(self.model.cost_usd.isnot(None))
        total_cost = 0
        for execution in cost_query.all():
            if execution.cost_usd:
                try:
                    total_cost += float(execution.cost_usd)
                except (ValueError, TypeError):
                    continue
        
        return {
            "period_days": days,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": round(success_rate, 2),
            "average_duration_seconds": round(float(avg_duration), 2),
            "total_tokens_used": int(total_tokens),
            "average_tokens_per_execution": round(float(avg_tokens), 2),
            "total_cost_usd": round(total_cost, 4)
        }

    def get_recent_failures(
        self, 
        db: Session, 
        *, 
        user_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[Execution]:
        """Get recent failed executions for debugging."""
        query = db.query(self.model).filter(self.model.status == ExecutionStatus.FAILED)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        return (
            query
            .order_by(desc(self.model.created_at))
            .limit(limit)
            .all()
        )

    def cleanup_old_executions(
        self, 
        db: Session, 
        *, 
        days_old: int = 90,
        batch_size: int = 1000
    ) -> int:
        """Clean up old completed executions."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Only delete completed, failed, or cancelled executions
        query = (
            db.query(self.model)
            .filter(self.model.created_at < cutoff_date)
            .filter(self.model.status.in_([
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED
            ]))
            .limit(batch_size)
        )
        
        deleted_count = 0
        while True:
            executions = query.all()
            if not executions:
                break
            
            for execution in executions:
                db.delete(execution)
                deleted_count += 1
            
            db.commit()
            
            if len(executions) < batch_size:
                break
        
        return deleted_count

    def retry_execution(
        self, 
        db: Session, 
        *, 
        execution_id: UUID
    ) -> Optional[Execution]:
        """Create a retry of a failed execution."""
        original = db.query(self.model).filter(self.model.id == execution_id).first()
        if not original or original.status != ExecutionStatus.FAILED:
            return None
        
        if original.retry_count >= original.max_retries:
            return None
        
        # Create new execution as retry
        retry_data = {
            "execution_id": f"retry_{original.execution_id}_{original.retry_count + 1}",
            "name": f"Retry of {original.name}",
            "description": original.description,
            "type": original.type,
            "agent_id": original.agent_id,
            "user_id": original.user_id,
            "conversation_id": original.conversation_id,
            "parent_execution_id": original.parent_execution_id,
            "input_data": original.input_data,
            "config": original.config,
            "context": original.context,
            "timeout_seconds": original.timeout_seconds,
            "priority": original.priority,
            "retry_count": original.retry_count + 1,
            "max_retries": original.max_retries,
            "is_monitored": original.is_monitored,
            "debug_mode": original.debug_mode,
            "log_level": original.log_level,
            "environment": original.environment,
            "version": original.version
        }
        
        db_obj = self.model(**retry_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


execution = CRUDExecution(Execution)
