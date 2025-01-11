import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
from anthropic import AsyncAnthropic

from nova.llm.claude import ClaudeClient, ClaudeResponse
from nova.rag.mcp import MCPBlock, MCPPayload


@pytest.fixture
def mock_anthropic():
    with patch("anthropic.AsyncAnthropic") as mock:
        yield mock


@pytest.fixture
def mock_response():
    response = MagicMock()
    response.content = [MagicMock(text="Test response")]
    response.usage = {"prompt_tokens": 10, "completion_tokens": 5}
    return response


@pytest.fixture
def test_payload():
    return MCPPayload(
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


@pytest.mark.asyncio
async def test_claude_client_complete(mock_anthropic, mock_response, test_payload):
    # Set up mock client
    mock_client = AsyncMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client
    
    # Create client
    client = ClaudeClient(api_key="test-key")
    
    # Complete prompt
    response = await client.complete(test_payload)
    
    # Verify response
    assert isinstance(response, ClaudeResponse)
    assert response.content == "Test response"
    assert response.metadata["model"] == "claude-2"
    assert response.usage == {"prompt_tokens": 10, "completion_tokens": 5}
    
    # Verify API call
    mock_client.messages.create.assert_called_once()
    call_args = mock_client.messages.create.call_args[1]
    assert call_args["model"] == "claude-2"
    assert call_args["max_tokens"] == 1000
    assert call_args["temperature"] == 0.7
    assert len(call_args["messages"]) == 1
    assert call_args["messages"][0]["role"] == "user"


@pytest.mark.asyncio
async def test_claude_client_stream(mock_anthropic, test_payload):
    # Set up mock stream
    mock_chunks = [
        MagicMock(content=[MagicMock(text="Chunk 1")]),
        MagicMock(content=[MagicMock(text="Chunk 2")]),
        MagicMock(content=[MagicMock(text="Chunk 3")])
    ]
    
    # Set up mock client
    mock_client = AsyncMock()
    mock_client.messages.create.return_value.__aiter__.return_value = mock_chunks
    mock_anthropic.return_value = mock_client
    
    # Create client
    client = ClaudeClient(api_key="test-key")
    
    # Stream response
    chunks = []
    async for chunk in await client.complete(test_payload, stream=True):
        chunks.append(chunk)
    
    # Verify chunks
    assert chunks == ["Chunk 1", "Chunk 2", "Chunk 3"]
    
    # Verify API call
    mock_client.messages.create.assert_called_once()
    assert mock_client.messages.create.call_args[1]["stream"] is True


@pytest.mark.asyncio
async def test_claude_client_retry(mock_anthropic, mock_response, test_payload):
    # Set up mock client to fail once then succeed
    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = [
        anthropic.APIError(
            message="Rate limit exceeded",
            status_code=429,
            body={}
        ),
        mock_response
    ]
    mock_anthropic.return_value = mock_client
    
    # Create client
    client = ClaudeClient(api_key="test-key")
    
    # Complete prompt (should retry once)
    response = await client.complete(test_payload)
    
    # Verify response after retry
    assert isinstance(response, ClaudeResponse)
    assert response.content == "Test response"
    
    # Verify API was called twice
    assert mock_client.messages.create.call_count == 2 