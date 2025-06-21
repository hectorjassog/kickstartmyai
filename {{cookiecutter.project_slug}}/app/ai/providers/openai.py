"""OpenAI provider implementation."""

from typing import Dict, List, Optional, AsyncGenerator
try:
    import openai
except ImportError:
    openai = None

from app.core.logging_utils import get_logger
from .base import BaseAIProvider, ChatMessage, ChatResponse

logger = get_logger(__name__)

class OpenAIProvider(BaseAIProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        if openai is None:
            raise ImportError(
                "OpenAI package is not installed. "
                "Install it with: pip install 'openai>=1.85.0' "
                "or install the full package with: pip install '.[openai]'"
            )
        
        super().__init__(api_key, model)
        self.client = openai.AsyncOpenAI(api_key=api_key)
        
        # Default models for different use cases
        self.default_models = {
            "fast": "gpt-3.5-turbo",
            "balanced": "gpt-4",
            "advanced": "gpt-4-turbo"
        }
    
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate chat completion."""
        try:
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return ChatResponse(
                content=response.choices[0].message.content,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                model=response.model
            )
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def stream_chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion."""
        try:
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise Exception(f"OpenAI streaming error: {str(e)}")
    
    async def get_embedding(
        self,
        text: str,
        model: str = "text-embedding-ada-002",
        **kwargs
    ) -> List[float]:
        """Get text embedding."""
        try:
            response = await self.client.embeddings.create(
                model=model,
                input=text,
                **kwargs
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"OpenAI embedding error: {str(e)}")
    
    @property
    def name(self) -> str:
        """Provider name."""
        return "openai"
    
    @property
    def available_models(self) -> List[str]:
        """Available models."""
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]
