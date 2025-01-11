"""Base interface for LLM clients."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Union

from nova.types import MCPPayload, LLMResponse


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def complete(
        self,
        payload: MCPPayload,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """Complete a prompt with the LLM.
        
        Args:
            payload: The MCP payload to send to the LLM
            stream: Whether to stream the response
            **kwargs: Additional model-specific arguments
            
        Returns:
            Either a complete response or an async generator for streaming
        """
        pass
    
    @abstractmethod
    def _format_payload(self, payload: MCPPayload) -> str:
        """Format MCP payload for the specific LLM.
        
        Args:
            payload: The MCP payload to format
            
        Returns:
            Formatted string for the LLM
        """
        pass 