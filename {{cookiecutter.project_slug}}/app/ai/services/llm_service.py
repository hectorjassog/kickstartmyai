"""LLM service for general language model operations."""

from typing import List, Optional, Dict, Any
from app.ai.providers.factory import get_ai_provider
from app.ai.providers.base import ChatMessage


class LLMService:
    """Service for general LLM operations."""
    
    def __init__(self, provider_name: str = "openai", model: Optional[str] = None):
        self.provider = get_ai_provider(provider_name, model=model)
    
    async def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """Complete a text prompt."""
        messages = []
        
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        
        messages.append(ChatMessage(role="user", content=prompt))
        
        response = await self.provider.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.content
    
    async def analyze_text(
        self,
        text: str,
        analysis_type: str = "sentiment",
        **kwargs
    ) -> Dict[str, Any]:
        """Analyze text using AI."""
        analysis_prompts = {
            "sentiment": f"Analyze the sentiment of the following text and return a JSON object with 'sentiment' (positive/negative/neutral) and 'confidence' (0-1): {text}",
            "summary": f"Provide a concise summary of the following text: {text}",
            "keywords": f"Extract the main keywords from the following text and return them as a JSON array: {text}",
            "classification": f"Classify the following text into categories and return a JSON object with the most likely category: {text}"
        }
        
        prompt = analysis_prompts.get(analysis_type)
        if not prompt:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
        
        response = await self.complete(
            prompt=prompt,
            temperature=0.1,  # Lower temperature for analysis
            **kwargs
        )
        
        return {"result": response, "analysis_type": analysis_type}
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get text embedding."""
        return await self.provider.get_embedding(text)
    
    async def batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings
