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
from app.schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
    AgentSearchFilters,
    AgentDuplicate,
    AgentStatistics,
    AgentConfigurationTemplate,
)


router = APIRouter()


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(get_pagination_params),
    search: SearchParams = Depends(get_search_params),
    filters: Optional[AgentSearchFilters] = None,
    _: None = Depends(rate_limiter),
):
    """List agents for the current user."""
    try:
        # Build filter dict
        filter_dict = {"user_id": current_user.id}
        if filters:
            if filters.agent_type:
                filter_dict["agent_type"] = filters.agent_type
            if filters.status:
                filter_dict["status"] = filters.status
            if filters.is_active is not None:
                filter_dict["is_active"] = filters.is_active
        
        # Get agents with search and pagination
        agents = await agent_crud.get_multi_filtered(
            db,
            filters=filter_dict,
            search_query=search.query,
            search_fields=["name", "description"],
            skip=pagination.skip,
            limit=pagination.limit,
            order_by=search.sort_by or "created_at",
            order_direction=search.get_sort_order(),
        )
        
        # Get total count
        total = await agent_crud.count_filtered(db, filters=filter_dict)
        
        return AgentListResponse(
            agents=agents,
            total=total,
            skip=pagination.skip,
            limit=pagination.limit,
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}"
        )


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limiter),
):
    """Create a new agent."""
    try:
        # Check if agent with same name exists for user
        existing_agent = await agent_crud.get_by_name_and_user(
            db, name=agent_data.name, user_id=current_user.id
        )
        if existing_agent:
            raise ConflictError("Agent", f"Agent with name '{agent_data.name}' already exists")
        
        # Create agent
        agent = await agent_crud.create_with_owner(
            db, obj_in=agent_data, owner_id=current_user.id
        )
        
        return AgentResponse.from_orm(agent)
    
    except ConflictError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}"
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_resource_owner("agent")),
    _: None = Depends(rate_limiter),
):
    """Get a specific agent."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise NotFoundError("Agent", f"Agent {agent_id} not found")
        
        return AgentResponse.from_orm(agent)
    
    except NotFoundError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent: {str(e)}"
        )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_resource_owner("agent")),
    _: None = Depends(rate_limiter),
):
    """Update an agent."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise NotFoundError("Agent", f"Agent {agent_id} not found")
        
        # Check if updating name and it conflicts
        if agent_data.name and agent_data.name != agent.name:
            existing_agent = await agent_crud.get_by_name_and_user(
                db, name=agent_data.name, user_id=current_user.id
            )
            if existing_agent and existing_agent.id != agent_id:
                raise ConflictError("Agent", f"Agent with name '{agent_data.name}' already exists")
        
        updated_agent = await agent_crud.update(db, db_obj=agent, obj_in=agent_data)
        return AgentResponse.from_orm(updated_agent)
    
    except (NotFoundError, ConflictError):
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
    current_user: User = Depends(require_resource_owner("agent")),
    _: None = Depends(rate_limiter),
):
    """Delete an agent."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise NotFoundError("Agent", f"Agent {agent_id} not found")
        
        await agent_crud.remove(db, id=agent_id)
    
    except NotFoundError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {str(e)}"
        )


@router.post("/{agent_id}/duplicate", response_model=AgentResponse)
async def duplicate_agent(
    agent_id: UUID,
    duplicate_data: AgentDuplicate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_resource_owner("agent")),
    _: None = Depends(rate_limiter),
):
    """Duplicate an agent."""
    try:
        # Check if agent with new name already exists
        existing_agent = await agent_crud.get_by_name_and_user(
            db, name=duplicate_data.name, user_id=current_user.id
        )
        if existing_agent:
            raise ConflictError("Agent", f"Agent with name '{duplicate_data.name}' already exists")
        
        duplicated_agent = await agent_crud.duplicate(
            db, agent_id=agent_id, new_name=duplicate_data.name
        )
        
        return AgentResponse.from_orm(duplicated_agent)
    
    except (NotFoundError, ConflictError):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate agent: {str(e)}"
        )


@router.patch("/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(
    agent_id: UUID,
    status_update: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_resource_owner("agent")),
    _: None = Depends(rate_limiter),
):
    """Update agent status."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise NotFoundError("Agent", f"Agent {agent_id} not found")
        
        new_status = status_update.get("status")
        if not new_status:
            raise ValidationError("Status is required")
        
        updated_agent = await agent_crud.update_status(db, agent_id=agent_id, status=new_status)
        return AgentResponse.from_orm(updated_agent)
    
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent status: {str(e)}"
        )


@router.get("/{agent_id}/statistics", response_model=AgentStatistics)
async def get_agent_statistics(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_resource_owner("agent")),
    _: None = Depends(rate_limiter),
):
    """Get agent statistics."""
    try:
        stats = await agent_crud.get_statistics(db, agent_id=agent_id)
        return AgentStatistics(**stats)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent statistics: {str(e)}"
        )


@router.get("/templates/configurations", response_model=List[AgentConfigurationTemplate])
async def get_configuration_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limiter),
):
    """Get available agent configuration templates."""
    try:
        templates = await agent_crud.get_configuration_templates(db)
        return [AgentConfigurationTemplate(**template) for template in templates]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration templates: {str(e)}"
        )


@router.post("/{agent_id}/activate", response_model=AgentResponse)
async def activate_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_resource_owner("agent")),
    _: None = Depends(rate_limiter),
):
    """Activate an agent."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise NotFoundError("Agent", f"Agent {agent_id} not found")
        
        activated_agent = await agent_crud.activate(db, agent_id=agent_id)
        return AgentResponse.from_orm(activated_agent)
    
    except NotFoundError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate agent: {str(e)}"
        )


@router.post("/{agent_id}/deactivate", response_model=AgentResponse)
async def deactivate_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_resource_owner("agent")),
    _: None = Depends(rate_limiter),
):
    """Deactivate an agent."""
    try:
        agent = await agent_crud.get(db, id=agent_id)
        if not agent:
            raise NotFoundError("Agent", f"Agent {agent_id} not found")
        
        deactivated_agent = await agent_crud.deactivate(db, agent_id=agent_id)
        return AgentResponse.from_orm(deactivated_agent)
    
    except NotFoundError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate agent: {str(e)}"
        )
