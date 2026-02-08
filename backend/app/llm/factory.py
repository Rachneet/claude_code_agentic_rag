from typing import Optional

from app.config import settings
from app.llm.base import LLMProvider

_provider_instance: Optional[LLMProvider] = None


def get_provider() -> LLMProvider:
    """Return a singleton LLM provider based on LLM_PROVIDER env var."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_name = settings.llm_provider.lower()

    if provider_name == "huggingface":
        from app.llm.huggingface import HuggingFaceProvider
        _provider_instance = HuggingFaceProvider()
    elif provider_name == "gemini":
        from app.llm.gemini import GeminiProvider
        _provider_instance = GeminiProvider()
    elif provider_name == "openrouter":
        from app.llm.openrouter import OpenRouterProvider
        _provider_instance = OpenRouterProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}. Use 'huggingface', 'gemini', or 'openrouter'.")

    return _provider_instance
