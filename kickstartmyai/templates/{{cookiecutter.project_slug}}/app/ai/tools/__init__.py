"""AI Tools Package

This package provides a comprehensive tool integration framework for AI agents,
including function calling, tool management, and extensible tool system.
"""

from .base import BaseTool, ToolResult, ToolParameter, ToolRegistry
from .manager import ToolManager
from .builtin import WebSearchTool, CalculatorTool, FileSystemTool, DatabaseTool
from .registry import tool_registry

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
    "tool_registry"
]
