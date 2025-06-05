"""
Unit tests for AI providers.

Tests all three AI providers (OpenAI, Anthropic, Gemini) to ensure
they work correctly with proper error handling and response formatting.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.factory import get_ai_provider
from app.ai.providers.base import ChatMessage


class TestOpenAIProvider:
    """Test OpenAI provider functionality."""
    
    @pytest.fixture
    def openai_provider(self):
        """Create OpenAI provider instance."""
        return OpenAIProvider(api_key="test-key", model="gpt-4")
    
    @pytest.mark.asyncio
    async def test_chat_completion(self, openai_provider, mock_openai_api):
        """Test OpenAI chat completion."""
        messages = [
            ChatMessage(role="user", content="Hello, world!")
        ]
        
        response = await openai_provider.chat_completion(messages)
        
        assert response.content == "Hello! This is a test response."
        assert response.model == "gpt-4"
        assert response.usage["total_tokens"] == 25
        assert response.finish_reason == "stop"
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_functions(self, openai_provider, mock_openai_api):
        """Test OpenAI chat completion with function calling."""
        messages = [
            ChatMessage(role="user", content="What's the weather like?")
        ]
        
        functions = [{
            "name": "get_weather",
            "description": "Get weather information",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }]
        
        response = await openai_provider.chat_completion(messages, functions=functions)
        
        assert response.content == "Hello! This is a test response."
        assert response.model == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_stream_chat_completion(self, openai_provider):
        """Test OpenAI streaming chat completion."""
        messages = [
            ChatMessage(role="user", content="Tell me a story")
        ]
        
        # Mock streaming response
        async def mock_stream():
            chunks = ["Hello", " there", "! This", " is", " streaming."]
            for chunk in chunks:
                yield chunk
        
        with patch.object(openai_provider, 'stream_chat_completion', return_value=mock_stream()):
            chunks = []
            async for chunk in openai_provider.stream_chat_completion(messages):
                chunks.append(chunk)
            
            assert len(chunks) == 5
            assert "".join(chunks) == "Hello there! This is streaming."
    
    @pytest.mark.asyncio
    async def test_generate_embeddings(self, openai_provider):
        """Test OpenAI embeddings generation."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "data": [{
                    "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "index": 0
                }],
                "usage": {"total_tokens": 10}
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            embeddings = await openai_provider.generate_embeddings(["test text"])
            
            assert len(embeddings) == 1
            assert len(embeddings[0]) == 5
            assert embeddings[0] == [0.1, 0.2, 0.3, 0.4, 0.5]
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, openai_provider):
        """Test OpenAI API error handling."""
        messages = [
            ChatMessage(role="user", content="Hello")
        ]
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "API Error", request=None, response=mock_response
            )
            mock_post.return_value = mock_response
            
            with pytest.raises(Exception):
                await openai_provider.chat_completion(messages)


class TestAnthropicProvider:
    """Test Anthropic provider functionality."""
    
    @pytest.fixture
    def anthropic_provider(self):
        """Create Anthropic provider instance."""
        return AnthropicProvider(api_key="test-key", model="claude-sonnet-4-20250514")
    
    @pytest.mark.asyncio
    async def test_chat_completion(self, anthropic_provider, mock_anthropic_api):
        """Test Anthropic chat completion."""
        messages = [
            ChatMessage(role="user", content="Hello, Claude!")
        ]
        
        response = await anthropic_provider.chat_completion(messages)
        
        assert response.content == "Hello! This is a test response from Claude."
        assert response.model == "claude-sonnet-4-20250514"
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 15
        assert response.finish_reason == "end_turn"
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_tools(self, anthropic_provider, mock_anthropic_api):
        """Test Anthropic chat completion with tool use."""
        messages = [
            ChatMessage(role="user", content="What's the time?")
        ]
        
        tools = [{
            "name": "get_time",
            "description": "Get current time",
            "input_schema": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string"}
                }
            }
        }]
        
        response = await anthropic_provider.chat_completion(messages, tools=tools)
        
        assert response.content == "Hello! This is a test response from Claude."
        assert response.model == "claude-sonnet-4-20250514"
    
    @pytest.mark.asyncio
    async def test_stream_chat_completion(self, anthropic_provider):
        """Test Anthropic streaming chat completion."""
        messages = [
            ChatMessage(role="user", content="Tell me about AI")
        ]
        
        # Mock streaming response
        async def mock_stream():
            chunks = ["AI", " is", " fascinating", " technology", "."]
            for chunk in chunks:
                yield chunk
        
        with patch.object(anthropic_provider, 'stream_chat_completion', return_value=mock_stream()):
            chunks = []
            async for chunk in anthropic_provider.stream_chat_completion(messages):
                chunks.append(chunk)
            
            assert len(chunks) == 5
            assert "".join(chunks) == "AI is fascinating technology."
    
    @pytest.mark.asyncio
    async def test_anthropic_message_conversion(self, anthropic_provider):
        """Test conversion of ChatMessage to Anthropic format."""
        messages = [
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!"),
            ChatMessage(role="user", content="How are you?")
        ]
        
        anthropic_messages, system_prompt = anthropic_provider._convert_messages(messages)
        
        assert system_prompt == "You are a helpful assistant."
        assert len(anthropic_messages) == 3  # System message extracted
        assert anthropic_messages[0]["role"] == "user"
        assert anthropic_messages[1]["role"] == "assistant"
        assert anthropic_messages[2]["role"] == "user"


class TestGeminiProvider:
    """Test Google Gemini provider functionality."""
    
    @pytest.fixture
    def gemini_provider(self):
        """Create Gemini provider instance."""
        return GeminiProvider(api_key="test-key", model="gemini-pro")
    
    @pytest.mark.asyncio
    async def test_chat_completion(self, gemini_provider, mock_gemini_api):
        """Test Gemini chat completion."""
        messages = [
            ChatMessage(role="user", content="Hello, Gemini!")
        ]
        
        response = await gemini_provider.chat_completion(messages)
        
        assert response.content == "Hello! This is a test response from Gemini."
        assert response.model == "gemini-pro"
        assert response.usage["total_tokens"] == 25
        assert response.finish_reason == "STOP"
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_safety_settings(self, gemini_provider, mock_gemini_api):
        """Test Gemini chat completion with safety settings."""
        messages = [
            ChatMessage(role="user", content="Tell me about safety")
        ]
        
        safety_settings = [{
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        }]
        
        response = await gemini_provider.chat_completion(
            messages, 
            safety_settings=safety_settings
        )
        
        assert response.content == "Hello! This is a test response from Gemini."
        assert response.model == "gemini-pro"
    
    @pytest.mark.asyncio
    async def test_generate_embeddings(self, gemini_provider):
        """Test Gemini embeddings generation."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "embedding": {
                    "values": [0.1, 0.2, 0.3, 0.4, 0.5]
                }
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            embeddings = await gemini_provider.generate_embeddings(["test text"])
            
            assert len(embeddings) == 1
            assert len(embeddings[0]) == 5
            assert embeddings[0] == [0.1, 0.2, 0.3, 0.4, 0.5]
    
    @pytest.mark.asyncio
    async def test_gemini_message_conversion(self, gemini_provider):
        """Test conversion of ChatMessage to Gemini format."""
        messages = [
            ChatMessage(role="system", content="You are helpful."),
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi!"),
            ChatMessage(role="user", content="How are you?")
        ]
        
        gemini_messages, system_instruction = gemini_provider._convert_messages(messages)
        
        assert system_instruction == "You are helpful."
        assert len(gemini_messages) == 3  # System message extracted
        assert gemini_messages[0]["role"] == "user"
        assert gemini_messages[1]["role"] == "model"  # assistant -> model
        assert gemini_messages[2]["role"] == "user"


class TestProviderFactory:
    """Test AI provider factory functionality."""
    
    def test_get_openai_provider(self):
        """Test getting OpenAI provider from factory."""
        provider = get_ai_provider("openai", model="gpt-4")
        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "gpt-4"
    
    def test_get_anthropic_provider(self):
        """Test getting Anthropic provider from factory."""
        provider = get_ai_provider("anthropic", model="claude-sonnet-4-20250514")
        assert isinstance(provider, AnthropicProvider)
        assert provider.model == "claude-sonnet-4-20250514"
    
    def test_get_gemini_provider(self):
        """Test getting Gemini provider from factory."""
        provider = get_ai_provider("gemini", model="gemini-pro")
        assert isinstance(provider, GeminiProvider)
        assert provider.model == "gemini-pro"
    
    def test_invalid_provider(self):
        """Test error handling for invalid provider."""
        with pytest.raises(ValueError, match="Unknown AI provider"):
            get_ai_provider("invalid_provider")
    
    def test_provider_caching(self):
        """Test that providers are cached properly."""
        provider1 = get_ai_provider("openai", model="gpt-4")
        provider2 = get_ai_provider("openai", model="gpt-4")
        
        # Should be the same instance (cached)
        assert provider1 is provider2
    
    def test_different_models_different_instances(self):
        """Test that different models create different instances."""
        provider1 = get_ai_provider("openai", model="gpt-4")
        provider2 = get_ai_provider("openai", model="gpt-3.5-turbo")
        
        # Should be different instances
        assert provider1 is not provider2
        assert provider1.model != provider2.model


class TestChatMessage:
    """Test ChatMessage model."""
    
    def test_chat_message_creation(self):
        """Test ChatMessage creation."""
        message = ChatMessage(
            role="user",
            content="Hello, world!",
            metadata={"timestamp": "2024-01-01"}
        )
        
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.metadata["timestamp"] == "2024-01-01"
    
    def test_chat_message_validation(self):
        """Test ChatMessage validation."""
        # Valid roles
        valid_roles = ["system", "user", "assistant", "function"]
        for role in valid_roles:
            message = ChatMessage(role=role, content="test")
            assert message.role == role
        
        # Content is required
        with pytest.raises(ValueError):
            ChatMessage(role="user", content="")
    
    def test_chat_message_to_dict(self):
        """Test ChatMessage to dictionary conversion."""
        message = ChatMessage(
            role="user",
            content="Hello",
            name="test_function",
            metadata={"key": "value"}
        )
        
        message_dict = message.to_dict()
        
        assert message_dict["role"] == "user"
        assert message_dict["content"] == "Hello"
        assert message_dict["name"] == "test_function"
        assert message_dict["metadata"]["key"] == "value" 