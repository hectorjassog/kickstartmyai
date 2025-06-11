"""
Tool Management API Endpoints

This module provides REST API endpoints for managing AI tools,
including listing tools, executing tools, and managing tool configurations.
"""

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api import deps
from app.ai.tools.manager import tool_manager, ToolExecutionContext
from app.models.user import User

router = APIRouter()


class ToolExecutionRequest(BaseModel):
    """Request model for tool execution."""
    tool_name: str
    parameters: Dict[str, Any]
    metadata: Dict[str, Any] = {}


class ToolExecutionResponse(BaseModel):
    """Response model for tool execution."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float
    metadata: Dict[str, Any] = {}


class ToolInfo(BaseModel):
    """Tool information model."""
    id: str
    name: str
    description: str
    category: str
    version: str
    enabled: bool
    parameters: List[Dict[str, Any]]
    created_at: str


class ToolStatsResponse(BaseModel):
    """Tool execution statistics response."""
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_execution_time: float
    tools_used: List[str]


@router.get("/", response_model=List[ToolInfo])
async def list_tools(
    *,
    category: Optional[str] = Query(None, description="Filter by tool category"),
    enabled_only: bool = Query(True, description="Only return enabled tools"),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    List available AI tools.
    
    Args:
        category: Filter by tool category
        enabled_only: Only return enabled tools
        current_user: Current authenticated user
        
    Returns:
        List of available tools
    """
    tools = tool_manager.get_available_tools(category=category, enabled_only=enabled_only)
    
    return [
        ToolInfo(
            id=tool.tool_id,
            name=tool.name,
            description=tool.description,
            category=tool.category,
            version=tool.version,
            enabled=tool.enabled,
            parameters=[p.dict() for p in tool.parameters],
            created_at=tool.created_at.isoformat()
        )
        for tool in tools
    ]


@router.get("/categories", response_model=List[str])
async def list_tool_categories(
    *,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    List available tool categories.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of tool categories
    """
    return tool_manager.get_tool_categories()


@router.get("/schemas", response_model=List[Dict[str, Any]])
async def get_function_schemas(
    *,
    enabled_only: bool = Query(True, description="Only return schemas for enabled tools"),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get function schemas for AI providers.
    
    Args:
        enabled_only: Only return schemas for enabled tools
        current_user: Current authenticated user
        
    Returns:
        List of function schemas
    """
    return tool_manager.get_function_schemas(enabled_only=enabled_only)


@router.get("/{tool_name}", response_model=ToolInfo)
async def get_tool(
    *,
    tool_name: str,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get detailed information about a specific tool.
    
    Args:
        tool_name: Name of the tool
        current_user: Current authenticated user
        
    Returns:
        Tool information
    """
    tool = tool_manager.registry.get(tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found"
        )
    
    return ToolInfo(
        id=tool.tool_id,
        name=tool.name,
        description=tool.description,
        category=tool.category,
        version=tool.version,
        enabled=tool.enabled,
        parameters=[p.dict() for p in tool.parameters],
        created_at=tool.created_at.isoformat()
    )


@router.post("/{tool_name}/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    *,
    tool_name: str,
    request: ToolExecutionRequest,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Execute a tool with given parameters.
    
    Args:
        tool_name: Name of the tool to execute
        request: Tool execution request
        current_user: Current authenticated user
        
    Returns:
        Tool execution result
    """
    # Create execution context
    context = ToolExecutionContext(
        user_id=current_user.id,
        metadata=request.metadata
    )
    
    try:
        # Execute tool
        result = await tool_manager.execute_tool(
            tool_name=tool_name,
            parameters=request.parameters,
            context=context
        )
        
        return ToolExecutionResponse(
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time=result.execution_time,
            metadata=result.metadata
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )


@router.post("/{tool_name}/enable", status_code=status.HTTP_200_OK)
async def enable_tool(
    *,
    tool_name: str,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Dict[str, Any]:
    """
    Enable a tool.
    
    Args:
        tool_name: Name of the tool to enable
        current_user: Current admin user
        
    Returns:
        Success status
    """
    success = tool_manager.enable_tool(tool_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found"
        )
    
    return {
        "success": True,
        "message": f"Tool '{tool_name}' enabled successfully"
    }


@router.post("/{tool_name}/disable", status_code=status.HTTP_200_OK)
async def disable_tool(
    *,
    tool_name: str,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Dict[str, Any]:
    """
    Disable a tool.
    
    Args:
        tool_name: Name of the tool to disable
        current_user: Current admin user
        
    Returns:
        Success status
    """
    success = tool_manager.disable_tool(tool_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found"
        )
    
    return {
        "success": True,
        "message": f"Tool '{tool_name}' disabled successfully"
    }


@router.get("/execution/history", response_model=List[Dict[str, Any]])
async def get_execution_history(
    *,
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of records"),
    tool_name: Optional[str] = Query(None, description="Filter by tool name"),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get tool execution history.
    
    Args:
        limit: Maximum number of records to return
        tool_name: Filter by tool name
        current_user: Current authenticated user
        
    Returns:
        List of execution records
    """
    # Only admins can see all execution history
    if not current_user.is_superuser:
        # Regular users might see limited history in the future
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access execution history"
        )
    
    return tool_manager.get_execution_history(limit=limit, tool_name=tool_name)


@router.get("/execution/stats", response_model=ToolStatsResponse)
async def get_execution_stats(
    *,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Get tool execution statistics.
    
    Args:
        current_user: Current admin user
        
    Returns:
        Tool execution statistics
    """
    stats = tool_manager.get_stats()
    
    return ToolStatsResponse(
        total_executions=stats["total_executions"],
        successful_executions=stats["successful_executions"],
        failed_executions=stats["failed_executions"],
        success_rate=stats["success_rate"],
        avg_execution_time=stats["avg_execution_time"],
        tools_used=stats["tools_used"]
    )


@router.delete("/execution/history", status_code=status.HTTP_200_OK)
async def clear_execution_history(
    *,
    current_user: User = Depends(deps.get_current_admin_user),
) -> Dict[str, Any]:
    """
    Clear tool execution history.
    
    Args:
        current_user: Current admin user
        
    Returns:
        Success status
    """
    tool_manager.clear_execution_history()
    
    return {
        "success": True,
        "message": "Tool execution history cleared successfully"
    } 