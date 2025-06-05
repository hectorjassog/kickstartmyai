"""
Tool Executor - Handles execution of AI tools with context management and error handling.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Type
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from ..tools.base import BaseTool, ToolResult, ToolError


class ExecutionStatus(str, Enum):
    """Status of tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ToolExecution(BaseModel):
    """Represents a single tool execution."""
    
    id: UUID = Field(default_factory=uuid4)
    tool_name: str
    arguments: Dict[str, Any]
    context: Dict[str, Any] = Field(default_factory=dict)
    
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolExecutor:
    """
    Executes AI tools with proper context management, error handling, and monitoring.
    """
    
    def __init__(
        self,
        tools: Optional[List[BaseTool]] = None,
        max_concurrent_executions: int = 5,
        default_timeout: int = 30
    ):
        """
        Initialize the tool executor.
        
        Args:
            tools: List of available tools
            max_concurrent_executions: Maximum number of concurrent tool executions
            default_timeout: Default timeout for tool execution in seconds
        """
        self.tools: Dict[str, BaseTool] = {}
        self.max_concurrent_executions = max_concurrent_executions
        self.default_timeout = default_timeout
        
        # Execution tracking
        self.executions: Dict[UUID, ToolExecution] = {}
        self.running_executions: set = set()
        self._semaphore = asyncio.Semaphore(max_concurrent_executions)
        
        # Register initial tools
        if tools:
            for tool in tools:
                self.register_tool(tool)
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool with the executor."""
        self.tools[tool.name] = tool
    
    def unregister_tool(self, tool_name: str) -> None:
        """Unregister a tool from the executor."""
        if tool_name in self.tools:
            del self.tools[tool_name]
    
    async def add_tool(self, tool: BaseTool) -> None:
        """Add a tool asynchronously (alias for register_tool)."""
        self.register_tool(tool)
    
    async def remove_tool(self, tool_name: str) -> None:
        """Remove a tool asynchronously (alias for unregister_tool)."""
        self.unregister_tool(tool_name)
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self.tools.keys())
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all available tools."""
        return [tool.get_schema() for tool in self.tools.values()]
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> ToolResult:
        """
        Execute a tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            context: Additional context for execution
            timeout: Timeout in seconds (uses default if not specified)
            
        Returns:
            Tool execution result
            
        Raises:
            ToolError: If tool is not found or execution fails
        """
        # Check if tool exists
        tool = self.tools.get(tool_name)
        if not tool:
            raise ToolError(f"Tool '{tool_name}' not found")
        
        # Create execution record
        execution = ToolExecution(
            tool_name=tool_name,
            arguments=arguments,
            context=context or {}
        )
        
        self.executions[execution.id] = execution
        
        try:
            # Acquire semaphore for concurrency control
            async with self._semaphore:
                execution.status = ExecutionStatus.RUNNING
                execution.start_time = datetime.utcnow()
                self.running_executions.add(execution.id)
                
                # Execute tool with timeout
                timeout_value = timeout or self.default_timeout
                
                try:
                    result = await asyncio.wait_for(
                        self._execute_tool_safe(tool, arguments, execution.context),
                        timeout=timeout_value
                    )
                    
                    execution.status = ExecutionStatus.COMPLETED
                    execution.result = result.result
                    execution.metadata.update(result.metadata)
                    
                    return result
                    
                except asyncio.TimeoutError:
                    execution.status = ExecutionStatus.TIMEOUT
                    execution.error = f"Tool execution timed out after {timeout_value} seconds"
                    
                    raise ToolError(
                        f"Tool '{tool_name}' timed out after {timeout_value} seconds"
                    )
                
                except Exception as e:
                    execution.status = ExecutionStatus.FAILED
                    execution.error = str(e)
                    raise
        
        finally:
            execution.end_time = datetime.utcnow()
            if execution.start_time:
                execution.execution_time = (
                    execution.end_time - execution.start_time
                ).total_seconds()
            
            self.running_executions.discard(execution.id)
    
    async def _execute_tool_safe(
        self,
        tool: BaseTool,
        arguments: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool with proper error handling."""
        try:
            # Validate arguments
            if hasattr(tool, 'validate_arguments'):
                validated_args = tool.validate_arguments(arguments)
            else:
                validated_args = arguments
            
            # Execute tool
            result = await tool.execute(validated_args, context)
            
            # Ensure result is a ToolResult
            if not isinstance(result, ToolResult):
                result = ToolResult(
                    success=True,
                    result=result,
                    metadata={"tool_name": tool.name}
                )
            
            return result
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e),
                metadata={"tool_name": tool.name}
            )