"""Function calling service for managing AI function calls and tool integrations."""

import json
import logging
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

from app.ai.tools.base import BaseTool, ToolRegistry

logger = logging.getLogger(__name__)


class FunctionCallingService:
    """Service for managing function calls and tool integrations."""
    
    def __init__(self):
        """Initialize the function calling service."""
        self.tool_registry = ToolRegistry()
        self.function_definitions: Dict[str, Dict[str, Any]] = {}
        self.registered_functions: Dict[str, Callable] = {}
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        Register a tool for function calling.
        
        Args:
            tool: Tool to register
        """
        # Check if already registered
        if tool.name in self.function_definitions:
            logger.warning(f"Tool '{tool.name}' is already registered, skipping")
            return
            
        try:
            # Register with tool registry
            self.tool_registry.register(tool)
            
            # Create function definition
            function_def = {
                "name": tool.name,
                "description": tool.description,
                "parameters": self._convert_tool_parameters(tool)
            }
            
            self.function_definitions[tool.name] = function_def
            self.registered_functions[tool.name] = tool.execute
            
            logger.info(f"Registered function: {tool.name}")
            
        except ValueError as e:
            # Tool already registered in registry, just create function definition
            if "already registered" in str(e):
                logger.warning(f"Tool '{tool.name}' already in registry, updating function definition")
                function_def = {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": self._convert_tool_parameters(tool)
                }
                self.function_definitions[tool.name] = function_def
                self.registered_functions[tool.name] = tool.execute
            else:
                logger.error(f"Failed to register tool {tool.name}: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to register tool {tool.name}: {e}")
            raise
    
    def unregister_function(self, function_name: str) -> None:
        """
        Unregister a function.
        
        Args:
            function_name: Name of function to unregister
        """
        try:
            # Remove from registry
            self.tool_registry.unregister(function_name)
            
            # Remove function definitions
            if function_name in self.function_definitions:
                del self.function_definitions[function_name]
            
            if function_name in self.registered_functions:
                del self.registered_functions[function_name]
            
            logger.info(f"Unregistered function: {function_name}")
            
        except Exception as e:
            logger.error(f"Failed to unregister function {function_name}: {e}")
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """
        Get all function definitions for AI providers.
        
        Returns:
            List of function definitions
        """
        return list(self.function_definitions.values())
    
    def get_function_names(self) -> List[str]:
        """Get list of all registered function names."""
        return list(self.function_definitions.keys())
    
    async def execute_function(
        self,
        function_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a registered function.
        
        Args:
            function_name: Name of function to execute
            arguments: Function arguments
            context: Optional execution context
            
        Returns:
            Function execution result
        """
        if function_name not in self.registered_functions:
            raise ValueError(f"Function '{function_name}' not registered")
        
        try:
            tool = self.tool_registry.get(function_name)
            if not tool:
                raise ValueError(f"Tool '{function_name}' not found in registry")
            
            # Validate arguments
            validated_args = tool.validate_parameters(arguments)
            
            # Execute function
            result = await tool.execute(**validated_args)
            
            return {
                "success": result.success,
                "result": result.result,
                "error": result.error,
                "execution_time": result.execution_time,
                "metadata": result.metadata
            }
            
        except Exception as e:
            logger.error(f"Function execution failed for {function_name}: {e}")
            return {
                "success": False,
                "result": None,
                "error": str(e),
                "execution_time": 0,
                "metadata": {"function_name": function_name}
            }
    
    def _convert_tool_parameters(self, tool: BaseTool) -> Dict[str, Any]:
        """Convert tool parameters to function calling format."""
        properties = {}
        required = []
        
        for param in tool.parameters:
            param_def = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum:
                param_def["enum"] = param.enum
            if param.min_value is not None:
                param_def["minimum"] = param.min_value
            if param.max_value is not None:
                param_def["maximum"] = param.max_value
            if param.pattern:
                param_def["pattern"] = param.pattern
            
            properties[param.name] = param_def
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their information."""
        tools = self.tool_registry.list_tools()
        return [tool.to_dict() for tool in tools]
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool."""
        tool = self.tool_registry.get(tool_name)
        return tool.to_dict() if tool else None
    
    def clear_all_functions(self) -> None:
        """Clear all registered functions."""
        self.tool_registry.clear()
        self.function_definitions.clear()
        self.registered_functions.clear()
        logger.info("Cleared all registered functions")


# Global instance
function_calling_service = FunctionCallingService() 