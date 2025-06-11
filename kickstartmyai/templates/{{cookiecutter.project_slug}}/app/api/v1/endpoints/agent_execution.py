"""
Agent Execution API Endpoints

This module provides REST API endpoints for executing AI agents,
including real-time execution, streaming responses, and execution management.
"""

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api import deps
from app.ai.services.execution_engine import execution_engine, ExecutionContext
from app.crud.agent import agent_crud
from app.crud.conversation import conversation_crud
from app.models.user import User
from app.schemas.execution import ExecutionResponse

router = APIRouter()


class AgentExecutionRequest(BaseModel):
    """Request model for agent execution."""
    message: str
    agent_id: UUID
    conversation_id: Optional[UUID] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    streaming: bool = False
    metadata: Dict[str, Any] = {}


class AgentExecutionResponse(BaseModel):
    """Response model for agent execution."""
    execution_id: UUID
    response: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = {}


class ActiveExecutionResponse(BaseModel):
    """Response model for active execution status."""
    execution_id: UUID
    agent_id: UUID
    conversation_id: UUID
    status: str
    started_at: str
    streaming: bool


@router.post("/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: AgentExecutionRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Execute an AI agent with the given message.
    
    Args:
        db: Database session
        request: Execution request
        current_user: Current authenticated user
        
    Returns:
        Execution result with response
    """
    # Get agent
    agent = await agent_crud.get(db, id=request.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Check agent ownership
    if agent.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to execute this agent"
        )
    
    # Get or create conversation
    if request.conversation_id:
        conversation = await conversation_crud.get(db, id=request.conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Check conversation ownership
        if conversation.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this conversation"
            )
    else:
        # Create new conversation
        from app.schemas.conversation import ConversationCreate
        conversation_create = ConversationCreate(
            title=f"Chat with {agent.name}",
            agent_id=agent.id,
            user_id=current_user.id
        )
        conversation = await conversation_crud.create(db, obj_in=conversation_create)
    
    # Create execution context
    context = ExecutionContext(
        agent_id=agent.id,
        conversation_id=conversation.id,
        user_id=current_user.id,
        provider_name=agent.provider,
        model=request.temperature and agent.model or request.model,
        temperature=request.temperature or agent.temperature,
        max_tokens=request.max_tokens or agent.max_tokens,
        streaming=request.streaming,
        metadata=request.metadata
    )
    
    try:
        # Execute agent
        result = await execution_engine.execute_agent(
            agent=agent,
            conversation=conversation,
            user_message=request.message,
            db=db,
            context=context
        )
        
        return AgentExecutionResponse(
            execution_id=result.execution_id,
            response=result.response or "",
            tokens_used=result.tokens_used,
            cost=float(result.cost) if result.cost else None,
            duration=result.duration,
            metadata=result.metadata
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.post("/execute/stream")
async def stream_agent_execution(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: AgentExecutionRequest,
    current_user: User = Depends(deps.get_current_user),
) -> StreamingResponse:
    """
    Execute an AI agent with streaming response.
    
    Args:
        db: Database session
        request: Execution request
        current_user: Current authenticated user
        
    Returns:
        Streaming response with real-time agent output
    """
    # Get agent
    agent = await agent_crud.get(db, id=request.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Check agent ownership
    if agent.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to execute this agent"
        )
    
    # Get or create conversation
    if request.conversation_id:
        conversation = await conversation_crud.get(db, id=request.conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Check conversation ownership
        if conversation.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this conversation"
            )
    else:
        # Create new conversation
        from app.schemas.conversation import ConversationCreate
        conversation_create = ConversationCreate(
            title=f"Chat with {agent.name}",
            agent_id=agent.id,
            user_id=current_user.id
        )
        conversation = await conversation_crud.create(db, obj_in=conversation_create)
    
    # Create execution context
    context = ExecutionContext(
        agent_id=agent.id,
        conversation_id=conversation.id,
        user_id=current_user.id,
        provider_name=agent.provider,
        model=request.temperature and agent.model or request.model,
        temperature=request.temperature or agent.temperature,
        max_tokens=request.max_tokens or agent.max_tokens,
        streaming=True,
        metadata=request.metadata
    )
    
    async def generate_stream():
        """Generate streaming response."""
        try:
            async for chunk in execution_engine.stream_agent_execution(
                agent=agent,
                conversation=conversation,
                user_message=request.message,
                db=db,
                context=context
            ):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [Error: {str(e)}]\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/active", response_model=List[ActiveExecutionResponse])
async def list_active_executions(
    *,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    List all active executions.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of active executions
    """
    active_executions = await execution_engine.list_active_executions()
    
    # Filter by user permissions
    if not current_user.is_superuser:
        active_executions = [
            exec_ctx for exec_ctx in active_executions
            if exec_ctx.user_id == current_user.id
        ]
    
    return [
        ActiveExecutionResponse(
            execution_id=exec_ctx.execution_id,
            agent_id=exec_ctx.agent_id,
            conversation_id=exec_ctx.conversation_id,
            status="running",
            started_at=str(exec_ctx.metadata.get("started_at", "")),
            streaming=exec_ctx.streaming
        )
        for exec_ctx in active_executions
        if exec_ctx.execution_id
    ]


@router.get("/active/{execution_id}", response_model=ActiveExecutionResponse)
async def get_active_execution(
    *,
    execution_id: UUID,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get status of an active execution.
    
    Args:
        execution_id: Execution ID
        current_user: Current authenticated user
        
    Returns:
        Active execution status
    """
    exec_ctx = await execution_engine.get_execution_status(execution_id)
    if not exec_ctx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active execution not found"
        )
    
    # Check permissions
    if exec_ctx.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this execution"
        )
    
    return ActiveExecutionResponse(
        execution_id=exec_ctx.execution_id,
        agent_id=exec_ctx.agent_id,
        conversation_id=exec_ctx.conversation_id,
        status="running",
        started_at=str(exec_ctx.metadata.get("started_at", "")),
        streaming=exec_ctx.streaming
    )


@router.post("/active/{execution_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_active_execution(
    *,
    db: AsyncSession = Depends(deps.get_db),
    execution_id: UUID,
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Cancel an active execution.
    
    Args:
        db: Database session
        execution_id: Execution ID
        current_user: Current authenticated user
        
    Returns:
        Cancellation result
    """
    exec_ctx = await execution_engine.get_execution_status(execution_id)
    if not exec_ctx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active execution not found"
        )
    
    # Check permissions
    if exec_ctx.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to cancel this execution"
        )
    
    success = await execution_engine.cancel_execution(execution_id, db)
    
    return {
        "success": success,
        "message": "Execution cancelled successfully" if success else "Failed to cancel execution"
    }


@router.post("/cleanup/stale", status_code=status.HTTP_200_OK)
async def cleanup_stale_executions(
    *,
    db: AsyncSession = Depends(deps.get_db),
    max_age_hours: int = Query(24, ge=1, le=168, description="Maximum age in hours"),
    current_user: User = Depends(deps.get_current_admin_user),
) -> Dict[str, Any]:
    """
    Clean up stale executions.
    
    Args:
        db: Database session
        max_age_hours: Maximum age in hours
        current_user: Current admin user
        
    Returns:
        Cleanup result
    """
    try:
        await execution_engine.cleanup_stale_executions(db, max_age_hours)
        return {
            "success": True,
            "message": f"Cleaned up stale executions older than {max_age_hours} hours"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        ) 