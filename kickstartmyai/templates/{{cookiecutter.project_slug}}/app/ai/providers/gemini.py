"""Google Gemini provider implementation."""

import asyncio
from typing import Dict, List, Optional, AsyncGenerator, Any
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from app.core.logging_utils import get_logger
from .base import BaseAIProvider, ChatMessage, ChatResponse

# Conditional import for HarmCategory and HarmBlockThreshold
try:
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    HarmCategory = None
    HarmBlockThreshold = None

logger = get_logger(__name__)

class GeminiProvider(BaseAIProvider):
    """Google Gemini provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        if genai is None:
            raise ImportError(
                "Google Generative AI package is not installed. "
                "Install it with: pip install 'google-generativeai>=0.7.2' "
                "or install the full package with: pip install '.[gemini]'"
            )
        
        super().__init__(api_key, model)
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)
        
        # Safety settings - more permissive for AI assistant use cases
        self.safety_settings = {}
        if HarmCategory and HarmBlockThreshold:
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        
        # Default models for different use cases
        self.default_models = {
            "fast": "gemini-1.5-flash",
            "balanced": "gemini-1.5-pro",
            "advanced": "gemini-1.5-pro"
        }
    
    def _convert_messages_to_gemini_format(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Convert messages to Gemini format."""
        gemini_messages = []
        
        for msg in messages:
            # Map roles to Gemini format
            if msg.role == "system":
                # Gemini doesn't have system role, prepend to first user message
                gemini_messages.append({
                    "role": "user",
                    "parts": [f"System: {msg.content}"]
                })
            elif msg.role == "user":
                gemini_messages.append({
                    "role": "user", 
                    "parts": [msg.content]
                })
            elif msg.role == "assistant":
                gemini_messages.append({
                    "role": "model",
                    "parts": [msg.content]
                })
        
        return gemini_messages
    
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate chat completion."""
        try:
            # Configure generation settings
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            
            # Convert messages to Gemini format
            gemini_messages = self._convert_messages_to_gemini_format(messages)
            
            # If we have a conversation history, use chat
            if len(gemini_messages) > 1:
                chat = self.client.start_chat(history=gemini_messages[:-1])
                response = await asyncio.to_thread(
                    chat.send_message,
                    gemini_messages[-1]["parts"][0],
                    generation_config=generation_config,
                    safety_settings=self.safety_settings
                )
            else:
                # Single message, use generate_content
                response = await asyncio.to_thread(
                    self.client.generate_content,
                    gemini_messages[0]["parts"][0],
                    generation_config=generation_config,
                    safety_settings=self.safety_settings
                )
            
            # Extract usage information if available
            usage = None
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count
                }
            
            return ChatResponse(
                content=response.text,
                usage=usage,
                model=self.model
            )
            
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    async def stream_chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion."""
        try:
            # Configure generation settings
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            
            # Convert messages to Gemini format
            gemini_messages = self._convert_messages_to_gemini_format(messages)
            
            # If we have a conversation history, use chat
            if len(gemini_messages) > 1:
                chat = self.client.start_chat(history=gemini_messages[:-1])
                response_stream = await asyncio.to_thread(
                    chat.send_message,
                    gemini_messages[-1]["parts"][0],
                    generation_config=generation_config,
                    safety_settings=self.safety_settings,
                    stream=True
                )
            else:
                # Single message, use generate_content with streaming
                response_stream = await asyncio.to_thread(
                    self.client.generate_content,
                    gemini_messages[0]["parts"][0],
                    generation_config=generation_config,
                    safety_settings=self.safety_settings,
                    stream=True
                )
            
            # Stream the response
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            raise Exception(f"Gemini streaming error: {str(e)}")
    
    async def get_embedding(
        self,
        text: str,
        model: str = "models/text-embedding-004",
        **kwargs
    ) -> List[float]:
        """Get text embedding."""
        try:
            # Use the embedding model
            embedding_model = genai.GenerativeModel(model)
            response = await asyncio.to_thread(
                genai.embed_content,
                model=model,
                content=text,
                **kwargs
            )
            return response['embedding']
        except Exception as e:
            raise Exception(f"Gemini embedding error: {str(e)}")
    
    @property
    def name(self) -> str:
        """Provider name."""
        return "gemini"
    
    @property
    def available_models(self) -> List[str]:
        """Available models."""
        return [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
            "gemini-pro-vision"
        ]
    
    async def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        try:
            response = await asyncio.to_thread(
                self.client.count_tokens,
                text
            )
            return response.total_tokens
        except Exception as e:
            raise Exception(f"Gemini token counting error: {str(e)}")
    
    async def generate_content_with_images(
        self,
        text: str,
        images: List[Any],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate content with images (multimodal)."""
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            
            # Prepare content with text and images
            content = [text] + images
            
            response = await asyncio.to_thread(
                self.client.generate_content,
                content,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )
            
            # Extract usage information if available
            usage = None
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count
                }
            
            return ChatResponse(
                content=response.text,
                usage=usage,
                model=self.model
            )
            
        except Exception as e:
            raise Exception(f"Gemini multimodal error: {str(e)}") 