import asyncio
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, Optional, Union

import anthropic
from anthropic import AsyncAnthropic

from nova.rag.mcp import MCPPayload


@dataclass
class ClaudeResponse:
    """Response from Claude API."""
    content: str
    metadata: Dict
    usage: Dict


class ClaudeClient:
    """Client for interacting with Claude API."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-2",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ):
        """Initialize Claude client."""
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
    async def complete(
        self,
        payload: MCPPayload,
        stream: bool = False,
        **kwargs
    ) -> Union[ClaudeResponse, AsyncGenerator[str, None]]:
        """Complete a prompt with Claude."""
        # Format payload for Claude
        prompt = self._format_payload(payload)
        
        try:
            if stream:
                return self._stream_response(prompt, **kwargs)
            else:
                return await self._complete_response(prompt, **kwargs)
        except anthropic.APIError as e:
            # Handle rate limits and retries
            if e.status_code == 429:
                await asyncio.sleep(1)  # Basic retry after 1s
                return await self.complete(payload, stream, **kwargs)
            raise
            
    async def _complete_response(
        self,
        prompt: str,
        **kwargs
    ) -> ClaudeResponse:
        """Get complete response from Claude."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        
        return ClaudeResponse(
            content=response.content[0].text,
            metadata={"model": self.model},
            usage=response.usage
        )
        
    async def _stream_response(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response from Claude."""
        stream = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.content:
                yield chunk.content[0].text
                
    def _format_payload(self, payload: MCPPayload) -> str:
        """Format MCP payload for Claude."""
        formatted = []
        
        for block in payload.blocks:
            if block.type == "system":
                formatted.append(f"{anthropic.HUMAN_PROMPT} <system>\n{block.content}\n</system>")
            elif block.type == "context":
                formatted.append(f"{anthropic.HUMAN_PROMPT} <context>\n{block.content}\n</context>")
            elif block.type == "user":
                formatted.append(f"{anthropic.HUMAN_PROMPT} {block.content}")
                
        formatted.append(f"{anthropic.ASSISTANT_PROMPT}")
        return "\n\n".join(formatted) 