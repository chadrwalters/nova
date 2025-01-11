"""Client for interacting with Claude API."""

from typing import AsyncGenerator, Optional, Union
import asyncio

from anthropic import AsyncAnthropic, RateLimitError, APIError

from nova.types import MCPPayload, LLMResponse
from nova.llm.base import LLMClient


class ClaudeClient(LLMClient):
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
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """Complete a prompt with Claude."""
        # Format payload for Claude
        prompt = self._format_payload(payload)
        
        try:
            if stream:
                return self._stream_response(prompt, **kwargs)
            else:
                return await self._complete_response(prompt, **kwargs)
        except RateLimitError:
            # Handle rate limits with retry
            await asyncio.sleep(1)  # Basic retry after 1s
            return await self.complete(payload, stream, **kwargs)
        except APIError as e:
            # Re-raise other API errors
            raise
            
    async def _complete_response(
        self,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Get complete response from Claude."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        
        return LLMResponse(
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
        
        # Add system instructions
        formatted.append(f"\n\nHuman: <s>\n{payload.system_instructions}\n</s>")
        
        # Add developer instructions
        formatted.append(f"\n\nHuman: <s>\n{payload.developer_instructions}\n</s>")
        
        # Add context blocks
        for block in payload.context_blocks:
            formatted.append(f"\n\nHuman: <context>\n{block.content}\n</context>")
        
        # Add user message
        formatted.append(f"\n\nHuman: {payload.user_message}")
        
        # Add assistant prompt
        formatted.append("\n\nAssistant:")
        return "".join(formatted) 