from nova.rag.mcp import MCPBuilder, MCPBlock, MCPPayload
from nova.rag.orchestrator import QueryResult


def test_mcp_builder_basic():
    # Create test query result
    query_result = QueryResult(
        context="Test context",
        sources=["test.md"],
        metadata={"key": "value"}
    )
    
    # Build payload
    payload = MCPBuilder.build_payload(
        query="test query",
        query_result=query_result
    )
    
    # Verify structure
    assert isinstance(payload, MCPPayload)
    assert len(payload.blocks) == 2  # context + query
    assert payload.query == "test query"
    assert payload.metadata == {"key": "value"}
    
    # Verify blocks
    context_block = payload.blocks[0]
    assert context_block.type == "context"
    assert context_block.content == "Test context"
    assert context_block.metadata == {"sources": ["test.md"]}
    
    query_block = payload.blocks[1]
    assert query_block.type == "user"
    assert query_block.content == "test query"


def test_mcp_builder_with_system():
    # Create test query result
    query_result = QueryResult(
        context="Test context",
        sources=["test.md"],
        metadata={}
    )
    
    # Build payload with system prompt
    payload = MCPBuilder.build_payload(
        query="test query",
        query_result=query_result,
        system_prompt="System instructions"
    )
    
    # Verify structure
    assert len(payload.blocks) == 3  # system + context + query
    
    # Verify system block
    system_block = payload.blocks[0]
    assert system_block.type == "system"
    assert system_block.content == "System instructions"


def test_mcp_builder_empty_context():
    # Create test query result with empty context
    query_result = QueryResult(
        context="",
        sources=[],
        metadata={}
    )
    
    # Build payload
    payload = MCPBuilder.build_payload(
        query="test query",
        query_result=query_result
    )
    
    # Verify structure
    assert len(payload.blocks) == 1  # only query
    assert payload.blocks[0].type == "user"


def test_mcp_format_payload():
    # Create test payload
    payload = MCPPayload(
        blocks=[
            MCPBlock(
                type="system",
                content="System instructions",
                metadata={}
            ),
            MCPBlock(
                type="context",
                content="Test context",
                metadata={"sources": ["test.md"]}
            ),
            MCPBlock(
                type="user",
                content="test query",
                metadata={}
            )
        ],
        query="test query",
        metadata={}
    )
    
    # Format payload
    formatted = MCPBuilder.format_payload(payload)
    
    # Verify format
    expected = (
        "<system>\nSystem instructions\n</system>\n\n"
        "<context>\nTest context\n</context>\n\n"
        "Human: test query\n\n"
        "Assistant: "
    )
    assert formatted == expected 