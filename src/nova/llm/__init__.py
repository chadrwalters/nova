"""Nova LLM module."""

from typing import Optional, AsyncGenerator

import anthropic
from nova.types import MCPPayload


class ClaudeClient:
    """Client for Anthropic's Claude API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-2",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ):
        """Initialize Claude client."""
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    async def complete(
        self,
        mcp_payload: MCPPayload,
        stream: bool = False
    ) -> AsyncGenerator[str, None]:
        """Send MCP payload to Claude and get response."""
        # TODO: Implement completion
        raise NotImplementedError
    
    def _build_prompt(self, mcp_payload: MCPPayload) -> str:
        """Build prompt from MCP payload."""
        # TODO: Implement prompt building
        raise NotImplementedError
