"""AI Tools Package

This package provides a comprehensive tool integration framework for AI agents,
including function calling, tool management, and extensible tool system.
"""

from typing import List, Dict, Any, Optional, Type
import logging

from .base import BaseTool, ToolResult, ToolParameter, ToolRegistry
from .manager import ToolManager
from .builtin import WebSearchTool, CalculatorTool, FileSystemTool, DatabaseTool, CodeExecutorTool, FileManagerTool
from .registry import tool_registry

logger = logging.getLogger(__name__)

# Tool class mapping for dynamic instantiation
TOOL_CLASSES = {
    "web_search": WebSearchTool,
    "calculator": CalculatorTool,
    "file_system": FileSystemTool,
    "database": DatabaseTool,
    "code_executor": CodeExecutorTool,
    "file_manager": FileManagerTool,
}


def get_available_tools() -> List[Dict[str, Any]]:
    """
    Get list of available tools with their metadata.
    
    Returns:
        List of tool information dictionaries
    """
    tools_info = []
    
    # Get tools from registry
    for tool in tool_registry.list_tools():
        tools_info.append({
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "version": tool.version,
            "enabled": tool.enabled,
            "parameters": [p.dict() for p in tool.parameters]
        })
    
    # Also include built-in tools that might not be registered yet
    for tool_name, tool_class in TOOL_CLASSES.items():
        # Check if already in registry
        if not any(t["name"] == tool_name for t in tools_info):
            try:
                # Create temporary instance to get metadata
                temp_tool = tool_class()
                tools_info.append({
                    "name": temp_tool.name,
                    "description": temp_tool.description,
                    "category": temp_tool.category,
                    "version": temp_tool.version,
                    "enabled": True,
                    "parameters": [p.dict() for p in temp_tool.parameters],
                    "available": True
                })
            except Exception as e:
                logger.warning(f"Could not load tool {tool_name}: {e}")
                tools_info.append({
                    "name": tool_name,
                    "description": f"Built-in {tool_name} tool",
                    "category": "builtin",
                    "version": "1.0.0",
                    "enabled": False,
                    "parameters": [],
                    "available": False,
                    "error": str(e)
                })
    
    return tools_info


def create_tool_instance(tool_name: str, **kwargs) -> Optional[BaseTool]:
    """
    Create an instance of a tool by name.
    
    Args:
        tool_name: Name of the tool to create
        **kwargs: Additional arguments for tool initialization
        
    Returns:
        Tool instance or None if not found
    """
    # First check the registry
    tool = tool_registry.get(tool_name)
    if tool:
        logger.info(f"Retrieved tool '{tool_name}' from registry")
        return tool
    
    # Check built-in tools
    if tool_name in TOOL_CLASSES:
        try:
            tool_class = TOOL_CLASSES[tool_name]
            tool_instance = tool_class(**kwargs)
            
            # Optionally register it for future use
            try:
                tool_registry.register(tool_instance)
                logger.info(f"Created and registered tool '{tool_name}'")
            except ValueError:
                # Already registered
                logger.debug(f"Tool '{tool_name}' already in registry")
            
            return tool_instance
            
        except Exception as e:
            logger.error(f"Failed to create tool '{tool_name}': {e}")
            return None
    
    # Try to find by partial name match
    available_tools = tool_registry.list_tools()
    for tool in available_tools:
        if tool_name.lower() in tool.name.lower():
            logger.info(f"Found tool '{tool.name}' by partial match for '{tool_name}'")
            return tool
    
    logger.warning(f"Tool '{tool_name}' not found")
    return None


def register_tool(tool: BaseTool) -> bool:
    """
    Register a tool in the global registry.
    
    Args:
        tool: Tool instance to register
        
    Returns:
        True if successful, False otherwise
    """
    try:
        tool_registry.register(tool)
        logger.info(f"Successfully registered tool: {tool.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to register tool {tool.name}: {e}")
        return False


def unregister_tool(tool_name: str) -> bool:
    """
    Unregister a tool from the global registry.
    
    Args:
        tool_name: Name of tool to unregister
        
    Returns:
        True if successful, False otherwise
    """
    try:
        tool_registry.unregister(tool_name)
        logger.info(f"Successfully unregistered tool: {tool_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to unregister tool {tool_name}: {e}")
        return False


def get_tool_by_name(tool_name: str) -> Optional[BaseTool]:
    """
    Get a tool by name from the registry.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Tool instance or None if not found
    """
    return tool_registry.get(tool_name)


def list_tool_categories() -> List[str]:
    """
    Get list of all tool categories.
    
    Returns:
        List of category names
    """
    return tool_registry.get_categories()


__all__ = [
    "BaseTool",
    "ToolResult", 
    "ToolParameter",
    "ToolRegistry",
    "ToolManager",
    "WebSearchTool",
    "CalculatorTool", 
    "FileSystemTool",
    "DatabaseTool",
    "CodeExecutorTool",
    "FileManagerTool",
    "tool_registry",
    "get_available_tools",
    "create_tool_instance",
    "register_tool",
    "unregister_tool",
    "get_tool_by_name",
    "list_tool_categories",
    "TOOL_CLASSES"
]
