"""
Tool Registry

This module provides the global tool registry and registers all built-in tools.
"""

import logging
from .base import ToolRegistry
from .builtin import (
    WebSearchTool,
    CalculatorTool,
    FileSystemTool,
    DatabaseTool,
    CodeExecutorTool,
    FileManagerTool
)

logger = logging.getLogger(__name__)

# Global tool registry instance
tool_registry = ToolRegistry()


def register_builtin_tools():
    """Register all built-in tools."""
    tools = [
        WebSearchTool(),
        CalculatorTool(),
        FileSystemTool(),
        DatabaseTool(),
        CodeExecutorTool(),
        FileManagerTool()
    ]
    
    for tool in tools:
        try:
            tool_registry.register(tool)
            logger.info(f"Registered built-in tool: {tool.name}")
        except ValueError as e:
            logger.error(f"Failed to register tool {tool.name}: {e}")


def initialize_tools():
    """Initialize the tool system."""
    logger.info("Initializing AI tool system...")
    register_builtin_tools()
    logger.info(f"Tool system initialized with {len(tool_registry)} tools")


# Auto-initialize tools when module is imported
initialize_tools() 