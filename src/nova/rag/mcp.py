from dataclasses import dataclass
from typing import List, Optional

from nova.rag.orchestrator import QueryResult


@dataclass
class MCPBlock:
    """A block of content in the MCP format."""
    type: str
    content: str
    metadata: dict


@dataclass
class MCPPayload:
    """A complete MCP payload for Claude."""
    blocks: List[MCPBlock]
    query: str
    metadata: dict


class MCPBuilder:
    """Builds MCP payloads for Claude."""
    
    @staticmethod
    def build_payload(
        query: str,
        query_result: QueryResult,
        system_prompt: Optional[str] = None
    ) -> MCPPayload:
        """Build an MCP payload from a query and its results."""
        blocks = []
        
        # Add system prompt if provided
        if system_prompt:
            blocks.append(MCPBlock(
                type="system",
                content=system_prompt,
                metadata={}
            ))
            
        # Add context block
        if query_result.context:
            blocks.append(MCPBlock(
                type="context",
                content=query_result.context,
                metadata={
                    "sources": query_result.sources
                }
            ))
            
        # Add query block
        blocks.append(MCPBlock(
            type="user",
            content=query,
            metadata={}
        ))
        
        return MCPPayload(
            blocks=blocks,
            query=query,
            metadata=query_result.metadata
        )
        
    @staticmethod
    def format_payload(payload: MCPPayload) -> str:
        """Format an MCP payload for Claude."""
        formatted = []
        
        for block in payload.blocks:
            if block.type == "system":
                formatted.append(f"<system>\n{block.content}\n</system>")
            elif block.type == "context":
                formatted.append(f"<context>\n{block.content}\n</context>")
            elif block.type == "user":
                formatted.append(f"Human: {block.content}")
                
        formatted.append("Assistant: ")
        return "\n\n".join(formatted) 