"""
Tool Service - High-level service for AI tool management and execution.

This service provides business logic for managing AI tools, including
registration, execution, monitoring, and security controls.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from app.ai.tools import (
    get_available_tools,
    create_tool_instance,
    BaseTool
)
from app.ai.tools.web_search import WebSearchTool
from app.ai.tools.code_executor import CodeExecutorTool
from app.ai.tools.file_manager import FileManagerTool
from app.ai.tools.database import DatabaseTool
from app.ai.services.function_calling_service import function_calling_service
from app.core.exceptions import ValidationError, AIServiceError

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of available tools."""
    WEB_SEARCH = "web_search"
    CODE_EXECUTION = "code_execution"
    FILE_MANAGEMENT = "file_management"
    DATABASE = "database"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


@dataclass
class ToolExecutionRequest:
    """Request for tool execution."""
    tool_name: str
    parameters: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timeout: float = 30.0
    security_level: str = "standard"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionResult:
    """Result from tool execution."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    tokens_used: int = 0
    security_warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolUsageStats:
    """Statistics for tool usage."""
    tool_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    avg_execution_time: float
    last_used: Optional[datetime]
    error_rate: float
    category: ToolCategory


class ToolService:
    """High-level service for AI tool operations."""
    
    def __init__(self):
        self.registered_tools: Dict[str, BaseTool] = {}
        self.tool_categories: Dict[str, Union[ToolCategory, str]] = {}
        self.usage_stats: Dict[str, Dict[str, Any]] = {}
        self.security_policies: Dict[str, Dict[str, Any]] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # Default security policies
        self.default_security_policies = {
            "web_search": {
                "max_requests_per_minute": 10,
                "allowed_domains": [],
                "blocked_domains": ["localhost", "127.0.0.1"],
                "require_https": False
            },
            "code_execution": {
                "max_execution_time": 30,
                "allowed_languages": ["python", "javascript", "bash"],
                "sandbox_enabled": True,
                "network_access": False
            },
            "file_management": {
                "allowed_paths": ["/tmp", "/workspace"],
                "blocked_paths": ["/etc", "/usr", "/bin"],
                "max_file_size": 10 * 1024 * 1024,  # 10MB
                "allowed_extensions": [".txt", ".json", ".csv", ".md"]
            },
            "database": {
                "read_only": False,
                "max_rows": 1000,
                "timeout": 10,
                "allowed_operations": ["SELECT", "INSERT", "UPDATE"]
            }
        }
        
        # Initialize with default tools
        self._initialize_default_tools()
    
    def _initialize_default_tools(self):
        """Initialize default tools."""
        try:
            # Register web search tool
            web_search_tool = WebSearchTool()
            self.register_tool(web_search_tool, web_search_tool.category)
            
            # Register code executor tool
            code_executor_tool = CodeExecutorTool()
            self.register_tool(code_executor_tool, code_executor_tool.category)
            
            # Register file manager tool
            file_manager_tool = FileManagerTool()
            self.register_tool(file_manager_tool, file_manager_tool.category)
            
            # Register database tool
            database_tool = DatabaseTool()
            self.register_tool(database_tool, database_tool.category)
            
            logger.info("Initialized default tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize default tools: {str(e)}")
    
    def register_tool(
        self,
        tool: BaseTool,
        category: Union[ToolCategory, str],
        security_policy: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a tool for use.
        
        Args:
            tool: Tool instance to register
            category: Tool category (enum or string)
            security_policy: Optional custom security policy
        """
        tool_name = tool.name
        
        # Check if tool is already registered
        if tool_name in self.registered_tools:
            logger.warning(f"Tool '{tool_name}' is already registered, skipping")
            return
        
        try:
            # Register with function calling service
            function_calling_service.register_tool(tool)
            
            # Store tool
            self.registered_tools[tool_name] = tool
            self.tool_categories[tool_name] = category
            
            # Handle both enum and string categories for security policy lookup
            if hasattr(category, 'value'):
                category_key = category.value
            else:
                category_key = str(category)
            
            # Set up security policy
            if security_policy:
                self.security_policies[tool_name] = security_policy
            elif category_key in self.default_security_policies:
                self.security_policies[tool_name] = self.default_security_policies[category_key]
            
            # Initialize usage stats
            self.usage_stats[tool_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "total_execution_time": 0.0,
                "last_used": None,
                "errors": []
            }
            
            logger.info(f"Registered tool: {tool_name} ({category_key})")
            
        except Exception as e:
            logger.error(f"Failed to register tool {tool_name}: {str(e)}")
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
            
        Returns:
            True if tool was unregistered
        """
        if tool_name in self.registered_tools:
            # Unregister from function calling service
            function_calling_service.unregister_function(tool_name)
            
            # Remove from local storage
            del self.registered_tools[tool_name]
            del self.tool_categories[tool_name]
            self.security_policies.pop(tool_name, None)
            self.usage_stats.pop(tool_name, None)
            
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        
        return False
    
    def get_available_tools(
        self,
        category: Optional[Union[ToolCategory, str]] = None,
        include_disabled: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get list of available tools.
        
        Args:
            category: Optional category filter
            include_disabled: Whether to include disabled tools
            
        Returns:
            List of tool information
        """
        tools = []
        
        for tool_name, tool in self.registered_tools.items():
            tool_category = self.tool_categories.get(tool_name)
            
            # Filter by category if specified
            if category and tool_category != category:
                continue
            
            # Check if tool is enabled
            if not include_disabled and not getattr(tool, 'enabled', True):
                continue
            
            # Handle both enum and string categories
            if hasattr(tool_category, 'value'):
                category_str = tool_category.value
            elif tool_category:
                category_str = str(tool_category)
            else:
                category_str = "unknown"
            
            tool_info = {
                "name": tool_name,
                "description": tool.description,
                "category": category_str,
                "parameters": tool.parameters,
                "required_params": getattr(tool, 'required_params', []),
                "enabled": getattr(tool, 'enabled', True)
            }
            
            tools.append(tool_info)
        
        return tools
    
    async def execute_tool(
        self,
        request: ToolExecutionRequest
    ) -> ToolExecutionResult:
        """
        Execute a tool with security and monitoring.
        
        Args:
            request: Tool execution request
            
        Returns:
            ToolExecutionResult with execution details
        """
        import time
        start_time = time.time()
        
        # Validate tool exists
        if request.tool_name not in self.registered_tools:
            return ToolExecutionResult(
                tool_name=request.tool_name,
                success=False,
                result=None,
                error=f"Tool '{request.tool_name}' not found"
            )
        
        tool = self.registered_tools[request.tool_name]
        
        try:
            # Check security policy
            security_warnings = await self._check_security_policy(request)
            
            # Execute tool
            result = await asyncio.wait_for(
                tool.execute(**request.parameters),
                timeout=request.timeout
            )
            
            execution_time = time.time() - start_time
            
            # Update usage stats
            await self._update_usage_stats(
                request.tool_name, True, execution_time, None
            )
            
            # Log execution
            await self._log_execution(request, result, True, execution_time)
            
            return ToolExecutionResult(
                tool_name=request.tool_name,
                success=True,
                result=result,
                execution_time=execution_time,
                security_warnings=security_warnings,
                metadata=request.metadata
            )
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error_msg = f"Tool execution timed out after {request.timeout}s"
            
            await self._update_usage_stats(
                request.tool_name, False, execution_time, error_msg
            )
            await self._log_execution(request, None, False, execution_time, error_msg)
            
            return ToolExecutionResult(
                tool_name=request.tool_name,
                success=False,
                result=None,
                error=error_msg,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            await self._update_usage_stats(
                request.tool_name, False, execution_time, error_msg
            )
            await self._log_execution(request, None, False, execution_time, error_msg)
            
            return ToolExecutionResult(
                tool_name=request.tool_name,
                success=False,
                result=None,
                error=error_msg,
                execution_time=execution_time
            )
    
    async def _check_security_policy(
        self,
        request: ToolExecutionRequest
    ) -> List[str]:
        """Check tool execution against security policy."""
        warnings = []
        tool_name = request.tool_name
        
        if tool_name not in self.security_policies:
            return warnings
        
        policy = self.security_policies[tool_name]
        category = self.tool_categories.get(tool_name)
        
        # Convert category to string for comparison
        if hasattr(category, 'value'):
            category_str = category.value
        else:
            category_str = str(category) if category else ""
        
        # Check category-specific policies based on tool name patterns
        # Since tools use their own category strings, we check by tool name
        if tool_name == "web_search" or category_str in ["information", "web_search"]:
            url = request.parameters.get('url', '')
            if url:
                # Check blocked domains
                blocked_domains = policy.get('blocked_domains', [])
                for domain in blocked_domains:
                    if domain in url:
                        warnings.append(f"URL contains blocked domain: {domain}")
                
                # Check HTTPS requirement
                if policy.get('require_https', False) and not url.startswith('https://'):
                    warnings.append("HTTPS required but HTTP URL provided")
        
        elif tool_name == "code_executor" or category_str in ["development", "code_execution"]:
            language = request.parameters.get('language', '')
            code = request.parameters.get('code', '')
            
            # Check allowed languages
            allowed_languages = policy.get('allowed_languages', [])
            if allowed_languages and language not in allowed_languages:
                warnings.append(f"Language '{language}' not in allowed list")
            
            # Check for potentially dangerous code patterns
            dangerous_patterns = ['os.system', 'subprocess', 'eval', 'exec', '__import__']
            for pattern in dangerous_patterns:
                if pattern in code:
                    warnings.append(f"Potentially dangerous code pattern detected: {pattern}")
        
        elif tool_name == "file_manager" or category_str in ["file_system", "file_management"]:
            file_path = request.parameters.get('file_path', '')
            
            # Check allowed paths
            allowed_paths = policy.get('allowed_paths', [])
            if allowed_paths and not any(file_path.startswith(path) for path in allowed_paths):
                warnings.append(f"File path not in allowed directories")
            
            # Check blocked paths
            blocked_paths = policy.get('blocked_paths', [])
            for blocked_path in blocked_paths:
                if file_path.startswith(blocked_path):
                    warnings.append(f"File path in blocked directory: {blocked_path}")
        
        return warnings
    
    async def _update_usage_stats(
        self,
        tool_name: str,
        success: bool,
        execution_time: float,
        error: Optional[str]
    ) -> None:
        """Update usage statistics for a tool."""
        if tool_name not in self.usage_stats:
            return
        
        stats = self.usage_stats[tool_name]
        stats["total_executions"] += 1
        stats["total_execution_time"] += execution_time
        stats["last_used"] = datetime.utcnow()
        
        if success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1
            if error:
                stats["errors"].append({
                    "timestamp": datetime.utcnow(),
                    "error": error
                })
                # Keep only last 10 errors
                stats["errors"] = stats["errors"][-10:]
    
    async def _log_execution(
        self,
        request: ToolExecutionRequest,
        result: Any,
        success: bool,
        execution_time: float,
        error: Optional[str] = None
    ) -> None:
        """Log tool execution."""
        log_entry = {
            "timestamp": datetime.utcnow(),
            "tool_name": request.tool_name,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "parameters": request.parameters,
            "success": success,
            "execution_time": execution_time,
            "error": error,
            "metadata": request.metadata
        }
        
        self.execution_history.append(log_entry)
        
        # Trim history if too large
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size:]
    
    def get_tool_usage_stats(
        self,
        tool_name: Optional[str] = None
    ) -> Union[ToolUsageStats, List[ToolUsageStats]]:
        """
        Get usage statistics for tools.
        
        Args:
            tool_name: Optional specific tool name
            
        Returns:
            ToolUsageStats or list of stats
        """
        if tool_name:
            if tool_name not in self.usage_stats:
                raise ValidationError(f"Tool '{tool_name}' not found")
            
            stats = self.usage_stats[tool_name]
            category = self.tool_categories.get(tool_name, "custom")
            
            # Convert category to ToolCategory enum if possible, otherwise use CUSTOM
            if isinstance(category, str):
                # Try to map string categories to enum values
                category_mapping = {
                    "information": ToolCategory.WEB_SEARCH,
                    "web_search": ToolCategory.WEB_SEARCH,
                    "development": ToolCategory.CODE_EXECUTION,
                    "code_execution": ToolCategory.CODE_EXECUTION,
                    "file_system": ToolCategory.FILE_MANAGEMENT,
                    "file_management": ToolCategory.FILE_MANAGEMENT,
                    "data": ToolCategory.DATABASE,
                    "database": ToolCategory.DATABASE,
                    "utility": ToolCategory.ANALYSIS,
                    "system": ToolCategory.CUSTOM
                }
                category = category_mapping.get(category, ToolCategory.CUSTOM)
            
            error_rate = 0.0
            if stats["total_executions"] > 0:
                error_rate = stats["failed_executions"] / stats["total_executions"]
            
            avg_execution_time = 0.0
            if stats["successful_executions"] > 0:
                avg_execution_time = stats["total_execution_time"] / stats["successful_executions"]
            
            return ToolUsageStats(
                tool_name=tool_name,
                total_executions=stats["total_executions"],
                successful_executions=stats["successful_executions"],
                failed_executions=stats["failed_executions"],
                avg_execution_time=avg_execution_time,
                last_used=stats["last_used"],
                error_rate=error_rate,
                category=category
            )
        else:
            # Return stats for all tools
            all_stats = []
            for tool_name in self.usage_stats:
                tool_stats = self.get_tool_usage_stats(tool_name)
                all_stats.append(tool_stats)
            
            return all_stats
    
    def get_execution_history(
        self,
        tool_name: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get execution history with filters.
        
        Args:
            tool_name: Optional tool name filter
            user_id: Optional user ID filter
            limit: Optional limit on results
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of execution log entries
        """
        history = self.execution_history.copy()
        
        # Apply filters
        if tool_name:
            history = [entry for entry in history if entry["tool_name"] == tool_name]
        
        if user_id:
            history = [entry for entry in history if entry["user_id"] == user_id]
        
        if start_date:
            history = [entry for entry in history if entry["timestamp"] >= start_date]
        
        if end_date:
            history = [entry for entry in history if entry["timestamp"] <= end_date]
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Apply limit
        if limit:
            history = history[:limit]
        
        return history
    
    def update_security_policy(
        self,
        tool_name: str,
        policy_updates: Dict[str, Any]
    ) -> bool:
        """
        Update security policy for a tool.
        
        Args:
            tool_name: Tool name
            policy_updates: Policy updates
            
        Returns:
            True if updated successfully
        """
        if tool_name not in self.registered_tools:
            raise ValidationError(f"Tool '{tool_name}' not found")
        
        if tool_name not in self.security_policies:
            self.security_policies[tool_name] = {}
        
        self.security_policies[tool_name].update(policy_updates)
        
        logger.info(f"Updated security policy for tool: {tool_name}")
        return True
    
    def enable_tool(self, tool_name: str) -> bool:
        """Enable a tool."""
        if tool_name in self.registered_tools:
            setattr(self.registered_tools[tool_name], 'enabled', True)
            logger.info(f"Enabled tool: {tool_name}")
            return True
        return False
    
    def disable_tool(self, tool_name: str) -> bool:
        """Disable a tool."""
        if tool_name in self.registered_tools:
            setattr(self.registered_tools[tool_name], 'enabled', False)
            logger.info(f"Disabled tool: {tool_name}")
            return True
        return False
    
    def get_tool_health(self) -> Dict[str, Any]:
        """Get overall tool system health."""
        total_tools = len(self.registered_tools)
        enabled_tools = sum(
            1 for tool in self.registered_tools.values()
            if getattr(tool, 'enabled', True)
        )
        
        total_executions = sum(
            stats["total_executions"] for stats in self.usage_stats.values()
        )
        total_failures = sum(
            stats["failed_executions"] for stats in self.usage_stats.values()
        )
        
        overall_error_rate = 0.0
        if total_executions > 0:
            overall_error_rate = total_failures / total_executions
        
        # Get categories, handling both enum and string values
        categories = []
        for cat in self.tool_categories.values():
            if hasattr(cat, 'value'):
                categories.append(cat.value)
            else:
                categories.append(str(cat))
        
        return {
            "total_tools": total_tools,
            "enabled_tools": enabled_tools,
            "disabled_tools": total_tools - enabled_tools,
            "total_executions": total_executions,
            "total_failures": total_failures,
            "overall_error_rate": overall_error_rate,
            "execution_history_size": len(self.execution_history),
            "categories": list(set(categories))
        }


# Singleton instance
tool_service = ToolService()
