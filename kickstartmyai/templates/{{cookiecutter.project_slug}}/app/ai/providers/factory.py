"""AI provider factory."""

from typing import Dict, Type, Optional
from app.core.config import settings
from .base import BaseAIProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .gemini import GeminiProvider


class AIProviderFactory:
    """Factory for creating AI providers."""
    
    _providers: Dict[str, Type[BaseAIProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
    }
    
    @classmethod
    def create_provider(
        self,
        provider_name: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> BaseAIProvider:
        """Create AI provider instance."""
        if provider_name not in self._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        provider_class = self._providers[provider_name]
        
        # Get API key from settings if not provided
        if not api_key:
            if provider_name == "openai":
                api_key = settings.OPENAI_API_KEY
            elif provider_name == "anthropic":
                api_key = settings.ANTHROPIC_API_KEY
            elif provider_name == "gemini":
                api_key = settings.GEMINI_API_KEY
            
            if not api_key:
                raise ValueError(f"No API key provided for {provider_name}")
        
        return provider_class(api_key=api_key, model=model)
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, Type[BaseAIProvider]]:
        """Get available providers."""
        return cls._providers.copy()
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseAIProvider]):
        """Register a new provider."""
        cls._providers[name] = provider_class


# Convenience function
def get_ai_provider(
    provider_name: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> BaseAIProvider:
    """Get AI provider instance."""
    return AIProviderFactory.create_provider(provider_name, api_key, model)
