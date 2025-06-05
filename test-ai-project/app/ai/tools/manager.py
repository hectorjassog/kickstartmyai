"""
Tool Manager

This module provides the ToolManager class for executing tools,
managing function calls, and integrating with AI providers.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from datetime import datetime

from .base import BaseTool, ToolResult, ToolRegistry
from .registry import tool_registry
from app.core.config import settings

logger = logging.getLogger(__name__)


class ToolExecutionContext:
    """Context for tool execution."""
    
    def __init__(
        self,
        execution_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.execution_id = execution_id or uuid4()
        self.user_id = user_id
        self.agent_id = agent_id
        self.conversation_id = conversation_id
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()


class FunctionCall:
    """Represents a function call from an AI provider."""
    
    def __init__(
        self,
        name: str,
        arguments: Dict[str, Any],
        call_id: Optional[str] = None
    ):
        self.name = name
        self.arguments = arguments
        self.call_id = call_id or str(uuid4())
        self.created_at = datetime.utcnow()
    
    @classmethod
    def from_openai_format(cls, function_call: Dict[str, Any]) -> "FunctionCall":
        """Create from OpenAI function call format."""
        return cls(
            name=function_call["name"],
            arguments=json.loads(function_call["arguments"]),
            call_id=function_call.get("id")
        )
    
    @classmethod
    def from_anthropic_format(cls, tool_use: Dict[str, Any]) -> "FunctionCall":
        """Create from Anthropic tool use format."""
        return cls(
            name=tool_use["name"],
            arguments=tool_use["input"],
            call_id=tool_use.get("id")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "call_id": self.call_id,
            "name": self.name,
            "arguments": self.arguments,
            "created_at": self.created_at.isoformat()
        }


class ToolManager:
    """
    Manager for executing AI tools and handling function calls.
    
    Provides a unified interface for tool execution across different AI providers,
    with support for parallel execution, error handling, and execution tracking.
    """
    
    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or tool_registry
        self.execution_history: List[Dict[str, Any]] = []
        self.max_concurrent_executions = settings.AI_BATCH_SIZE or 5
        self.execution_timeout = settings.FUNCTION_TIMEOUT or 30
        
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None
    ) -> ToolResult:
        """
        Execute a single tool.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            context: Execution context
            
        Returns:
            Tool execution result
        """
        start_time = time.time()
        
        # Get tool
        tool = self.registry.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found",
                execution_time=time.time() - start_time
            )
        
        if not tool.enabled:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' is disabled",
                execution_time=time.time() - start_time
            )
        
        try:
            # Validate parameters
            validated_params = tool.validate_parameters(parameters)
            
            # Execute tool with timeout
            result = await asyncio.wait_for(
                tool.execute(**validated_params),
                timeout=self.execution_timeout
            )
            
            # Record execution
            execution_record = {
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result.to_dict(),
                "context": context.to_dict() if context else None,
                "executed_at": datetime.utcnow().isoformat()
            }
            self.execution_history.append(execution_record)
            
            logger.info(f"Tool '{tool_name}' executed successfully in {result.execution_time:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.error(f"Tool '{tool_name}' execution timed out after {execution_time:.2f}s")
            return ToolResult(
                success=False,
                error=f"Tool execution timed out after {self.execution_timeout}s",
                execution_time=execution_time
            )
        except ValueError as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool '{tool_name}' parameter validation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Parameter validation failed: {str(e)}",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool '{tool_name}' execution failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}",
                execution_time=execution_time
            )
    
    async def execute_function_calls(
        self,
        function_calls: List[FunctionCall],
        context: Optional[ToolExecutionContext] = None
    ) -> List[Tuple[FunctionCall, ToolResult]]:
        """
        Execute multiple function calls concurrently.
        
        Args:
            function_calls: List of function calls to execute
            context: Execution context
            
        Returns:
            List of (function_call, result) tuples
        """
        if not function_calls:
            return []
        
        # Limit concurrent executions
        if len(function_calls) > self.max_concurrent_executions:
            logger.warning(
                f"Limiting concurrent executions to {self.max_concurrent_executions} "
                f"(requested: {len(function_calls)})"
            )
        
        # Create execution tasks
        tasks = []
        for call in function_calls[:self.max_concurrent_executions]:
            task = asyncio.create_task(
                self.execute_tool(call.name, call.arguments, context),
                name=f"tool_execution_{call.name}_{call.call_id}"
            )
            tasks.append((call, task))
        
        # Execute and collect results
        results = []
        for call, task in tasks:
            try:
                result = await task
                results.append((call, result))
            except Exception as e:
                logger.error(f"Failed to execute function call {call.name}: {e}")
                results.append((call, ToolResult(
                    success=False,
                    error=f"Execution failed: {str(e)}",
                    execution_time=0.0
                )))
        
        return results
    
    async def handle_openai_function_calls(
        self,
        function_calls: List[Dict[str, Any]],
        context: Optional[ToolExecutionContext] = None
    ) -> List[Dict[str, Any]]:
        """
        Handle OpenAI function calls and return function call results.
        
        Args:
            function_calls: OpenAI function calls
            context: Execution context
            
        Returns:
            List of function call result messages
        """
        calls = [FunctionCall.from_openai_format(fc) for fc in function_calls]
        results = await self.execute_function_calls(calls, context)
        
        # Convert to OpenAI message format
        messages = []
        for call, result in results:
            content = json.dumps(result.to_dict()) if result.success else result.error
            messages.append({
                "role": "function",
                "name": call.name,
                "content": content,
                "function_call_id": call.call_id
            })
        
        return messages
    
    async def handle_anthropic_tool_use(
        self,
        tool_uses: List[Dict[str, Any]],
        context: Optional[ToolExecutionContext] = None
    ) -> List[Dict[str, Any]]:
        """
        Handle Anthropic tool use and return tool result blocks.
        
        Args:
            tool_uses: Anthropic tool use blocks
            context: Execution context
            
        Returns:
            List of tool result blocks
        """
        calls = [FunctionCall.from_anthropic_format(tu) for tu in tool_uses]
        results = await self.execute_function_calls(calls, context)
        
        # Convert to Anthropic tool result format
        tool_results = []
        for call, result in results:
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.call_id,
                "content": json.dumps(result.to_dict()) if result.success else [
                    {
                        "type": "text",
                        "text": f"Error: {result.error}"
                    }
                ],
                "is_error": not result.success
            })
        
        return tool_results
    
    def get_available_tools(
        self,
        category: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[BaseTool]:
        """Get available tools."""
        return self.registry.list_tools(category=category, enabled_only=enabled_only)
    
    def get_function_schemas(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """Get function schemas for AI providers."""
        return self.registry.get_function_schemas(enabled_only=enabled_only)
    
    def get_tool_categories(self) -> List[str]:
        """Get available tool categories."""
        return self.registry.get_categories()
    
    def enable_tool(self, tool_name: str) -> bool:
        """Enable a tool."""
        tool = self.registry.get(tool_name)
        if tool:
            tool.enable()
            logger.info(f"Enabled tool: {tool_name}")
            return True
        return False
    
    def disable_tool(self, tool_name: str) -> bool:
        """Disable a tool."""
        tool = self.registry.get(tool_name)
        if tool:
            tool.disable()
            logger.info(f"Disabled tool: {tool_name}")
            return True
        return False
    
    def get_execution_history(
        self,
        limit: Optional[int] = None,
        tool_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tool execution history.
        
        Args:
            limit: Maximum number of executions to return
            tool_name: Filter by tool name
            
        Returns:
            List of execution records
        """
        history = self.execution_history
        
        if tool_name:
            history = [h for h in history if h["tool_name"] == tool_name]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def clear_execution_history(self) -> None:
        """Clear execution history."""
        self.execution_history.clear()
        logger.info("Cleared tool execution history")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        total_executions = len(self.execution_history)
        if not total_executions:
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "tools_used": []
            }
        
        successful = sum(1 for h in self.execution_history if h["result"]["success"])
        failed = total_executions - successful
        
        execution_times = [h["result"]["execution_time"] for h in self.execution_history]
        avg_time = sum(execution_times) / len(execution_times)
        
        tools_used = list(set(h["tool_name"] for h in self.execution_history))
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": successful / total_executions,
            "avg_execution_time": avg_time,
            "tools_used": tools_used
        }


# Global tool manager instance
tool_manager = ToolManager() 