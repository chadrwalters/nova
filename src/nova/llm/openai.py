"""Client for interacting with OpenAI API."""

from typing import AsyncGenerator, Optional, Union
import asyncio

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice

from nova.types import MCPPayload, LLMResponse
from nova.llm.base import LLMClient


class OpenAIClient(LLMClient):
    """Client for interacting with OpenAI API."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ):
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
    async def complete(
        self,
        payload: MCPPayload,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """Complete a prompt with OpenAI."""
        # Format payload for OpenAI
        messages = self._format_payload(payload)
        
        try:
            if stream:
                return self._stream_response(messages, **kwargs)
            else:
                return await self._complete_response(messages, **kwargs)
        except Exception as e:
            # Re-raise API errors
            raise
            
    async def _complete_response(
        self,
        messages: list,
        **kwargs
    ) -> LLMResponse:
        """Get complete response from OpenAI."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            **kwargs
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            metadata={"model": self.model},
            usage=response.usage
        )
        
    async def _stream_response(
        self,
        messages: list,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI."""
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
                
    def _format_payload(self, payload: MCPPayload) -> list:
        """Format MCP payload for OpenAI."""
        messages = []
        
        # Add system instructions
        messages.append({
            "role": "system",
            "content": payload.system_instructions
        })
        
        # Add developer instructions
        messages.append({
            "role": "system",
            "content": payload.developer_instructions
        })
        
        # Add context blocks
        if payload.context_blocks:
            context = "\n\n".join(
                f"<context>\n{block.content}\n</context>"
                for block in payload.context_blocks
            )
            messages.append({
                "role": "user",
                "content": context
            })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": payload.user_message
        })
        
        return messages 