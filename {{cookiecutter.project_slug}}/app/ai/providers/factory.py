"""AI provider factory."""

from typing import Dict, Type, Optional
from app.core.config import settings
from .base import BaseAIProvider

# Conditional imports based on cookiecutter configuration
{% if cookiecutter.include_openai == "y" %}
from .openai import OpenAIProvider
{% endif %}
{% if cookiecutter.include_anthropic == "y" %}
from .anthropic import AnthropicProvider
{% endif %}
{% if cookiecutter.include_gemini == "y" %}
from .gemini import GeminiProvider
{% endif %}


class AIProviderFactory:
    """Factory for creating AI providers."""
    
    # Build providers dict conditionally
    _providers: Dict[str, Type[BaseAIProvider]] = {}
    
{% if cookiecutter.include_openai == "y" %}
    _providers["openai"] = OpenAIProvider
{% endif %}
{% if cookiecutter.include_anthropic == "y" %}
    _providers["anthropic"] = AnthropicProvider
{% endif %}
{% if cookiecutter.include_gemini == "y" %}
    _providers["gemini"] = GeminiProvider
{% endif %}
    
    @classmethod
    def create_provider(
        cls,
        provider_name: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> BaseAIProvider:
        """Create AI provider instance."""
        if provider_name not in cls._providers:
            available = list(cls._providers.keys())
            raise ValueError(f"Unknown provider: {provider_name}. Available providers: {available}")
        
        provider_class = cls._providers[provider_name]
        
        # Get API key from settings if not provided
        if not api_key:
{% if cookiecutter.include_openai == "y" %}
            if provider_name == "openai":
                api_key = settings.OPENAI_API_KEY
{% endif %}
{% if cookiecutter.include_anthropic == "y" %}
            elif provider_name == "anthropic":
                api_key = settings.ANTHROPIC_API_KEY
{% endif %}
{% if cookiecutter.include_gemini == "y" %}
            elif provider_name == "gemini":
                api_key = settings.GEMINI_API_KEY
{% endif %}
            
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


# Convenience function with default provider selection
def get_ai_provider(
{% if cookiecutter.include_openai == "y" %}
    provider_name: str = "openai",
{% elif cookiecutter.include_anthropic == "y" %}
    provider_name: str = "anthropic",
{% elif cookiecutter.include_gemini == "y" %}
    provider_name: str = "gemini",
{% else %}
    provider_name: str = "",
{% endif %}
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> BaseAIProvider:
    """Get AI provider instance."""
    if not provider_name:
        available = list(AIProviderFactory.get_available_providers().keys())
        if not available:
            raise ValueError("No AI providers are configured. Please enable at least one provider in your cookiecutter configuration.")
        provider_name = available[0]  # Use first available provider
    
    return AIProviderFactory.create_provider(provider_name, api_key, model)
