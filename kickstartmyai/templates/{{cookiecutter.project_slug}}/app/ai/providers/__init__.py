"""AI providers package."""

from .base import BaseAIProvider, ChatMessage, ChatResponse

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

from .factory import AIProviderFactory, get_ai_provider

# Build __all__ list conditionally
__all__ = [
    "BaseAIProvider",
    "ChatMessage", 
    "ChatResponse",
{% if cookiecutter.include_openai == "y" %}
    "OpenAIProvider",
{% endif %}
{% if cookiecutter.include_anthropic == "y" %}
    "AnthropicProvider",
{% endif %}
{% if cookiecutter.include_gemini == "y" %}
    "GeminiProvider",
{% endif %}
    "AIProviderFactory",
    "get_ai_provider"
]
