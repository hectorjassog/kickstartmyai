"""
Integration tests for complete AI pipeline workflows.

Tests the full AI processing pipeline including provider integration,
tool execution, conversation management, and response generation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from fastapi import status

# Conditional imports based on cookiecutter configuration
{% if cookiecutter.include_openai == "y" %}
from app.ai.providers.openai import OpenAIProvider
{% endif %}
{% if cookiecutter.include_anthropic == "y" %}
from app.ai.providers.anthropic import AnthropicProvider
{% endif %}
{% if cookiecutter.include_gemini == "y" %}
from app.ai.providers.gemini import GeminiProvider
{% endif %}
from app.ai.tools.manager import ToolManager
from app.ai.tools.web_search import WebSearchTool
from app.ai.tools.calculator import CalculatorTool
from app.ai.tools.file_system import FileSystemTool
from app.core.config import settings


class TestCompleteAIPipeline:
    """Test complete AI processing pipeline."""

    async def test_full_ai_conversation_pipeline(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers,
        mock_openai_client,
        db_session
    ):
        """Test complete AI conversation pipeline from user input to AI response."""
        
        # Step 1: Create agent with tools
        agent_data = {
            "name": "Full Pipeline Agent",
            "description": "Agent for testing complete pipeline",
            "ai_provider": "openai",
            "model": "gpt-4",
            "system_prompt": "You are a helpful assistant with access to tools.",
            "tools": ["web_search", "calculator", "file_system"],
            "temperature": 0.7,
            "max_tokens": 1500
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=agent_data, 
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        agent = response.json()
        agent_id = agent["id"]
        
        # Step 2: Create conversation
        conversation_data = {
            "title": "Full Pipeline Test",
            "agent_id": agent_id
        }
        
        response = await async_client.post(
            "/api/v1/conversations", 
            json=conversation_data, 
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        conversation_id = response.json()["id"]
        
        # Step 3: Mock AI response with tool calls
        mock_response = MagicMock()
        mock_response.choices[0].message.content = None
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                id="call_1",
                function=MagicMock(
                    name="calculator",
                    arguments='{"expression": "15 * 23"}'
                )
            )
        ]
        mock_response.usage.total_tokens = 150
        
        # Second call for final response
        mock_final_response = MagicMock()
        mock_final_response.choices[0].message.content = "The calculation result is 345."
        mock_final_response.usage.total_tokens = 75
        
        mock_openai_client.chat.completions.create.side_effect = [
            mock_response,
            mock_final_response
        ]
        
        # Step 4: Send message that should trigger tool usage
        message_data = {
            "content": "What is 15 multiplied by 23?",
            "conversation_id": conversation_id
        }
        
        with patch('app.ai.tools.calculator.CalculatorTool.execute') as mock_calc:
            mock_calc.return_value = {"result": 345, "expression": "15 * 23"}
            
            response = await async_client.post(
                "/api/v1/messages", 
                json=message_data, 
                headers=authenticated_user_headers
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            user_message = response.json()
            assert user_message["content"] == message_data["content"]
            assert user_message["role"] == "user"
            
            # Verify tool was called
            mock_calc.assert_called_once_with({"expression": "15 * 23"})
        
        # Step 5: Verify AI response was created
        response = await async_client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_200_OK
        messages = response.json()["items"]
        
        # Should have user message and AI response
        assert len(messages) >= 2
        
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        ai_messages = [msg for msg in messages if msg["role"] == "assistant"]
        
        assert len(user_messages) >= 1
        assert len(ai_messages) >= 1
        
        # Verify AI response contains calculation result
        ai_response = ai_messages[-1]
        assert "345" in ai_response["content"]
        
        # Step 6: Verify OpenAI was called with correct parameters
        assert mock_openai_client.chat.completions.create.call_count >= 1
        first_call = mock_openai_client.chat.completions.create.call_args_list[0]
        assert first_call[1]["model"] == "gpt-4"
        assert first_call[1]["temperature"] == 0.7
        assert first_call[1]["max_tokens"] == 1500
        
        # Verify tools were included in the call
        tools = first_call[1].get("tools", [])
        tool_names = [tool["function"]["name"] for tool in tools]
        assert "calculator" in tool_names

    async def test_multi_tool_conversation(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers,
        mock_openai_client,
        db_session
    ):
        """Test conversation using multiple tools in sequence."""
        
        # Create agent with multiple tools
        agent_data = {
            "name": "Multi-Tool Agent",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo",
            "tools": ["web_search", "calculator", "file_system"]
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=agent_data, 
            headers=authenticated_user_headers
        )
        agent_id = response.json()["id"]
        
        # Create conversation
        conversation_data = {
            "title": "Multi-Tool Test",
            "agent_id": agent_id
        }
        
        response = await async_client.post(
            "/api/v1/conversations", 
            json=conversation_data, 
            headers=authenticated_user_headers
        )
        conversation_id = response.json()["id"]
        
        # Test sequence: web search -> calculator -> file system
        test_cases = [
            {
                "message": "Search for information about Python programming",
                "tool": "web_search",
                "tool_args": {"query": "Python programming"},
                "tool_result": {"results": [{"title": "Python.org", "snippet": "Official Python website"}]},
                "ai_response": "I found information about Python programming from the official website."
            },
            {
                "message": "Calculate 100 * 0.15",
                "tool": "calculator", 
                "tool_args": {"expression": "100 * 0.15"},
                "tool_result": {"result": 15.0, "expression": "100 * 0.15"},
                "ai_response": "The calculation result is 15.0"
            },
            {
                "message": "List files in the current directory",
                "tool": "file_system",
                "tool_args": {"action": "list", "path": "."},
                "tool_result": {"files": ["main.py", "requirements.txt", "README.md"]},
                "ai_response": "Here are the files in the current directory: main.py, requirements.txt, README.md"
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            # Mock AI response with tool call
            mock_response = MagicMock()
            mock_response.choices[0].message.content = None
            mock_response.choices[0].message.tool_calls = [
                MagicMock(
                    id=f"call_{i}",
                    function=MagicMock(
                        name=test_case["tool"],
                        arguments=str(test_case["tool_args"]).replace("'", '"')
                    )
                )
            ]
            
            # Mock final response
            mock_final_response = MagicMock()
            mock_final_response.choices[0].message.content = test_case["ai_response"]
            
            mock_openai_client.chat.completions.create.side_effect = [
                mock_response,
                mock_final_response
            ]
            
            # Mock tool execution
            tool_class_name = f'{test_case["tool"].title().replace("_", "")}Tool'
            tool_module = f'app.ai.tools.{test_case["tool"]}'
            
            with patch(f'{tool_module}.{tool_class_name}.execute') as mock_tool:
                mock_tool.return_value = test_case["tool_result"]
                
                # Send message
                message_data = {
                    "content": test_case["message"],
                    "conversation_id": conversation_id
                }
                
                response = await async_client.post(
                    "/api/v1/messages", 
                    json=message_data, 
                    headers=authenticated_user_headers
                )
                
                assert response.status_code == status.HTTP_201_CREATED
                
                # Verify tool was called
                mock_tool.assert_called_once()
        
        # Verify conversation history
        response = await async_client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_200_OK
        messages = response.json()["items"]
        
        # Should have 3 user messages and 3 AI responses
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        ai_messages = [msg for msg in messages if msg["role"] == "assistant"]
        
        assert len(user_messages) == 3
        assert len(ai_messages) == 3

    async def test_ai_provider_switching(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers,
        mock_openai_client,
        mock_anthropic_client,
        db_session
    ):
        """Test conversation with different AI providers."""
        
        # Create agents with different providers
        providers_data = [
            {
                "name": "OpenAI Agent",
                "ai_provider": "openai",
                "model": "gpt-3.5-turbo"
            },
            {
                "name": "Anthropic Agent", 
                "ai_provider": "anthropic",
                "model": "claude-sonnet-4-20250514"
            }
        ]
        
        agent_ids = []
        for provider_data in providers_data:
            response = await async_client.post(
                "/api/v1/agents", 
                json=provider_data, 
                headers=authenticated_user_headers
            )
            assert response.status_code == status.HTTP_201_CREATED
            agent_ids.append(response.json()["id"])
        
        # Test conversations with each provider
        test_messages = [
            "Hello from OpenAI!",
            "Hello from Anthropic!"
        ]
        
        # Mock responses
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "OpenAI response"
        mock_anthropic_client.messages.create.return_value.content[0].text = "Anthropic response"
        
        for i, agent_id in enumerate(agent_ids):
            # Create conversation
            conversation_data = {
                "title": f"Provider Test {i+1}",
                "agent_id": agent_id
            }
            
            response = await async_client.post(
                "/api/v1/conversations", 
                json=conversation_data, 
                headers=authenticated_user_headers
            )
            conversation_id = response.json()["id"]
            
            # Send message
            message_data = {
                "content": test_messages[i],
                "conversation_id": conversation_id
            }
            
            response = await async_client.post(
                "/api/v1/messages", 
                json=message_data, 
                headers=authenticated_user_headers
            )
            
            assert response.status_code == status.HTTP_201_CREATED
        
        # Verify both providers were called
        mock_openai_client.chat.completions.create.assert_called()
        mock_anthropic_client.messages.create.assert_called()

    async def test_error_recovery_in_pipeline(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers,
        mock_openai_client,
        db_session
    ):
        """Test error recovery in AI pipeline."""
        
        # Create agent
        agent_data = {
            "name": "Error Recovery Agent",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo",
            "tools": ["calculator"]
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=agent_data, 
            headers=authenticated_user_headers
        )
        agent_id = response.json()["id"]
        
        # Create conversation
        conversation_data = {
            "title": "Error Recovery Test",
            "agent_id": agent_id
        }
        
        response = await async_client.post(
            "/api/v1/conversations", 
            json=conversation_data, 
            headers=authenticated_user_headers
        )
        conversation_id = response.json()["id"]
        
        # Test 1: Tool execution error
        mock_response = MagicMock()
        mock_response.choices[0].message.content = None
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                id="call_1",
                function=MagicMock(
                    name="calculator",
                    arguments='{"expression": "1/0"}'  # Division by zero
                )
            )
        ]
        
        # Recovery response
        mock_recovery_response = MagicMock()
        mock_recovery_response.choices[0].message.content = "I encountered an error with the calculation. Division by zero is not allowed."
        
        mock_openai_client.chat.completions.create.side_effect = [
            mock_response,
            mock_recovery_response
        ]
        
        with patch('app.ai.tools.calculator.CalculatorTool.execute') as mock_calc:
            mock_calc.side_effect = ValueError("Division by zero")
            
            message_data = {
                "content": "Calculate 1 divided by 0",
                "conversation_id": conversation_id
            }
            
            response = await async_client.post(
                "/api/v1/messages", 
                json=message_data, 
                headers=authenticated_user_headers
            )
            
            # Should still create the message even with tool error
            assert response.status_code == status.HTTP_201_CREATED
        
        # Verify conversation continues after error
        response = await async_client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_200_OK
        messages = response.json()["items"]
        
        # Should have user message and error recovery response
        assert len(messages) >= 2
        
        ai_messages = [msg for msg in messages if msg["role"] == "assistant"]
        assert len(ai_messages) >= 1
        
        # AI should acknowledge the error
        latest_ai_message = ai_messages[-1]
        assert "error" in latest_ai_message["content"].lower()

    async def test_concurrent_ai_requests(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers,
        mock_openai_client,
        db_session
    ):
        """Test handling concurrent AI requests."""
        
        # Create agent
        agent_data = {
            "name": "Concurrent Agent",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo"
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=agent_data, 
            headers=authenticated_user_headers
        )
        agent_id = response.json()["id"]
        
        # Create multiple conversations
        conversation_ids = []
        for i in range(3):
            conversation_data = {
                "title": f"Concurrent Conversation {i+1}",
                "agent_id": agent_id
            }
            
            response = await async_client.post(
                "/api/v1/conversations", 
                json=conversation_data, 
                headers=authenticated_user_headers
            )
            conversation_ids.append(response.json()["id"])
        
        # Mock AI responses
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "Concurrent response"
        
        # Send concurrent messages
        async def send_concurrent_message(conv_id, content):
            message_data = {
                "content": content,
                "conversation_id": conv_id
            }
            return await async_client.post(
                "/api/v1/messages", 
                json=message_data, 
                headers=authenticated_user_headers
            )
        
        # Create concurrent tasks
        tasks = []
        for i, conv_id in enumerate(conversation_ids):
            task = send_concurrent_message(conv_id, f"Concurrent message {i+1}")
            tasks.append(task)
        
        # Execute concurrently
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_201_CREATED
        
        # Verify all AI calls were made
        assert mock_openai_client.chat.completions.create.call_count >= len(conversation_ids)


class TestAIProviderSpecificWorkflows:
    """Test provider-specific AI workflow features."""

{% if cookiecutter.include_openai == "y" %}
    async def test_openai_function_calling_workflow(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers,
        mock_openai_client,
        db_session
    ):
        """Test OpenAI function calling workflow."""
        
        # Create OpenAI agent with function calling
        agent_data = {
            "name": "OpenAI Function Agent",
            "ai_provider": "openai",
            "model": "gpt-4",
            "tools": ["calculator", "web_search"],
            "function_calling": "auto"
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=agent_data, 
            headers=authenticated_user_headers
        )
        agent_id = response.json()["id"]
        
        # Create conversation
        conversation_data = {
            "title": "Function Calling Test",
            "agent_id": agent_id
        }
        
        response = await async_client.post(
            "/api/v1/conversations", 
            json=conversation_data, 
            headers=authenticated_user_headers
        )
        conversation_id = response.json()["id"]
        
        # Mock function calling response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = None
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                id="call_calculator",
                function=MagicMock(
                    name="calculator",
                    arguments='{"expression": "25 + 30"}'
                )
            ),
            MagicMock(
                id="call_search",
                function=MagicMock(
                    name="web_search",
                    arguments='{"query": "mathematical operations"}'
                )
            )
        ]
        
        # Final response after tools
        mock_final_response = MagicMock()
        mock_final_response.choices[0].message.content = "I calculated 25 + 30 = 55 and found relevant information about mathematical operations."
        
        mock_openai_client.chat.completions.create.side_effect = [
            mock_response,
            mock_final_response
        ]
        
        # Mock tool executions
        with patch('app.ai.tools.calculator.CalculatorTool.execute') as mock_calc, \
             patch('app.ai.tools.web_search.WebSearchTool.execute') as mock_search:
            
            mock_calc.return_value = {"result": 55, "expression": "25 + 30"}
            mock_search.return_value = {"results": [{"title": "Math Operations", "snippet": "Basic math info"}]}
            
            message_data = {
                "content": "Calculate 25 + 30 and search for information about mathematical operations",
                "conversation_id": conversation_id
            }
            
            response = await async_client.post(
                "/api/v1/messages", 
                json=message_data, 
                headers=authenticated_user_headers
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            
            # Verify both tools were called
            mock_calc.assert_called_once_with({"expression": "25 + 30"})
            mock_search.assert_called_once_with({"query": "mathematical operations"})
        
        # Verify OpenAI was called with tools parameter
        first_call = mock_openai_client.chat.completions.create.call_args_list[0]
        assert "tools" in first_call[1]
        tools = first_call[1]["tools"]
        tool_names = [tool["function"]["name"] for tool in tools]
        assert "calculator" in tool_names
        assert "web_search" in tool_names
{% endif %}

{% if cookiecutter.include_anthropic == "y" %}
    async def test_anthropic_tool_use_workflow(
        self, 
        async_client: AsyncClient,
        authenticated_user_headers,
        mock_anthropic_client,
        db_session
    ):
        """Test Anthropic tool use workflow."""
        
        # Create Anthropic agent with tools
        agent_data = {
            "name": "Claude Tool Agent",
            "ai_provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "tools": ["calculator"]
        }
        
        response = await async_client.post(
            "/api/v1/agents", 
            json=agent_data, 
            headers=authenticated_user_headers
        )
        agent_id = response.json()["id"]
        
        # Create conversation
        conversation_data = {
            "title": "Anthropic Tool Test",
            "agent_id": agent_id
        }
        
        response = await async_client.post(
            "/api/v1/conversations", 
            json=conversation_data, 
            headers=authenticated_user_headers
        )
        conversation_id = response.json()["id"]
        
        # Mock Anthropic tool use response
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                type="tool_use",
                id="toolu_calculator",
                name="calculator",
                input={"expression": "50 * 2"}
            )
        ]
        mock_response.stop_reason = "tool_use"
        
        # Final response after tool
        mock_final_response = MagicMock()
        mock_final_response.content = [
            MagicMock(
                type="text",
                text="The calculation 50 * 2 equals 100."
            )
        ]
        mock_final_response.stop_reason = "end_turn"
        
        mock_anthropic_client.messages.create.side_effect = [
            mock_response,
            mock_final_response
        ]
        
        with patch('app.ai.tools.calculator.CalculatorTool.execute') as mock_calc:
            mock_calc.return_value = {"result": 100, "expression": "50 * 2"}
            
            message_data = {
                "content": "What is 50 multiplied by 2?",
                "conversation_id": conversation_id
            }
            
            response = await async_client.post(
                "/api/v1/messages", 
                json=message_data, 
                headers=authenticated_user_headers
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            
            # Verify tool was called
            mock_calc.assert_called_once_with({"expression": "50 * 2"})
        
        # Verify Anthropic was called with tools parameter
        first_call = mock_anthropic_client.messages.create.call_args_list[0]
        assert "tools" in first_call[1]
{% endif %}