"""
Built-in AI Tools

This module provides a collection of built-in tools that agents can use,
including web search, calculator, file system operations, and database queries.
"""

import asyncio
import json
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseTool, ToolResult, ToolParameter, ToolParameterType
from app.core.config import settings
from app.db.base import get_db_session

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Tool for searching the web."""
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Search the web for information using a search query"
    
    @property
    def category(self) -> str:
        return "information"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type=ToolParameterType.STRING,
                description="Search query",
                required=True
            ),
            ToolParameter(
                name="max_results",
                type=ToolParameterType.INTEGER,
                description="Maximum number of results to return",
                required=False,
                default=settings.WEB_SEARCH_MAX_RESULTS or 5,
                min_value=1,
                max_value=20
            )
        ]
    
    async def execute(self, query: str, max_results: int = 5) -> ToolResult:
        """Execute web search."""
        start_time = time.time()
        
        try:
            # For demo purposes, return mock search results
            # In production, integrate with actual search APIs (Google, Bing, DuckDuckGo)
            
            # Simulate API call delay
            await asyncio.sleep(0.5)
            
            mock_results = [
                {
                    "title": f"Search result {i+1} for: {query}",
                    "url": f"https://example.com/search-result-{i+1}",
                    "snippet": f"This is a mock search result snippet {i+1} containing information about {query}...",
                    "source": "example.com"
                }
                for i in range(min(max_results, 3))
            ]
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                success=True,
                result={
                    "query": query,
                    "results": mock_results,
                    "total_results": len(mock_results)
                },
                execution_time=execution_time,
                metadata={"search_engine": "mock"}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Web search failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )


class CalculatorTool(BaseTool):
    """Tool for mathematical calculations."""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "Perform mathematical calculations and evaluate expressions"
    
    @property
    def category(self) -> str:
        return "utility"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type=ToolParameterType.STRING,
                description="Mathematical expression to evaluate (e.g., '2 + 3 * 4', 'sqrt(25)', 'sin(pi/2)')",
                required=True
            )
        ]
    
    async def execute(self, expression: str) -> ToolResult:
        """Execute calculation."""
        start_time = time.time()
        
        try:
            # Sanitize expression for safety
            sanitized = self._sanitize_expression(expression)
            
            # Create safe evaluation context
            safe_dict = {
                "__builtins__": {},
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pi": math.pi,
                "e": math.e,
                "ceil": math.ceil,
                "floor": math.floor,
            }
            
            # Evaluate expression
            result = eval(sanitized, safe_dict)
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                success=True,
                result={
                    "expression": expression,
                    "result": result,
                    "formatted_result": str(result)
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Calculator execution failed: {e}")
            return ToolResult(
                success=False,
                error=f"Calculation error: {str(e)}",
                execution_time=execution_time
            )
    
    def _sanitize_expression(self, expression: str) -> str:
        """Sanitize mathematical expression for safe evaluation."""
        # Remove dangerous keywords
        dangerous_keywords = [
            'import', 'exec', 'eval', 'open', 'file', 'input', 'raw_input',
            '__import__', '__builtins__', '__globals__', '__locals__',
            'globals', 'locals', 'vars', 'dir', 'help'
        ]
        
        expr_lower = expression.lower()
        for keyword in dangerous_keywords:
            if keyword in expr_lower:
                raise ValueError(f"Dangerous keyword '{keyword}' not allowed")
        
        # Allow only safe characters
        safe_pattern = re.compile(r'^[0-9+\-*/().,\s\w]+$')
        if not safe_pattern.match(expression):
            raise ValueError("Expression contains invalid characters")
        
        return expression


class FileSystemTool(BaseTool):
    """Tool for basic file system operations."""
    
    @property
    def name(self) -> str:
        return "file_system"
    
    @property
    def description(self) -> str:
        return "Perform basic file system operations like listing directories and reading file info"
    
    @property
    def category(self) -> str:
        return "system"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="operation",
                type=ToolParameterType.STRING,
                description="File system operation to perform",
                required=True,
                enum=["list", "info", "exists"]
            ),
            ToolParameter(
                name="path",
                type=ToolParameterType.STRING,
                description="File or directory path",
                required=True
            )
        ]
    
    async def execute(self, operation: str, path: str) -> ToolResult:
        """Execute file system operation."""
        start_time = time.time()
        
        try:
            # Security: Restrict to safe directories
            safe_path = self._validate_path(path)
            
            if operation == "list":
                result = await self._list_directory(safe_path)
            elif operation == "info":
                result = await self._get_file_info(safe_path)
            elif operation == "exists":
                result = await self._check_exists(safe_path)
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"File system operation failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def _validate_path(self, path: str) -> Path:
        """Validate and restrict file path for security."""
        # Convert to Path object
        p = Path(path).resolve()
        
        # Define allowed base directories (customize as needed)
        allowed_bases = [
            Path.cwd(),  # Current working directory
            Path.home() / "Documents",  # User documents
            Path("/tmp") if os.name != "nt" else Path(os.environ.get("TEMP", "C:\\temp"))
        ]
        
        # Check if path is within allowed directories
        for base in allowed_bases:
            try:
                p.relative_to(base)
                return p
            except ValueError:
                continue
        
        raise ValueError(f"Access to path '{path}' is not allowed")
    
    async def _list_directory(self, path: Path) -> Dict[str, Any]:
        """List directory contents."""
        if not path.is_dir():
            raise ValueError(f"Path '{path}' is not a directory")
        
        items = []
        for item in path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
                "modified": item.stat().st_mtime
            })
        
        return {
            "path": str(path),
            "items": items,
            "count": len(items)
        }
    
    async def _get_file_info(self, path: Path) -> Dict[str, Any]:
        """Get file information."""
        if not path.exists():
            raise ValueError(f"Path '{path}' does not exist")
        
        stat = path.stat()
        
        return {
            "path": str(path),
            "name": path.name,
            "type": "directory" if path.is_dir() else "file",
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "permissions": oct(stat.st_mode)[-3:]
        }
    
    async def _check_exists(self, path: Path) -> Dict[str, Any]:
        """Check if path exists."""
        return {
            "path": str(path),
            "exists": path.exists(),
            "is_file": path.is_file(),
            "is_directory": path.is_dir()
        }


class DatabaseTool(BaseTool):
    """Tool for database queries (read-only)."""
    
    @property
    def name(self) -> str:
        return "database_query"
    
    @property
    def description(self) -> str:
        return "Execute read-only database queries to retrieve information"
    
    @property
    def category(self) -> str:
        return "data"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type=ToolParameterType.STRING,
                description="SQL query to execute (SELECT only)",
                required=True
            ),
            ToolParameter(
                name="limit",
                type=ToolParameterType.INTEGER,
                description="Maximum number of rows to return",
                required=False,
                default=100,
                min_value=1,
                max_value=1000
            )
        ]
    
    async def execute(self, query: str, limit: int = 100) -> ToolResult:
        """Execute database query."""
        start_time = time.time()
        
        try:
            # Validate query is read-only
            self._validate_readonly_query(query)
            
            # Add LIMIT clause if not present
            if "limit" not in query.lower():
                query = f"{query.rstrip(';')} LIMIT {limit}"
            
            async with get_db_session() as db:
                result = await db.execute(text(query))
                rows = result.fetchall()
                columns = result.keys()
                
                # Convert to list of dictionaries
                data = [dict(zip(columns, row)) for row in rows]
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                success=True,
                result={
                    "query": query,
                    "data": data,
                    "row_count": len(data),
                    "columns": list(columns)
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Database query failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def _validate_readonly_query(self, query: str) -> None:
        """Validate that query is read-only."""
        query_lower = query.lower().strip()
        
        # Must start with SELECT
        if not query_lower.startswith('select'):
            raise ValueError("Only SELECT queries are allowed")
        
        # Check for dangerous keywords
        dangerous_keywords = [
            'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'truncate', 'replace', 'merge', 'call', 'exec', 'execute'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query_lower:
                raise ValueError(f"Keyword '{keyword}' is not allowed in read-only queries")


class TimeTool(BaseTool):
    """Tool for time and date operations."""
    
    @property
    def name(self) -> str:
        return "time_info"
    
    @property
    def description(self) -> str:
        return "Get current time, date, and time zone information"
    
    @property
    def category(self) -> str:
        return "utility"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="operation",
                type=ToolParameterType.STRING,
                description="Time operation to perform",
                required=True,
                enum=["current", "timestamp", "format"]
            ),
            ToolParameter(
                name="format",
                type=ToolParameterType.STRING,
                description="Date format string (for format operation)",
                required=False,
                default="%Y-%m-%d %H:%M:%S"
            )
        ]
    
    async def execute(self, operation: str, format: str = "%Y-%m-%d %H:%M:%S") -> ToolResult:
        """Execute time operation."""
        start_time = time.time()
        
        try:
            from datetime import datetime, timezone
            
            now = datetime.now(timezone.utc)
            
            if operation == "current":
                result = {
                    "current_time": now.isoformat(),
                    "utc_time": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "timestamp": now.timestamp(),
                    "year": now.year,
                    "month": now.month,
                    "day": now.day,
                    "hour": now.hour,
                    "minute": now.minute,
                    "second": now.second,
                    "weekday": now.strftime("%A"),
                    "timezone": "UTC"
                }
            elif operation == "timestamp":
                result = {
                    "timestamp": now.timestamp(),
                    "timestamp_ms": int(now.timestamp() * 1000)
                }
            elif operation == "format":
                result = {
                    "formatted_time": now.strftime(format),
                    "format_used": format
                }
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Time operation failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )


class CodeExecutorTool(BaseTool):
    """Tool for executing code in a sandboxed environment."""
    
    @property
    def name(self) -> str:
        return "code_executor"
    
    @property
    def description(self) -> str:
        return "Execute code snippets in a secure sandboxed environment"
    
    @property
    def category(self) -> str:
        return "development"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type=ToolParameterType.STRING,
                description="Code to execute",
                required=True
            ),
            ToolParameter(
                name="language",
                type=ToolParameterType.STRING,
                description="Programming language",
                required=False,
                default="python",
                enum=["python", "javascript", "bash"]
            ),
            ToolParameter(
                name="timeout",
                type=ToolParameterType.INTEGER,
                description="Execution timeout in seconds",
                required=False,
                default=10,
                min_value=1,
                max_value=30
            )
        ]
    
    async def execute(self, code: str, language: str = "python", timeout: int = 10) -> ToolResult:
        """Execute code in sandbox."""
        start_time = time.time()
        
        try:
            # For security, this is a mock implementation
            # In production, use proper sandboxing like Docker containers
            
            if language == "python":
                # Mock Python execution
                result = {
                    "output": f"Mock execution of Python code:\n{code}\n\n# This would be executed in a secure sandbox",
                    "exit_code": 0,
                    "language": language,
                    "execution_time": 0.1
                }
            elif language == "javascript":
                # Mock JavaScript execution
                result = {
                    "output": f"Mock execution of JavaScript code:\n{code}\n\n// This would be executed in a secure sandbox",
                    "exit_code": 0,
                    "language": language,
                    "execution_time": 0.1
                }
            elif language == "bash":
                # Mock Bash execution
                result = {
                    "output": f"Mock execution of Bash code:\n{code}\n\n# This would be executed in a secure sandbox",
                    "exit_code": 0,
                    "language": language,
                    "execution_time": 0.1
                }
            else:
                raise ValueError(f"Unsupported language: {language}")
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                success=True,
                result=result,
                execution_time=execution_time,
                metadata={"sandbox": "mock", "security_level": "high"}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Code execution failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )


class FileManagerTool(BaseTool):
    """Tool for advanced file management operations."""
    
    @property
    def name(self) -> str:
        return "file_manager"
    
    @property
    def description(self) -> str:
        return "Advanced file management operations including read, write, copy, move"
    
    @property
    def category(self) -> str:
        return "file_system"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="operation",
                type=ToolParameterType.STRING,
                description="File operation to perform",
                required=True,
                enum=["read", "write", "copy", "move", "delete", "create_dir"]
            ),
            ToolParameter(
                name="source_path",
                type=ToolParameterType.STRING,
                description="Source file or directory path",
                required=True
            ),
            ToolParameter(
                name="target_path",
                type=ToolParameterType.STRING,
                description="Target path (for copy/move operations)",
                required=False
            ),
            ToolParameter(
                name="content",
                type=ToolParameterType.STRING,
                description="Content to write (for write operations)",
                required=False
            )
        ]
    
    async def execute(
        self, 
        operation: str, 
        source_path: str, 
        target_path: Optional[str] = None,
        content: Optional[str] = None
    ) -> ToolResult:
        """Execute file management operation."""
        start_time = time.time()
        
        try:
            # Validate paths for security
            source = self._validate_path(source_path)
            target = Path(target_path) if target_path else None
            
            if operation == "read":
                if not source.exists():
                    raise FileNotFoundError(f"File not found: {source}")
                
                content = source.read_text(encoding='utf-8')
                result = {
                    "operation": operation,
                    "path": str(source),
                    "content": content,
                    "size": len(content)
                }
                
            elif operation == "write":
                if content is None:
                    raise ValueError("Content is required for write operation")
                
                source.write_text(content, encoding='utf-8')
                result = {
                    "operation": operation,
                    "path": str(source),
                    "bytes_written": len(content.encode('utf-8'))
                }
                
            elif operation == "copy":
                if target is None:
                    raise ValueError("Target path is required for copy operation")
                
                import shutil
                shutil.copy2(source, target)
                result = {
                    "operation": operation,
                    "source": str(source),
                    "target": str(target)
                }
                
            elif operation == "move":
                if target is None:
                    raise ValueError("Target path is required for move operation")
                
                import shutil
                shutil.move(source, target)
                result = {
                    "operation": operation,
                    "source": str(source),
                    "target": str(target)
                }
                
            elif operation == "delete":
                if source.is_file():
                    source.unlink()
                elif source.is_dir():
                    import shutil
                    shutil.rmtree(source)
                
                result = {
                    "operation": operation,
                    "path": str(source),
                    "deleted": True
                }
                
            elif operation == "create_dir":
                source.mkdir(parents=True, exist_ok=True)
                result = {
                    "operation": operation,
                    "path": str(source),
                    "created": True
                }
                
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"File management operation failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def _validate_path(self, path: str) -> Path:
        """Validate file path for security."""
        path_obj = Path(path).resolve()
        
        # Security check: prevent access to sensitive directories
        sensitive_dirs = ["/etc", "/usr", "/bin", "/sbin", "/root", "/home"]
        for sensitive_dir in sensitive_dirs:
            if str(path_obj).startswith(sensitive_dir):
                raise ValueError(f"Access to {sensitive_dir} is not allowed")
        
        return path_obj 