"""
Unit tests for AI tools framework.

Tests all built-in tools and the tool framework infrastructure
to ensure they work correctly and safely.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from app.ai.tools.base import BaseTool, ToolResult, ToolParameter, ToolParameterType, ToolRegistry
from app.ai.tools.manager import ToolManager, ToolExecutionContext, FunctionCall
from app.ai.tools.builtin import (
    WebSearchTool, CalculatorTool, FileSystemTool, 
    DatabaseTool, TimeTool
)
from app.ai.tools.registry import tool_registry


class TestBaseTool:
    """Test base tool functionality."""
    
    def test_tool_parameter_creation(self):
        """Test tool parameter creation."""
        param = ToolParameter(
            name="test_param",
            type=ToolParameterType.STRING,
            description="Test parameter",
            required=True,
            enum=["option1", "option2"]
        )
        
        assert param.name == "test_param"
        assert param.type == ToolParameterType.STRING
        assert param.required is True
        assert param.enum == ["option1", "option2"]
    
    def test_tool_result_creation(self):
        """Test tool result creation."""
        result = ToolResult(
            success=True,
            result={"data": "test"},
            execution_time=1.5,
            metadata={"tool": "test"}
        )
        
        assert result.success is True
        assert result.result == {"data": "test"}
        assert result.execution_time == 1.5
        assert result.metadata["tool"] == "test"
    
    def test_tool_result_to_dict(self):
        """Test tool result to dictionary conversion."""
        result = ToolResult(
            success=True,
            result="test result",
            execution_time=2.0
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["result"] == "test result"
        assert result_dict["execution_time"] == 2.0
        assert result_dict["error"] is None


class MockTool(BaseTool):
    """Mock tool for testing."""
    
    @property
    def name(self) -> str:
        return "mock_tool"
    
    @property
    def description(self) -> str:
        return "A mock tool for testing"
    
    @property
    def parameters(self):
        return [
            ToolParameter(
                name="input_text",
                type=ToolParameterType.STRING,
                description="Input text",
                required=True
            ),
            ToolParameter(
                name="count",
                type=ToolParameterType.INTEGER,
                description="Count value",
                required=False,
                default=1,
                min_value=1,
                max_value=10
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        import time
        start_time = time.time()
        
        input_text = kwargs.get("input_text", "")
        count = kwargs.get("count", 1)
        
        result = f"Processed '{input_text}' {count} times"
        
        return ToolResult(
            success=True,
            result=result,
            execution_time=time.time() - start_time
        )


class TestToolRegistry:
    """Test tool registry functionality."""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh tool registry."""
        return ToolRegistry()
    
    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool."""
        return MockTool()
    
    def test_register_tool(self, registry, mock_tool):
        """Test tool registration."""
        registry.register(mock_tool)
        
        assert "mock_tool" in registry
        assert len(registry) == 1
        assert registry.get("mock_tool") is mock_tool
    
    def test_register_duplicate_tool(self, registry, mock_tool):
        """Test registering duplicate tool raises error."""
        registry.register(mock_tool)
        
        duplicate_tool = MockTool()
        with pytest.raises(ValueError, match="already registered"):
            registry.register(duplicate_tool)
    
    def test_unregister_tool(self, registry, mock_tool):
        """Test tool unregistration."""
        registry.register(mock_tool)
        assert "mock_tool" in registry
        
        registry.unregister("mock_tool")
        assert "mock_tool" not in registry
        assert len(registry) == 0
    
    def test_list_tools(self, registry, mock_tool):
        """Test listing tools."""
        registry.register(mock_tool)
        
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0] is mock_tool
    
    def test_get_function_schemas(self, registry, mock_tool):
        """Test getting function schemas."""
        registry.register(mock_tool)
        
        schemas = registry.get_function_schemas()
        assert len(schemas) == 1
        
        schema = schemas[0]
        assert schema["name"] == "mock_tool"
        assert schema["description"] == "A mock tool for testing"
        assert "parameters" in schema


class TestBuiltinTools:
    """Test all built-in tools."""
    
    @pytest.mark.asyncio
    async def test_web_search_tool(self):
        """Test web search tool."""
        tool = WebSearchTool()
        
        assert tool.name == "web_search"
        assert tool.category == "information"
        
        # Test execution
        result = await tool.execute(query="test search", max_results=3)
        
        assert result.success is True
        assert "results" in result.result
        assert len(result.result["results"]) <= 3
    
    @pytest.mark.asyncio
    async def test_calculator_tool(self):
        """Test calculator tool."""
        tool = CalculatorTool()
        
        assert tool.name == "calculator"
        assert tool.category == "utility"
        
        # Test basic calculation
        result = await tool.execute(expression="2 + 3 * 4")
        
        assert result.success is True
        assert result.result["result"] == 14
        
        # Test math functions
        result = await tool.execute(expression="sqrt(25)")
        
        assert result.success is True
        assert result.result["result"] == 5.0
    
    @pytest.mark.asyncio
    async def test_calculator_tool_error_handling(self):
        """Test calculator tool error handling."""
        tool = CalculatorTool()
        
        # Test invalid expression
        result = await tool.execute(expression="invalid expression")
        
        assert result.success is False
        assert "error" in result.error
        
        # Test dangerous expression
        result = await tool.execute(expression="import os")
        
        assert result.success is False
        assert "Dangerous keyword" in result.error
    
    @pytest.mark.asyncio
    async def test_file_system_tool(self):
        """Test file system tool."""
        tool = FileSystemTool()
        
        assert tool.name == "file_system"
        assert tool.category == "system"
        
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test directory listing
            result = await tool.execute(operation="list", path=temp_dir)
            
            assert result.success is True
            assert "items" in result.result
            assert isinstance(result.result["items"], list)
            
            # Test path existence check
            result = await tool.execute(operation="exists", path=temp_dir)
            
            assert result.success is True
            assert result.result["exists"] is True
            assert result.result["is_directory"] is True
    
    @pytest.mark.asyncio
    async def test_file_system_tool_security(self):
        """Test file system tool security restrictions."""
        tool = FileSystemTool()
        
        # Test access to restricted path
        result = await tool.execute(operation="list", path="/etc/passwd")
        
        assert result.success is False
        assert "not allowed" in result.error
    
    @pytest.mark.asyncio
    async def test_database_tool(self):
        """Test database tool."""
        tool = DatabaseTool()
        
        assert tool.name == "database_query"
        assert tool.category == "data"
        
        # Mock database session
        with patch('app.ai.tools.builtin.get_db_session') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.fetchall.return_value = [("test", 1), ("data", 2)]
            mock_result.keys.return_value = ["name", "value"]
            mock_session.execute.return_value = mock_result
            mock_get_db.return_value.__aenter__.return_value = mock_session
            
            result = await tool.execute(query="SELECT name, value FROM test_table", limit=10)
            
            assert result.success is True
            assert "data" in result.result
            assert len(result.result["data"]) == 2
            assert result.result["data"][0]["name"] == "test"
    
    @pytest.mark.asyncio
    async def test_database_tool_security(self):
        """Test database tool security."""
        tool = DatabaseTool()
        
        # Test INSERT query (should be blocked)
        result = await tool.execute(query="INSERT INTO users VALUES ('hack', 'pass')")
        
        assert result.success is False
        assert "not allowed" in result.error
        
        # Test DROP query (should be blocked)
        result = await tool.execute(query="DROP TABLE users")
        
        assert result.success is False
        assert "not allowed" in result.error
    
    @pytest.mark.asyncio
    async def test_time_tool(self):
        """Test time tool."""
        tool = TimeTool()
        
        assert tool.name == "time_info"
        assert tool.category == "utility"
        
        # Test current time
        result = await tool.execute(operation="current")
        
        assert result.success is True
        assert "current_time" in result.result
        assert "timestamp" in result.result
        assert "year" in result.result
        
        # Test timestamp
        result = await tool.execute(operation="timestamp")
        
        assert result.success is True
        assert "timestamp" in result.result
        assert isinstance(result.result["timestamp"], float)
        
        # Test custom format
        result = await tool.execute(operation="format", format="%Y-%m-%d")
        
        assert result.success is True
        assert "formatted_time" in result.result


class TestToolManager:
    """Test tool manager functionality."""
    
    @pytest.fixture
    def tool_manager(self):
        """Create a tool manager with mock registry."""
        registry = ToolRegistry()
        registry.register(MockTool())
        return ToolManager(registry=registry)
    
    @pytest.mark.asyncio
    async def test_execute_tool(self, tool_manager):
        """Test tool execution."""
        context = ToolExecutionContext()
        
        result = await tool_manager.execute_tool(
            tool_name="mock_tool",
            parameters={"input_text": "hello", "count": 3},
            context=context
        )
        
        assert result.success is True
        assert "Processed 'hello' 3 times" in result.result
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, tool_manager):
        """Test executing non-existent tool."""
        context = ToolExecutionContext()
        
        result = await tool_manager.execute_tool(
            tool_name="nonexistent_tool",
            parameters={},
            context=context
        )
        
        assert result.success is False
        assert "not found" in result.error
    
    @pytest.mark.asyncio
    async def test_parameter_validation(self, tool_manager):
        """Test parameter validation."""
        context = ToolExecutionContext()
        
        # Test missing required parameter
        result = await tool_manager.execute_tool(
            tool_name="mock_tool",
            parameters={"count": 3},  # missing input_text
            context=context
        )
        
        assert result.success is False
        assert "Required parameter" in result.error
        
        # Test invalid parameter value
        result = await tool_manager.execute_tool(
            tool_name="mock_tool",
            parameters={"input_text": "hello", "count": 15},  # count > max_value
            context=context
        )
        
        assert result.success is False
        assert "must be <=" in result.error
    
    @pytest.mark.asyncio
    async def test_function_calls_execution(self, tool_manager):
        """Test function calls execution."""
        function_calls = [
            FunctionCall(
                name="mock_tool",
                arguments={"input_text": "test1", "count": 1}
            ),
            FunctionCall(
                name="mock_tool", 
                arguments={"input_text": "test2", "count": 2}
            )
        ]
        
        context = ToolExecutionContext()
        results = await tool_manager.execute_function_calls(function_calls, context)
        
        assert len(results) == 2
        
        for call, result in results:
            assert result.success is True
            assert "Processed" in result.result
    
    @pytest.mark.asyncio
    async def test_openai_function_calls(self, tool_manager):
        """Test OpenAI function call handling."""
        openai_calls = [{
            "name": "mock_tool",
            "arguments": '{"input_text": "openai test", "count": 1}',
            "id": "call_123"
        }]
        
        context = ToolExecutionContext()
        messages = await tool_manager.handle_openai_function_calls(openai_calls, context)
        
        assert len(messages) == 1
        assert messages[0]["role"] == "function"
        assert messages[0]["name"] == "mock_tool"
        assert "Processed 'openai test' 1 times" in messages[0]["content"]
    
    @pytest.mark.asyncio
    async def test_anthropic_tool_use(self, tool_manager):
        """Test Anthropic tool use handling."""
        tool_uses = [{
            "name": "mock_tool",
            "input": {"input_text": "anthropic test", "count": 2},
            "id": "tool_123"
        }]
        
        context = ToolExecutionContext()
        tool_results = await tool_manager.handle_anthropic_tool_use(tool_uses, context)
        
        assert len(tool_results) == 1
        assert tool_results[0]["type"] == "tool_result"
        assert tool_results[0]["tool_use_id"] == "tool_123"
        assert tool_results[0]["is_error"] is False
    
    def test_tool_enable_disable(self, tool_manager):
        """Test tool enable/disable functionality."""
        # Tool should be enabled by default
        tool = tool_manager.registry.get("mock_tool")
        assert tool.enabled is True
        
        # Disable tool
        success = tool_manager.disable_tool("mock_tool")
        assert success is True
        assert tool.enabled is False
        
        # Enable tool
        success = tool_manager.enable_tool("mock_tool")
        assert success is True
        assert tool.enabled is True
    
    def test_execution_history(self, tool_manager):
        """Test execution history tracking."""
        # Initially empty
        history = tool_manager.get_execution_history()
        assert len(history) == 0
        
        # Add some mock history
        tool_manager.execution_history.append({
            "tool_name": "mock_tool",
            "parameters": {"input_text": "test"},
            "result": {"success": True},
            "executed_at": "2024-01-01T00:00:00Z"
        })
        
        history = tool_manager.get_execution_history()
        assert len(history) == 1
        assert history[0]["tool_name"] == "mock_tool"
        
        # Test history filtering
        history = tool_manager.get_execution_history(tool_name="other_tool")
        assert len(history) == 0
        
        # Clear history
        tool_manager.clear_execution_history()
        history = tool_manager.get_execution_history()
        assert len(history) == 0
    
    def test_execution_stats(self, tool_manager):
        """Test execution statistics."""
        # Initially empty stats
        stats = tool_manager.get_stats()
        assert stats["total_executions"] == 0
        assert stats["success_rate"] == 0.0
        
        # Add mock execution data
        tool_manager.execution_history.extend([
            {
                "tool_name": "mock_tool",
                "result": {"success": True, "execution_time": 1.0},
                "executed_at": "2024-01-01T00:00:00Z"
            },
            {
                "tool_name": "mock_tool",
                "result": {"success": False, "execution_time": 0.5},
                "executed_at": "2024-01-01T00:01:00Z"
            },
            {
                "tool_name": "other_tool",
                "result": {"success": True, "execution_time": 2.0},
                "executed_at": "2024-01-01T00:02:00Z"
            }
        ])
        
        stats = tool_manager.get_stats()
        assert stats["total_executions"] == 3
        assert stats["successful_executions"] == 2
        assert stats["failed_executions"] == 1
        assert stats["success_rate"] == 2/3
        assert stats["avg_execution_time"] == 1.5  # (1.0 + 0.5 + 2.0) / 3
        assert "mock_tool" in stats["tools_used"]
        assert "other_tool" in stats["tools_used"]


class TestFunctionCall:
    """Test function call functionality."""
    
    def test_function_call_creation(self):
        """Test function call creation."""
        call = FunctionCall(
            name="test_function",
            arguments={"param": "value"},
            call_id="call_123"
        )
        
        assert call.name == "test_function"
        assert call.arguments == {"param": "value"}
        assert call.call_id == "call_123"
    
    def test_from_openai_format(self):
        """Test creating function call from OpenAI format."""
        openai_call = {
            "name": "get_weather",
            "arguments": '{"location": "New York"}',
            "id": "call_456"
        }
        
        call = FunctionCall.from_openai_format(openai_call)
        
        assert call.name == "get_weather"
        assert call.arguments == {"location": "New York"}
        assert call.call_id == "call_456"
    
    def test_from_anthropic_format(self):
        """Test creating function call from Anthropic format."""
        anthropic_call = {
            "name": "search_web",
            "input": {"query": "AI tools", "max_results": 5},
            "id": "tool_789"
        }
        
        call = FunctionCall.from_anthropic_format(anthropic_call)
        
        assert call.name == "search_web"
        assert call.arguments == {"query": "AI tools", "max_results": 5}
        assert call.call_id == "tool_789"
    
    def test_to_dict(self):
        """Test function call to dictionary conversion."""
        call = FunctionCall(
            name="test_function",
            arguments={"param": "value"}
        )
        
        call_dict = call.to_dict()
        
        assert call_dict["name"] == "test_function"
        assert call_dict["arguments"] == {"param": "value"}
        assert "call_id" in call_dict
        assert "created_at" in call_dict


class TestToolExecutionContext:
    """Test tool execution context."""
    
    def test_context_creation(self):
        """Test execution context creation."""
        from uuid import uuid4
        
        user_id = uuid4()
        agent_id = uuid4()
        
        context = ToolExecutionContext(
            user_id=user_id,
            agent_id=agent_id,
            metadata={"test": "value"}
        )
        
        assert context.user_id == user_id
        assert context.agent_id == agent_id
        assert context.metadata["test"] == "value"
        assert context.execution_id is not None
        assert context.created_at is not None


class TestParameterValidation:
    """Test tool parameter validation."""
    
    def test_string_validation(self):
        """Test string parameter validation."""
        tool = MockTool()
        
        # Valid string
        params = tool.validate_parameters({"input_text": "hello", "count": 1})
        assert params["input_text"] == "hello"
        
        # Non-string value
        with pytest.raises(ValueError, match="must be a string"):
            tool.validate_parameters({"input_text": 123, "count": 1})
    
    def test_integer_validation(self):
        """Test integer parameter validation."""
        tool = MockTool()
        
        # Valid integer
        params = tool.validate_parameters({"input_text": "test", "count": 5})
        assert params["count"] == 5
        
        # String that can be converted to int
        params = tool.validate_parameters({"input_text": "test", "count": "3"})
        assert params["count"] == 3
        
        # Out of range
        with pytest.raises(ValueError, match="must be <="):
            tool.validate_parameters({"input_text": "test", "count": 15})
        
        with pytest.raises(ValueError, match="must be >="):
            tool.validate_parameters({"input_text": "test", "count": 0})
    
    def test_required_parameters(self):
        """Test required parameter validation."""
        tool = MockTool()
        
        # Missing required parameter
        with pytest.raises(ValueError, match="Required parameter"):
            tool.validate_parameters({"count": 1})  # missing input_text
        
        # All required parameters present
        params = tool.validate_parameters({"input_text": "test"})
        assert params["input_text"] == "test"
        assert params["count"] == 1  # default value
    
    def test_default_values(self):
        """Test default parameter values."""
        tool = MockTool()
        
        # Use default value
        params = tool.validate_parameters({"input_text": "test"})
        assert params["count"] == 1  # default value from parameter definition
        
        # Override default value
        params = tool.validate_parameters({"input_text": "test", "count": 3})
        assert params["count"] == 3 