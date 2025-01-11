"""Factory for creating LLM clients."""

from typing import Dict, Any

from nova.llm.base import LLMClient
from nova.llm.claude import ClaudeClient
from nova.llm.openai import OpenAIClient


def create_llm_client(config: Dict[str, Any]) -> LLMClient:
    """Create an LLM client based on configuration.
    
    Args:
        config: LLM configuration dictionary
        
    Returns:
        An instance of LLMClient
        
    Raises:
        ValueError: If provider is not supported
    """
    provider = config.get("provider", "openai")
    api_key = config.get("api_key")
    model = config.get("model")
    max_tokens = config.get("max_tokens", 1000)
    temperature = config.get("temperature", 0.7)
    
    if not api_key:
        raise ValueError("API key is required")
        
    if provider == "openai":
        return OpenAIClient(
            api_key=api_key,
            model=model or "gpt-3.5-turbo-16k",
            max_tokens=max_tokens,
            temperature=temperature
        )
    elif provider == "claude":
        return ClaudeClient(
            api_key=api_key,
            model=model or "claude-2",
            max_tokens=max_tokens,
            temperature=temperature
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}") 