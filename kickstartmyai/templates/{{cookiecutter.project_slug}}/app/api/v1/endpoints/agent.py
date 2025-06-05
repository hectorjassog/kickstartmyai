"""Agent endpoints for the API."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_current_user,
    get_pagination_params,
    get_search_params,
    PaginationParams,
    SearchParams,
    require_resource_owner,
    rate_limiter,
)
from app.core.exceptions import (
    NotFoundError,
    ConflictError,
    ValidationError,
)
from app.crud import agent_crud
from app.models import User
from app.models.agent import AgentStatus, AgentType
from app.schemas import (
    Agent,
    AgentCreate,
    AgentUpdate,
    AgentListResponse,
    AgentFilter,
    AgentStatistics,
    AgentWithExecutions
)


router = APIRouter()


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    agent_type: Optional[AgentType] = None,
    status: Optional[AgentStatus] = None,
    is_public: Optional[bool] = None,
    search_term: Optional[str] = None,
    include_deprecated: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List agents for the current user."""
    try:
        filters = AgentFilter(
            user_id=current_user.id,
            agent_type=agent_type,
            status=status,
            is_public=is_public,
            search_term=search_term,
            include_deprecated=include_deprecated
        )
        
        if search_term:
            agents = await agent_crud.search_agents(
                db, search_term=search_term, user_id=current_user.id, skip=skip, limit=limit
            )
            total_count = len(agents)  # For search, we'll use simple count
        else:
            agents, total_count = await agent_crud.get_by_user_with_count(
                db, user_id=current_user.id, skip=skip, limit=limit, 
                include_deprecated=include_deprecated
            )
        
        return AgentListResponse(
            agents=agents,
            total_count=total_count,
            page=skip // limit + 1,
            page_size=limit,
            has_next=(skip + limit) < total_count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}"
        )


@router.post("/", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new agent."""
    try:
        # Check if agent with same name exists for user
        existing_agent = await agent_crud.get_by_name(
            db, user_id=current_user.id, name=agent_data.name
        )
        if existing_agent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent with name '{agent_data.name}' already exists"
            )
        
        # Create agent
        agent = await agent_crud.create_with_user(
            db, obj_in=agent_data, user_id=current_user.id
        )
        
        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}"
        )


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific agent."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        # Check ownership
        if agent.user_id != current_user.id and not agent.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this agent"
            )
        
        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent: {str(e)}"
        )


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an agent."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        # Check ownership
        if agent.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this agent"
            )
        
        # Check if updating name and it conflicts
        if agent_data.name and agent_data.name != agent.name:
            existing_agent = await agent_crud.get_by_name(
                db, user_id=current_user.id, name=agent_data.name
            )
            if existing_agent and existing_agent.id != agent_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Agent with name '{agent_data.name}' already exists"
                )
        
        updated_agent = await agent_crud.update(db, db_obj=agent, obj_in=agent_data)
        return updated_agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {str(e)}"
        )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an agent."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        # Check ownership
        if agent.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this agent"
            )
        
        await agent_crud.remove(db, id=agent_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {str(e)}"
        )


@router.post("/{agent_id}/duplicate", response_model=Agent)
async def duplicate_agent(
    agent_id: UUID,
    new_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Duplicate an agent."""
    try:
        # Check if new name already exists
        existing_agent = await agent_crud.get_by_name(
            db, user_id=current_user.id, name=new_name
        )
        if existing_agent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent with name '{new_name}' already exists"
            )
        
        duplicated_agent = await agent_crud.duplicate_agent(
            db, agent_id=agent_id, new_name=new_name, user_id=current_user.id
        )
        
        if not duplicated_agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        return duplicated_agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate agent: {str(e)}"
        )


@router.patch("/{agent_id}/status", response_model=Agent)
async def update_agent_status(
    agent_id: UUID,
    new_status: AgentStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update agent status."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        # Check ownership
        if agent.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this agent"
            )
        
        updated_agent = await agent_crud.set_status(
            db, agent_id=agent_id, status=new_status
        )
        
        return updated_agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent status: {str(e)}"
        )


@router.get("/{agent_id}/statistics", response_model=dict)
async def get_agent_statistics(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get agent statistics."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        # Check ownership or public access
        if agent.user_id != current_user.id and not agent.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view agent statistics"
            )
        
        stats = await agent_crud.get_statistics(db, user_id=agent.user_id)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent statistics: {str(e)}"
        )


@router.get("/{agent_id}/executions", response_model=AgentWithExecutions)
async def get_agent_with_executions(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get agent with its executions."""
    try:
        agent = await agent_crud.get_with_executions(db, agent_id=agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        # Check ownership
        if agent.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this agent"
            )
        
        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent with executions: {str(e)}"
        )


@router.get("/active/list", response_model=List[Agent])
async def list_active_agents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active agents for the current user."""
    try:
        agents = await agent_crud.get_active_agents(
            db, user_id=current_user.id, skip=skip, limit=limit
        )
        return agents
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list active agents: {str(e)}"
        )


@router.post("/{agent_id}/usage", response_model=Agent)
async def update_agent_usage(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update agent usage count."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        
        # Check ownership or public access
        if agent.user_id != current_user.id and not agent.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this agent"
            )
        
        updated_agent = await agent_crud.update_usage(db, agent_id=agent_id)
        return updated_agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent usage: {str(e)}"
        )
