"""AI tools package."""

from .base import BaseTool, ToolInput, ToolOutput
from .web_search import WebSearchTool, WebSearchInput, WebSearchOutput, WebContentInput, WebContentOutput
from .code_executor import CodeExecutorTool, CodeExecutionInput, CodeExecutionOutput, CodeSnippetInput, CodeSnippetOutput
from .file_manager import FileManagerTool, FileReadInput, FileWriteInput, FileListInput, FileDeleteInput, FileCopyInput, FileSearchInput
from .database import DatabaseTool, DatabaseQueryInput, DatabaseSchemaInput, DatabaseExecuteInput, DatabaseAnalysisInput

__all__ = [
    # Base classes
    "BaseTool",
    "ToolInput", 
    "ToolOutput",
    
    # Web search tool
    "WebSearchTool",
    "WebSearchInput",
    "WebSearchOutput", 
    "WebContentInput",
    "WebContentOutput",
    
    # Code executor tool
    "CodeExecutorTool",
    "CodeExecutionInput",
    "CodeExecutionOutput",
    "CodeSnippetInput", 
    "CodeSnippetOutput",
    
    # File manager tool
    "FileManagerTool",
    "FileReadInput",
    "FileWriteInput",
    "FileListInput",
    "FileDeleteInput", 
    "FileCopyInput",
    "FileSearchInput",
    
    # Database tool
    "DatabaseTool",
    "DatabaseQueryInput",
    "DatabaseSchemaInput", 
    "DatabaseExecuteInput",
    "DatabaseAnalysisInput",
]


def get_available_tools():
    """Get list of available AI tools."""
    return {
        "web_search": WebSearchTool,
        "code_executor": CodeExecutorTool,
        "file_manager": FileManagerTool,
        "database": DatabaseTool,
    }


def create_tool(tool_name: str, config: dict = None):
    """Create a tool instance by name."""
    tools = get_available_tools()
    
    if tool_name not in tools:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    return tools[tool_name](config=config)
