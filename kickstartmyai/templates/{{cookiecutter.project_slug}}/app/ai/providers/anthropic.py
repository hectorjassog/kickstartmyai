"""Anthropic provider implementation."""

from typing import List, Optional, AsyncGenerator
import anthropic

from .base import BaseAIProvider, ChatMessage, ChatResponse


class AnthropicProvider(BaseAIProvider):
    """Anthropic provider implementation."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        super().__init__(api_key, model)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
    
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = 1000,
        **kwargs
    ) -> ChatResponse:
        """Generate chat completion."""
        try:
            # Convert messages format for Anthropic
            system_message = None
            anthropic_messages = []
            
            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    anthropic_messages.append({
                        "role": "user" if msg.role == "user" else "assistant",
                        "content": msg.content
                    })
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or 1000,
                temperature=temperature,
                system=system_message,
                messages=anthropic_messages,
                **kwargs
            )
            
            return ChatResponse(
                content=response.content[0].text,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                } if response.usage else None,
                model=response.model
            )
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    async def stream_chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = 1000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion."""
        try:
            system_message = None
            anthropic_messages = []
            
            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    anthropic_messages.append({
                        "role": "user" if msg.role == "user" else "assistant",
                        "content": msg.content
                    })
            
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens or 1000,
                temperature=temperature,
                system=system_message,
                messages=anthropic_messages,
                **kwargs
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            raise Exception(f"Anthropic streaming error: {str(e)}")
    
    async def get_embedding(
        self,
        text: str,
        **kwargs
    ) -> List[float]:
        """Get text embedding."""
        # Anthropic doesn't provide embeddings, raise not implemented
        raise NotImplementedError("Anthropic doesn't provide embedding functionality")
    
    @property
    def name(self) -> str:
        """Provider name."""
        return "anthropic"
    
    @property
    def available_models(self) -> List[str]:
        """Available models."""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]
