"""
Base Tool Framework

This module provides the foundational classes and interfaces for the AI tool system,
including abstract base classes, tool parameters, results, and registry.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union, Callable
from enum import Enum
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class ToolError(Exception):
    """Exception raised when tool execution fails."""
    pass


class ToolParameterType(str, Enum):
    """Tool parameter types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Tool parameter definition."""
    name: str
    type: ToolParameterType
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    
    class Config:
        use_enum_values = True


class ToolResult(BaseModel):
    """Tool execution result."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float
    metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }


class BaseTool(ABC):
    """
    Abstract base class for AI tools.
    
    All tools must inherit from this class and implement the required methods.
    """
    
    def __init__(self):
        self.tool_id = str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        self._enabled = True
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (must be unique)."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters."""
        pass
    
    @property
    def version(self) -> str:
        """Tool version."""
        return "1.0.0"
    
    @property
    def category(self) -> str:
        """Tool category."""
        return "general"
    
    @property
    def enabled(self) -> bool:
        """Whether the tool is enabled."""
        return self._enabled
    
    def enable(self):
        """Enable the tool."""
        self._enabled = True
    
    def disable(self):
        """Disable the tool."""
        self._enabled = False
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize tool parameters.
        
        Args:
            parameters: Raw parameters
            
        Returns:
            Validated parameters
            
        Raises:
            ValueError: If parameters are invalid
        """
        validated = {}
        param_map = {p.name: p for p in self.parameters}
        
        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in parameters:
                if param.default is not None:
                    validated[param.name] = param.default
                else:
                    raise ValueError(f"Required parameter '{param.name}' is missing")
        
        # Validate provided parameters
        for name, value in parameters.items():
            if name not in param_map:
                logger.warning(f"Unknown parameter '{name}' for tool '{self.name}'")
                continue
            
            param = param_map[name]
            validated[name] = self._validate_parameter_value(param, value)
        
        return validated
    
    def _validate_parameter_value(self, param: ToolParameter, value: Any) -> Any:
        """Validate a single parameter value."""
        # Type validation
        if param.type == ToolParameterType.STRING and not isinstance(value, str):
            raise ValueError(f"Parameter '{param.name}' must be a string")
        elif param.type == ToolParameterType.INTEGER and not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValueError(f"Parameter '{param.name}' must be an integer")
        elif param.type == ToolParameterType.FLOAT and not isinstance(value, (int, float)):
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValueError(f"Parameter '{param.name}' must be a number")
        elif param.type == ToolParameterType.BOOLEAN and not isinstance(value, bool):
            if isinstance(value, str):
                value = value.lower() in ('true', '1', 'yes', 'on')
            else:
                value = bool(value)
        elif param.type == ToolParameterType.ARRAY and not isinstance(value, list):
            raise ValueError(f"Parameter '{param.name}' must be an array")
        elif param.type == ToolParameterType.OBJECT and not isinstance(value, dict):
            raise ValueError(f"Parameter '{param.name}' must be an object")
        
        # Enum validation
        if param.enum and value not in param.enum:
            raise ValueError(f"Parameter '{param.name}' must be one of {param.enum}")
        
        # Range validation
        if param.min_value is not None and value < param.min_value:
            raise ValueError(f"Parameter '{param.name}' must be >= {param.min_value}")
        if param.max_value is not None and value > param.max_value:
            raise ValueError(f"Parameter '{param.name}' must be <= {param.max_value}")
        
        # Pattern validation
        if param.pattern and isinstance(value, str):
            import re
            if not re.match(param.pattern, value):
                raise ValueError(f"Parameter '{param.name}' does not match pattern {param.pattern}")
        
        return value
    
    def to_function_schema(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function schema format.
        
        Returns:
            Function schema dictionary
        """
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type.value,
                "description": param.description
            }
            
            if param.enum:
                prop["enum"] = param.enum
            if param.min_value is not None:
                prop["minimum"] = param.min_value
            if param.max_value is not None:
                prop["maximum"] = param.max_value
            if param.pattern:
                prop["pattern"] = param.pattern
            
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation."""
        return {
            "id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "enabled": self.enabled,
            "parameters": [p.dict() for p in self.parameters],
            "created_at": self.created_at.isoformat()
        }
    
    def __str__(self) -> str:
        return f"{self.name}({self.version})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"


class ToolRegistry:
    """Registry for managing AI tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool to register
            
        Raises:
            ValueError: If tool name already exists
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        
        self._tools[tool.name] = tool
        
        # Update categories
        category = tool.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.name)
        
        logger.info(f"Registered tool: {tool.name}")
    
    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name not in self._tools:
            logger.warning(f"Tool '{tool_name}' not found for unregistration")
            return
        
        tool = self._tools.pop(tool_name)
        
        # Update categories
        category = tool.category
        if category in self._categories:
            self._categories[category].remove(tool_name)
            if not self._categories[category]:
                del self._categories[category]
        
        logger.info(f"Unregistered tool: {tool_name}")
    
    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(tool_name)
    
    def list_tools(self, category: Optional[str] = None, enabled_only: bool = True) -> List[BaseTool]:
        """
        List available tools.
        
        Args:
            category: Filter by category
            enabled_only: Only return enabled tools
            
        Returns:
            List of tools
        """
        tools = list(self._tools.values())
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        
        return tools
    
    def list_tool_names(self, category: Optional[str] = None, enabled_only: bool = True) -> List[str]:
        """List tool names."""
        tools = self.list_tools(category=category, enabled_only=enabled_only)
        return [t.name for t in tools]
    
    def get_categories(self) -> List[str]:
        """Get all tool categories."""
        return list(self._categories.keys())
    
    def get_function_schemas(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get function schemas for all tools.
        
        Args:
            enabled_only: Only return schemas for enabled tools
            
        Returns:
            List of function schemas
        """
        tools = self.list_tools(enabled_only=enabled_only)
        return [tool.to_function_schema() for tool in tools]
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._categories.clear()
        logger.info("Cleared all registered tools")
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        return tool_name in self._tools
