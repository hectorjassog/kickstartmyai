"""
Execution API Endpoints

This module provides REST API endpoints for managing agent executions,
including CRUD operations, status management, and performance monitoring.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.crud.execution import execution_crud
from app.models.execution import Execution
from app.schemas.execution import (
    ExecutionCreate,
    ExecutionUpdate,
    ExecutionInDB,
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionFilter,
    ExecutionBatchCreate,
    ExecutionBatchResponse,
    ExecutionStatsResponse,
    ExecutionPerformanceMetrics,
    ExecutionTreeResponse,
    ExecutionStatus,
    ExecutionType,
)

router = APIRouter()


@router.post("/", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def create_execution(
    *,
    db: Session = Depends(deps.get_db),
    execution_in: ExecutionCreate,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Create a new execution.
    
    Args:
        db: Database session
        execution_in: Execution creation data
        current_user: Current authenticated user
        
    Returns:
        Created execution
    """
    try:
        execution = await execution_crud.create(db=db, obj_in=execution_in)
        return ExecutionResponse.from_orm(execution)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create execution: {str(e)}"
        )


@router.post("/batch", response_model=ExecutionBatchResponse)
async def create_executions_batch(
    *,
    db: Session = Depends(deps.get_db),
    batch_in: ExecutionBatchCreate,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Create multiple executions in batch.
    
    Args:
        db: Database session
        batch_in: Batch creation data
        current_user: Current authenticated user
        
    Returns:
        Batch creation results
    """
    try:
        result = await execution_crud.create_batch(db=db, batch_in=batch_in)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create execution batch: {str(e)}"
        )


@router.get("/", response_model=ExecutionListResponse)
async def list_executions(
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0, description="Number of executions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of executions to return"),
    agent_id: Optional[UUID] = Query(None, description="Filter by agent ID"),
    conversation_id: Optional[UUID] = Query(None, description="Filter by conversation ID"),
    status: Optional[ExecutionStatus] = Query(None, description="Filter by status"),
    execution_type: Optional[ExecutionType] = Query(None, description="Filter by type"),
    search: Optional[str] = Query(None, description="Search in task description"),
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    List executions with filtering and pagination.
    
    Args:
        db: Database session
        skip: Number of items to skip
        limit: Number of items to return
        agent_id: Filter by agent ID
        conversation_id: Filter by conversation ID
        status: Filter by execution status
        execution_type: Filter by execution type
        search: Search term
        current_user: Current authenticated user
        
    Returns:
        List of executions with pagination
    """
    # Build filter
    filters = ExecutionFilter(
        agent_id=agent_id,
        conversation_id=conversation_id,
        status=status,
        execution_type=execution_type,
        search=search,
    )
    
    # Get executions with count
    executions, total_count = await execution_crud.get_filtered_with_count(
        db=db, filters=filters, skip=skip, limit=limit
    )
    
    return ExecutionListResponse(
        executions=[ExecutionResponse.from_orm(execution) for execution in executions],
        total_count=total_count,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=(total_count + limit - 1) // limit,
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    *,
    db: Session = Depends(deps.get_db),
    execution_id: UUID,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Get execution by ID.
    
    Args:
        db: Database session
        execution_id: Execution ID
        current_user: Current authenticated user
        
    Returns:
        Execution details
    """
    execution = await execution_crud.get(db=db, id=execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return ExecutionResponse.from_orm(execution)


@router.put("/{execution_id}", response_model=ExecutionResponse)
async def update_execution(
    *,
    db: Session = Depends(deps.get_db),
    execution_id: UUID,
    execution_in: ExecutionUpdate,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Update execution.
    
    Args:
        db: Database session
        execution_id: Execution ID
        execution_in: Execution update data
        current_user: Current authenticated user
        
    Returns:
        Updated execution
    """
    execution = await execution_crud.get(db=db, id=execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    try:
        execution = await execution_crud.update(db=db, db_obj=execution, obj_in=execution_in)
        return ExecutionResponse.from_orm(execution)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update execution: {str(e)}"
        )


@router.delete("/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_execution(
    *,
    db: Session = Depends(deps.get_db),
    execution_id: UUID,
    current_user: dict = Depends(deps.get_current_user),
) -> None:
    """
    Delete execution.
    
    Args:
        db: Database session
        execution_id: Execution ID
        current_user: Current authenticated user
    """
    execution = await execution_crud.get(db=db, id=execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    await execution_crud.remove(db=db, id=execution_id)


@router.post("/{execution_id}/start", response_model=ExecutionResponse)
async def start_execution(
    *,
    db: Session = Depends(deps.get_db),
    execution_id: UUID,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Start execution.
    
    Args:
        db: Database session
        execution_id: Execution ID
        current_user: Current authenticated user
        
    Returns:
        Updated execution
    """
    try:
        execution = await execution_crud.start_execution(db=db, execution_id=execution_id)
        return ExecutionResponse.from_orm(execution)
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to start execution: {str(e)}"
        )


@router.post("/{execution_id}/pause", response_model=ExecutionResponse)
async def pause_execution(
    *,
    db: Session = Depends(deps.get_db),
    execution_id: UUID,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Pause execution.
    
    Args:
        db: Database session
        execution_id: Execution ID
        current_user: Current authenticated user
        
    Returns:
        Updated execution
    """
    try:
        execution = await execution_crud.pause_execution(db=db, execution_id=execution_id)
        return ExecutionResponse.from_orm(execution)
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to pause execution: {str(e)}"
        )


@router.post("/{execution_id}/resume", response_model=ExecutionResponse)
async def resume_execution(
    *,
    db: Session = Depends(deps.get_db),
    execution_id: UUID,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Resume execution.
    
    Args:
        db: Database session
        execution_id: Execution ID
        current_user: Current authenticated user
        
    Returns:
        Updated execution
    """
    try:
        execution = await execution_crud.resume_execution(db=db, execution_id=execution_id)
        return ExecutionResponse.from_orm(execution)
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to resume execution: {str(e)}"
        )


@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_execution(
    *,
    db: Session = Depends(deps.get_db),
    execution_id: UUID,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Cancel execution.
    
    Args:
        db: Database session
        execution_id: Execution ID
        current_user: Current authenticated user
        
    Returns:
        Updated execution
    """
    try:
        execution = await execution_crud.cancel_execution(db=db, execution_id=execution_id)
        return ExecutionResponse.from_orm(execution)
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel execution: {str(e)}"
        )


@router.post("/{execution_id}/retry", response_model=ExecutionResponse)
async def retry_execution(
    *,
    db: Session = Depends(deps.get_db),
    execution_id: UUID,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Retry failed execution.
    
    Args:
        db: Database session
        execution_id: Execution ID
        current_user: Current authenticated user
        
    Returns:
        New execution (retry)
    """
    try:
        execution = await execution_crud.retry_execution(db=db, execution_id=execution_id)
        return ExecutionResponse.from_orm(execution)
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retry execution: {str(e)}"
        )


@router.get("/{execution_id}/tree", response_model=ExecutionTreeResponse)
async def get_execution_tree(
    *,
    db: Session = Depends(deps.get_db),
    execution_id: UUID,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Get execution tree (parent-child relationships).
    
    Args:
        db: Database session
        execution_id: Root execution ID
        current_user: Current authenticated user
        
    Returns:
        Execution tree structure
    """
    try:
        tree = await execution_crud.get_execution_tree(db=db, root_execution_id=execution_id)
        return tree
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get execution tree: {str(e)}"
        )


@router.get("/{execution_id}/performance", response_model=ExecutionPerformanceMetrics)
async def get_execution_performance(
    *,
    db: Session = Depends(deps.get_db),
    execution_id: UUID,
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Get execution performance metrics.
    
    Args:
        db: Database session
        execution_id: Execution ID
        current_user: Current authenticated user
        
    Returns:
        Performance metrics
    """
    try:
        metrics = await execution_crud.get_performance_metrics(db=db, execution_id=execution_id)
        return metrics
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/stats/summary", response_model=ExecutionStatsResponse)
async def get_execution_stats(
    *,
    db: Session = Depends(deps.get_db),
    agent_id: Optional[UUID] = Query(None, description="Filter by agent ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: dict = Depends(deps.get_current_user),
) -> Any:
    """
    Get execution statistics.
    
    Args:
        db: Database session
        agent_id: Optional agent ID filter
        days: Number of days to analyze
        current_user: Current authenticated user
        
    Returns:
        Execution statistics
    """
    try:
        stats = await execution_crud.get_execution_statistics(
            db=db, agent_id=agent_id, days=days
        )
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get execution statistics: {str(e)}"
        )


@router.delete("/cleanup/old", status_code=status.HTTP_200_OK)
async def cleanup_old_executions(
    *,
    db: Session = Depends(deps.get_db),
    days: int = Query(90, ge=1, le=365, description="Delete executions older than N days"),
    dry_run: bool = Query(False, description="Perform dry run without actual deletion"),
    current_user: dict = Depends(deps.get_current_admin_user),
) -> Dict[str, Any]:
    """
    Clean up old executions (admin only).
    
    Args:
        db: Database session
        days: Delete executions older than this many days
        dry_run: Whether to perform a dry run
        current_user: Current authenticated admin user
        
    Returns:
        Cleanup summary
    """
    try:
        result = await execution_crud.cleanup_old_executions(
            db=db, days=days, dry_run=dry_run
        )
        return {
            "message": "Cleanup completed successfully",
            "deleted_count": result["deleted_count"],
            "dry_run": dry_run,
            "criteria": f"Executions older than {days} days",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cleanup executions: {str(e)}"
        )
